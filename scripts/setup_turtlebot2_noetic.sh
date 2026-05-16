#!/usr/bin/env bash
# Clona dependências TurtleBot2 para ROS Noetic (simulação + teleop).
# Baseado em: https://github.com/ailabspace/turtlebot2-noetic/blob/main/install.md
set -euo pipefail

WS_SRC="${1:-/root/catkin_ws/src}"
cd "${WS_SRC}"

clone_if_missing() {
  local url="$1"
  local dir="$2"
  local branch="${3:-}"
  if [ -d "${dir}" ]; then
    echo "[setup] já existe: ${dir}"
    return
  fi
  if [ -n "${branch}" ]; then
    git clone --depth 1 -b "${branch}" "${url}" "${dir}"
  else
    git clone --depth 1 "${url}" "${dir}"
  fi
}

echo "[setup] TurtleBot2 + Kobuki (Noetic, build from source)"

clone_if_missing https://github.com/turtlebot/turtlebot.git turtlebot
clone_if_missing https://github.com/turtlebot/turtlebot_msgs.git turtlebot_msgs
clone_if_missing https://github.com/turtlebot/turtlebot_simulator.git turtlebot_simulator

clone_if_missing https://github.com/yujinrobot/kobuki_core.git kobuki_core
clone_if_missing https://github.com/yujinrobot/kobuki_msgs.git kobuki_msgs
clone_if_missing https://github.com/yujinrobot/kobuki.git kobuki

clone_if_missing https://github.com/yujinrobot/yujin_ocs.git yujin_ocs
clone_if_missing https://github.com/yujinrobot/yocs_msgs.git yocs_msgs

# Extrai só os pacotes yocs necessários ao TurtleBot2 sim; remove o resto de yujin_ocs
for pkg in yocs_cmd_vel_mux yocs_controllers yocs_velocity_smoother; do
  if [ ! -d "${pkg}" ] && [ -d "yujin_ocs/${pkg}" ]; then
    mv "yujin_ocs/${pkg}" .
  fi
done
rm -rf yujin_ocs

clone_if_missing https://github.com/stonier/ecl_tools.git ecl_tools release/0.61-noetic
clone_if_missing https://github.com/stonier/ecl_lite.git ecl_lite release/0.61-noetic
clone_if_missing https://github.com/stonier/ecl_core.git ecl_core release/0.62-noetic
clone_if_missing https://github.com/stonier/ecl_navigation.git ecl_navigation release/0.60-noetic

echo "[setup] Concluído. Próximo passo: rosdep install + catkin_make"
