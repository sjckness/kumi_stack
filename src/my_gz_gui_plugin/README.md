# my_gz_gui_plugin

A custom **C++/QML** panel loaded directly inside the Gazebo GUI sidebar. Acts as the in-simulation operator interface for the Kumi robot.

<p align="center">
  <img src="../../assets/gui_v4.png" alt="Kumi Gazebo GUI panel" width="640" />
</p>

Built on `gz-gui8` and `gz-transport13`.

---

## Features

| Control | What it does |
|---|---|
| **Robot selector** | Switches which spawned robot the panel is controlling |
| **EMERGENCY ON / OFF** | Publishes the emergency state for the selected robot |
| **Walk enabled** | Enables / disables walking commands |
| **Gait selector** | Switches the active gait |
| **Spawn / Despawn** | Adds or removes models from the current world |
| **Update entities** | Refreshes the robot / model dropdowns |
| **Camera preview** | Live image from the selected robot’s front camera |

---

## Architecture

The plugin is a Gazebo GUI plugin (not a ROS 2 node). It runs inside the Gazebo process and talks to the simulator over gz-transport — ROS 2 sees the same intent through `ros_gz_bridge` configured by `kumi_bringup`.

| Side | Mechanism | Purpose |
|---|---|---|
| Gazebo world | gz-transport topics on `/<robot_name>/...` | Emergency, walk, gait |
| Gazebo services | World transport services declared in the world SDF | Spawn / despawn |
| Camera | gz-transport subscription to `/<robot_name>/front_camera/image` | Live preview |

The plugin queries Gazebo for entities, populates its dropdowns, and re-publishes operator intent on per-robot transport topics. ROS 2 nodes downstream (the behavior tree, the trajectory controller) consume the bridged equivalents.

---

## File layout

| File | Purpose |
|---|---|
| `CMakeLists.txt` | gz-gui8 + gz-transport13 plugin build |
| `include/my_gz_gui_plugin/MyGuiPlugin.hh` | Plugin C++ header |
| `src/MyGuiPlugin.cc` | Plugin C++ implementation |
| `qml/my_gz_gui_plugin.qml` | Panel layout (QML) |
| `qml/qml.qrc` | Qt resource manifest |
| `env-hooks/` | Ament hooks that extend `IGN_GUI_PLUGIN_PATH` after a sourced install |

---

## How it loads

The panel is referenced from the world SDF (`<gui>` block) shipped by `kumi_sim` (`config/kumi_gui.config`). When `sim_bringup.launch.py` opens that world, the panel appears docked in the Gazebo sidebar automatically.

---

## SDF configuration

All plugin parameters are optional and have sensible defaults:

```xml
<plugin filename="my_gz_gui_plugin" name="my_gz_gui_plugin::MyGuiPlugin">
  <topic_cmd_vel>/cmd_vel</topic_cmd_vel>
  <topic_spawn>/world/default/create</topic_spawn>
  <topic_remove>/world/default/remove</topic_remove>
  <topic_set_pose>/world/default/set_pose</topic_set_pose>
  <topic_physics>/world/default/set_physics</topic_physics>
  <max_linear_vel>1.0</max_linear_vel>
  <max_angular_vel>1.5</max_angular_vel>
  <title>Robot Control</title>
</plugin>
```

---

## Typical workflow

1. Launch the simulation:
   ```bash
   ros2 launch kumi_bringup sim_bringup.launch.py
   ```
2. Wait for Gazebo to open and for the *Kumi Control* panel to appear.
3. Select a robot in the **Robot** dropdown.
4. Use **EMERGENCY**, **Walk**, and **Gait** to drive the robot.
5. Use the lower section to spawn additional entities or remove existing ones.
6. Open the camera preview to monitor the front camera.

---

## Notes

- The camera preview only works when the robot is launched with `enable_sensors:=true`.
- If the robot list looks stale, press **update entities**.
- Spawn / despawn relies on the world plugin loaded by `kumi_sim` — running this panel against a stock SDF world will not provide those services.

---

## Build

```bash
colcon build --packages-select my_gz_gui_plugin
source install/setup.bash
```
