import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    use_gui = LaunchConfiguration("use_gui")
    use_rviz = LaunchConfiguration("use_rviz")

    declare_use_gui = DeclareLaunchArgument(
        "use_gui",
        default_value="true",
        description="Launch the Tkinter control GUI",
    )
    declare_use_rviz = DeclareLaunchArgument(
        "use_rviz",
        default_value="false",
        description="Launch RViz",
    )

    # Resolve paths eagerly in Python so the xacro command is a plain string
    # with no substitution ambiguity. This also lets us pass control_config
    # explicitly, preventing xacro from trying to evaluate $(find kumi_control)
    # which can silently fail and produce an empty robot_description.
    kumi_description_share = get_package_share_directory("kumi_description")
    kumi_control_share = get_package_share_directory("kumi_control")
    xacro_file = os.path.join(kumi_description_share, "urdf", "kumi.xacro")
    control_config = os.path.join(
        kumi_control_share, "config", "trajectory_control_config.yaml"
    )

    robot_description_content = Command(
        [
            "xacro ",
            xacro_file,
            " use_sim:=false",
            " enable_sensors:=false",
            " robot_name:=kumi",
            " ros_namespace:=kumi",
            " control_config:=",
            control_config,
            " pkg_share:=",
            kumi_description_share,
        ]
    )

    robot_description = {
        "robot_description": ParameterValue(robot_description_content, value_type=str)
    }

    # RSP runs in /kumi namespace → publishes /kumi/robot_description naturally.
    # TF topics are remapped to the global tree so RViz sees /tf and /tf_static.
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        namespace="kumi",
        parameters=[robot_description, {"use_sim_time": False}],
        remappings=[
            ("tf", "/tf"),
            ("tf_static", "/tf_static"),
        ],
        output="screen",
    )

    # Sequenziatore CSV: pubblica JointState su /kumi/joint_commands
    seq_traj_controller = Node(
        package="kumi_control",
        executable="kumi_seq_traj_controller",
        name="kumi_seq_traj_controller",
        parameters=[
            {
                "use_isaac": True,
                "joint_commands_topic": "/kumi/joint_commands",
                "enable_topic": "/kumi/kumi_seq_traj_controller/enabled",
                "gait_topic": "/kumi/kumi_seq_traj_controller/gait",
            }
        ],
        output="screen",
    )

    # GUI runs in /kumi namespace so all relative topics resolve correctly:
    # kumi_seq_traj_controller/enabled -> /kumi/kumi_seq_traj_controller/enabled
    # kumi_seq_traj_controller/gait    -> /kumi/kumi_seq_traj_controller/gait
    # kumi_behavior/emergency          -> /kumi/kumi_behavior/emergency
    control_gui = Node(
        package="kumi_control",
        executable="kumi_control_gui",
        name="kumi_control_gui",
        namespace="kumi",
        output="screen",
        condition=IfCondition(use_gui),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription(
        [
            declare_use_gui,
            declare_use_rviz,
            robot_state_publisher,
            seq_traj_controller,
            control_gui,
            rviz,
        ]
    )
