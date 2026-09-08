#!/usr/bin/env bash
# Use with: source scripts/use_env.sh
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    printf 'source scripts/use_env.sh 로 실행하세요.\n' >&2
    exit 1
fi

MODULE2_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P) || return 1

if [[ ! -f /opt/ros/humble/setup.bash ]]; then
    printf 'ROS 2 Humble이 없습니다: /opt/ros/humble/setup.bash\nUbuntu 22.04에서 ros-humble-desktop을 설치하세요.\n' >&2
    return 1
fi

resolve_venv() {
    local candidates=() candidate
    if [[ -n "${ROS2_VENV:-}" ]]; then
        # An explicit override must never silently select a different environment.
        candidates+=("$ROS2_VENV")
    else
        candidates+=("$HOME/.venvs/ros2-humble" "$MODULE2_ROOT/.venv")
    fi
    for candidate in "${candidates[@]}"; do
        if [[ -x "$candidate/bin/python" && -f "$candidate/bin/activate" && -f "$candidate/pyvenv.cfg" ]]; then
            (cd -- "$candidate" && pwd -P)
            return 0
        fi
    done
    return 1
}

VENV_DIR="$(resolve_venv)" || {
    printf '사용 가능한 가상환경이 없습니다. ROS2_VENV=%s\n' "${ROS2_VENV:-<자동 검색>}" >&2
    printf '다음을 실행하고 출력되는 환경 적용 명령을 따르세요:\n  bash "%s/scripts/setup_venv.sh"\n  source "%s/scripts/use_env.sh"\n' \
        "$MODULE2_ROOT" "$MODULE2_ROOT" >&2
    return 1
}

# Humble binary packages require the Ubuntu 22.04 system Python ABI.
if ! "$VENV_DIR/bin/python" - "$VENV_DIR" <<'PY'
import pathlib
import sys

venv = pathlib.Path(sys.argv[1]).resolve()
cfg = dict(line.split('=', 1) for line in (venv / 'pyvenv.cfg').read_text().splitlines() if '=' in line)
cfg = {key.strip(): value.strip().lower() for key, value in cfg.items()}
valid = (sys.version_info[:2] == (3, 10)
         and pathlib.Path(sys.prefix).resolve() == venv
         and sys.prefix != sys.base_prefix
         and pathlib.Path(sys._base_executable).resolve() == pathlib.Path('/usr/bin/python3').resolve()
         and cfg.get('include-system-site-packages') == 'true')
if not valid:
    sys.exit('Ubuntu 시스템 Python 3.10 및 --system-site-packages venv가 필요합니다. setup_venv.sh로 다른 경로에 생성하세요.')
PY
then
    return 1
fi

source_without_nounset() {
    local restore=0 source_status=0
    if [[ -o nounset ]]; then
        restore=1
        set +u
    fi
    # shellcheck disable=SC1090
    if source "$1"; then
        source_status=0
    else
        source_status=$?
    fi
    if [[ "$restore" -eq 1 ]]; then
        set -u
    fi
    return "$source_status"
}

# shellcheck disable=SC1091
source_without_nounset "$VENV_DIR/bin/activate" || return $?
if [[ "$(command -v python)" != "$VENV_DIR/bin/python" ]]; then
    printf '선택한 venv가 활성화되지 않았습니다. 옮기거나 복사한 venv는 setup_venv.sh로 새로 생성하세요.\n' >&2
    return 1
fi
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH
# shellcheck disable=SC1091
source_without_nounset /opt/ros/humble/setup.bash || return $?
if ! python -c 'import rclpy, turtlesim' >/dev/null 2>&1; then
    printf '현재 venv에서 rclpy 또는 turtlesim을 불러올 수 없습니다. ROS 설치와 venv 설정을 확인하세요.\n' >&2
    return 1
fi
# Build from the ROS underlay so a broken or outdated local install can be rebuilt.
if [[ "${MODULE2_SKIP_OVERLAY:-0}" != 1 && -d "$MODULE2_ROOT/ros2_ws/install" ]]; then
    for module2_pkg in turtle_interfaces turtle_cpp turtle_py; do
        if [[ ! -f "$MODULE2_ROOT/ros2_ws/install/$module2_pkg/share/$module2_pkg/package.bash" ||
              ! -f "$MODULE2_ROOT/ros2_ws/install/$module2_pkg/share/ament_index/resource_index/packages/$module2_pkg" ]]; then
            printf '워크스페이스 설치가 불완전합니다: %s\nbash scripts/build_ws.sh로 다시 빌드하세요.\n' "$module2_pkg" >&2
            return 1
        fi
    done
    if [[ ! -f "$MODULE2_ROOT/ros2_ws/install/local_setup.bash" ]]; then
        printf 'install/local_setup.bash가 없습니다. bash scripts/build_ws.sh로 다시 빌드하세요.\n' >&2
        return 1
    fi
    # shellcheck disable=SC1091
    source_without_nounset "$MODULE2_ROOT/ros2_ws/install/local_setup.bash" || return $?
fi
export ROS_DOMAIN_ID="${MODULE2_DOMAIN_ID:-62}"
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
# UDP transport is restricted to 127.0.0.1 by the XML profile.
export ROS_LOCALHOST_ONLY=0
unset ROS_DISCOVERY_SERVER CYCLONEDDS_URI FASTDDS_DEFAULT_PROFILES_FILE
export FASTRTPS_DEFAULT_PROFILES_FILE="$MODULE2_ROOT/config/fastdds_loopback.xml"
export PYTHONUNBUFFERED=1
export MODULE2_ROOT
export ROS2_VENV="$VENV_DIR"
printf 'Python: %s\nROS domain: %s\nvenv: %s\n' "$(command -v python)" "$ROS_DOMAIN_ID" "$VENV_DIR"
