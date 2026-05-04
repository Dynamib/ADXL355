from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='adxl355_viz',
            executable='viz_node',
            name='adxl355_viz_node',
            output='screen',
            parameters=[{
                'history_seconds': 60.0,
                'smoothing_window': 5,
                'smoothing_alpha': 0.3,
            }],
        ),
    ])
