import subprocess
import threading
import re

import rclpy

from rclpy.node import Node

from geometry_msgs.msg import PoseStamped


class GazeboPoseBridge(Node):

    def __init__(self):
        super().__init__('gazebo_pose_bridge')

        self.declare_parameter('world_name', 'simple_world')

        self.declare_parameter('robot_name', 'bruno')

        self.world_name = self.get_parameter('world_name').value

        self.robot_name = self.get_parameter('robot_name').value

        self.pub = self.create_publisher(PoseStamped,'/robot_pose',10)

        self.thread = threading.Thread(target=self._read_gz_pose,daemon=True)

        self.thread.start()

        self.get_logger().info(f'Listening to Gazebo poses for {self.robot_name}')

    def _read_gz_pose(self):

        topic = (f'/world/{self.world_name}/dynamic_pose/info')

        cmd = ['gz','topic','-e','-t',topic]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        current_name = None

        x = y = z = 0.0
        qx = qy = qz = qw = 0.0

        for line in process.stdout:
            line = line.strip()

            if line.startswith('name:'):

                current_name = (
                    line.split('"')[1]
                    if '"' in line
                    else None
                )

            if current_name != self.robot_name:
                continue

            if line.startswith('x:'):
                value = float(line.split(':')[1].strip())

                if qx == qy == qz == qw == 0.0:
                    x = value

            elif line.startswith('y:'):
                value = float(line.split(':')[1].strip())

                if qx == qy == qz == qw == 0.0:
                    y = value

            elif line.startswith('z:'):
                value = float(line.split(':')[1].strip())

                if qx == qy == qz == qw == 0.0:
                    z = value
                else:
                    qz = value

            elif line.startswith('w:'):

                qw = float(
                    line.split(':')[1].strip()
                )

                msg = PoseStamped()

                msg.header.stamp = (
                    self.get_clock()
                    .now()
                    .to_msg()
                )

                msg.header.frame_id = 'map'

                msg.pose.position.x = x
                msg.pose.position.y = y
                msg.pose.position.z = z

                msg.pose.orientation.x = qx
                msg.pose.orientation.y = qy
                msg.pose.orientation.z = qz
                msg.pose.orientation.w = qw

                self.pub.publish(msg)


def main(args=None):

    rclpy.init(args=args)

    node = GazeboPoseBridge()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
