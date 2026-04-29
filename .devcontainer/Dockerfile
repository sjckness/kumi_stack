FROM osrf/ros:jazzy-desktop

# Install system deps, Gazebo Harmonic (via ros-jazzy-ros-gz) and Python tooling.
# User creation is handled by the devcontainer common-utils feature (devcontainer.json).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    sudo \
    python3-pip \
    python3-venv \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    pipx \
    ros-jazzy-ros-gz \
    ros-jazzy-gz-ros2-control \
    ros-jazzy-rmw-cyclonedds-cpp \
    ros-jazzy-py-trees \
    ros-jazzy-rclpy \
    ros-jazzy-tf2-ros \
    ros-jazzy-std-msgs \
    ros-jazzy-sensor-msgs \
    ros-jazzy-trajectory-msgs \
    ros-jazzy-controller-manager \
    ros-jazzy-ros2-controllers \
    ros-jazzy-joint-state-publisher-gui \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-xacro \
    ros-jazzy-rviz2 \
    ros-jazzy-rmw-fastrtps-cpp \
    libgl1 \
    libglx-mesa0 \
    libgl1-mesa-dri \
    mesa-utils \
    x11-apps \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x (required by Claude Code and Codex CLIs)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code and OpenAI Codex CLIs globally
RUN npm install -g @anthropic-ai/claude-code @openai/codex

ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# Create render group if the base image does not already provide it.
# The devcontainer also passes --group-add=render for GPU device access.
RUN groupadd -f -r render

# Initialize rosdep (as root; update happens in postCreate as the final user)
RUN rosdep init || true

WORKDIR /workspaces/kumi_stack
