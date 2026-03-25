# kumi_stack
![Descrizione immagine](assets/kumi.png)

![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?)
![ROS](https://img.shields.io/badge/ROS-2_Jazzy-22314E?logo=ros)
![Gazebo](https://img.shields.io/badge/Gazebo-Harmonic-6C3AB2?logo=gazebo)

Workspace ROS 2 per il robot `kumi`, con descrizione robot, controllo, simulazione Gazebo e bringup completo.

## Indice

- [Package Overview](#package-overview)
- [Installazione](#installazione)
- [Build](#build)
- [Launch](#launch)
- [Controller](#controller)
- [Sensori](#sensori)
- [Comandi utili](#comandi-utili)

## Package Overview

### `kumi_description`

Contiene il modello del robot e tutte le risorse associate:
- URDF / Xacro
- mesh
- sensori
- plugin Gazebo / ros2_control

Struttura attuale dei file Xacro:
- [kumi.xacro](/home/andreas/dev_ws/kumi_stack/src/kumi_description/urdf/kumi.xacro)
- [macros.xacro](/home/andreas/dev_ws/kumi_stack/src/kumi_description/urdf/macros.xacro)
- [core.xacro](/home/andreas/dev_ws/kumi_stack/src/kumi_description/urdf/core.xacro)
- [sensors.xacro](/home/andreas/dev_ws/kumi_stack/src/kumi_description/urdf/sensors.xacro)
- [gazebo_plugins.xacro](/home/andreas/dev_ws/kumi_stack/src/kumi_description/urdf/gazebo_plugins.xacro)

### `kumi_control`

Gestisce il layer di controllo:
- configurazione controller
- launch del controller manager
- nodi Python per pubblicare traiettorie sui giunti

Controller configurato:
- `joint_state_broadcaster`
- `multi_joint_trajectory_controller`

### `kumi_sim`

Contiene la simulazione:
- launch di Gazebo
- world files
- modelli e risorse per Gazebo

World disponibili:
- `my_empty`
- `stairs`

### `kumi_bringup`

Launch package per avviare lo stack completo in simulazione:
- Gazebo
- robot description
- spawn del robot
- controller
- bridge Gazebo/ROS per clock e camere

### `kumi_perception`

Pacchetto placeholder per la parte perception. Al momento nel workspace è minimale.

## Installazione

### Requisiti

- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic

Guide ufficiali:
- [ROS 2 Jazzy installation guide](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
- [Gazebo Harmonic installation guide](https://gazebosim.org/docs/harmonic/install_ubuntu/)

### Clonazione

```bash
git clone <repo-url> ~/dev_ws/kumi_stack
```

### Install completa del workspace

Dentro [kumi_stack](/home/andreas/dev_ws/kumi_stack):

```bash
./scripts/kumi_install.sh
```

Lo script:
- installa dipendenze di sistema
- inizializza `rosdep`
- crea la virtualenv [`.venv`](/home/andreas/dev_ws/kumi_stack/.venv)
- installa le dipendenze Python
- esegue `colcon build --symlink-install`

## Build

Ogni volta che apri un nuovo terminale:

```bash
cd /home/andreas/dev_ws/kumi_stack
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
source install/setup.bash
```

Se modifichi il codice:

```bash
colcon build --symlink-install
source install/setup.bash
```

## Launch

### Stack completo in simulazione

```bash
ros2 launch kumi_bringup sim_bringup.launch.py
```

Parametri utili:
- `world:=my_empty`
- `world:=stairs`
- `enable_sensors:=true`
- `use_rviz:=false`
- `use_joint_state_publisher_gui:=false`
- `ros_namespace:=kumi`
- `robot_name:=bruno`

Esempio:

```bash
ros2 launch kumi_bringup sim_bringup.launch.py world:=my_empty enable_sensors:=true
```

### Solo descrizione robot

```bash
ros2 launch kumi_description description.launch.py use_rviz:=false use_joint_state_publisher_gui:=false
```

### Solo Gazebo

```bash
ros2 launch kumi_sim sim.launch.py world:=my_empty
```

### Solo controllo

```bash
ros2 launch kumi_control control.launch.py
```

## Controller

Il controller configurato è `multi_joint_trajectory_controller`.

Configurazione:
- [trajectory_control_config.yaml](/home/andreas/dev_ws/kumi_stack/src/kumi_control/config/trajectory_control_config.yaml)

Topic usato dal controller:
- `/kumi/multi_joint_trajectory_controller/joint_trajectory`

Nodo demo per inviare traiettorie da CSV:

```bash
ros2 run kumi_control kumi_seq_traj_controller
```

CSV di default:
- [demo_flip_500.csv](/home/andreas/dev_ws/kumi_stack/src/kumi_control/resource/demo_flip_500.csv)

## Sensori

Attualmente il robot espone:
- camera RGB frontale
- depth camera frontale

Topic bridgeati da Gazebo:
- `/front_camera/image`
- `/front_camera/camera_info`
- `/front_depth/image`
- `/front_depth/camera_info`

Puoi disattivarli passando:

```bash
ros2 launch kumi_bringup sim_bringup.launch.py enable_sensors:=false
```

## Comandi utili

Lista controller:

```bash
ros2 control list_controllers
```

Verifica topic traiettoria:

```bash
ros2 topic echo /kumi/multi_joint_trajectory_controller/joint_trajectory
```

Kill di Gazebo:

```bash
pkill -9 -f 'gz-sim|gz sim|gz'
```

Build di un singolo package:

```bash
colcon build --packages-select kumi_description --symlink-install
```
