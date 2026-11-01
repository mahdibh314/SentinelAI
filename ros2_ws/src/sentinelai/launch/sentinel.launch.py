"""Launch SentinelAI nodes."""
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='sentinelai',
            executable='scanner_node',
            name='scanner_node',
            output='screen'
        ),
        Node(
            package='sentinelai',
            executable='access_node',
            name='access_node',
            output='screen'
        ),
        Node(
            package='sentinelai',
            executable='vision_node',
            name='vision_node',
            output='screen'
        ),
        Node(
            package='sentinelai',
            executable='web_bridge',
            name='web_bridge',
            output='screen'
        ),
    ])
