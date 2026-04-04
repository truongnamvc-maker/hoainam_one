#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import pymcprotocol
import time
import sys
import termios
import tty
import select
import signal
import threading


class PLCModbusBridge(Node):
    def __init__(self):
        super().__init__('plc_modbus_bridge')

        # ===== PARAMETERS =====
        self.declare_parameter('plc_ip', '192.168.3.39')
        self.declare_parameter('plc_port', 1025)
        self.declare_parameter('default_speed', 200)
        self.declare_parameter('test_m1_on_start', True)
        self.declare_parameter('lidar_stop_distance', 0.6)
        self.declare_parameter('reconnect_interval_sec', 2.0)

        self.plc_ip = self.get_parameter('plc_ip').value
        self.plc_port = self.get_parameter('plc_port').value
        self.default_speed = self.get_parameter('default_speed').value
        self.test_m1_on_start = self.get_parameter('test_m1_on_start').value
        self.lidar_stop_distance = self.get_parameter('lidar_stop_distance').value
        self.reconnect_interval_sec = float(
            self.get_parameter('reconnect_interval_sec').value)
        self._is_shutting_down = False
        self._plc_lock = threading.Lock()
        self.plc = None
        self._last_reconnect_try = 0.0

        # ===== PLC CONNECT =====
        self.connect_plc(initial=True)

        # ===== LIDAR =====
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)

        self.get_logger().info(
            f'📡 Subscribed /scan | Stop < {self.lidar_stop_distance} m')

        # ===== INFO =====
        self.get_logger().info('🚀 PLC Bridge READY')
        self.get_logger().info('Keyboard control:')
        self.get_logger().info('  ↑ : Forward')
        self.get_logger().info('  ↓ : Backward')
        self.get_logger().info('  ← : Left')
        self.get_logger().info('  → : Right')
        self.get_logger().info('  0 : STOP')

        # ===== PLC RECONNECT TIMER =====
        self.create_timer(1.0, self.reconnect_timer_cb)

        # ===== SIGNAL =====
        signal.signal(signal.SIGINT, self.signal_handler)

        # ===== KEYBOARD THREAD (KHÔNG BLOCK ROS) =====
        threading.Thread(target=self.read_keyboard, daemon=True).start()

    def connect_plc(self, initial=False):
        did_connect = False
        with self._plc_lock:
            if self.plc is not None:
                return True
            try:
                plc = pymcprotocol.Type3E()
                plc.setaccessopt(commtype="ascii")
                plc.connect(self.plc_ip, self.plc_port)
                self.plc = plc
                did_connect = True
                self.get_logger().info(
                    f'✅ PLC connected (ASCII) - {self.plc_ip}:{self.plc_port}')
            except Exception as e:
                if initial:
                    self.get_logger().error(f'❌ PLC connection failed: {e}')
                else:
                    self.get_logger().warn(f'PLC reconnect failed: {e}')
                self.plc = None
                return False
        if did_connect and self.test_m1_on_start:
            self.test_m1_startup()
        return did_connect

    def mark_plc_disconnected(self, reason):
        with self._plc_lock:
            if self.plc is not None:
                try:
                    self.plc.close()
                except Exception:
                    pass
            self.plc = None
        self.get_logger().error(f'PLC disconnected: {reason}')

    def reconnect_timer_cb(self):
        if self._is_shutting_down:
            return
        if self.plc is not None:
            return
        now = time.time()
        if now - self._last_reconnect_try < self.reconnect_interval_sec:
            return
        self._last_reconnect_try = now
        self.connect_plc(initial=False)

    # =========================================================
    # KEYBOARD
    # =========================================================
    def read_keyboard(self):
        if not sys.stdin.isatty():
            self.get_logger().error('Not interactive terminal')
            return

        old_settings = termios.tcgetattr(sys.stdin)

        try:
            tty.setcbreak(sys.stdin.fileno())
            self.get_logger().info('Keyboard mode: ACTIVE')

            while rclpy.ok():
                rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                if rlist:
                    key = sys.stdin.read(1)
                    if key == '\x1b':
                        key += sys.stdin.read(2)
                    elif key == '\x03':  # Ctrl+C in cbreak mode
                        self.get_logger().info('🛑 Ctrl+C detected from keyboard thread')
                        self.signal_handler(signal.SIGINT, None)
                        break

                    self.process_key(key)

        except Exception as e:
            self.get_logger().error(f'Keyboard error: {e}')

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self.stop_robot()

    def process_key(self, key):
        speed = self.default_speed

        if key == '\x1b[A':  # UP
            self.set_movement(1, 0, 0, 0, speed)
            self.get_logger().info(f'↑ Forward | D20={speed}, D22={speed}')

        elif key == '\x1b[B':  # DOWN
            self.set_movement(0, 1, 0, 0, speed)
            self.get_logger().info(f'↓ Backward | D20={speed}, D22={speed}')

        elif key == '\x1b[D':  # LEFT
            self.set_movement(0, 0, 1, 0, speed)
            self.get_logger().info(f'← Left | D20={speed}, D22={speed}')

        elif key == '\x1b[C':  # RIGHT
            self.set_movement(0, 0, 0, 1, speed)
            self.get_logger().info(f'→ Right | D20={speed}, D22={speed}')

        elif key == '0':
            self.stop_robot()
            self.get_logger().info('STOP command')

        else:
            self.stop_robot()

    # =========================================================
    # PLC CONTROL
    # =========================================================
    def set_movement(self, M1=0, M2=0, M3=0, M4=0, speed=0):
        if self.plc is None:
            return

        try:
            with self._plc_lock:
                if self.plc is None:
                    return
                # SPEED
                self.plc.batchwrite_wordunits("D20", [speed])
                self.plc.batchwrite_wordunits("D22", [speed])

                # WRITE ALL BITS AT ONCE (CRITICAL FIX)
                self.plc.batchwrite_bitunits("M1", [M1, M2, M3, M4])

                # ENABLE
                self.plc.batchwrite_bitunits("M0", [1])

        except Exception as e:
            self.mark_plc_disconnected(f'write error: {e}')

    def stop_robot(self):
        if self.plc is None:
            return

        try:
            with self._plc_lock:
                if self.plc is None:
                    return
                self.plc.batchwrite_wordunits("D20", [0])
                self.plc.batchwrite_wordunits("D22", [0])

                # RESET ALL BITS AT ONCE
                self.plc.batchwrite_bitunits("M1", [0, 0, 0, 0])

                self.plc.batchwrite_bitunits("M0", [0])

            self.get_logger().info('⛔ ROBOT STOPPED')

        except Exception as e:
            self.mark_plc_disconnected(f'stop error: {e}')

    # =========================================================
    # LIDAR SAFETY
    # =========================================================
    def scan_callback(self, msg: LaserScan):
        if self.plc is None:
            return

        try:
            valid = [r for r in msg.ranges if msg.range_min <= r <= msg.range_max]

            if not valid:
                return

            closest = min(valid)

            if closest < self.lidar_stop_distance:
                self.get_logger().warn(
                    f'⚠️ Obstacle: {closest:.2f} m → STOP')
                self.stop_robot()

        except Exception as e:
            self.get_logger().error(f'Lidar error: {e}')

    # =========================================================
    # STARTUP TEST
    # =========================================================
    def test_m1_startup(self):
        if self.plc is None:
            return

        try:
            self.get_logger().info('Test M1 ON')
            with self._plc_lock:
                if self.plc is None:
                    return
                self.plc.batchwrite_bitunits('M1', [1])
            time.sleep(0.2)

        except Exception as e:
            self.mark_plc_disconnected(f'test error: {e}')

    # =========================================================
    # EXIT
    # =========================================================
    def signal_handler(self, sig, frame):
        if self._is_shutting_down:
            return
        self._is_shutting_down = True

        self.get_logger().info('🛑 Ctrl+C → Emergency STOP')
        self.stop_robot()

        with self._plc_lock:
            if self.plc:
                try:
                    self.plc.close()
                except Exception:
                    pass
                self.plc = None

        rclpy.shutdown()

    def destroy_node(self):
        self.stop_robot()

        with self._plc_lock:
            if self.plc:
                try:
                    self.plc.close()
                except Exception:
                    pass
                self.plc = None

        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)

    node = PLCModbusBridge()

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
