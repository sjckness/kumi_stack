import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    UnsetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import PushRosNamespace


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
    declare_world = DeclareLaunchArgument(
        'world',
        default_value='my_empty',
        description='World name without .sdf extension'
    )

    declare_namespace = DeclareLaunchArgument(
        'namespace',
        default_value='kumi',
        description='namespace'
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
        SetEnvironmentVariable(
            name='GZ_IP',
            value='127.0.0.1'
        ),
        SetEnvironmentVariable(
            name='IGN_IP',
            value='127.0.0.1'
        ),
        SetEnvironmentVariable(
            name='KUMI_GZ_WORLD',
            value=world
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
    gui_config = PathJoinSubstitution([
        FindPackageShare('kumi_sim'),
        'config',
        'kumi_gui.config'
    ])

    gz_sim = GroupAction([
        PushRosNamespace(namespace),

        IncludeLaunchDescription(
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
                    TextSubstitution(text=' -v 5 -r --gui-config '),
                    gui_config,
                ]
            }.items()
        )
    ])

    return LaunchDescription([
        *clean_env_actions,
        *gz_env,
        declare_world,
        declare_namespace,
        gz_sim,
    ])
