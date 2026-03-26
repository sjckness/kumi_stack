import py_trees
from std_msgs.msg import String

class ChangeGait(py_trees.behaviour.Behaviour):
    def __init__(self, name, node):
        super().__init__(name)
        self.node = node
        self.gait_pub = node.create_publisher(String, '/kumi_seq_traj_controller/gait', 10)

    def update(self):
        self.node.current_gait = self.node.requested_gait
        self.node.change_gait_request = False

        msg = String()
        msg.data = self.node.current_gait
        self.gait_pub.publish(msg)
        return py_trees.common.Status.SUCCESS


class KeepCurrentGait(py_trees.behaviour.Behaviour):
    def __init__(self, name, node):
        super().__init__(name)
        self.node = node

    def update(self):
        return py_trees.common.Status.SUCCESS
