import py_trees

class IsEmergency(py_trees.behaviour.Behaviour):
    def __init__(self, name, node):
        super().__init__(name)
        self.node = node

    def update(self):
        if self.node.emergency:
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE


class IsWalkingEnabled(py_trees.behaviour.Behaviour):
    def __init__(self, name, node):
        super().__init__(name)
        self.node = node

    def update(self):
        if self.node.walk_enabled:
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE


class GaitChangeRequested(py_trees.behaviour.Behaviour):
    def __init__(self, name, node):
        super().__init__(name)
        self.node = node

    def update(self):
        if self.node.change_gait_request:
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE


class IsInBasePosition(py_trees.behaviour.Behaviour):
    def __init__(self, name, node):
        super().__init__(name)
        self.node = node

    def update(self):
        if self.node.in_base_position:
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE