#!/usr/bin/env python3
import copy

import rclpy
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy


class MapSpeckleFilter(Node):
    def __init__(self):
        super().__init__('map_speckle_filter')

        self.declare_parameter('input_topic', '/map')
        self.declare_parameter('output_topic', '/map_filtered')
        self.declare_parameter('occupied_threshold', 50)
        self.declare_parameter('min_occupied_neighbors', 2)

        input_topic = str(self.get_parameter('input_topic').value)
        output_topic = str(self.get_parameter('output_topic').value)
        self.occupied_threshold = int(self.get_parameter('occupied_threshold').value)
        self.min_occupied_neighbors = int(
            self.get_parameter('min_occupied_neighbors').value
        )

        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.sub = self.create_subscription(
            OccupancyGrid, input_topic, self.map_cb, qos
        )
        self.pub = self.create_publisher(OccupancyGrid, output_topic, qos)

    def map_cb(self, msg: OccupancyGrid):
        width = msg.info.width
        height = msg.info.height
        src = list(msg.data)
        dst = src[:]

        for y in range(1, height - 1):
            row_offset = y * width
            for x in range(1, width - 1):
                idx = row_offset + x
                if src[idx] < self.occupied_threshold:
                    continue

                occupied_neighbors = 0
                for ny in range(y - 1, y + 2):
                    for nx in range(x - 1, x + 2):
                        if nx == x and ny == y:
                            continue
                        nidx = ny * width + nx
                        if src[nidx] >= self.occupied_threshold:
                            occupied_neighbors += 1

                if occupied_neighbors < self.min_occupied_neighbors:
                    dst[idx] = 0

        filtered = copy.deepcopy(msg)
        filtered.data = dst
        self.pub.publish(filtered)


def main():
    rclpy.init()
    node = MapSpeckleFilter()
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
