#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifica se os tópicos RGB-D do Kinect (simulado ou real) estão ativos.

Simulação: dados vêm do plugin Gazebo (URDF kinect), não de libfreenect/OpenNI.
Hardware: os mesmos nomes de tópico seriam preenchidos por freenect_stack ou openni2_camera.
"""

from __future__ import print_function

import rospy
from sensor_msgs.msg import Image, PointCloud2, LaserScan


class RgbdTopicVerifier(object):
    def __init__(self):
        rospy.init_node("verify_rgbd_topics", anonymous=False)
        self._seen = {
            "rgb": False,
            "depth": False,
            "cloud": False,
            "scan": False,
        }
        rgb = rospy.get_param("~rgb_topic", "/camera/rgb/image_raw")
        depth = rospy.get_param("~depth_topic", "/camera/depth/image_raw")
        cloud = rospy.get_param("~cloud_topic", "/camera/depth/points")
        scan = rospy.get_param("~scan_topic", "/scan")

        rospy.Subscriber(rgb, Image, self._cb_rgb, queue_size=1)
        rospy.Subscriber(depth, Image, self._cb_depth, queue_size=1)
        rospy.Subscriber(cloud, PointCloud2, self._cb_cloud, queue_size=1)
        rospy.Subscriber(scan, LaserScan, self._cb_scan, queue_size=1)

        rospy.loginfo(
            "Aguardando tópicos Kinect RGB-D (sim Gazebo ou driver real): "
            "rgb=%s depth=%s cloud=%s scan=%s",
            rgb,
            depth,
            cloud,
            scan,
        )
        rospy.loginfo(
            "Nota: em simulação NÃO usamos libfreenect/OpenNI; o Gazebo publica "
            "sensor_msgs diretamente (equivalente ao pipeline do slide ROS+Kinect)."
        )

    def _cb_rgb(self, _msg):
        self._mark("rgb")

    def _cb_depth(self, _msg):
        self._mark("depth")

    def _cb_cloud(self, _msg):
        self._mark("cloud")

    def _cb_scan(self, _msg):
        self._mark("scan")

    def _mark(self, key):
        if not self._seen[key]:
            self._seen[key] = True
            rospy.loginfo("OK: recebido primeiro %s", key)
        if all(self._seen.values()):
            rospy.loginfo("Todos os canais RGB-D/scan verificados com sucesso.")
            rospy.signal_shutdown("verificacao concluida")

    def spin(self):
        rate = rospy.Rate(1.0)
        timeout = rospy.get_param("~timeout_sec", 120.0)
        start = rospy.get_time()
        while not rospy.is_shutdown():
            if rospy.get_time() - start > timeout:
                missing = [k for k, v in self._seen.items() if not v]
                rospy.logwarn(
                    "Timeout: ainda faltam canais: %s. "
                    "Confira se bringup_sim está rodando e TURTLEBOT_3D_SENSOR=kinect.",
                    ", ".join(missing),
                )
                return
            rate.sleep()


if __name__ == "__main__":
    try:
        RgbdTopicVerifier().spin()
    except rospy.ROSInterruptException:
        pass
