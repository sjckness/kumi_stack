# kumi_control

Control layer for the Kumi robot on the Isaac Sim side — CSV gait playback that drives Isaac Sim joints, and a Tkinter operator GUI.

---

## Contents

| Path | Purpose |
|---|---|
| `kumi_control/kumi_seq_traj_controller.py` | CSV gait → `sensor_msgs/JointState` publisher |
| `kumi_control/kumi_control_gui.py` | Tkinter control window |
| `kumi_control/kumi_keyboard_node.py` | Keyboard-driven manual walking |
| `config/trajectory_control_config.yaml` | Joint and topic configuration |
| `moves/*.csv` | Gait files (joint angles in **degrees**, one row per step) |
| `launch/control.launch.py` | Controller + GUI launch |

---

## Architecture

```
┌──────────────────────┐  /enabled, /gait   ┌─────────────────────────────┐
│ kumi_control_gui     │───────────────────►│ kumi_seq_traj_controller    │
│ (Tkinter operator)   │                    │                             │
└──────────────────────┘                    │   reads CSV @ 10 Hz         │
                                            │   publishes JointState      │
                                            └──────────────┬──────────────┘
                                                           │
                                                           ▼
                                          /kumi/joint_commands  (Isaac Sim)
```

> Unlike the Gazebo branches, this controller does **not** publish `trajectory_msgs/JointTrajectory` into ros2_control — it publishes `sensor_msgs/JointState` directly into Isaac Sim on `/kumi/joint_commands`.

---

## `kumi_seq_traj_controller`

A ROS 2 node that streams pre-recorded joint trajectories to Isaac Sim as `sensor_msgs/JointState` at 10 Hz, but only while walking is enabled.

The node owns a small state machine:

- Subscribes to `/enabled` (`std_msgs/Bool`) — pauses / resumes publishing.
- Subscribes to `/gait` (`std_msgs/String`) — switches the active CSV. The switch only takes effect at the next *base-position* of the cycle, so steps are never interrupted mid-stride.

Available gaits:

| Gait | Direction | Mode |
|---|---|---|
| `walk` | forward | loop |
| `bwalk` | backward | loop |
| `flip` / `flip_sx` / `flip_dx` | forward, forward-left, forward-right | single |
| `bflip` / `bflip_sx` / `bflip_dx` | backward, backward-left, backward-right | single |
| `accovacciato` | crouch | single |

Parameters:

| Parameter | Default | Description |
|---|---|---|
| `joint_commands_topic` | `/kumi/joint_commands` | Publisher topic (Isaac Sim consumes this) |
| `enable_topic` | `kumi_seq_traj_controller/enabled` | Walk enable |
| `gait_topic` | `kumi_seq_traj_controller/gait` | Gait selector |
| `csv_path` | gait-derived | Override CSV path |

Run standalone:

```bash
ros2 run kumi_control kumi_seq_traj_controller
```

---

## `kumi_control_gui`

A small Tkinter window for the human operator. Three controls:

- **Emergency** — publishes the emergency flag (latches walking off)
- **Walk enabled** — toggles `/enabled` on the trajectory publisher
- **Gait selector** — switches the active gait CSV

Run standalone:

```bash
ros2 run kumi_control kumi_control_gui
```

Or bundle it with the Isaac bringup: `ros2 launch kumi_bringup isaac_bringup.launch.py use_gui:=true`.

---

## Launch

```bash
ros2 launch kumi_control control.launch.py
```

Selected arguments:

| Argument | Default | Description |
|---|---|---|
| `namespace` | `kumi` | Topic namespace |
| `use_gui` | `true` | Spawn `kumi_control_gui` |
| `use_keyboard` | `false` | Spawn `kumi_keyboard_node` |
