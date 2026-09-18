"""
ROS2 node wrapper around the RRT planner.

Subscribes:
  - occupancy grid (nav_msgs/OccupancyGrid)   on `costmap_topic`
  - goal pose      (geometry_msgs/PoseStamped) on `goal_topic`
    (this is the topic RViz's "2D Goal Pose" tool publishes to by default)

Publishes:
  - planned path (nav_msgs/Path) on `path_topic`, with orientation set at
    each waypoint from the heading the planner tracked at that node.

The robot's current pose AND heading are looked up via tf2 (map ->
base_link), so this node does not need odometry directly -- it relies on
whatever already publishes that transform (e.g. your localization stack).

This file should stay "dumb": message parsing, coordinate conversion, and
pub/sub plumbing only. All actual planning logic lives in rrt.py.
"""

import math

import numpy as np
import rclpy
from rclpy.node import Node as RclpyNode
from rclpy.time import Time
from nav_msgs.msg import OccupancyGrid, Path
from geometry_msgs.msg import PoseStamped
import tf2_ros
from tf2_ros import TransformException
from geometry_msgs.msg import PoseStamped
#from tf_transformations import euler_from_quaternion

import time

from kumi_path_planning.rrt import RRTPlanner, WorldOccupancyGrid

def quaternion_to_yaw(x, y, z, w):
    return math.atan2(
        2.0 * (w * z + x * y),
        1.0 - 2.0 * (y * y + z * z)
    )


