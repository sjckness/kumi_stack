# msauber stack
![Descrizione immagine](assets/msauber_on_track.png)

![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?) 
![ROS](https://img.shields.io/badge/ROS-2_Jazzy-22314E?logo=ros)
![Gazebo](https://img.shields.io/badge/Gazebo-Harmonic_8.10-6C3AB2?logo=gazebo)

# Table of content
[Package-overview](#package-overview)

[Installation](#installation)

[Build](#build)

[Launch](#launch)

[Controller](#controller)

[Settings](#hands-on)

[Usefull commands](#usefull-commands)

[Foxglove](#foxglove)

---

# Package Overview

## msauber_description

This package contains the robot model and all related resources.

Contents:
- URDF / Xacro robot model
- meshes
- sensor configuration

Purpose:
- Defines the physical structure of the robot
- Used by simulation and visualization tools

---

## msauber_bringup

Responsible for launching and initializing the robot system.

Contents:
- main launch file
- configuration files
- system initialization

Purpose:
- Starts the complete robot stack
- Launches the required nodes and parameters

---

## msauber_control

Handles the robot control layer.

Contents:
- ROS 2 controllers
- velocity and position command interfaces (`/cmd_vel`)
- hardware interfaces

Purpose:
- Converts high-level commands into actuator commands
- Interfaces with the robot hardware

---

## msauber_sim

Provides simulation support.

Contents:
- gz_sim launch
- world files
- simulation plugins

Purpose:
- Allows testing the robot in simulation
- Development without physical hardware

---

## msauber_perception

Contents:
- YOLO algorithms
- cone detection
- 

Purpose:
- Enables the robot to see the world

---

# Installation
[ROS2 Jazzy installation guide](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)

[Gazebo Harmonic 8.9 installation guide](https://gazebosim.org/docs/harmonic/install_ubuntu/)

### Package installation
For our case you can clone the main branch of this repository in `~/dev_ws/src/` using:

 ```bash
git clone https://github.com/sjckness/msauber_stack
```

Msauber_stack includes different packages, and from now on Msauber_stack will be the workspace, so the folders `build/` `log/` and `install/` will be created here.

Inside /msauber_stack run the full project installation:

 ```bash
./scripts/install.sh
```
This installs all dependencies (ROS2, Python, etc.) and builds the workspace.

## Environment

Inside /msauber_stack activate the working environment:

 ```bash
source scripts/env.sh
```
This loads ROS2, the workspace, and the Python environment.

⚠️ Use `source`, not `./env.sh`.

## Typical usage

```bash
./scripts/install.sh
source scripts/env.sh
```

# Build
Inside `/msauber_stack` use the following command to build the packages (this step is mandatory every time you open a new terminal): 
```bash
colcon build --simlink-install 
```
Then you have to source the workspace, and now ros knows where your files are. Use:
```bash
source install/setup.bash
```
# Launch
If you want to launch everything you can run:
```bash 
ros2 launch msauber_bringup sim_bringup.launch.py
```

### specific launches
See the robot on rviz2:
```bash 
ros2 launch msauber_description description.launch.py use_rviz:=true
```
Gazebo+robot w/o control and perception with custom world:
```bash 
ros2 launch msauber_sim sim.launch.py world:=cone_empty
```
Controllers launch and activation(not so usefull):
```bash 
ros2 launch msauber_control control.launch.py
```
Perception, YOLO and cone detection
```bash 
ros2 launch msauber_perception perception.launch.py
```

# Controller
### Ackerman controller
The ackerman controller is a ROS2 type of controller that allowes you to choose velocity and stearing rate. In this version is used with the node `teleop_twist_keyboard` from the namesake package. It take imput from the keyboard and the car moves.

To use it just run:
```bash 
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```
It works better with US keyboards, istead of WASD you should use IJML.

# Hands on
## Worlds
In order to try different worlds is now possible to select it when launching the simulation by setting the `world` parameter:
```bash
ros2 launch msauber_stack sim_bringup.launch.py world:=world_name
```
Worlds available in the stack:
- cone_empty
- sonoma
- my_empty

## Cameras
Cameras are implemented for perception. One classic front camera and one depth camera. 
To visualize the cameras outputs we need to use [Foxglove](#foxglove).

You should add an IMAGE pannel and set, for the classic camera:
- topic : `/front_camera/image`
- calibration : `/front_camera/camera_info`

And for the depth camera:
- topic : `/front_depth/image`
- calibration : `/front_depth/camera_info`

Is possible to disable the sensors by passign the following argument to false while launching:
```bash
ros2 launch msauber msauber.launch.py enable_sensors:=false
```
## Perception pkg
By launching the world `cone_empty` is possible to test the perception models, in gazebo you'll see:

![Descrizione immagine](assets/gz_cones.png)

In foxglove you will see this from the cameras:

![Descrizione immagine](assets/foxglove_cones.png)

The stack is using a [YOLO model](https://docs.ultralytics.com/models/yolov8/)  trained on a set of cones from [FSOCO dataset](https://universe.roboflow.com/cone-detection-bsgwo/fsoco-67vav). The front_camera image is passed to it and cones are identified, then the position of the cone is completed with the info from the depth camera and from there a 3D position is computed and the a marker is sent on the topic: `/perception/cones_markers` and that can be viasulized on RVIZ:

![Descrizione immagine](assets/rviz_cones.png)

In the futur a explaination of the trainign process will be added ;)

# Usefull commands
Rviz2:
```bash
rviz2
```

to kill gazebo:
```bash
pkill -9 -f 'gz-sim|gz sim|gz'
```

## Foxglove
Foxglove is a visualization and debugging tool for robotics that allows you to inspect, analyze, and replay ROS data (topics, messages, and logs) in real time or from recorded bag files.

In a new terminal:
```bash
foxglove-studio
```
Foxglove session info:
 - address: `ws://localhost`
 - port: `8765` (defined in launch file)