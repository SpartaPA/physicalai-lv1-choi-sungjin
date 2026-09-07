import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'turtle_py'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='chsjh',
    maintainer_email='chsjh@example.com',
    description='Python turtlesim nodes for the ROS 2 module 2 assignment',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'distance_publisher = turtle_py.distance_publisher:main',
            'warn_subscriber = turtle_py.warn_subscriber:main',
            'square_driver = turtle_py.square_driver:main',
            'service_sequence_client = turtle_py.service_sequence_client:main',
            'rotate_action_client = turtle_py.rotate_action_client:main',
            'waypoint_publisher = turtle_py.waypoint_publisher:main',
            'waypoint_subscriber = turtle_py.waypoint_subscriber:main',
            'slow_distance_subscriber = turtle_py.slow_distance_subscriber:main',
            'draw_polygon_server = turtle_py.draw_polygon_server:main',
            'draw_polygon_client = turtle_py.draw_polygon_client:main',
            'pose_tf_broadcaster = turtle_py.pose_tf_broadcaster:main',
            'waypoint_marker_publisher = turtle_py.waypoint_marker_publisher:main',
        ],
    },
)
