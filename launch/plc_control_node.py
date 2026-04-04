#!/usr/bin/env python3
"""
PLC Control Node - Sử dụng ROS2 Service
Cho phép điều khiển robot thông qua lệnh dạng string từ PLC
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_srvs.srv import SetBool
from std_msgs.msg import String

class PLCControlNode(Node):
    def __init__(self):
        super().__init__('plc_control_node')
        
        # Publisher cho /cmd_vel
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(0.1, self.timer_callback)
        
        # Biến lưu trữ lệnh hiện tại
        self.linear = 0.0
        self.angular = 0.0
        
        # Tốc độ cấu hình
        self.speed = 0.5      # m/s
        self.turn = 1.0       # rad/s
        
        # Service cho PLC
        self.srv = self.create_service(SetBool, 'plc_command', self.plc_command_callback)
        
        # Subscriber để nhận lệnh từ topic (nếu cần)
        self.command_sub = self.create_subscription(
            String, '/plc/command', self.command_callback, 10)
        
        self.get_logger().info('=== PLC Control Node Started ===')
        self.get_logger().info('Available commands:')
        self.get_logger().info('  forward / tiến')
        self.get_logger().info('  backward / lùi')
        self.get_logger().info('  left / trái')
        self.get_logger().info('  right / phải')
        self.get_logger().info('  stop / dừng')
        self.get_logger().info('')
        self.get_logger().info('Usage examples:')
        self.get_logger().info('  ros2 topic pub /plc/command std_msgs/String "data: forward"')
        self.get_logger().info('  ros2 service call /plc_command std_srvs/SetBool "{data: true}"')

    def plc_command_callback(self, request, response):
        """Xử lý lệnh từ PLC thông qua ROS2 Service"""
        self.get_logger().info(f'PLC Service command received: {request.data}')
        response.success = True
        response.message = 'received'
        return response

    def command_callback(self, msg):
        """Xử lý lệnh từ topic /plc/command"""
        command = msg.data.lower().strip()
        
        if command in ['tiến', 'forward', 'f']:
            self.linear = self.speed
            self.angular = 0.0
            self.get_logger().info(f'-> Tiến: linear={self.linear}, angular={self.angular}')
            
        elif command in ['lùi', 'backward', 'b']:
            self.linear = -self.speed
            self.angular = 0.0
            self.get_logger().info(f'-> Lùi: linear={self.linear}, angular={self.angular}')
            
        elif command in ['trái', 'left', 'l']:
            self.linear = 0.0
            self.angular = self.turn
            self.get_logger().info(f'-> Quay trái: angular={self.angular}')
            
        elif command in ['phải', 'right', 'r']:
            self.linear = 0.0
            self.angular = -self.turn
            self.get_logger().info(f'-> Quay phải: angular={self.angular}')
            
        elif command in ['dừng', 'stop', 's']:
            self.linear = 0.0
            self.angular = 0.0
            self.get_logger().info('-> Dừng')
            
        elif command.startswith('linear:'):
            try:
                self.linear = float(command.split(':')[1])
                self.get_logger().info(f'-> Cài linear: {self.linear}')
            except:
                self.get_logger().warn(f'Lỗi parse lệnh: {command}')
                
        elif command.startswith('angular:'):
            try:
                self.angular = float(command.split(':')[1])
                self.get_logger().info(f'-> Cài angular: {self.angular}')
            except:
                self.get_logger().warn(f'Lỗi parse lệnh: {command}')
                
        elif command.startswith('cmd:'):
            # Format: cmd:linear,angular
            try:
                parts = command.split(':')[1].split(',')
                self.linear = float(parts[0])
                self.angular = float(parts[1]) if len(parts) > 1 else 0.0
                self.get_logger().info(f'-> CMD: linear={self.linear}, angular={self.angular}')
            except:
                self.get_logger().warn(f'Lỗi parse lệnh: {command}')
        else:
            self.get_logger().warn(f'Lệnh không xác định: {command}')

    def timer_callback(self):
        """Gửi lệnh vận động robot"""
        msg = Twist()
        msg.linear.x = self.linear
        msg.angular.z = self.angular
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = PLCControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Stopping PLC Control Node')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
