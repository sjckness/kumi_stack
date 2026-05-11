<div align="center">

# kumi_stack — NVIDIA Isaac Sim · GNU/Linux

<img src="assets/kumi_&_spot.jpg" alt="Kumi next to Spot in Isaac Sim" width="480" />

ROS 2 Jazzy workspace for the **Kumi** robot, targeting **NVIDIA Isaac Sim 4.x** on **Ubuntu 24.04** with the NVIDIA Container Toolkit.

[![ROS 2](https://img.shields.io/badge/ROS_2-Jazzy-22314E?logo=ros)](https://docs.ros.org/en/jazzy/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?logo=ubuntu)](https://ubuntu.com/)
[![Isaac Sim](https://img.shields.io/badge/Isaac_Sim-4.x-76B900?logo=nvidia)](https://developer.nvidia.com/isaac/sim)
[![NVIDIA GPU](https://img.shields.io/badge/NVIDIA_GPU-required-76B900?logo=nvidia)](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

</div>

---

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Build](#build)
- [Isaac Sim integration](#isaac-sim-integration)
- [Launch](#launch)
- [Packages](#packages)
- [Useful Commands](#useful-commands)

---

## Overview

This branch carries the **Isaac Sim** side of `kumi_stack`. The ROS 2 side (description, control, behavior tree, GUI) lives here; physics, sensors, and joint state feedback are handled by a separate NVIDIA Isaac Sim container.

For other targets:

- Gazebo on Linux → [`jazzy-gazebo-GNU-linux`](../../tree/jazzy-gazebo-GNU-linux)
- Gazebo on Windows → [`jazzy-gazebo-win`](../../tree/jazzy-gazebo-win)
- Project entry point → [`main`](../../tree/main)

<p align="center">
  <img src="assets/isaac-sim.png" alt="Kumi inside NVIDIA Isaac Sim" width="640" />
</p>

---

## Architecture

All ROS 2 topics live under the `/kumi` namespace. The ROS 2 side publishes the description, the TF tree, and the joint commands. Isaac Sim is responsible for physics, rendering, and joint feedback.

```
┌──────────────────────────────┐        ┌────────────────────────────┐
│   ROS 2 (this repository)    │        │       Isaac Sim container  │
│                              │        │                            │
│  robot_state_publisher       │◄───────│  /kumi/joint_states        │
│                              │────────►  /kumi/joint_commands      │
│  kumi_seq_traj_controller    │        │                            │
│  kumi_control_gui            │        │                            │
│  kumi_behavior  (BT)         │        │                            │
└──────────────────────────────┘        └────────────────────────────┘
```

| Topic | Direction | Type | Purpose |
|---|---|---|---|
| `/kumi/robot_description` | ROS 2 → Isaac | `std_msgs/String` | URDF (latched) |
| `/kumi/joint_states` | Isaac → ROS 2 | `sensor_msgs/JointState` | Current joint positions |
| `/kumi/joint_commands` | ROS 2 → Isaac | `sensor_msgs/JointState` | Target joint positions |
| `/kumi/kumi_behavior/emergency` | GUI → BT | `std_msgs/Bool` | Emergency stop |
| `/kumi/kumi_seq_traj_controller/enabled` | GUI → controller | `std_msgs/Bool` | Walk enable |
| `/kumi/kumi_seq_traj_controller/gait` | GUI → controller | `std_msgs/String` | Active gait |
| `/tf`, `/tf_static` | ROS 2 → global | `tf2_msgs/TFMessage` | TF tree |

---

## Requirements

- Ubuntu 24.04
- Docker Engine + Compose plugin
- **NVIDIA GPU** with recent drivers
- **NVIDIA Container Toolkit** — see the [official install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- An Isaac Sim 4.x container, pulled and configured separately (see [Isaac Sim integration](#isaac-sim-integration))

---

## Installation

```bash
git clone <repo-url> ~/dev_ws/kumi_stack
cd ~/dev_ws/kumi_stack
git checkout jazzy-isaac-GNU-linux
```

Start the ROS 2 side dev container:

```bash
docker compose -f .devcontainer/docker-compose.yml up -d
docker exec -it kumi_stack-kumi-1 bash
```

The first run triggers [`setup.sh`](.devcontainer/setup.sh) — it installs Poetry, resolves rosdep, and builds the workspace.

> The Dockerfile here intentionally does **not** install `ros-jazzy-ros-gz` or `ros-jazzy-gz-ros2-control`. Gazebo is not part of this branch.

---

## Build

```bash
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
colcon build --symlink-install
source install/setup.bash
```

Single-package build:

```bash
colcon build --packages-select kumi_behavior --symlink-install
```

---

## Isaac Sim integration

Isaac Sim runs in a **separate** container (NVIDIA-provided image) on the same host. The two sides communicate over DDS.

### Workflow overview

1. Start the Isaac Sim container with GPU access (`--gpus all`).
2. Open the stage that contains the Kumi USD and the Isaac–ROS bridge nodes.
3. Verify the bridge publishes `/kumi/joint_states` and subscribes to `/kumi/joint_commands`.
4. Start this side of the stack:
   ```bash
   ros2 launch kumi_bringup isaac_bringup.launch.py
   ```

### DDS configuration

The repository ships a `fastdds.xml` at the root that pins the metatraffic locator to the Isaac container address on a Docker bridge network. If the two containers do not share a Docker network, point Fast DDS at the file explicitly:

```bash
export FASTRTPS_DEFAULT_PROFILES_FILE=$PWD/fastdds.xml
```

---

## Launch

ROS 2 side bringup:

```bash
ros2 launch kumi_bringup isaac_bringup.launch.py
```

Arguments:

| Argument | Default | Description |
|---|---|---|
| `use_gui` | `true` | Launch the Tkinter control GUI |
| `use_rviz` | `false` | Launch RViz |

See [`src/kumi_bringup/README.md`](src/kumi_bringup/README.md) for the complete launch reference.

---

## Packages

| Package | Description | Docs |
|---|---|---|
| `kumi_description` | URDF / Xacro / meshes / sensors | [README](src/kumi_description/README.md) |
| `kumi_control` | Isaac `JointState` trajectory publisher + GUI | [README](src/kumi_control/README.md) |
| `kumi_bringup` | Top-level launch orchestration | [README](src/kumi_bringup/README.md) |
| `kumi_behavior` | py_trees behavior tree | [README](src/kumi_behavior/README.md) |
| `kumi_perception` | Perception pipeline (placeholder) | [README](src/kumi_perception/README.md) |

---

## Useful Commands

```bash
# List all topics under the /kumi namespace
ros2 topic list | grep kumi

# Inspect the TF tree
ros2 run tf2_tools view_frames

# Verify joint feedback from Isaac
ros2 topic echo /kumi/joint_states

# Drive a single joint command for testing
ros2 topic pub --once /kumi/joint_commands sensor_msgs/JointState \
  "{name: ['front_sh'], position: [0.1]}"
```

---

## License

TBD.
