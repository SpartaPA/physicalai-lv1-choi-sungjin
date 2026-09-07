#!/usr/bin/env bash
# Use with: source scripts/use_env.sh
MODULE2_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source /home/chsjh/.venvs/ros2-humble/bin/activate
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH
source /opt/ros/humble/setup.bash
if [[ -f "$MODULE2_ROOT/ros2_ws/install/setup.bash" ]]; then
    source "$MODULE2_ROOT/ros2_ws/install/setup.bash"
fi
export ROS_DOMAIN_ID="${MODULE2_DOMAIN_ID:-62}"
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
# UDP transport is restricted to 127.0.0.1 by the XML profile.
export ROS_LOCALHOST_ONLY=0
unset ROS_DISCOVERY_SERVER CYCLONEDDS_URI FASTDDS_DEFAULT_PROFILES_FILE
export FASTRTPS_DEFAULT_PROFILES_FILE="$MODULE2_ROOT/config/fastdds_loopback.xml"
export PYTHONUNBUFFERED=1
printf 'Python: %s\nROS domain: %s\n' "$(command -v python)" "$ROS_DOMAIN_ID"
