#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    channel_type = LaunchConfiguration('channel_type', default='serial')
    serial_port = LaunchConfiguration('serial_port', default='/dev/ttyUSB0')
    serial_baudrate = LaunchConfiguration('serial_baudrate', default='460800')
    frame_id = LaunchConfiguration('frame_id', default='laser_frame')
    inverted = LaunchConfiguration('inverted', default='false')
    angle_compensate = LaunchConfiguration('angle_compensate', default='true')
    scan_mode = LaunchConfiguration('scan_mode', default='Standard')
    # Ignore the rear half of the scan where the robot body occludes the lidar.
    enable_angle_window_filter = LaunchConfiguration('enable_angle_window_filter', default='true')
    angle_window_min_deg = LaunchConfiguration('angle_window_min_deg', default='90.0')
    angle_window_max_deg = LaunchConfiguration('angle_window_max_deg', default='-90.0')

    return LaunchDescription([
        LogInfo(msg='[LAUNCH] SLLiDAR C1 - Chỉ chạy node lidar (dùng cho slam)'),

        DeclareLaunchArgument('channel_type', default_value=channel_type),
        DeclareLaunchArgument('use_sim_time', default_value=use_sim_time),
        DeclareLaunchArgument('serial_port', default_value=serial_port),
        DeclareLaunchArgument('serial_baudrate', default_value=serial_baudrate),
        DeclareLaunchArgument('frame_id', default_value=frame_id),
        DeclareLaunchArgument('inverted', default_value=inverted),
        DeclareLaunchArgument('angle_compensate', default_value=angle_compensate),
        DeclareLaunchArgument('scan_mode', default_value=scan_mode),
        DeclareLaunchArgument('enable_angle_window_filter', default_value=enable_angle_window_filter),
        DeclareLaunchArgument('angle_window_min_deg', default_value=angle_window_min_deg),
        DeclareLaunchArgument('angle_window_max_deg', default_value=angle_window_max_deg),

        Node(
            package='sllidar_ros2',
            executable='sllidar_node',
            name='sllidar_node',
            parameters=[{
                'channel_type': channel_type,
                'serial_port': serial_port,
                'serial_baudrate': serial_baudrate,
                'frame_id': frame_id,
                'inverted': inverted,
                'angle_compensate': angle_compensate,
                'scan_mode': scan_mode,
                'use_sim_time': use_sim_time,
                'enable_angle_window_filter': enable_angle_window_filter,
                'angle_window_min_deg': angle_window_min_deg,
                'angle_window_max_deg': angle_window_max_deg,
            }],
            output='screen'
        ),
    ])
