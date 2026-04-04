#!/usr/bin/env python3

import os
from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
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
    serial_port = LaunchConfiguration('serial_port', default='/dev/ttyUSB0')
    serial_baudrate = LaunchConfiguration('serial_baudrate', default='460800')
    lidar_frame = LaunchConfiguration('lidar_frame', default='laser_frame')
    enable_angle_window_filter = LaunchConfiguration('enable_angle_window_filter', default='true')
    angle_window_min_deg = LaunchConfiguration('angle_window_min_deg', default='90.0')
    angle_window_max_deg = LaunchConfiguration('angle_window_max_deg', default='-90.0')
    use_rf2o = LaunchConfiguration('use_rf2o', default='true')
    enable_fake_odom_tf = LaunchConfiguration('enable_fake_odom_tf', default='false')
    enable_odom_axis_corrector = LaunchConfiguration('enable_odom_axis_corrector', default='true')
    enable_map_filter = LaunchConfiguration('enable_map_filter', default='true')
    enable_plc_node = LaunchConfiguration('enable_plc_node', default='false')

    # Đường dẫn file params cho SLAM Toolbox
    default_slam_params = os.path.join(pkg_dir, 'config', 'mapper_params_online_async.yaml')
    try:
        get_package_share_directory('rf2o_laser_odometry')
        rf2o_available = True
    except PackageNotFoundError:
        rf2o_available = False

    # === 1. Robot State Publisher ===
    rsp_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_dir, 'launch', 'rsp.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # === 2. SLLiDAR C1 (RẤT QUAN TRỌNG) ===
    sllidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_dir, 'launch', 'view_sllidar_c1_launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'serial_port': serial_port,
            'serial_baudrate': serial_baudrate,
            'frame_id': lidar_frame,
            'enable_angle_window_filter': enable_angle_window_filter,
            'angle_window_min_deg': angle_window_min_deg,
            'angle_window_max_deg': angle_window_max_deg,
        }.items()
    )

    # === 3. SLAM Toolbox ===
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
        }.items()
    )

    # === 4. RViz2 ===
    rviz_config_file = os.path.join(pkg_dir, 'config', 'map.rviz')

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file] if os.path.exists(rviz_config_file) else [],
        output='screen'
    )

    # === 5. Laser Odometry (rf2o) ===
    rf2o_node = Node(
        package='rf2o_laser_odometry',
        executable='rf2o_laser_odometry_node',
        name='rf2o_laser_odometry',
        output='screen',
        condition=IfCondition(use_rf2o),
        parameters=[{
            'use_sim_time': use_sim_time,
            'laser_scan_topic': '/scan',
            'odom_topic': '/odom_rf2o_raw',
            'base_frame_id': 'base_footprint',
            'odom_frame_id': 'odom',
            'publish_tf': False,
            'init_pose_from_topic': '',
            'freq': 20.0
        }]
    ) if rf2o_available else LogInfo(
        msg='[LAUNCH] rf2o_laser_odometry chưa được cài. Có thể bật enable_fake_odom_tf:=true để fallback tạm.'
    )

    # === 6. Fallback TF khi không có odom encoder ===
    fake_odom_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='fake_odom_to_base_footprint_tf',
        arguments=['0', '0', '0', '0', '0', '0', 'odom', 'base_footprint'],
        condition=IfCondition(enable_fake_odom_tf),
        output='screen'
    )

    map_filter_node = Node(
        package=pkg_name,
        executable='map_speckle_filter',
        name='map_speckle_filter',
        condition=IfCondition(enable_map_filter),
        output='screen'
    )

    odom_axis_corrector_node = Node(
        package=pkg_name,
        executable='odom_axis_corrector',
        name='odom_axis_corrector',
        condition=IfCondition(enable_odom_axis_corrector),
        output='screen'
    )

    # === 7. PLC Control Node (dùng Node thay vì ExecuteProcess) ===
    plc_control_node = Node(
        package=pkg_name,
        executable='plc_control_node',        # Tên executable (không phải .py)
        name='plc_control_node',
        condition=IfCondition(enable_plc_node),
        output='screen'
    )

    return LaunchDescription([
        LogInfo(msg='[LAUNCH] Khởi động: Robot Model + SLLiDAR C1 + SLAM Toolbox + RViz2 + PLC Control'),

        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=default_slam_params,
            description='Full path to the SLAM Toolbox parameters file'
        ),
        DeclareLaunchArgument(
            'serial_port',
            default_value='/dev/ttyUSB0',
            description='Serial port used by the SLLiDAR node'
        ),
        DeclareLaunchArgument(
            'serial_baudrate',
            default_value='460800',
            description='Baudrate used by the SLLiDAR node'
        ),
        DeclareLaunchArgument(
            'lidar_frame',
            default_value='laser_frame',
            description='TF frame_id published in LaserScan messages'
        ),
        DeclareLaunchArgument(
            'enable_angle_window_filter',
            default_value='true',
            description='Enable front-sector filtering to remove rear beams blocked by the robot body.'
        ),
        DeclareLaunchArgument(
            'angle_window_min_deg',
            default_value='90.0',
            description='Minimum angle to keep in LaserScan for the 90 to 270 degree sector'
        ),
        DeclareLaunchArgument(
            'angle_window_max_deg',
            default_value='-90.0',
            description='Maximum angle to keep in LaserScan for the 90 to 270 degree sector'
        ),
        DeclareLaunchArgument(
            'use_rf2o',
            default_value='true',
            description='Enable rf2o_laser_odometry to estimate odom from LiDAR'
        ),
        DeclareLaunchArgument(
            'enable_fake_odom_tf',
            default_value='false',
            description='Publish static TF odom -> base_footprint when no wheel odometry is available'
        ),
        DeclareLaunchArgument(
            'enable_odom_axis_corrector',
            default_value='true',
            description='Rotate RF2O odom axes to match robot forward direction'
        ),
        DeclareLaunchArgument(
            'enable_map_filter',
            default_value='true',
            description='Filter isolated occupied speckles from /map'
        ),
        DeclareLaunchArgument(
            'enable_plc_node',
            default_value='false',
            description='Launch plc_control_node (set false for pure LiDAR + SLAM mode)'
        ),

        rsp_launch,
        sllidar_launch,      # ← Phải có lidar mới mapping được
        rf2o_node,
        odom_axis_corrector_node,
        fake_odom_tf,
        slam_launch,
        map_filter_node,
        rviz_node,
        plc_control_node,
    ])
