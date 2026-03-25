from glob import glob
from setuptools import find_packages, setup

package_name = 'kumi_description'

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

        # URDF / xacro
        (f'share/{package_name}/urdf/', glob('urdf/*.xacro')),

        # meshes
        (f'share/{package_name}/meshes/', glob('meshes/*')),

        # RViz config
        (f'share/{package_name}/rviz', glob('rviz/*.rviz')),
        
        # Config files (YAML)
        (f'share/{package_name}/config', glob('config/*.yaml')),
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
        ],
    },
)
