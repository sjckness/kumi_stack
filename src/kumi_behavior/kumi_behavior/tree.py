import py_trees

from kumi_behavior.behaviors.actions import ExecuteWalk, HandleEmergency, Idle
from kumi_behavior.behaviors.conditions import (
    GaitChangeRequested,
    IsEmergency,
    IsInBasePosition,
    IsWalkingEnabled,
)
from kumi_behavior.behaviors.gait import ChangeGait, KeepCurrentGait


def create_tree(node):
    root = py_trees.composites.Selector(name="Root", memory=False)

    emergency = py_trees.composites.Sequence(name="Emergency", memory=False)
    emergency.add_children([
        IsEmergency(name="IsEmergency", node=node),
        HandleEmergency(name="HandleEmergency", node=node),
    ])

    change_gait = py_trees.composites.Sequence(name="ChangeGait", memory=False)
    change_gait.add_children([
        GaitChangeRequested(name="GaitChangeRequested", node=node),
        IsInBasePosition(name="IsInBasePosition", node=node),
        ChangeGait(name="ApplyGaitChange", node=node),
    ])

    manage_gait = py_trees.composites.Selector(name="ManageGait", memory=False)
    manage_gait.add_children([
        change_gait,
        KeepCurrentGait(name="KeepCurrentGait", node=node),
    ])

    walking = py_trees.composites.Sequence(name="Walking", memory=False)
    walking.add_children([
        IsWalkingEnabled(name="IsWalkingEnabled", node=node),
        manage_gait,
        ExecuteWalk(name="ExecuteWalk", node=node),
    ])

    idle = Idle(name="Idle", node=node)

    root.add_children([
        emergency,
        walking,
        idle,
    ])

    return root
