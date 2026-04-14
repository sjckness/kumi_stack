#!/usr/bin/env bash
# Post-create setup: installs Python deps, resolves ROS deps, builds the workspace.
# Runs once after the container is created.

set -euo pipefail

WS_DIR="/workspaces/kumi_stack"
cd "${WS_DIR}"

if [ "${EUID}" -eq 0 ]; then
  echo "Do not run this setup as root; use the devcontainer user instead." >&2
  exit 1
fi

mkdir -p build install log .colcon

echo "=== Sourcing ROS ==="
set +u
source /opt/ros/jazzy/setup.bash
set -u

echo "=== Installing Poetry ==="
export PATH="$HOME/.local/bin:$PATH"
if ! command -v poetry &>/dev/null; then
  pipx install poetry
  pipx ensurepath
fi
echo "Using $(poetry --version)"

echo "=== Updating rosdep ==="
rosdep update

echo "=== Installing Python dependencies (Poetry) ==="
poetry config virtualenvs.in-project true --local
poetry install --no-root

echo "=== Resolving ROS dependencies (rosdep) ==="
rosdep install \
  --from-paths src \
  --ignore-src \
  --rosdistro jazzy \
  --skip-keys "ament_python" \
  -r -y

echo "=== Building workspace (colcon) ==="
colcon build --symlink-install

echo "=== Appending workspace overlay to .bashrc ==="
OVERLAY_LINE="source /workspaces/kumi_stack/install/setup.bash"
grep -qxF "${OVERLAY_LINE}" ~/.bashrc || echo "${OVERLAY_LINE}" >> ~/.bashrc

echo ""
echo "Setup complete. Workspace is ready."
echo "  - Activate venv : source .venv/bin/activate"
echo "  - Source install : source install/setup.bash"
echo "  - Launch sim     : ros2 launch kumi_bringup sim_bringup.launch.py"
