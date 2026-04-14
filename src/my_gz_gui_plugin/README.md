# my_gz_gui_plugin

A reusable Gazebo Harmonic (gz-sim 8) GUI plugin for robot control, written in C++ and QML.

## Features

- **Velocity control** — publish `gz::msgs::Twist` via sliders
- **Set model pose** — reposition models in the world
- **Spawn / Remove models** — dynamically add or remove entities
- **World parameters** — adjust gravity at runtime

## Configuration (SDF)

All parameters are optional and have sensible defaults:

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

## Build

```bash
colcon build --packages-select my_gz_gui_plugin
source install/setup.bash
```
