cmake_minimum_required(VERSION 3.0.2)
project(robo_aspirador_kinect)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  sensor_msgs
  geometry_msgs
  gazebo_ros
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/verify_rgbd_topics.py
  scripts/kinect_teleop.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config worlds maps
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
