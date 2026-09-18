import numpy as np

import rclpy

from rclpy.node import Node

from sensor_msgs.msg import Image
from sensor_msgs.msg import CameraInfo
from nav_msgs.msg import OccupancyGrid

from cv_bridge import CvBridge


class DepthToOccupancyGrid(Node):

    def __init__(self):

        super().__init__('depth_to_occupancy_grid')

        self.bridge = CvBridge()

        self.depth_sub = self.create_subscription(
            Image,
            '/bruno/camera/rear_left/depth/image_raw',     # address the correct topic name for your depth camera
            self.depth_callback,
            10
        )

        self.camera_info = None
        self.info_sub = self.create_subscription(
            CameraInfo,
            '/bruno/camera/rear_left/depth/camera_info',  # address the correct topic name for your depth camera
            self.camera_info_callback,
            10
        )

        self.map_pub = self.create_publisher(
            OccupancyGrid,
            '/map',
            10
        )

    def depth_callback(self, msg):
        # Convert depth image to numpy array

        depth = self.bridge.imgmsg_to_cv2(
            msg,
            desired_encoding='32FC1'
        )

        # dimension of the grid map
        grid_width = 200
        grid_height = 200

        resolution = 0.05  # meters per cell

        map_half_size = (grid_width * resolution) / 2.0  # half size of the map in meters

        grid = np.zeros(
            (grid_height, grid_width),
            dtype=np.int8
        )

        # very simple prototype

        obstacle_mask = (
            np.isfinite(depth)
            &
            (depth < 2.0)
            &
            (depth > 0.0)
        )

        """
        ys, xs = np.where(obstacle_mask)

        for x, y in zip(xs, ys):

            gx = int(x / depth.shape[1] * grid_width)
            gy = int(y / depth.shape[0] * grid_height)

            grid[gy, gx] = 100
        """

        if self.camera_info is None:
            self.get_logger().warn('No camera info received yet.')
            return

        fx = self.camera_info.k[0]  # focal length in x in pixels
        fy = self.camera_info.k[4]  # focal length in y in pixels

        cx = self.camera_info.k[2]  # principal point x-coordinate in pixels
        cy = self.camera_info.k[5]  # principal point y-coordinate in pixels

        for v in range(0, depth.shape[0], 4):
            for u in range(0, depth.shape[1], 4):

                z = depth[v, u]

                if not np.isfinite(z):
                    continue

                if z <= 0.1 or z >= 5.0:
                    continue

                x_cam = (u - cx) * z / fx
                y_cam = (v - cy) * z / fy

                # ignore points too high or too low
                if abs(y_cam) > 1.0:
                    continue

                map_x = z
                map_y = -x_cam

                gx = int((map_x + map_half_size) / resolution)
                gy = int((map_y + map_half_size) / resolution)

                if (
                    0 <= gx < grid_width
                    and
                    0 <= gy < grid_height
                ):
                    for dx in range(-1, 2):
                        for dy in range(-1, 2):
                            if (
                                0 <= gx + dx < grid_width
                                and
                                0 <= gy + dy < grid_height
                            ):
                                grid[gy + dy, gx + dx] = 100

        map_msg = OccupancyGrid()

        map_msg.header.stamp = self.get_clock().now().to_msg()
        map_msg.header.frame_id = 'map'

        map_msg.info.resolution = resolution

        map_msg.info.width = grid_width
        map_msg.info.height = grid_height

        map_msg.info.origin.position.x = -map_half_size
        map_msg.info.origin.position.y = -map_half_size
        map_msg.info.origin.position.z = 0.0

        map_msg.info.origin.orientation.x = 0.0
        map_msg.info.origin.orientation.y = 0.0
        map_msg.info.origin.orientation.z = 0.0
        map_msg.info.origin.orientation.w = 1.0

        map_msg.data = grid.flatten().tolist()

        self.map_pub.publish(map_msg)

    def camera_info_callback(self, msg):
        self.camera_info = msg


def main(args=None):

    rclpy.init(args=args)

    node = DepthToOccupancyGrid()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()