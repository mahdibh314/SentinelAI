from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'sentinelai'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mahdi',
    maintainer_email='mahdi@example.com',
    description='SentinelAI ROS 2 access control and intrusion system',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'scanner_node = sentinelai.scanner_node:main',
            'access_node = sentinelai.access_node:main',
            'vision_node = sentinelai.vision_node:main',
            'web_bridge = sentinelai.web_bridge:main',
        ],
    },
)
