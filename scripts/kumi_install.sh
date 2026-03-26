#!/usr/bin/env bash

set -euo pipefail

# === PATH SETUP ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SRC_DIR="${WS_DIR}/src"

# === DETECT ROS DISTRO ===
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
echo

# === SOURCE ROS ===
set +u
source "${ROS_SETUP}"
set -u

echo "Installing system and ROS packages..."

sudo apt-get update
sudo apt-get install -y \
  build-essential \
  git \
  python3-pip \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool \
  pipx \
  "ros-${ROS_DISTRO_NAME}-py-trees" \
  "ros-${ROS_DISTRO_NAME}-rclpy" \
  "ros-${ROS_DISTRO_NAME}-tf2-ros" \
  "ros-${ROS_DISTRO_NAME}-std-msgs"

echo "Checking Poetry..."

if ! command -v poetry &> /dev/null; then
  echo "Installing Poetry..."
  pipx ensurepath
  pipx install poetry

  export PATH="$HOME/.local/bin:$PATH"
fi

echo "Using $(poetry --version)"

echo "Setting up rosdep..."

if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init || true
fi

rosdep update

echo "Installing Python dependencies via Poetry..."
cd "${WS_DIR}"
poetry config virtualenvs.in-project true --local
poetry install --no-root

echo "Installing ROS dependencies from src..."
echo "Skipping rosdep key: ament_python"
echo "Note: Python packages used inside the workspace venv are installed via Poetry."

rosdep install \
  --from-paths "${SRC_DIR}" \
  --ignore-src \
  --rosdistro "${ROS_DISTRO_NAME}" \
  --skip-keys "ament_python" \
  -r -y

echo "Building workspace..."
colcon build --symlink-install

cat <<EOF

INSTALLAZIONE COMPLETATA

EOF
