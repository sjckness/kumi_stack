#!/usr/bin/env python3
import threading
import tkinter as tk

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32, String


class KeyboardNode(Node):
    def __init__(self):
        super().__init__('kumi_keyboard_node')
        self.angle_index = 0
        self._key_pub = self.create_publisher(String, 'keyboard_input', 10)
        self._angle_pub = self.create_publisher(Int32, 'keyboard_angle_index', 10)
        self.get_logger().info('Keyboard node ready')

    def publish_key(self, key_name: str):
        if key_name == 'RIGHT':
            self.angle_index += 1
        elif key_name == 'LEFT':
            self.angle_index -= 1

        key_msg = String()
        key_msg.data = key_name
        self._key_pub.publish(key_msg)

        angle_msg = Int32()
        angle_msg.data = self.angle_index
        self._angle_pub.publish(angle_msg)

        self.get_logger().info(f'key={key_name}  angle_index={self.angle_index}')


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardNode()

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    root = tk.Tk()
    root.title('Kumi Keyboard Control')
    root.geometry('300x160')
    root.resizable(False, False)

    tk.Label(root, text='Click here, then use arrow keys', font=('Arial', 11)).pack(pady=12)

    angle_var = tk.StringVar(value='angle_index:  0')
    tk.Label(root, textvariable=angle_var, font=('Arial', 14, 'bold')).pack(pady=4)

    status_var = tk.StringVar(value='')
    tk.Label(root, textvariable=status_var, font=('Arial', 10), fg='gray').pack(pady=4)

    def on_key(event):
        key_map = {'Up': 'UP', 'Down': 'DOWN', 'Left': 'LEFT', 'Right': 'RIGHT'}
        key_name = key_map.get(event.keysym)
        if key_name is None:
            return
        node.publish_key(key_name)
        angle_var.set(f'angle_index:  {node.angle_index}')
        status_var.set(f'last key: {key_name}')

    root.bind('<KeyPress>', on_key)
    root.focus_set()

    try:
        root.mainloop()
    finally:
        rclpy.try_shutdown()
