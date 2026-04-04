#!/usr/bin/env python3
import copy

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped


class OdomAxisCorrector(Node):
    def __init__(self):
        super().__init__('odom_axis_corrector')

        self.declare_parameter('input_odom_topic', '/odom_rf2o_raw')
        self.declare_parameter('output_odom_topic', '/odom')
        self.declare_parameter('odom_frame_id', 'odom')
        self.declare_parameter('base_frame_id', 'base_footprint')
        self.declare_parameter('publish_tf', True)

        self.input_odom_topic = str(self.get_parameter('input_odom_topic').value)
        self.output_odom_topic = str(self.get_parameter('output_odom_topic').value)
        self.odom_frame_id = str(self.get_parameter('odom_frame_id').value)
        self.base_frame_id = str(self.get_parameter('base_frame_id').value)
        self.publish_tf = bool(self.get_parameter('publish_tf').value)

        self.pub = self.create_publisher(Odometry, self.output_odom_topic, 20)
        self.sub = self.create_subscription(Odometry, self.input_odom_topic, self.cb, 20)
        self.tf_broadcaster = TransformBroadcaster(self)

    def cb(self, msg: Odometry):
        corrected = copy.deepcopy(msg)
        corrected.header.frame_id = self.odom_frame_id
        corrected.child_frame_id = self.base_frame_id

        x_raw = msg.pose.pose.position.x
        y_raw = msg.pose.pose.position.y

        # Rotate translation by -90 deg so forward motion aligns with +X in RViz/map.
        corrected.pose.pose.position.x = y_raw
        corrected.pose.pose.position.y = -x_raw

        vx_raw = msg.twist.twist.linear.x
        vy_raw = msg.twist.twist.linear.y
        corrected.twist.twist.linear.x = vy_raw
        corrected.twist.twist.linear.y = -vx_raw

        self.pub.publish(corrected)

        if self.publish_tf:
            tf_msg = TransformStamped()
            tf_msg.header = corrected.header
            tf_msg.child_frame_id = corrected.child_frame_id
            tf_msg.transform.translation.x = corrected.pose.pose.position.x
            tf_msg.transform.translation.y = corrected.pose.pose.position.y
            tf_msg.transform.translation.z = corrected.pose.pose.position.z
            tf_msg.transform.rotation = corrected.pose.pose.orientation
            self.tf_broadcaster.sendTransform(tf_msg)


def main():
    rclpy.init()
    node = OdomAxisCorrector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
