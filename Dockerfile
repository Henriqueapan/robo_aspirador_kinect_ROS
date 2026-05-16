# POC TurtleBot2 + Kinect simulado — ROS Noetic + Gazebo
FROM osrf/ros:noetic-desktop-full

ENV DEBIAN_FRONTEND=noninteractive
ENV TURTLEBOT_3D_SENSOR=kinect
ENV TURTLEBOT_BASE=kobuki
ENV TURTLEBOT_STACKS=hexagons

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-rosdep \
    python3-rosinstall \
    python3-rosinstall-generator \
    python3-wstool \
    build-essential \
    git \
    nano \
    net-tools \
    iputils-ping \
    libusb-dev \
    libftdi-dev \
    liborocos-kdl-dev \
    ros-noetic-joy \
    ros-noetic-sophus \
    ros-noetic-depthimage-to-laserscan \
    ros-noetic-openni-description \
    ros-noetic-openni-launch \
    ros-noetic-openni2-launch \
    ros-noetic-tf2-ros \
    ros-noetic-robot-state-publisher \
    ros-noetic-xacro \
    ros-noetic-gazebo-ros \
    ros-noetic-gazebo-ros-control \
    ros-noetic-gazebo-plugins \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir rospkg catkin_pkg

RUN rosdep init 2>/dev/null || true
RUN rosdep update

RUN mkdir -p /root/catkin_ws/src
WORKDIR /root/catkin_ws

COPY scripts/setup_turtlebot2_noetic.sh /tmp/setup_turtlebot2_noetic.sh
RUN chmod +x /tmp/setup_turtlebot2_noetic.sh && /tmp/setup_turtlebot2_noetic.sh /root/catkin_ws/src

COPY src/robo_aspirador_kinect /root/catkin_ws/src/robo_aspirador_kinect

RUN /bin/bash -c "source /opt/ros/noetic/setup.bash \
    && rosdep install --from-paths src --ignore-src -r -y || true \
    && catkin_make -DCMAKE_BUILD_TYPE=Release"

RUN echo 'source /opt/ros/noetic/setup.bash' >> /root/.bashrc \
 && echo 'source /root/catkin_ws/devel/setup.bash' >> /root/.bashrc \
 && echo 'export TURTLEBOT_3D_SENSOR=kinect' >> /root/.bashrc

WORKDIR /root/catkin_ws
