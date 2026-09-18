import rclpy

from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid

class MapPublisher(Node):

    def __init__(self):
        super().__init__('map_publisher')

        self.declare_parameter('map_type', 'simple')
        self.map_type = self.get_parameter('map_type').value


        self.pub = self.create_publisher(
            OccupancyGrid,
            '/map',
            10
        )

        self.timer = self.create_timer(
            1.0,
            self.publish_map
        )


    # simple map with a block obstacle in the middle
    def build_simple_map(self):
        width = 20
        height = 20

        grid = [0] * (width * height)

        for y in range(5, 10):
            for x in range(8, 12):
                grid[y * width + x] = 100

        return grid
    
    # narrow map with a wall and a gap
    def build_narrow_map(self):
        width = 20
        height = 20

        grid = [0] * (width * height)

        for x in range(width):
            grid[x] = 100
            grid[(height - 1) * width + x] = 100
        for y in range(height):
            grid[y * width] = 100
            grid[y * width + width - 1] = 100
        for y in range(1, 19):
            grid[y * width + 10] = 100

                
        for y in range(7, 13):
            grid[y * width + 10] = 0    


        return grid

    # maze map with multiple walls and gaps
    def build_maze_map(self):
        width = 20
        height = 20

        grid = [0] * (width * height)

        for x in range(width):
            grid[x] = 100
            grid[(height - 1) * width + x] = 100
        for y in range(height):
            grid[y * width] = 100
            grid[y * width + width - 1] = 100
        for y in range(1, 15):
            grid[y * width + 5] = 100
        for y in range(5, 19):
            grid[y * width + 10] = 100
        for y in range(1, 15):
            grid[y * width + 15] = 100
        
        grid[4 * width + 5] = 0
        grid[5 * width + 5] = 0
        grid[10 * width + 10] = 0
        grid[11 * width + 10] = 0
        grid[7 * width + 15] = 0
        grid[8 * width + 15] = 0

        return grid


    def publish_map(self):

        msg = OccupancyGrid()

        msg.header.frame_id = "map"

        msg.info.resolution = 0.25
        msg.info.width = 20
        msg.info.height = 20

        msg.info.origin.position.x = 0.0
        msg.info.origin.position.y = 0.0

        if self.map_type == "simple":
            grid = self.build_simple_map() 
        elif self.map_type == "narrow":
            grid = self.build_narrow_map()
        elif self.map_type == "maze":
            grid = self.build_maze_map()
        else:
            self.get_logger().warn(
                f'Unknown map type "{self.map_type}". Using simple map.'
            )
            grid = self.build_simple_map()

        msg.data = grid

        self.pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)

    node = MapPublisher()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == '__main__':
    main()
