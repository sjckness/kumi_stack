#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from std_msgs.msg import Bool, String
import csv
import math
from pathlib import Path
from ament_index_python.packages import get_package_share_directory


GAIT_TO_CSV = {
    'walk': 'demo_flip_500.csv',
    'frontflip': 'demo_flip_500.csv',
    'backwalk': 'backflip.csv',
    'backflip': 'backflip.csv',
    'accovacciato': 'accovacciato.csv',
}

GAIT_EXECUTION_MODE = {
    'walk': 'loop',
    'frontflip': 'single',
    'backwalk': 'loop',
    'backflip': 'single',
    'accovacciato': 'single',
}


class CSVJointTrajectory(Node):
    def __init__(self, csv_path: str | None = None):
        super().__init__('csv_joint_trajectory')
        self.walk_enabled = True

        self.declare_parameter(
            'trajectory_topic',
            '/kumi/multi_joint_trajectory_controller/joint_trajectory'
        )
        trajectory_topic = str(self.get_parameter('trajectory_topic').value)

        # Publisher
        self.pub = self.create_publisher(
            JointTrajectory,
            trajectory_topic,
            10
        )
        self.enable_sub = self.create_subscription(
            Bool,
            'kumi_seq_traj_controller/enabled',
            self.enable_callback,
            10
        )
        self.gait_sub = self.create_subscription(
            String,
            'kumi_seq_traj_controller/gait',
            self.gait_callback,
            10
        )

        # Joint names
        self.joint_names = [
            'front_sh', 'front_ank_y', 'front_ank_z',
            'rear_sh', 'rear_ank_y', 'rear_ank_z'
        ]

        self.frequency = 10 #hz

        pkg_share = Path(get_package_share_directory('kumi_control'))
        self.gait_csv_map = {
            gait: pkg_share / 'resource' / relative_path
            for gait, relative_path in GAIT_TO_CSV.items()
        }
        self.current_gait = 'walk'
        self.current_mode = GAIT_EXECUTION_MODE[self.current_gait]
        default_csv = self.gait_csv_map[self.current_gait]

        # consenti override via parametro ROS o argomento esplicito
        self.declare_parameter('csv_path', str(default_csv))
        param_csv = Path(self.get_parameter('csv_path').value)
        csv_path = Path(csv_path) if csv_path else param_csv

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV non trovato: {csv_path}")

        self.positions_list = self.load_csv_in_radians(csv_path)
        self.current_csv_path = csv_path

        #elf.get_logger().info(f"Pubblico traiettorie su: {trajectory_topic}")
        self.get_logger().info(f"Gait disponibili: {list(self.gait_csv_map.keys())}")
        self.get_logger().info(f"Gait iniziale: {self.current_gait} -> {self.current_csv_path}")
        self.get_logger().info("Walk controller enabled at startup.")
        self.get_logger().info(f"Caricate {len(self.positions_list)} pose dal CSV (in radianti).")

        self.index = 0

        # Timer che pubblica solo quando il BT abilita la camminata.
        self.timer = self.create_timer(1/self.frequency, self.timer_callback)

    def load_csv_in_radians(self, path):
        positions = []
        with open(path, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                degrees = [float(v) for v in row]
                radians = [math.radians(v) for v in degrees]
                positions.append(radians)
        return positions

    def timer_callback(self):
        if not self.walk_enabled:
            return

        self.send_next_point()

    def enable_callback(self, msg: Bool):
        if self.walk_enabled == msg.data:
            return

        self.walk_enabled = msg.data
        state = 'enabled' if self.walk_enabled else 'disabled'
        if self.walk_enabled:
            self.get_logger().info(
                f"Walk controller {state}. Resuming from CSV index {self.index}."
            )
        else:
            self.get_logger().info(
                f"Walk controller {state}. Pausing at CSV index {self.index}."
            )

    def gait_callback(self, msg: String):
        requested_gait = msg.data.strip()
        csv_path = self.gait_csv_map.get(requested_gait)

        if csv_path is None:
            self.get_logger().warn(
                f"Gait '{requested_gait}' non configurato. "
                f"Disponibili: {list(self.gait_csv_map.keys())}"
            )
            return

        if requested_gait == self.current_gait:
            return

        if not csv_path.exists():
            self.get_logger().warn(f"CSV per gait '{requested_gait}' non trovato: {csv_path}")
            return

        self.positions_list = self.load_csv_in_radians(csv_path)
        self.current_gait = requested_gait
        self.current_mode = GAIT_EXECUTION_MODE[requested_gait]
        self.current_csv_path = csv_path
        self.index = 0
        self.get_logger().info(
            f"Gait cambiato in '{self.current_gait}' ({self.current_mode}) usando {self.current_csv_path}"
        )

    def send_next_point(self):
        if self.index >= len(self.positions_list):
            if self.current_mode == 'loop':
                self.index = 0
            else:
                self.walk_enabled = False
                self.index = len(self.positions_list)
                self.get_logger().info(
                    f"Gait '{self.current_gait}' completato. Walk controller disabled."
                )
                return

        positions = self.positions_list[self.index]

        traj = JointTrajectory()
        traj.joint_names = self.joint_names

        point = JointTrajectoryPoint()
        point.positions = positions

        #tempo target per il controller
        point.time_from_start = Duration(sec=0, nanosec=20_000_000)

        traj.points.append(point)

        self.pub.publish(traj)
        #self.get_logger().info(f"[{self.index}] inviato punto: {positions}")

        self.index += 1


def main(args=None):
    rclpy.init(args=args)

    node = CSVJointTrajectory()
    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
