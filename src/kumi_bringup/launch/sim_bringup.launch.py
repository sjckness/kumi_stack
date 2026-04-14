import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    sim_pkg_share = get_package_share_directory('kumi_sim')

    world = LaunchConfiguration('world')
    robot_xacro = LaunchConfiguration('robot_xacro')
    ros_namespace = LaunchConfiguration('ros_namespace')
    robot_name = LaunchConfiguration('robot_name')
    use_sim_time = LaunchConfiguration('use_sim_time')
    enable_sensors = LaunchConfiguration('enable_sensors')
    use_rviz = LaunchConfiguration('use_rviz')
    use_joint_state_publisher_gui = LaunchConfiguration('use_joint_state_publisher_gui')
    use_control_gui = LaunchConfiguration('use_control_gui')
    spawn_delay = LaunchConfiguration('spawn_delay')
    spawner_delay = LaunchConfiguration('spawner_delay')

    declare_world = DeclareLaunchArgument(
        'world',
        default_value='my_empty',
        description='World name without .sdf extension'
    )

    declare_robot_xacro = DeclareLaunchArgument(
        'robot_xacro',
        default_value='kumi.xacro',
        description='name of xacro file'
    )

    declare_robot_name = DeclareLaunchArgument(
        'robot_name',
        default_value='bruno',
        description='Robot name passed to xacro'
    )

    declare_ros_namespace = DeclareLaunchArgument(
        'ros_namespace',
        default_value='bruno',
        description='Namespace used for controllers and spawned ROS nodes'
    )

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation clock if true'
    )

    declare_enable_sensors = DeclareLaunchArgument(
        'enable_sensors',
        default_value='true',
        description='Enable camera and depth sensors in xacro'
    )

    declare_use_rviz = DeclareLaunchArgument(
        'use_rviz',
        default_value='false',
        description='Launch RViz from description.launch.py'
    )

    declare_use_joint_state_publisher_gui = DeclareLaunchArgument(
        'use_joint_state_publisher_gui',
        default_value='false',
        description='Launch joint_state_publisher_gui from description.launch.py'
    )

    declare_use_control_gui = DeclareLaunchArgument(
        'use_control_gui',
        default_value='false',
        description='Launch the control GUI from kumi_control'
    )

    declare_spawn_delay = DeclareLaunchArgument(
        'spawn_delay',
        default_value='8.0',
        description='Delay before spawning the robot and control stack'
    )

    declare_spawner_delay = DeclareLaunchArgument(
        'spawner_delay',
        default_value='10.0',
        description='Delay before spawning controllers in kumi_control'
    )

    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(sim_pkg_share, 'launch', 'sim.launch.py')
        ),
        launch_arguments={
            'world': world,
            'namespace': ros_namespace,
            'robot_xacro': robot_xacro,
            'robot_name': robot_name,
            'enable_sensors': enable_sensors,
        }.items()
    )

    controllers_file = PathJoinSubstitution([
        FindPackageShare('kumi_control'),
        'config',
        'trajectory_control_config.yaml'
    ])

    robot_runtime_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(sim_pkg_share, 'launch', 'robot_runtime.launch.py')
        ),
        launch_arguments={
            'namespace': ros_namespace,
            'robot_name': robot_name,
            'use_sim_time': use_sim_time,
            'enable_sensors': enable_sensors,
            'spawner_delay': spawner_delay,
            'use_gz_bridge': 'true',
            'use_control_gui': use_control_gui,
            'use_rviz': use_rviz,
            'use_joint_state_publisher_gui': use_joint_state_publisher_gui,
        }.items()
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
        ],
        output='screen',
    )

    spawn_poses = {
        'my_empty': {'x': '0.0', 'y': '0.0', 'z': '0.3', 'yaw': '0.0'},
        'piazza':   {'x': '0.0', 'y': '0.0', 'z': '0.3', 'yaw': '0.0'},
        'stairs':   {'x': '-0.15', 'y': '0.0', 'z': '0.3', 'yaw': '3.141592653589793'},
    }

    xacro_file = PathJoinSubstitution([
        FindPackageShare('kumi_description'),
        'urdf',
        robot_xacro
    ])

    robot_description_str = Command([
        'xacro ',
        xacro_file,
        ' use_sim:=true',
        ' enable_sensors:=', enable_sensors,
        ' robot_name:=', robot_name,
        ' pkg_share:=', FindPackageShare('kumi_description'),
        ' control_config:=', controllers_file,
        ' ros_namespace:=', ros_namespace,
    ])

    def make_spawn_entity(context):
        selected_world = world.perform(context)
        pose = spawn_poses.get(selected_world, spawn_poses['my_empty'])
        resolved_robot_name = robot_name.perform(context)

        return [Node(
            package='ros_gz_sim',
            executable='create',
            output='screen',
            arguments=[
                '-world', selected_world,
                '-string', robot_description_str,
                '-x', pose['x'],
                '-y', pose['y'],
                '-z', pose['z'],
                '-R', '0.0',
                '-P', '0.0',
                '-Y', pose['yaw'],
                '-name', resolved_robot_name,
            ],
        )]

    spawn_entity = OpaqueFunction(function=make_spawn_entity)

    delayed_spawn_and_control = TimerAction(
        period=spawn_delay,
        actions=[
            spawn_entity,
            robot_runtime_launch,
        ]
    )

    return LaunchDescription([
        declare_world,
        declare_robot_xacro,
        declare_ros_namespace,
        declare_robot_name,
        declare_use_sim_time,
        declare_enable_sensors,
        declare_use_rviz,
        declare_use_joint_state_publisher_gui,
        declare_use_control_gui,
        declare_spawn_delay,
        declare_spawner_delay,
        sim_launch,
        clock_bridge,
        delayed_spawn_and_control,
    ])
