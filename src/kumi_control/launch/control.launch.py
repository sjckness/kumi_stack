from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, TextSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    controller_manager_name = LaunchConfiguration('controller_manager_name')
    controllers_file = LaunchConfiguration('controllers_file')
    spawner_delay = LaunchConfiguration('spawner_delay')
    controller_manager_timeout = LaunchConfiguration('controller_manager_timeout')
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_sim = LaunchConfiguration('use_sim')
    enable_sensors = LaunchConfiguration('enable_sensors')
    robot_name = LaunchConfiguration('robot_name')
    start_controller_manager = LaunchConfiguration('start_controller_manager')
    namespace = LaunchConfiguration('namespace')

    declare_namespace = DeclareLaunchArgument(
        'namespace',
        default_value='kumi',
        description='Namespace'
    )
    
    declare_controller_manager_name = DeclareLaunchArgument(
        'controller_manager_name',
        default_value=PathJoinSubstitution([
            TextSubstitution(text='/'),
            namespace,
            'controller_manager'
        ]),
        description='Fully-qualified controller manager name (includes namespace)'
    )

    declare_controllers_file = DeclareLaunchArgument(
        'controllers_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('kumi_control'),
            'config',
            'trajectory_control_config.yaml'
        ]),
        description='Path to the controllers yaml file'
    )

    declare_spawner_delay = DeclareLaunchArgument(
        'spawner_delay',
        default_value='6.0',
        description='Delay before spawning controllers'
    )

    declare_controller_manager_timeout = DeclareLaunchArgument(
        'controller_manager_timeout',
        default_value='30.0',
        description='Timeout (s) for spawners waiting on the controller manager'
    )

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation clock if true'
    )

    declare_use_sim = DeclareLaunchArgument(
        'use_sim',
        default_value='true',
        description='Generate robot for simulation (needed for Gazebo plugins)'
    )

    declare_enable_sensors = DeclareLaunchArgument(
        'enable_sensors',
        default_value='true',
        description='Enable sensors in the xacro description'
    )

    declare_robot_name = DeclareLaunchArgument(
        'robot_name',
        default_value='bruno',
        description='Robot name passed to xacro'
    )

    declare_start_controller_manager = DeclareLaunchArgument(
        'start_controller_manager',
        default_value='true',
        description='Start a ros2_control_node (disable when controller manager is provided by the simulator)'
    )

    xacro_file = PathJoinSubstitution([
        FindPackageShare('kumi_description'),
        'urdf',
        'kumi.xacro'
    ])

    robot_description_content = Command([
        'xacro ',
        xacro_file,
        ' use_sim:=', use_sim,
        ' enable_sensors:=', enable_sensors,
        ' robot_name:=', robot_name,
        ' pkg_share:=', FindPackageShare('kumi_description'),
        ' control_config:=', controllers_file,
    ])

    robot_description = {
        'robot_description': ParameterValue(robot_description_content, value_type=str)
    }

    controller_manager = Node(
        package='controller_manager',
        executable='ros2_control_node',
        namespace=namespace,
        parameters=[robot_description, controllers_file, {'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(start_controller_manager),
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'joint_state_broadcaster',
            '--controller-manager', controller_manager_name,
            '--param-file', controllers_file,
            '--controller-manager-timeout', controller_manager_timeout,
        ],
        output='screen',
    )

    trajectory_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'multi_joint_trajectory_controller',
            '--controller-manager', controller_manager_name,
            '--param-file', controllers_file,
            '--controller-manager-timeout', controller_manager_timeout,
        ],
        output='screen',
    )

    delayed_spawners = TimerAction(
        period=spawner_delay,
        actions=[
            joint_state_broadcaster_spawner,
            trajectory_controller_spawner,
        ]
    )

    return LaunchDescription([
        declare_controller_manager_name,
        declare_controllers_file,
        declare_spawner_delay,
        declare_use_sim_time,
        declare_use_sim,
        declare_enable_sensors,
        declare_robot_name,
        declare_namespace,
        declare_start_controller_manager,
        declare_controller_manager_timeout,
        controller_manager,
        delayed_spawners,
    ])
