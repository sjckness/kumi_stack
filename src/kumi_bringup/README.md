# kumi_bringup

Top-level launch orchestration for the **Isaac Sim** workflow. Composes the robot description, the Isaac-side trajectory publisher, and the behavior tree.

---

## Launch files

| File | Purpose |
|---|---|
| `launch/isaac_bringup.launch.py` | ROS 2 side for the Isaac Sim integration |

---

## `isaac_bringup.launch.py`

Brings up:

1. **`robot_state_publisher`** with the URDF generated from [`kumi_description`](../kumi_description/README.md)
2. **`kumi_seq_traj_controller`** — publishes `sensor_msgs/JointState` on `/kumi/joint_commands`
3. *(Optional)* **`kumi_control_gui`** — Tkinter operator window
4. *(Optional)* **RViz**

> Isaac Sim itself runs in a **separate** NVIDIA-provided container. This launch does **not** start the simulator — see [Isaac Sim integration](../../README.md#isaac-sim-integration) at the branch root.

### Arguments

| Argument | Default | Description |
|---|---|---|
| `use_gui` | `true` | Launch the Tkinter control GUI |
| `use_rviz` | `false` | Launch RViz with the Kumi preset |

### Example

```bash
ros2 launch kumi_bringup isaac_bringup.launch.py use_rviz:=true
```

---

## Composition diagram

```
isaac_bringup.launch.py
├── robot_state_publisher                   ← URDF from kumi_description/kumi.xacro
├── kumi_seq_traj_controller                ← JointState publisher on /kumi/joint_commands
├── kumi_control_gui      (optional)        ← operator window
├── kumi_behavior/bt_node                   ← py_trees BT @ 10 Hz
└── rviz2                 (optional)
```

Each component is documented next to its source — see [`kumi_description`](../kumi_description/README.md), [`kumi_control`](../kumi_control/README.md), and [`kumi_behavior`](../kumi_behavior/README.md).

---

## Topic summary

See the [branch root README](../../README.md#architecture) for the full ROS ↔ Isaac topic table.
