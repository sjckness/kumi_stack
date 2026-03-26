import py_trees
from std_msgs.msg import Bool

class HandleEmergency(py_trees.behaviour.Behaviour):
    def __init__(self, name, node):
        super().__init__(name)
        self.node = node
        self.walk_enable_pub = node.create_publisher(Bool, '/kumi_seq_traj_controller/enabled', 10)

    def update(self):
        msg = Bool()
        msg.data = False
        self.walk_enable_pub.publish(msg)
        return py_trees.common.Status.RUNNING


class ExecuteWalk(py_trees.behaviour.Behaviour):
    def __init__(self, name, node):
        super().__init__(name)
        self.node = node
        self.walk_enable_pub = node.create_publisher(Bool, '/kumi_seq_traj_controller/enabled', 10)

    def initialise(self):
        msg = Bool()
        msg.data = True
        self.walk_enable_pub.publish(msg)

    def update(self):
        return py_trees.common.Status.RUNNING

    def terminate(self, new_status):
        enable_msg = Bool()
        enable_msg.data = False
        self.walk_enable_pub.publish(enable_msg)


class Idle(py_trees.behaviour.Behaviour):
    def __init__(self, name, node):
        super().__init__(name)
        self.node = node

    def update(self):
        return py_trees.common.Status.RUNNING