class RRTPlannerNode(RclpyNode):
    def __init__(self):
        super().__init__('rrt_planner_node')

        # ---- parameters (overridden by config/rrt_params.yaml at launch) ----
        self.declare_parameter('costmap_topic', '/map')
        self.declare_parameter('goal_topic', '/goal_pose')
        self.declare_parameter('path_topic', '/plan')
        self.declare_parameter('occupancy_threshold', 50)    # cost >= this => occupied
        self.declare_parameter('eps', 0.4)                   # m, target-direction step
        self.declare_parameter('b_length', 0.3)              # m, fixed stride length
        self.declare_parameter('n_samples', 2000)            # heading candidates / iter
        self.declare_parameter('max_turn_angle_deg', 90.0)   # +/- per step
        self.declare_parameter('goal_tolerance', 0.3)        # m
        self.declare_parameter('max_iterations', 2000)
        self.declare_parameter('map_frame', 'body')
        self.declare_parameter('robot_frame', 'body')

        self.declare_parameter('world_name', 'simple_world')  # name of the world in Gazebo, used to get the robot pose from Pose_V

        self.costmap_topic = self.get_parameter('costmap_topic').value
        self.goal_topic = self.get_parameter('goal_topic').value
        self.path_topic = self.get_parameter('path_topic').value
        self.occupancy_threshold = self.get_parameter('occupancy_threshold').value
        self.eps = self.get_parameter('eps').value
        self.b_length = self.get_parameter('b_length').value
        self.n_samples = self.get_parameter('n_samples').value
        self.max_turn_angle = math.radians(self.get_parameter('max_turn_angle_deg').value)
        self.goal_tolerance = self.get_parameter('goal_tolerance').value
        self.max_iterations = self.get_parameter('max_iterations').value
        self.map_frame = self.get_parameter('map_frame').value
        self.robot_frame = self.get_parameter('robot_frame').value
        self.world_name = self.get_parameter('world_name').value

        # ---- robot pose variables (got from tf later) ----
        self.robot_x = None
        self.robot_y = None
        self.robot_yaw = None
        
        self.pose_sub = self.create_subscription(
            PoseStamped, '/robot_pose', self._pose_callback, 10)


        # ---- state ----
        self.latest_map = None  # most recent OccupancyGrid message
        self.current_path = None  # most recent planned path (list of (x, y, heading, maneuver_angle) tuples)

        self.replanning = False  # flag to indicate if replanning is in progress


        # ---- tf2, for "where am I and which way am I facing" ----
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # ---- pub/sub ----
        self.map_sub = self.create_subscription(
            OccupancyGrid, self.costmap_topic, self._map_callback, 10)
        self.goal_sub = self.create_subscription(
            PoseStamped, self.goal_topic, self._goal_callback, 10)
        self.path_pub = self.create_publisher(Path, self.path_topic, 10)


        self.get_logger().info(
            f'RRT planner ready. Listening for goals on "{self.goal_topic}", '
            f'map on "{self.costmap_topic}", publishing paths on "{self.path_topic}".'
        )

    # ---- callbacks -------------------------------------------------

    def _map_callback(self, msg: OccupancyGrid):
        self.latest_map = msg

        if self.current_path is not None:
            self.check_current_path()

    def _pose_callback(self, msg: PoseStamped):
        # Find the pose of the robot in the PoseStamped message
        self.robot_x = msg.pose.position.x
        self.robot_y = msg.pose.position.y

        self.robot_yaw = quaternion_to_yaw(
            msg.pose.orientation.x,     # qx
            msg.pose.orientation.y,     # qy
            msg.pose.orientation.z,     # qz
            msg.pose.orientation.w      # qw
            )
        

    def _goal_callback(self, goal_msg: PoseStamped):

        start_time = time.perf_counter()    # start time needed to path plan 

        self.last_goal = goal_msg
        if self.latest_map is None:
            self.get_logger().warn('No map received yet -- ignoring goal.')
            return

        pose = self._get_robot_pose()
        if pose is None:
            self.get_logger().warn('Robot pose not available.')
            return
        
        start_x, start_y, start_yaw = pose

        
        """
        # temporary start pose for testing
        start_x = 0
        start_y = 0
        start_yaw = 0.0
        """
        
        goal_x = goal_msg.pose.position.x
        goal_y = goal_msg.pose.position.y

        self.get_logger().info(
            f'Planning from ({start_x:.2f}, {start_y:.2f}) '
            f'to ({goal_msg.pose.position.x:.2f}, {goal_msg.pose.position.y:.2f})'
        )

        occ_map = self._build_world_occupancy_grid(self.latest_map)

        self.get_logger().info(
            f"Start occupied: {occ_map.is_occupied(start_x, start_y)}"
        )

        self.get_logger().info(
            f"Goal occupied: {occ_map.is_occupied(goal_x, goal_y)}"
        )

        planner = RRTPlanner(
            occ_map=occ_map,
            eps=self.eps,
            b_length=self.b_length,
            n_samples=self.n_samples,
            max_turn_angle=self.max_turn_angle,
            goal_tolerance=self.goal_tolerance,
            max_iterations=self.max_iterations,
        )

        path = planner.plan((start_x, start_y), (goal_x, goal_y), start_heading=start_yaw)

        if path is None:
            self.get_logger().warn('RRT failed to find a path to the goal.')
            return

        path_msg = self._build_path_msg(path)
        self.path_pub.publish(path_msg)

        self.current_path = path_msg

        end_time = time.perf_counter()      # end time needed to path plan

        planning_time = end_time - start_time  # total time taken to path plan

        # compute total path length (using Euclidean distance between waypoints)
        path_length = 0.0
        for i in range(1, len(path)):
            x1, y1, _, _ = path[i - 1]
            x2, y2, _, _ = path[i]
            path_length += np.hypot(x2 - x1, y2 - y1)

        # goal error (distance from the last waypoint to the goal)
        goal_error_x = abs(path[-1][0] - goal_x)
        goal_error_y = abs(path[-1][1] - goal_y)
        goal_error = np.hypot(goal_error_x, goal_error_y)

        self.get_logger().info(
            f'Published path with {len(path)} waypoints. \n'
            f'Path planning time: {planning_time:.3f} s\n'
            f'Total path length: {path_length:.3f} m\n'
            f'Goal error: {goal_error:.3f}'
            )
        

    # ---- helpers -----------------------------------------------------

    def _get_robot_pose(self):
        if self.robot_x is None:
            self.get_logger().warn('Robot pose not available yet.')
            return None
        return (self.robot_x, self.robot_y, self.robot_yaw)
        

    def _build_world_occupancy_grid(self, msg: OccupancyGrid):
        """OccupancyGrid.data is 0-100 (occupancy probability) or -1 (unknown).
        This collapses it to a binary grid for the collision check. Unknown
        cells are treated as occupied -- see the earlier discussion on why
        that's the safer default; change here if you want the opposite."""
        data = np.array(msg.data, dtype=np.int16).reshape(
            msg.info.height, msg.info.width)
        binary = np.where(
            (data >= self.occupancy_threshold) | (data == -1), 1, 0)
        

        return WorldOccupancyGrid(
            binary_grid=binary,
            resolution=msg.info.resolution,
            origin_x=msg.info.origin.position.x,
            origin_y=msg.info.origin.position.y,
        )
    

    def _build_path_msg(self, path):
        msg = Path()
        msg.header.frame_id = self.map_frame
        msg.header.stamp = self.get_clock().now().to_msg()
        for x, y, heading, _maneuver_angle in path:
            pose = PoseStamped()
            pose.header = msg.header
            pose.pose.position.x = x
            pose.pose.position.y = y
            qx, qy, qz, qw = self._yaw_to_quaternion(heading)
            pose.pose.orientation.x = qx
            pose.pose.orientation.y = qy
            pose.pose.orientation.z = qz
            pose.pose.orientation.w = qw
            msg.poses.append(pose)
        return msg

    @staticmethod
    def _yaw_to_quaternion(yaw):
        return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))  # x, y, z, w

    @staticmethod
    def _quaternion_to_yaw(q):
        return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))

    # to verify the planner actually receives the map
    def map_callback(self, msg):
        self.get_logger().info(
            f"Received map: {msg.info.width}x{msg.info.height}"
        )

        self.map = msg
        if self.map is not None:
            self.check_current_path()


    def check_current_path(self):
        """
        Checks if the current path is still valid given the latest occupancy grid.
        If the path is blocked, it triggers replanning.
        """

        if self.current_path is None:       # is there already a path?
            return
        if self.replanning:                 # is replanning already in progress?
            return

        occ_map = self._build_world_occupancy_grid(self.latest_map)

        for pose_stamped in self.current_path.poses:
            x = pose_stamped.pose.position.x
            y = pose_stamped.pose.position.y

            if occ_map.is_occupied(x, y):
                self.get_logger().warn(
                    f"Path blocked at ({x:.2f}, {y:.2f}). Replanning."
                )

                if self.last_goal is not None:
                    self.replanning = True

                    try:
                        self._goal_callback(self.last_goal)
                    finally:
                        self.replanning = False
                
                return

def main(args=None):
    rclpy.init(args=args)
    node = RRTPlannerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

