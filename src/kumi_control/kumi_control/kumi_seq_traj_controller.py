#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, String
import csv
import math
from pathlib import Path
from ament_index_python.packages import get_package_share_directory


GAIT_TO_CSV = {
    "walk": "flip.csv",
    "flip": "flip.csv",
    "flip_sx": "flip_sx.csv",
    "flip_dx": "flip_dx.csv",
    "bwalk": "bflip.csv",
    "bflip": "bflip.csv",
    "bflip_sx": "bflip_sx.csv",
    "bflip_dx": "bflip_dx.csv",
    "accovacciato": "rac.csv",
}

GAIT_EXECUTION_MODE = {
    "walk": "loop",
    "flip": "single",
    "flip_sx": "single",
    "flip_dx": "single",
    "bwalk": "loop",
    "bflip": "single",
    "bflip_sx": "single",
    "bflip_dx": "single",
    "accovacciato": "single",
}


class CSVJointTrajectory(Node):
    def __init__(self, csv_path: str | None = None):
        super().__init__("csv_joint_trajectory")
        self.walk_enabled = False
        self.pending_gait = None

        self.declare_parameter(
            "trajectory_topic",
            "/bruno/multi_joint_trajectory_controller/joint_trajectory",
        )
        self.declare_parameter(
            "enable_topic",
            "/bruno/kumi_seq_traj_controller/enabled",
        )
        self.declare_parameter(
            "gait_topic",
            "/bruno/kumi_seq_traj_controller/gait",
        )
        self.declare_parameter("use_isaac", False)
        self.declare_parameter("joint_commands_topic", "/kumi/joint_commands")

        trajectory_topic = str(self.get_parameter("trajectory_topic").value)
        enable_topic = str(self.get_parameter("enable_topic").value)
        gait_topic = str(self.get_parameter("gait_topic").value)
        self.use_isaac = bool(self.get_parameter("use_isaac").value)

        # Publisher — JointState per Isaac, JointTrajectory per Gazebo/ros2_control
        if self.use_isaac:
            joint_commands_topic = str(self.get_parameter("joint_commands_topic").value)
            self.pub = self.create_publisher(JointState, joint_commands_topic, 10)
            self.get_logger().info(f"Isaac mode: JointState su {joint_commands_topic}")
        else:
            self.pub = self.create_publisher(JointTrajectory, trajectory_topic, 10)
        self.enable_sub = self.create_subscription(
            Bool, enable_topic, self.enable_callback, 10
        )
        self.gait_sub = self.create_subscription(
            String, gait_topic, self.gait_callback, 10
        )

        # Joint names
        self.joint_names = [
            "front_sh",
            "front_ank_y",
            "front_ank_z",
            "rear_sh",
            "rear_ank_y",
            "rear_ank_z",
        ]

        self.frequency = 10  # hz

        pkg_share = Path(get_package_share_directory("kumi_control"))
        self.gait_csv_map = {
            gait: pkg_share / "moves" / relative_path
            for gait, relative_path in GAIT_TO_CSV.items()
        }
        self.current_gait = "walk"
        self.current_mode = GAIT_EXECUTION_MODE[self.current_gait]
        default_csv = self.gait_csv_map[self.current_gait]

        # consenti override via parametro ROS o argomento esplicito
        self.declare_parameter("csv_path", str(default_csv))
        param_csv = Path(self.get_parameter("csv_path").value)
        csv_path = Path(csv_path) if csv_path else param_csv

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV non trovato: {csv_path}")

        self.positions_list = self.load_csv_in_radians(csv_path)
        self.current_csv_path = csv_path

        # elf.get_logger().info(f"Pubblico traiettorie su: {trajectory_topic}")
        self.get_logger().info(f"Gait disponibili: {list(self.gait_csv_map.keys())}")
        self.get_logger().info(
            f"Gait iniziale: {self.current_gait} -> {self.current_csv_path}"
        )
        self.get_logger().info("Walk controller disabled at startup.")
        self.get_logger().info(
            f"Caricate {len(self.positions_list)} pose dal CSV (in radianti)."
        )

        self.index = 0

        # Timer che pubblica solo quando il BT abilita la camminata.
        self.timer = self.create_timer(1 / self.frequency, self.timer_callback)

    def load_csv_in_radians(self, path):
        positions = []
        with open(path, "r") as f:
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
        state = "enabled" if self.walk_enabled else "disabled"
        if self.walk_enabled:
            self.get_logger().info(
                f"Walk controller {state}. Resuming from CSV index {self.index}."
            )
        else:
            self.get_logger().info(
                f"Walk controller {state}. Pausing at CSV index {self.index}."
            )
            if self.pending_gait is not None:
                self._apply_pending_gait()

    def gait_callback(self, msg: String):
        requested_gait = msg.data.strip()
        csv_path = self.gait_csv_map.get(requested_gait)

        if csv_path is None:
            self.get_logger().warn(
                f"Gait '{requested_gait}' non configurato. "
                f"Disponibili: {list(self.gait_csv_map.keys())}"
            )
            return

        if not csv_path.exists():
            self.get_logger().warn(
                f"CSV per gait '{requested_gait}' non trovato: {csv_path}"
            )
            return

        if requested_gait == self.current_gait:
            if self.pending_gait is not None:
                self.get_logger().info(
                    f"Gait pending '{self.pending_gait}' annullato: richiesto di nuovo '{requested_gait}'."
                )
                self.pending_gait = None
            return

        if not self.walk_enabled:
            self._swap_gait(requested_gait, csv_path)
            return

        self.pending_gait = requested_gait
        self.get_logger().info(
            f"Gait '{requested_gait}' in coda: verrà applicato a fine passo."
        )

    def _swap_gait(self, gait: str, csv_path):
        self.positions_list = self.load_csv_in_radians(csv_path)
        self.current_gait = gait
        self.current_mode = GAIT_EXECUTION_MODE[gait]
        self.current_csv_path = csv_path
        self.index = 0
        self.pending_gait = None
        self.get_logger().info(
            f"Gait cambiato in '{self.current_gait}' ({self.current_mode}) usando {self.current_csv_path}"
        )

    def _apply_pending_gait(self):
        gait = self.pending_gait
        csv_path = self.gait_csv_map.get(gait) if gait else None
        if gait is None or csv_path is None or not csv_path.exists():
            self.pending_gait = None
            return
        self._swap_gait(gait, csv_path)

    def send_next_point(self):
        # Se siamo alla fine → applica pending o ricomincia da capo
        if self.index >= len(self.positions_list):
            if self.pending_gait is not None:
                self._apply_pending_gait()
            elif self.current_mode == "loop":
                self.index = 0
            else:
                self.walk_enabled = False
                self.index = len(self.positions_list)
                self.get_logger().info(
                    f"Gait '{self.current_gait}' completato. Walk controller disabled."
                )
                return

        positions = self.positions_list[self.index]

        if self.use_isaac:
            msg = JointState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.name = self.joint_names
            msg.position = positions
            self.pub.publish(msg)
        else:
            traj = JointTrajectory()
            traj.joint_names = self.joint_names
            point = JointTrajectoryPoint()
            point.positions = positions
            point.time_from_start = Duration(sec=0, nanosec=20_000_000)
            traj.points.append(point)
            self.pub.publish(traj)

        self.index += 1


def main(args=None):
    rclpy.init(args=args)

    node = CSVJointTrajectory()
    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
