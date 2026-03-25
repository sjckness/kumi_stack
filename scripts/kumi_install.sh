#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SRC_DIR="${WS_DIR}/src"
VENV_DIR="${WS_DIR}/.venv"

detect_ros_distro() {
  if [[ -n "${ROS_DISTRO:-}" ]]; then
    echo "${ROS_DISTRO}"
    return
  fi

  if [[ -d /opt/ros/jazzy ]]; then
    echo "jazzy"
    return
  fi

  local first_distro
  first_distro="$(find /opt/ros -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -n 1 | xargs -r basename)"
  if [[ -n "${first_distro}" ]]; then
    echo "${first_distro}"
    return
  fi

  echo "Impossibile determinare ROS_DISTRO" >&2
  exit 1
}

ROS_DISTRO_NAME="$(detect_ros_distro)"
ROS_SETUP="/opt/ros/${ROS_DISTRO_NAME}/setup.bash"

if [[ ! -f "${ROS_SETUP}" ]]; then
  echo "File non trovato: ${ROS_SETUP}" >&2
  exit 1
fi

echo "Workspace: ${WS_DIR}"
echo "ROS_DISTRO: ${ROS_DISTRO_NAME}"
echo "Python venv: ${VENV_DIR}"
echo

set +u
source "${ROS_SETUP}"
set -u

echo "Installing system and ROS packages..."

sudo apt-get update
sudo apt-get install -y \
  build-essential \
  git \
  python3-pip \
  python3-venv \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool

echo "Setting up rosdep..."

if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init || true
fi

rosdep update

echo "Creating Python virtual environment..."
if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

set +u
source "${VENV_DIR}/bin/activate"
set -u

echo "Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install \
  numpy \
  PyYAML \
  empy \
  catkin-pkg \
  lark \
  jinja2 \
  typeguard

echo "Installing ROS dependencies from src..."
echo "Skipping rosdep key: ament_python"

rosdep install \
  --from-paths "${SRC_DIR}" \
  --ignore-src \
  --rosdistro "${ROS_DISTRO_NAME}" \
  --skip-keys "ament_python" \
  -r -y

echo "Building workspace..."
cd "${WS_DIR}"
colcon build --symlink-install

cat <<EOF

INSTALLAZIONE COMPLETATA

Python packages installati esplicitamente:
- numpy
- PyYAML
- empy
- catkin-pkg
- lark
- jinja2
- typeguard

EOF
