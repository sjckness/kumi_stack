import rclpy
from rclpy.node import Node
import py_trees
from std_msgs.msg import Bool, String

from kumi_behavior.tree import create_tree


class BTNode(Node):
    def __init__(self):
        super().__init__('bt_node')

        # --- stato interno ---
        self.emergency = False
        self.walk_enabled = True
        self.change_gait_request = False
        self.in_base_position = True
        self.current_gait = "walk"
        self.requested_gait = "walk"

        self.create_subscription(
            Bool,
            'kumi_behavior/emergency',
            self._emergency_callback,
            10
        )
        self.create_subscription(
            Bool,
            'kumi_seq_traj_controller/enabled',
            self._walk_enabled_callback,
            10
        )
        self.create_subscription(
            String,
            'kumi_seq_traj_controller/gait',
            self._gait_callback,
            10
        )

        # --- tree ---
        root = create_tree(self)
        self.tree = py_trees.trees.BehaviourTree(root)

        # --- timer ---
        self.create_timer(0.1, self.tick_tree)
        self.create_timer(1.0, self.log_tree_state)

    def tick_tree(self):
        self.tree.tick()

    def _emergency_callback(self, msg: Bool):
        self.emergency = msg.data

    def _walk_enabled_callback(self, msg: Bool):
        self.walk_enabled = msg.data

    def _gait_callback(self, msg: String):
        requested_gait = msg.data.strip()
        if not requested_gait:
            return

        self.requested_gait = requested_gait
        self.change_gait_request = requested_gait != self.current_gait

    def log_tree_state(self):
        summary = self._format_tree_state()
        self.get_logger().info(
            f"BT state: {summary} | current_gait={self.current_gait} | walk_enabled={self.walk_enabled} "
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
