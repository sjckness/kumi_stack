import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'kumi_sim'

data_files = [
    ('share/ament_index/resource_index/packages',
        ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    # Launch files
    (f'share/{package_name}/launch', glob('launch/*.py')),

    # meshes (flat)
    (f'share/{package_name}/meshes', glob('meshes/*')),
    
    # Config files
    (f'share/{package_name}/config', glob('config/*.yaml') + glob('config/*.config')),

    # Worlds
    (f'share/{package_name}/worlds', glob('worlds/*')),
]

# Preserve nested structure for models (e.g., cone_orange meshes/thumbnails)
for dirpath, _, filenames in os.walk('models'):
    if filenames:
        files = [os.path.join(dirpath, f) for f in filenames]
        install_dir = os.path.join('share', package_name, dirpath)
        data_files.append((install_dir, files))

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=data_files,
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
