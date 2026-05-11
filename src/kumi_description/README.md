# kumi_description

Robot model and all description-side resources for the Kumi robot — URDF/Xacro, meshes, sensor links, and the ros2_control + Gazebo plugin glue.

---

## Contents

| File | Purpose |
|---|---|
| `urdf/kumi.xacro` | Main entry point — composes everything below |
| `urdf/core.xacro` | Body links, joints, feet |
| `urdf/macros.xacro` | Shared macros and materials |
| `urdf/sensors.xacro` | Camera link macros (front RGB + depth, optional corner cameras) |
| `urdf/gazebo_plugins.xacro` | Gazebo-side plugin includes |
| `launch/description.launch.py` | Standalone description bringup + optional RViz |

---

## Xacro architecture

The model is decomposed into modular Xacro files so the same description tree drives Gazebo, RViz, and standalone TF publication. `kumi.xacro` is the only file the launch files reference; it includes the rest.

```
kumi.xacro
├── macros.xacro          shared macros, material colors, inertial helpers
├── core.xacro            body links, leg joints, feet, basic <gazebo> blocks
├── sensors.xacro         front + corner camera macros (RGB / depth)
└── gazebo_plugins.xacro  ros2_control plugin, world plugins, joint limits
```

Generate the URDF on the fly:

```bash
xacro $(ros2 pkg prefix kumi_description)/share/kumi_description/urdf/kumi.xacro > /tmp/kumi.urdf
```

---

## Sensors

The default model exposes a front RGB + front depth pair declared via the macros in `sensors.xacro`. Optional corner cameras (4 RGB + 4 depth) are also defined as macros and can be instantiated by editing `kumi.xacro`.

| Macro | Output topics (Gazebo) |
|---|---|
| `front_camera` | `/front_camera/image`, `/front_camera/camera_info` |
| `front_depth` | `/front_depth/image`, `/front_depth/camera_info` |
| Corner cameras | `/<corner>_camera/...`, `/<corner>_depth/...` |

Topics are bridged 1:1 to ROS by `kumi_bringup`.

---

## ros2_control integration

The `<ros2_control>` block in `kumi.xacro` declares the joint command and state interfaces. The Gazebo-side plugin loads them at simulation startup:

```xml
<plugin filename="gz_ros2_control-system"
        name="gz_ros2_control::GazeboSimROS2ControlPlugin">
  <parameters>$(find kumi_control)/config/trajectory_control_config.yaml</parameters>
</plugin>
```

Controllers themselves are spawned by `kumi_bringup` after the controller manager comes up — see [`kumi_control/README.md`](../kumi_control/README.md).

---

## Standalone launch

Publish the description (and optionally open RViz):

```bash
ros2 launch kumi_description description.launch.py \
  use_rviz:=true \
  use_joint_state_publisher_gui:=true
```

| Argument | Default | Description |
|---|---|---|
| `use_rviz` | `false` | Launch RViz with a preset Kumi config |
| `use_joint_state_publisher_gui` | `false` | Joint sliders for manual posing |
| `namespace` | `kumi` | Namespace under which the description is published |

---

## Topics published

| Topic | Type | Notes |
|---|---|---|
| `robot_description` | `std_msgs/String` | Latched URDF |
| `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | Standard TF tree |
