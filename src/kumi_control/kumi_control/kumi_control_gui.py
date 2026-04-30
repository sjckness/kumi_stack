#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import ttk

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

from kumi_control.kumi_seq_traj_controller import GAIT_TO_CSV


class KumiControlGui(Node):
    def __init__(self):
        super().__init__('kumi_control_gui')

        self.emergency = False
        self.walk_enabled = False
        self.selected_gait = 'walk'

        self.emergency_pub = self.create_publisher(Bool, 'kumi_behavior/emergency', 10)
        self.enable_pub = self.create_publisher(Bool, 'kumi_seq_traj_controller/enabled', 10)
        self.gait_pub = self.create_publisher(String, 'kumi_seq_traj_controller/gait', 10)

        self.root = tk.Tk()
        self.root.title('Kumi Control')
        self.root.geometry('520x420')
        self.root.resizable(False, False)
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

        self.status_var = tk.StringVar()
        self.walk_var = tk.BooleanVar(value=self.walk_enabled)
        self.gait_var = tk.StringVar(value=self.selected_gait)

        self._build_ui()
        self._refresh_status()
        self._publish_initial_state()

        self.root.after(50, self._spin_once)

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(container, text='Kumi Motion Control', font=('TkDefaultFont', 13, 'bold'))
        title.pack(anchor=tk.W, pady=(0, 12))

        self.emergency_button = ttk.Button(
            container,
            text='Emergency OFF',
            command=self._toggle_emergency
        )
        self.emergency_button.pack(fill=tk.X, pady=(0, 10))

        walk_check = ttk.Checkbutton(
            container,
            text='Walk enabled',
            variable=self.walk_var,
            command=self._toggle_walk
        )
        walk_check.pack(anchor=tk.W, pady=(0, 12))

        gait_label = ttk.Label(container, text='Gait')
        gait_label.pack(anchor=tk.W)

        gait_selector = ttk.Combobox(
            container,
            textvariable=self.gait_var,
            values=list(GAIT_TO_CSV.keys()),
            state='readonly'
        )
        gait_selector.pack(fill=tk.X, pady=(4, 12))
        gait_selector.bind('<<ComboboxSelected>>', self._select_gait)

        status = ttk.Label(container, textvariable=self.status_var, justify=tk.LEFT)
        status.pack(anchor=tk.W, pady=(8, 0))

    def _publish_initial_state(self):
        self._publish_emergency(self.emergency)
        self._publish_walk_enabled(self.walk_enabled)
        self._publish_gait(self.selected_gait)

    def _toggle_emergency(self):
        self.emergency = not self.emergency
        if self.emergency:
            self.walk_enabled = False
            self.walk_var.set(False)
            self._publish_walk_enabled(False)
        self._publish_emergency(self.emergency)
        self._refresh_status()

    def _toggle_walk(self):
        self.walk_enabled = self.walk_var.get()
        if self.walk_enabled and self.emergency:
            self.emergency = False
            self._publish_emergency(False)
        self._publish_walk_enabled(self.walk_enabled)
        self._refresh_status()

    def _select_gait(self, _event=None):
        self.selected_gait = self.gait_var.get()
        self._publish_gait(self.selected_gait)
        self._refresh_status()

    def _publish_emergency(self, enabled: bool):
        msg = Bool()
        msg.data = enabled
        self.emergency_pub.publish(msg)
        self.get_logger().info(f"Emergency set to {enabled}")

    def _publish_walk_enabled(self, enabled: bool):
        msg = Bool()
        msg.data = enabled
        self.enable_pub.publish(msg)
        self.get_logger().info(f"Walk enabled set to {enabled}")

    def _publish_gait(self, gait: str):
        msg = String()
        msg.data = gait
        self.gait_pub.publish(msg)
        self.get_logger().info(f"Gait selected: {gait}")

    def _refresh_status(self):
        self.emergency_button.config(
            text='Emergency ON' if self.emergency else 'Emergency OFF'
        )
        self.status_var.set(
            f"Emergency: {'ON' if self.emergency else 'OFF'}\n"
            f"Walk: {'enabled' if self.walk_enabled else 'disabled'}\n"
            f"Gait: {self.selected_gait}"
        )

    def _spin_once(self):
        if not rclpy.ok():
            self.root.quit()
            return

        rclpy.spin_once(self, timeout_sec=0.0)
        self.root.after(50, self._spin_once)

    def _on_close(self):
        self.root.quit()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = KumiControlGui()
    except tk.TclError as exc:
        display = os.environ.get('DISPLAY', '<unset>')
        print(
            f"kumi_control_gui could not open the graphical display "
            f"(DISPLAY={display}): {exc}",
            flush=True,
        )
        rclpy.shutdown()
        return

    try:
        node.root.mainloop()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
