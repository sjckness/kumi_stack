import py_trees

from kumi_behavior.behaviors.actions import ExecuteWalk, HandleEmergency, Idle
from kumi_behavior.behaviors.conditions import (
    GaitChangeRequested,
    IsEmergency,
    IsInBasePosition,
    IsWalkingEnabled,
)
from kumi_behavior.behaviors.gait import ChangeGait, KeepCurrentGait
from kumi_behavior.behaviors.step_sequence import ExecuteStepSequence, KeyStepTriggered


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

    keyboard_step = py_trees.composites.Sequence(name="KeyboardStep", memory=True)
    keyboard_step.add_children([
        KeyStepTriggered(name="KeyStepTriggered", node=node),
        ExecuteStepSequence(name="ExecuteStepSequence", node=node),
    ])

    idle = Idle(name="Idle", node=node)

    root.add_children([
        emergency,
        keyboard_step,
        walking,
        idle,
    ])

    return root
