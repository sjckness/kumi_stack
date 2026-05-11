# kumi_control

Control layer for the Kumi robot — controller configuration, gait playback from CSV files, and a Tkinter operator GUI.

---

## Contents

| Path | Purpose |
|---|---|
| `kumi_control/kumi_seq_traj_controller.py` | CSV gait → `JointTrajectory` publisher |
| `kumi_control/kumi_control_gui.py` | Tkinter control window |
| `kumi_control/kumi_keyboard_node.py` | Keyboard-driven manual walking |
| `config/trajectory_control_config.yaml` | controller_manager configuration |
| `moves/*.csv` | Gait files (joint angles in **degrees**, one row per step) |
| `launch/control.launch.py` | Controller manager + spawner orchestration |

---

## Architecture

```
┌──────────────────────┐  /enabled, /gait   ┌─────────────────────────────┐
│ kumi_control_gui     │───────────────────►│ kumi_seq_traj_controller    │
│ (Tkinter operator)   │                    │                             │
└──────────────────────┘                    │   reads CSV @ 10 Hz         │
                                            │   publishes JointTrajectory │
                                            └──────────────┬──────────────┘
                                                           ▼
                              /<ns>/multi_joint_trajectory_controller/joint_trajectory
                                                           │
                                                           ▼
                                               Gazebo joints (via ros2_control)
```

---

## Configured controllers

`config/trajectory_control_config.yaml` declares:

- `joint_state_broadcaster`
- `multi_joint_trajectory_controller` *(the active trajectory consumer)*

Both are spawned by `control.launch.py` once the controller manager is up.

---

## `kumi_seq_traj_controller`

A ROS 2 node that streams pre-recorded joint trajectories to ros2_control as `trajectory_msgs/JointTrajectory` at 10 Hz, but only while walking is enabled.

The node owns a small state machine:

- Subscribes to `/enabled` (`std_msgs/Bool`) — pauses/resumes publishing.
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
| `trajectory_topic` | `multi_joint_trajectory_controller/joint_trajectory` | Publisher topic |
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
- **Walk enabled** — toggles `/enabled` on the trajectory controller
- **Gait selector** — switches the active gait CSV

Run standalone:

```bash
ros2 run kumi_control kumi_control_gui
```

Or bundle it with the simulation: `ros2 launch kumi_bringup sim_bringup.launch.py use_control_gui:=true`.

---

## Launch

```bash
ros2 launch kumi_control control.launch.py
```

Selected arguments:

| Argument | Default | Description |
|---|---|---|
| `namespace` | `kumi` | Namespace used for the controller manager |
| `controllers_file` | `config/trajectory_control_config.yaml` | Override controller config |
| `use_sim_time` | `true` | Source clock from `/clock` |
| `use_gui` | `true` | Spawn `kumi_control_gui` |
| `use_keyboard` | `false` | Spawn `kumi_keyboard_node` |
| `spawner_delay` | `5.0` | Seconds before spawning controllers |
