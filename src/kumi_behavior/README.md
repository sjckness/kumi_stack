# kumi_behavior

py_trees-based behavior tree for the Kumi robot. Owns high-level decision logic: emergency handling, gait management, and an idle fallback.

<p align="center">
  <img src="../../assets/bt_diagram.png" alt="Kumi behavior tree" width="640" />
</p>

---

## Architecture

The tree is owned by `bt_node` (a ROS 2 node) and ticked at **10 Hz**. State flows in from ROS topics; the tree publishes control intent to the trajectory controller.

```
Root (Selector)
├── Emergency (Sequence)              ← highest priority
│   ├── IsEmergency?
│   └── HandleEmergency               publishes walk_enabled = false
│
├── Walking (Sequence)
│   ├── IsWalkingEnabled?
│   ├── ManageGait (Selector)
│   │   ├── ChangeGait (Sequence)
│   │   │   ├── GaitChangeRequested?
│   │   │   ├── IsInBasePosition?
│   │   │   └── ApplyGaitChange       swaps CSV, publishes new gait
│   │   └── KeepCurrentGait           no-op, always SUCCESS
│   └── ExecuteWalk                   enables the trajectory controller
│
└── Idle                              ← fallback, always RUNNING
```

---

## How it works

1. **Emergency runs first.** If the emergency flag is set, `HandleEmergency` disables the trajectory publisher regardless of any other state.
2. **Walking runs only if enabled.** `ManageGait` decides whether a new gait was requested:
   - A gait change is applied only when the robot is back in its base position (`IsInBasePosition`), avoiding mid-step transitions.
   - If no change is needed, `KeepCurrentGait` succeeds and the tree proceeds to `ExecuteWalk`.
3. **Idle fallback.** If neither branch succeeds, the robot falls through to `Idle`, which keeps the tree alive without publishing anything.

---

## ROS interfaces

State subscriptions:

| Topic | Type | Source |
|---|---|---|
| `kumi_behavior/emergency` | `std_msgs/Bool` | Control GUI |
| `kumi_seq_traj_controller/enabled` | `std_msgs/Bool` | Control GUI |
| `kumi_seq_traj_controller/gait` | `std_msgs/String` | Control GUI |

The tree drives the trajectory controller through the same enable / gait topics.

---

## Files

| Path | Purpose |
|---|---|
| `kumi_behavior/bt_node.py` | ROS 2 node that owns the tree and the tick timer |
| `kumi_behavior/tree.py` | Tree factory |
| `kumi_behavior/behaviors/` | Individual condition and action nodes |

Behaviors are split by concern: `actions.py`, `conditions.py`, `gait.py`, `manual_walk.py`, `step_sequence.py`.

---

## Run standalone

```bash
ros2 run kumi_behavior bt_node
```

Or include it in the full simulation via `kumi_bringup`.

---

## References

- [behaviortree.dev](https://www.behaviortree.dev/docs/intro)
- [py_trees documentation](https://py-trees.readthedocs.io/en/devel/)
