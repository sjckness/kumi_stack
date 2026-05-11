# kumi_description

Robot model and all description-side resources for the Kumi robot — URDF/Xacro, meshes, and sensor link macros.

---

## Contents

| File | Purpose |
|---|---|
| `urdf/kumi.xacro` | Main entry point — composes everything below |
| `urdf/core.xacro` | Body links, joints, feet |
| `urdf/macros.xacro` | Shared macros and materials |
| `urdf/sensors.xacro` | Camera link macros (front RGB + depth, optional corner cameras) |
| `launch/description.launch.py` | Standalone description bringup + optional RViz |

> The Gazebo-side `gazebo_plugins.xacro` is **not** shipped on this branch — Isaac Sim provides its own physics and sensors, the URDF is consumed as a pure description.

---

## Xacro architecture

The model is decomposed into modular Xacro files so the same description drives Isaac, RViz, and standalone TF publication. `kumi.xacro` is the only file the launch files reference; it includes the rest.

```
kumi.xacro
├── macros.xacro     shared macros, material colors, inertial helpers
├── core.xacro       body links, leg joints, feet
└── sensors.xacro    front + corner camera macros (RGB / depth)
```

Generate the URDF on the fly:

```bash
xacro $(ros2 pkg prefix kumi_description)/share/kumi_description/urdf/kumi.xacro > /tmp/kumi.urdf
```

The same URDF is consumed by Isaac Sim — push it into Isaac as the latched `/kumi/robot_description` topic and use it to import the robot into the stage.

---

## Sensors

The default model exposes a front RGB + front depth pair, declared via the macros in `sensors.xacro`. Optional corner cameras (4 RGB + 4 depth) are also defined as macros and can be instantiated by editing `kumi.xacro`.

The actual camera *images* and *camera_info* topics are produced **by Isaac Sim**, not by this package — Isaac binds the sensor links declared in the URDF to its own camera renderer. The macros here exist so the same sensor frames appear in TF on the ROS 2 side.

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
| `/kumi/robot_description` | `std_msgs/String` | Latched URDF — consumed by Isaac Sim |
| `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | Standard TF tree |
