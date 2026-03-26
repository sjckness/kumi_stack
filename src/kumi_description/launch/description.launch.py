import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def _clean_gui_environment():
    env = dict(os.environ)

    ld_library_path = env.get('LD_LIBRARY_PATH', '')
    if ld_library_path:
        filtered_paths = [
            path for path in ld_library_path.split(':')
            if path and '/snap/' not in path
        ]
        env['LD_LIBRARY_PATH'] = ':'.join(filtered_paths)

    for key in list(env.keys()):
        if key.startswith('SNAP'):
            env.pop(key, None)

    return env


def _gui_prefix():
    keys_to_unset = [
        'SNAP',
        'SNAP_ARCH',
        'SNAP_COMMON',
        'SNAP_CONTEXT',
        'SNAP_COOKIE',
        'SNAP_DATA',
        'SNAP_EUID',
        'SNAP_INSTANCE_NAME',
        'SNAP_LAUNCHER_ARCH_TRIPLET',
        'SNAP_LIBRARY_PATH',
        'SNAP_NAME',
        'SNAP_REAL_HOME',
        'SNAP_REVISION',
        'SNAP_UID',
        'SNAP_USER_COMMON',
        'SNAP_USER_DATA',
        'SNAP_VERSION',
        'GDK_PIXBUF_MODULEDIR',
        'GDK_PIXBUF_MODULE_FILE',
        'GIO_MODULE_DIR',
        'GSETTINGS_SCHEMA_DIR',
        'GTK_EXE_PREFIX',
        'GTK_IM_MODULE_FILE',
        'GTK_PATH',
        'XDG_DATA_HOME',
    ]
    return 'env ' + ' '.join(f'-u {key}' for key in keys_to_unset)


def generate_launch_description():
    pkg_name = 'kumi_description'
    pkg_share = get_package_share_directory(pkg_name)
    gui_env = _clean_gui_environment()
    gui_prefix = _gui_prefix()

    use_sim_time = LaunchConfiguration('use_sim_time')
    use_sim = LaunchConfiguration('use_sim')
    enable_sensors = LaunchConfiguration('enable_sensors')
    use_joint_state_publisher_gui = LaunchConfiguration('use_joint_state_publisher_gui')
    use_rviz = LaunchConfiguration('use_rviz')
    robot_name = LaunchConfiguration('robot_name')
    ros_namespace = LaunchConfiguration('ros_namespace')
    control_config = LaunchConfiguration('control_config')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock if true'
    )

    declare_use_sim = DeclareLaunchArgument(
        'use_sim',
        default_value='false',
        description='Generate robot for simulation'
    )

    declare_enable_sensors = DeclareLaunchArgument(
        'enable_sensors',
        default_value='true',
        description='Enable sensors in xacro'
    )

    declare_use_joint_state_publisher_gui = DeclareLaunchArgument(
        'use_joint_state_publisher_gui',
        default_value='true',
        description='Launch joint_state_publisher_gui'
    )

    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Launch RViz'
    )

    declare_robot_name = DeclareLaunchArgument(
        'robot_name',
        default_value='bruno',
        description='Robot name passed to xacro'
    )

    declare_ros_namespace = DeclareLaunchArgument(
        'ros_namespace',
        default_value='kumi',
        description='ROS namespace used by ros2_control and description'
    )

    declare_control_config = DeclareLaunchArgument(
        'control_config',
        default_value=PathJoinSubstitution([
            FindPackageShare('kumi_control'),
            'config',
            'trajectory_control_config.yaml'
        ]),
        description='Path to the ros2_control controllers yaml file'
    )

    xacro_file = PathJoinSubstitution([
        FindPackageShare(pkg_name),
        'urdf',
        'kumi.xacro'
    ])

    rviz_config = PathJoinSubstitution([
        FindPackageShare(pkg_name),
        'rviz',
        'description.rviz'
    ])

    robot_description_content = Command([
        'xacro ',
        xacro_file,
        ' use_sim:=', use_sim,
        ' enable_sensors:=', enable_sensors,
        ' robot_name:=', robot_name,
        ' pkg_share:=', pkg_share,
        ' ros_namespace:=', ros_namespace,
        ' control_config:=', control_config,
    ])

    robot_description = {
        'robot_description': ParameterValue(
            robot_description_content,
            value_type=str
        )
    }

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[
            robot_description,
            {'use_sim_time': use_sim_time}
        ]
    )

    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        condition=IfCondition(use_joint_state_publisher_gui),
        prefix=gui_prefix,
        additional_env=gui_env,
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        condition=IfCondition(use_rviz),
        name='rviz2',
        prefix=gui_prefix,
        additional_env=gui_env,
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}]
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_use_sim,
        declare_enable_sensors,
        declare_use_joint_state_publisher_gui,
        declare_use_rviz,
        declare_robot_name,
        declare_ros_namespace,
        declare_control_config,
        joint_state_publisher_gui,
        robot_state_publisher,
        rviz2,
    ])
