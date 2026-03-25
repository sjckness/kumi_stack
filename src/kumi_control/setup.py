from glob import glob
from setuptools import find_packages, setup

package_name = 'kumi_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Launch files
        (f'share/{package_name}/launch', glob('launch/*.py')),

        # Config files (YAML)
        (f'share/{package_name}/config', glob('config/*.yaml')),

        # CSV resources
        (f'share/{package_name}/resource', glob('resource/*.csv')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='andreas',
    maintainer_email='andreas21steffens@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'PID_effort_controller = kumi_control.PID_effort_controller:main',
            'kumi_seq_traj_controller = kumi_control.kumi_seq_traj_controller:main',
            'kumi_seq_traj_controller_keyboard = kumi_control.kumi_seq_traj_controller_keyboard:main',
            'kumi_trajectory_controller = kumi_control.kumi_trajectory_controller:main',
        ],
    },
)
