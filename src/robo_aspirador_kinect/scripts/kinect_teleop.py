#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teleop por teclado para TurtleBot2 (POC Kinect).

Publica continuamente em cmd_vel_mux/input/teleop (10 Hz) para o Gazebo
receber fluxo estável de velocidade — diferente do teleop_twist_keyboard,
onde q/w/e ajustam velocidade mas i/j/l precisam ser mantidos e competem
com RViz pelo stdin quando tudo sobe no mesmo roslaunch.

Layout (estilo TurtleBot / teleop_twist):
  i ,  frente / trás
  j l  girar
  k s  parar
  r f  +/- velocidade
  q    sair
"""

from __future__ import print_function

import select
import sys
import termios
import tty

import rospy
from geometry_msgs.msg import Twist


class KinectTeleop(object):
    def __init__(self):
        rospy.init_node("kinect_teleop")
        topic = rospy.get_param("~cmd_vel_topic", "/cmd_vel_mux/input/teleop")
        if not topic.startswith("/"):
            topic = "/" + topic
        self.pub = rospy.Publisher(topic, Twist, queue_size=1)
        self.rate_hz = float(rospy.get_param("~rate_hz", 10.0))
        self.linear_speed = float(rospy.get_param("~linear_speed", 0.5))
        self.angular_speed = float(rospy.get_param("~angular_speed", 1.0))
        self.linear_max = float(rospy.get_param("~linear_max", 1.0))
        self.angular_max = float(rospy.get_param("~angular_max", 2.0))
        self.linear_min = float(rospy.get_param("~linear_min", 0.05))
        self._linear = 0.0
        self._angular = 0.0
        self._settings = None
        if sys.stdin.isatty():
            self._settings = termios.tcgetattr(sys.stdin)

        print(
            """
Controle TurtleBot2 (Kinect POC)
==============================
      i
  j   k   l
      ,

  i / ,  : frente / trás
  j / l  : girar esquerda / direita
  k ou s : parar
  r / f  : aumentar / diminuir velocidade
  q      : sair

Publicando em: {topic}
Mantenha o foco NESTE terminal (não no RViz/Gazebo).
""".format(topic=topic)
        )

    def _enter_raw_mode(self):
        if self._settings is not None:
            tty.setraw(sys.stdin.fileno())

    def _get_key(self, timeout):
        if not sys.stdin.isatty():
            return ""
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        return sys.stdin.read(1) if rlist else ""

    def _handle_key(self, key):
        if key in ("i",):
            self._linear = self.linear_speed
            self._angular = 0.0
        elif key in (",",):
            self._linear = -self.linear_speed
            self._angular = 0.0
        elif key in ("j",):
            self._linear = 0.0
            self._angular = self.angular_speed
        elif key in ("l",):
            self._linear = 0.0
            self._angular = -self.angular_speed
        elif key in ("k", "s", " "):
            self._linear = 0.0
            self._angular = 0.0
        elif key == "r":
            self.linear_speed = min(self.linear_max, self.linear_speed + 0.1)
            self.angular_speed = min(self.angular_max, self.angular_speed + 0.1)
            rospy.loginfo(
                "Velocidade: linear=%.2f angular=%.2f",
                self.linear_speed,
                self.angular_speed,
            )
        elif key == "f":
            self.linear_speed = max(self.linear_min, self.linear_speed - 0.1)
            self.angular_speed = max(self.linear_min, self.angular_speed - 0.1)
            rospy.loginfo(
                "Velocidade: linear=%.2f angular=%.2f",
                self.linear_speed,
                self.angular_speed,
            )
        elif key == "q":
            return False
        return True

    def run(self):
        rate = rospy.Rate(self.rate_hz)
        self._enter_raw_mode()
        try:
            while not rospy.is_shutdown():
                key = self._get_key(0.1)
                if key:
                    if key == "\x03":
                        break
                    if not self._handle_key(key):
                        break
                twist = Twist()
                twist.linear.x = self._linear
                twist.angular.z = self._angular
                self.pub.publish(twist)
                rate.sleep()
        finally:
            self.pub.publish(Twist())
            if self._settings is not None:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._settings)
            print("\nTeleop encerrado.")


if __name__ == "__main__":
    try:
        KinectTeleop().run()
    except rospy.ROSInterruptException:
        pass
