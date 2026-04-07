#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

def generate_launch_description():
    pkg_name = 'hoainam_one'
    pkg_dir = get_package_share_directory(pkg_name)

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    slam_params_file = LaunchConfiguration('slam_params_file')
    enable_rviz = LaunchConfiguration('enable_rviz', default='true')

    default_slam_params = os.path.join(pkg_dir, 'config', 'mapper_params_online_async.yaml')

    # 1. Robot State Publisher
    rsp_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_dir, 'launch', 'rsp.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # 2. SLLiDAR C1 (chỉ lidar)
    sllidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_dir, 'launch', 'view_sllidar_c1_launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # 3. SLAM Toolbox
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                get_package_share_directory('slam_toolbox'),
                'launch',
                'online_async_launch.py'
            ])
        ]),
        launch_arguments={
            'slam_params_file': slam_params_file,
            'use_sim_time': use_sim_time,
            'launch_rviz': 'false'
        }.items()
    )

    # 4. RViz2 (chỉ 1 cái)
    rviz_config_file = os.path.join(pkg_dir, 'config', 'map.rviz')
    if not os.path.exists(rviz_config_file):
        rviz_config_file = os.path.join(pkg_dir, 'config', 'drive_bot.rviz')

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file] if os.path.exists(rviz_config_file) else [],
        condition=IfCondition(enable_rviz),
        output='screen'
    )

    return LaunchDescription([
        LogInfo(msg='[LAUNCH] Robot + SLLiDAR C1 + SLAM Toolbox + RViz2 (chỉ 1 RViz)'),

        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('slam_params_file', default_value=default_slam_params),
        DeclareLaunchArgument(
            'enable_rviz',
            default_value='true',
            description='Launch RViz2 on this machine'
        ),

        rsp_launch,
        sllidar_launch,
        slam_launch,
        rviz_node,
    ])
