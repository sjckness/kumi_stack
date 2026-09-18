import numpy as np

import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from yolo_msgs.msg import DetectionArray


class YoloToOccupancyGrid(Node):

    def __init__(self):

        super().__init__('yolo_to_occupancy_grid')

        self.create_subscription(DetectionArray, '/yolo/detections_3d', self.detections_callback, 10)

        self.map_pub = self.create_publisher(OccupancyGrid, '/map', 10)

        self.grid_width = 400
        self.grid_height = 400

        self.resolution = 0.05      # 20*20m grid

        self.origin_x = -10.0
        self.origin_y = -10.0


    def detections_callback(self, msg):

        grid = np.zeros((self.grid_height, self.grid_width), dtype=np.int8)

        for det in msg.detections:

            map_x = det.bbox3d.center.position.z
            map_y = det.bbox3d.center.position.x

            gx = int((map_x - self.origin_x) / self.resolution)
            gy = int((map_y - self.origin_y) / self.resolution)

            size_x = max(det.bbox3d.size.x, 0.2)
            size_y = max(det.bbox3d.size.y, 0.2)

            half_w = max(1, int(size_x/self.resolution/2))
            half_h = max(1, int(size_y/self.resolution/2))


            for dx in range(-half_w, half_w + 1):
                for dy in range(-half_h, half_h + 1):
                    nx = gx + dx
                    ny = gy + dy

                    if (0 <= nx < self.grid_width and 0 <= ny < self.grid_height):
                        grid[ny, nx] = 100

        map_msg = OccupancyGrid()

        map_msg.header.stamp = (self.get_clock().now().to_msg())

        map_msg.header.frame_id = "body"

        map_msg.info.resolution = self.resolution

        map_msg.info.width = self.grid_width
        map_msg.info.height = self.grid_height

        map_msg.info.origin.position.x = (self.origin_x)
        map_msg.info.origin.position.y = (self.origin_y)
        map_msg.info.origin.orientation.w = 1.0

        map_msg.data = (grid.flatten().tolist())

        self.map_pub.publish(map_msg)


def main(args=None):

    rclpy.init(args=args)

    node = YoloToOccupancyGrid()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == '__main__':

    main()