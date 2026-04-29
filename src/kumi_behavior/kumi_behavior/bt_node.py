import rclpy
from rclpy.node import Node
import py_trees
from std_msgs.msg import Bool, Int32, String
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory

from kumi_behavior.tree import create_tree


class BTNode(Node):
    def __init__(self):
        super().__init__('bt_node')

        # --- existing state ---
        self.emergency = False
        self.walk_enabled = False
        self.change_gait_request = False
        self.in_base_position = True
        self.current_gait = "walk"
        self.requested_gait = "walk"

        # --- keyboard / step-sequence state ---
        self.step_triggered = False
        self.angle_index = 0
        self.current_joint_positions: dict = {}

        # --- joint names (must match trajectory controller) ---
        self.joint_names = [
            "front_sh",
            "front_ank_y",
            "front_ank_z",
            "rear_sh",
            "rear_ank_y",
            "rear_ank_z",
        ]

        # --- parameters ---
        self.declare_parameter(
            "trajectory_topic",
            "/bruno/multi_joint_trajectory_controller/joint_trajectory",
        )
        self.declare_parameter("joint_states_topic", "/bruno/joint_states")
        self.declare_parameter("step_deg", 15.0)
        self.declare_parameter("rotation_wait_sec", 2.0)

        trajectory_topic = str(self.get_parameter("trajectory_topic").value)
        joint_states_topic = str(self.get_parameter("joint_states_topic").value)
        self.step_deg = float(self.get_parameter("step_deg").value)
        self.rotation_wait_sec = float(self.get_parameter("rotation_wait_sec").value)

        # --- publisher for direct trajectory commands (Phase 2 & 3) ---
        self.traj_pub = self.create_publisher(JointTrajectory, trajectory_topic, 10)

        # --- existing subscriptions ---
        self.create_subscription(
            Bool, 'kumi_behavior/emergency', self._emergency_callback, 10
        )
        self.create_subscription(
            Bool, 'kumi_seq_traj_controller/enabled', self._walk_enabled_callback, 10
        )
        self.create_subscription(
            String, 'kumi_seq_traj_controller/gait', self._gait_callback, 10
        )

        # --- keyboard subscriptions ---
        self.create_subscription(
            String, 'keyboard_input', self._keyboard_callback, 10
        )
        self.create_subscription(
            Int32, 'keyboard_angle_index', self._angle_index_callback, 10
        )
        self.create_subscription(
            JointState, joint_states_topic, self._joint_states_callback, 10
        )

        # --- tree ---
        root = create_tree(self)
        self.tree = py_trees.trees.BehaviourTree(root)

        # --- timers ---
        self.create_timer(0.1, self.tick_tree)
        self.create_timer(1.0, self.log_tree_state)

    def tick_tree(self):
        self.tree.tick()

    # ------------------------------------------------------------------
    # Existing callbacks
    # ------------------------------------------------------------------

    def _emergency_callback(self, msg: Bool):
        self.emergency = msg.data

    def _walk_enabled_callback(self, msg: Bool):
        self.walk_enabled = msg.data

    def _gait_callback(self, msg: String):
        requested_gait = msg.data.strip()
        if not requested_gait:
            return
        self.requested_gait = requested_gait
        if requested_gait != self.current_gait:
            self.change_gait_request = True

    # ------------------------------------------------------------------
    # Keyboard callbacks
    # ------------------------------------------------------------------

    def _keyboard_callback(self, msg: String):
        if msg.data == 'UP' and not self.step_triggered:
            self.step_triggered = True
            self.get_logger().info(
                f'Step triggered (UP), angle_index={self.angle_index}'
            )

    def _angle_index_callback(self, msg: Int32):
        self.angle_index = msg.data

    def _joint_states_callback(self, msg: JointState):
        for name, pos in zip(msg.name, msg.position):
            self.current_joint_positions[name] = pos

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_tree_state(self):
        summary = self._format_tree_state()
        self.get_logger().info(
            f"BT state: {summary} | current_gait={self.current_gait} "
            f"| walk_enabled={self.walk_enabled} "
            f"| step_triggered={self.step_triggered} "
            f"| angle_index={self.angle_index}"
        )

    def _format_tree_state(self):
        root = self.tree.root
        parts = [f"{root.name}={self._status_name(root.status)}"]
        for child in root.children:
            parts.append(f"{child.name}={self._status_name(child.status)}")
        return ", ".join(parts)

    @staticmethod
    def _status_name(status):
        return status.name if status is not None else "INVALID"


def main():
    rclpy.init()
    node = BTNode()
    rclpy.spin(node)
    rclpy.shutdown()
