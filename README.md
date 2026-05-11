<div align="center">

# kumi_stack — Gazebo · Windows

<img src="assets/kumi.png" alt="Kumi robot" width="320" />

ROS 2 Jazzy + Gazebo Harmonic, running on **Windows 10 / 11** through Docker Desktop. A Linux desktop is served over noVNC and opened from any browser — no Linux tools required on the host machine.

[![Windows](https://img.shields.io/badge/Windows-10/11-0078D6?logo=windows)](https://www.microsoft.com/windows/)
[![Docker](https://img.shields.io/badge/Docker_Desktop-WSL2-2496ED?logo=docker)](https://www.docker.com/products/docker-desktop/)
[![ROS 2](https://img.shields.io/badge/ROS_2-Jazzy-22314E?logo=ros)](https://docs.ros.org/en/jazzy/)
[![Gazebo](https://img.shields.io/badge/Gazebo-Harmonic-6C3AB2?logo=gazebo)](https://gazebosim.org/)

</div>

---

## Contents

- [Who is this for](#who-is-this-for)
- [How it works](#how-it-works)
- [Step-by-step setup](#step-by-step-setup)
- [Build inside the desktop](#build-inside-the-desktop)
- [Launch](#launch)
- [Troubleshooting](#troubleshooting)
- [Packages](#packages)

---

## Who is this for

Windows users with **little or no Linux / ROS experience**. The whole simulation stack runs inside a single Docker container; you only ever interact with:

- **Docker Desktop** *(one-time install)*
- **PowerShell** *(to start the container)*
- **A browser** *(to use the Linux desktop)*

If you already work on Linux natively, use [`jazzy-gazebo-GNU-linux`](../../tree/jazzy-gazebo-GNU-linux) instead. For Isaac Sim, see [`jazzy-isaac-GNU-linux`](../../tree/jazzy-isaac-GNU-linux).

---

## How it works

```
┌────────────────────────────────────────────────────────────┐
│                       Windows host                         │
│                                                            │
│   PowerShell ──► docker compose ──► Docker Desktop (WSL2)  │
│                                          │                 │
│                                          ▼                 │
│                                  ┌────────────────┐        │
│                                  │ Linux container│        │
│                                  │  ROS 2 Jazzy   │        │
│                                  │  Gazebo + Xvfb │        │
│                                  │  + noVNC :6080 │        │
│                                  └────────┬───────┘        │
│                                           │                │
│   Browser ─────────────────────────────────► http://...    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

The container ships a virtual X server (`Xvfb`), a VNC bridge (`x11vnc`), and a websocket gateway (`noVNC`) so that Gazebo, RViz, and any other Linux GUI can be opened from the browser tab.

---

## Step-by-step setup

### 1. Install Docker Desktop

Download from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) and run the installer. Keep the default WSL 2 option.

<p align="center">
  <img src="assets/docker-desktop-download.png" alt="Docker Desktop download page" width="640" />
</p>

### 2. Enable the WSL 2 backend

Open Docker Desktop → **Settings → General** → check **Use the WSL 2 based engine** → **Apply & restart**.

### 3. Clone the repository

In PowerShell:

```powershell
git clone <repo-url> kumi_stack
cd kumi_stack
git checkout jazzy-gazebo-win
```

### 4. Build the container

```powershell
docker compose -f .devcontainer/docker-compose.yml build
```

The first build can take several minutes.

### 5. Start the container

```powershell
docker compose -f .devcontainer/docker-compose.yml up
```

Wait until you see:

```
noVNC ready → http://127.0.0.1:6080/vnc.html
```

### 6. Open the Linux desktop

Navigate to **<http://127.0.0.1:6080/vnc.html>** in any browser (Chrome, Edge, Firefox) and click **Connect**. A Linux desktop loads inside the browser tab.

### 7. Open a terminal in the desktop

Right-click on the desktop → **Open Terminal** (or use the taskbar terminal icon).

---

## Build inside the desktop

Inside the noVNC desktop terminal:

```bash
source /opt/ros/jazzy/setup.bash
cd /workspaces/kumi_stack
colcon build --symlink-install
source install/setup.bash
```

The very first launch runs the bootstrap script automatically — it installs Poetry, resolves rosdep, and builds the workspace once.

---

## Launch

```bash
ros2 launch kumi_bringup sim_bringup.launch.py
```

Gazebo and any other GUI tools open inside the same browser desktop.

See [`src/kumi_bringup/README.md`](src/kumi_bringup/README.md) for the full argument reference.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Browser cannot connect to `127.0.0.1:6080` | Wait for the `noVNC ready` log line; verify the container is running with `docker ps`. |
| Black screen in noVNC | The X server may not have come up yet — refresh after a few seconds. |
| Build fails with `ros-jazzy-...` missing | Re-run with a clean build cache: `docker compose -f .devcontainer/docker-compose.yml build --no-cache`. |
| Container exits immediately | Allocate at least 4 GB of memory to WSL 2 (Docker Desktop → Settings → Resources). |
| Gazebo runs but is slow | The container uses Mesa software rendering — heavy worlds may stutter. Start with `world:=my_empty`. |
| Browser closes / connection drops | The noVNC tab needs to stay open while you work — open more terminals from inside the desktop, not from PowerShell. |

---

## Packages

| Package | Docs |
|---|---|
| `kumi_description` | [README](src/kumi_description/README.md) |
| `kumi_control` | [README](src/kumi_control/README.md) |
| `kumi_sim` | [README](src/kumi_sim/README.md) |
| `kumi_bringup` | [README](src/kumi_bringup/README.md) |
| `kumi_behavior` | [README](src/kumi_behavior/README.md) |
| `my_gz_gui_plugin` | [README](src/my_gz_gui_plugin/README.md) |
| `kumi_perception` | [README](src/kumi_perception/README.md) |

---

## License

TBD.
