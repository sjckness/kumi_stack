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

from kumi_path_planning.rrt import RRTPlanner, WorldOccupancyGrid


class RRTPlannerNode(RclpyNode):
    def __init__(self):
        super().__init__('rrt_planner_node')

        # ---- parameters (overridden by config/rrt_params.yaml at launch) ----
        self.declare_parameter('costmap_topic', '/map')
        self.declare_parameter('goal_topic', '/goal_pose')
        self.declare_parameter('path_topic', '/plan')
        self.declare_parameter('occupancy_threshold', 50)   # cost >= this => occupied
        self.declare_parameter('eps', 0.4)                   # m, target-direction step
        self.declare_parameter('b_length', 0.3)              # m, fixed stride length
        self.declare_parameter('n_samples', 500)             # heading candidates / iter
        self.declare_parameter('max_turn_angle_deg', 90.0)   # +/- per step
        self.declare_parameter('goal_tolerance', 0.3)        # m
        self.declare_parameter('max_iterations', 300)
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('robot_frame', 'base_link')

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

        # ---- state ----
        self.latest_map = None  # most recent OccupancyGrid message

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

    def _goal_callback(self, goal_msg: PoseStamped):
        if self.latest_map is None:
            self.get_logger().warn('No map received yet -- ignoring goal.')
            return

        pose = self._get_robot_pose()
        if pose is None:
            self.get_logger().warn('Could not look up robot pose via tf -- ignoring goal.')
            return
        start_x, start_y, start_yaw = pose

        goal_x = goal_msg.pose.position.x
        goal_y = goal_msg.pose.position.y

        occ_map = self._build_world_occupancy_grid(self.latest_map)

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
        self.get_logger().info(f'Published path with {len(path)} waypoints.')

    # ---- helpers -----------------------------------------------------

    def _get_robot_pose(self):
        try:
            tf = self.tf_buffer.lookup_transform(
                self.map_frame, self.robot_frame, Time())
            x = tf.transform.translation.x
            y = tf.transform.translation.y
            yaw = self._quaternion_to_yaw(tf.transform.rotation)
            return (x, y, yaw)
        except TransformException as ex:
            self.get_logger().warn(f'tf lookup failed: {ex}')
            return None

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

