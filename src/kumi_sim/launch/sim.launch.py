import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    UnsetEnvironmentVariable,
)
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def _clean_ld_library_path():
    ld_library_path = os.environ.get('LD_LIBRARY_PATH', '')
    if not ld_library_path:
        return ''

    filtered_paths = [
        path for path in ld_library_path.split(':')
        if path and '/snap/' not in path
    ]
    return ':'.join(filtered_paths)


def generate_launch_description():
    sim_pkg_share = get_package_share_directory('kumi_sim')
    description_pkg_share = get_package_share_directory('kumi_description')

    world = LaunchConfiguration('world')
    namespace = LaunchConfiguration('namespace')
    robot_xacro = LaunchConfiguration('robot_xacro')
    robot_name = LaunchConfiguration('robot_name')
    enable_sensors = LaunchConfiguration('enable_sensors')

    declare_world = DeclareLaunchArgument(
        'world',
        default_value='piazza',
        description='World name without .sdf extension'
    )

    declare_namespace = DeclareLaunchArgument(
        'namespace',
        default_value='kumi',
        description='namespace'
    )

    declare_robot_xacro = DeclareLaunchArgument(
        'robot_xacro',
        default_value='kumi.xacro',
        description='Xacro filename passed to spawn_despawn_node'
    )

    declare_robot_name = DeclareLaunchArgument(
        'robot_name',
        default_value='bruno',
        description='Robot name used by spawn_despawn_node'
    )

    declare_enable_sensors = DeclareLaunchArgument(
        'enable_sensors',
        default_value='true',
        description='Enable sensors for spawn_despawn_node xacro processing'
    )

    resource_paths = [
        sim_pkg_share,
        os.path.join(sim_pkg_share, 'worlds'),
        os.path.join(sim_pkg_share, 'models'),
        os.path.join(sim_pkg_share, 'meshes'),
        description_pkg_share,
        os.path.join(description_pkg_share, 'meshes'),
    ]

    gz_env = []
    for env_var in ['GZ_SIM_RESOURCE_PATH', 'IGN_GAZEBO_RESOURCE_PATH']:
        for path in resource_paths:
            gz_env.append(
                AppendEnvironmentVariable(
                    name=env_var,
                    value=path,
                    separator=':'
                )
            )

    clean_env_actions = [
        SetEnvironmentVariable(
            name='LD_LIBRARY_PATH',
            value=_clean_ld_library_path()
        ),
    ]

    for env_var in [
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
    ]:
        clean_env_actions.append(UnsetEnvironmentVariable(name=env_var))

    world_file = PathJoinSubstitution([
        FindPackageShare('kumi_sim'),
        'worlds',
        world
    ])

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                FindPackageShare('ros_gz_sim').find('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            )
        ),
        launch_arguments={
            'gz_args': [
                world_file,
                TextSubstitution(text='.sdf'),
                TextSubstitution(text=' -v 5 -r')
            ]
        }.items()
    )

    spawn_despawn_node = Node(
        package='kumi_sim',
        executable='spawn_despawn_node',
        parameters=[{
            'world': world,
            'xacro_file': robot_xacro,
            'robot_name': robot_name,
            'ros_namespace': namespace,
            'enable_sensors': enable_sensors,
        }],
        output='screen',
    )

    return LaunchDescription([
        *clean_env_actions,
        *gz_env,
        declare_world,
        declare_namespace,
        declare_robot_xacro,
        declare_robot_name,
        declare_enable_sensors,
        gz_sim,
        spawn_despawn_node,
    ])
