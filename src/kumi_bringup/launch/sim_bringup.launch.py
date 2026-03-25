import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, TextSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    description_pkg_share = get_package_share_directory('kumi_description')
    control_pkg_share = get_package_share_directory('kumi_control')
    sim_pkg_share = get_package_share_directory('kumi_sim')

    world = LaunchConfiguration('world')
    ros_namespace = LaunchConfiguration('ros_namespace')
    robot_name = LaunchConfiguration('robot_name')
    use_sim_time = LaunchConfiguration('use_sim_time')
    enable_sensors = LaunchConfiguration('enable_sensors')
    use_gz_bridge = LaunchConfiguration('use_gz_bridge')
    use_rviz = LaunchConfiguration('use_rviz')
    use_joint_state_publisher_gui = LaunchConfiguration('use_joint_state_publisher_gui')
    gz_start_delay = LaunchConfiguration('gz_start_delay')
    spawn_delay = LaunchConfiguration('spawn_delay')
    spawner_delay = LaunchConfiguration('spawner_delay')

    declare_world = DeclareLaunchArgument(
        'world',
        default_value='my_empty',
        description='World name without .sdf extension'
    )

    declare_ros_namespace = DeclareLaunchArgument(
        'ros_namespace',
        default_value='kumi',
        description='Namespace used for controllers and spawned ROS nodes'
    )

    declare_robot_name = DeclareLaunchArgument(
        'robot_name',
        default_value='bruno',
        description='Robot name passed to xacro'
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

    declare_use_gz_bridge = DeclareLaunchArgument(
        'use_gz_bridge',
        default_value='true',
        description='Bridge Gazebo topics to ROS 2'
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

    declare_gz_start_delay = DeclareLaunchArgument(
        'gz_start_delay',
        default_value='2.0',
        description='Delay before starting the description stack'
    )

    declare_spawn_delay = DeclareLaunchArgument(
        'spawn_delay',
        default_value='4.0',
        description='Delay before spawning the robot and control stack'
    )

    declare_spawner_delay = DeclareLaunchArgument(
        'spawner_delay',
        default_value='6.0',
        description='Delay before spawning controllers in kumi_control'
    )

    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(sim_pkg_share, 'launch', 'sim.launch.py')
        ),
        launch_arguments={
            'world': world,
            'namespace': ros_namespace,
        }.items()
    )

    description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(description_pkg_share, 'launch', 'description.launch.py')
        ),
        launch_arguments={
            'use_sim': 'true',
            'use_sim_time': use_sim_time,
            'enable_sensors': enable_sensors,
            'use_joint_state_publisher_gui': use_joint_state_publisher_gui,
            'use_rviz': use_rviz,
            'robot_name': robot_name,
            'ros_namespace': ros_namespace,
        }.items()
    )

    controller_manager_name = PathJoinSubstitution([
        TextSubstitution(text='/'),
        ros_namespace,
        'controller_manager'
    ])

    control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(control_pkg_share, 'launch', 'control.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_sim': 'true',
            'enable_sensors': enable_sensors,
            'robot_name': robot_name,
            'start_controller_manager': 'false',
            'controller_manager_name': controller_manager_name,
            'spawner_delay': spawner_delay,
            'namespace': ros_namespace,
        }.items()
    )

    spawn_poses = {
        'my_empty': {'x': '0.0', 'y': '0.0', 'z': '0.3', 'yaw': '0.0'},
        'stairs': {'x': '0.0', 'y': '0.0', 'z': '0.3', 'yaw': '0.0'},
    }

    xacro_file = PathJoinSubstitution([
        FindPackageShare('kumi_description'),
        'urdf',
        'kumi.xacro'
    ])

    controllers_file = PathJoinSubstitution([
        FindPackageShare('kumi_control'),
        'config',
        'trajectory_control_config.yaml'
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

    gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/front_camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/front_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            '/front_depth/image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/front_depth/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        output='screen',
        condition=IfCondition(use_gz_bridge),
    )

    delayed_robot_stack = TimerAction(
        period=gz_start_delay,
        actions=[description_launch]
    )

    delayed_spawn_and_control = TimerAction(
        period=spawn_delay,
        actions=[
            spawn_entity,
            control_launch,
            gz_bridge,
        ]
    )

    return LaunchDescription([
        declare_world,
        declare_ros_namespace,
        declare_robot_name,
        declare_use_sim_time,
        declare_enable_sensors,
        declare_use_gz_bridge,
        declare_use_rviz,
        declare_use_joint_state_publisher_gui,
        declare_gz_start_delay,
        declare_spawn_delay,
        declare_spawner_delay,
        sim_launch,
        delayed_robot_stack,
        delayed_spawn_and_control,
    ])
