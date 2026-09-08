#!/usr/bin/env bash
# Create a ROS 2 Humble-compatible Python virtual environment.
# Usage: bash scripts/setup_venv.sh [--venv DIR]
set -euo pipefail

VENV_DIR="${ROS2_VENV:-$HOME/.venvs/ros2-humble}"
SYSTEM_PYTHON=/usr/bin/python3
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

usage() {
    cat <<'EOF'
Usage: bash scripts/setup_venv.sh [--venv DIR]

Create a Python virtual environment that can use ROS 2 Humble packages.
Default path: $HOME/.venvs/ros2-humble
Override with --venv DIR or the ROS2_VENV environment variable.

Requires Ubuntu 22.04 with ROS 2 Humble, python3-venv, and
python3-colcon-common-extensions.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)
            if [[ $# -lt 2 || -z "$2" || "$2" == --* ]]; then
                printf '%s\n' '--venv 다음에 사용할 디렉터리를 지정하세요.' >&2
                exit 1
            fi
            VENV_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'unknown argument: %s\n' "$1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ ! -x "$SYSTEM_PYTHON" ]]; then
    printf '시스템 Python이 없습니다: %s\n' "$SYSTEM_PYTHON" >&2
    exit 1
fi

if ! "$SYSTEM_PYTHON" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 10))'; then
    printf 'Ubuntu 22.04의 시스템 Python 3.10이 필요합니다: %s\n' "$SYSTEM_PYTHON" >&2
    exit 1
fi

if ! "$SYSTEM_PYTHON" -c 'import venv' >/dev/null 2>&1; then
    printf 'python3-venv가 없습니다. 설치: sudo apt install python3-venv\n' >&2
    exit 1
fi

if [[ ! -f /opt/ros/humble/setup.bash ]]; then
    printf 'ROS 2 Humble이 없습니다: /opt/ros/humble/setup.bash\n' >&2
    printf 'README의 Ubuntu 22.04 / ROS 2 Humble 설치 안내를 먼저 완료하세요.\n' >&2
    exit 1
fi

if [[ -L "$VENV_DIR" && ! -e "$VENV_DIR" ]]; then
    printf '가상환경 경로가 끊어진 심볼릭 링크입니다: %s\n' "$VENV_DIR" >&2
    exit 1
fi
VENV_DIR="$("$SYSTEM_PYTHON" -c 'import os, sys; print(os.path.realpath(os.path.abspath(os.path.expanduser(sys.argv[1]))))' "$VENV_DIR")"

created=0
if [[ -e "$VENV_DIR" ]]; then
    if [[ ! -d "$VENV_DIR" || ! -x "$VENV_DIR/bin/python" || ! -f "$VENV_DIR/bin/activate" || ! -f "$VENV_DIR/pyvenv.cfg" ]]; then
        printf '기존 경로가 완전한 가상환경이 아닙니다: %s\n' "$VENV_DIR" >&2
        printf '기존 파일을 보존했습니다. --venv로 새로운 경로를 지정하세요.\n' >&2
        exit 1
    fi
else
    mkdir -p "$(dirname -- "$VENV_DIR")"
    "$SYSTEM_PYTHON" -m venv --system-site-packages "$VENV_DIR"
    created=1
fi

# A path named venv is insufficient: verify the interpreter and its configuration.
if ! "$VENV_DIR/bin/python" - "$VENV_DIR" "$SYSTEM_PYTHON" <<'PY'
import pathlib
import sys

target = pathlib.Path(sys.argv[1]).resolve()
system_python = pathlib.Path(sys.argv[2]).resolve()
config = {}
for line in (target / "pyvenv.cfg").read_text().splitlines():
    key, separator, value = line.partition("=")
    if separator:
        config[key.strip().lower()] = value.strip().lower()
errors = []
if sys.version_info[:2] != (3, 10):
    errors.append("Python 3.10이 아님")
if sys.prefix == sys.base_prefix or pathlib.Path(sys.prefix).resolve() != target:
    errors.append("실제로 선택한 가상환경의 Python이 아님")
if pathlib.Path(getattr(sys, "_base_executable", "")).resolve() != system_python:
    errors.append("Ubuntu 시스템 Python으로 만든 가상환경이 아님")
if config.get("include-system-site-packages") != "true":
    errors.append("--system-site-packages가 꺼져 있음")
if errors:
    print("호환되지 않는 가상환경: " + "; ".join(errors), file=sys.stderr)
    sys.exit(1)
PY
then
    printf '기존 환경을 변경하지 않았습니다. --venv로 새로운 경로를 지정하세요.\n' >&2
    exit 1
fi

source_humble() {
    local had_nounset=0 source_status=0
    [[ $- == *u* ]] && had_nounset=1
    set +u
    source /opt/ros/humble/setup.bash || source_status=$?
    if [[ "$had_nounset" -eq 1 ]]; then
        set -u
    fi
    return "$source_status"
}

if ! source_humble; then
    printf 'ROS 2 Humble 환경 적용에 실패했습니다.\n' >&2
    exit 1
fi
if ! "$VENV_DIR/bin/python" -c 'import rclpy; import turtlesim.msg'; then
    printf '가상환경에서 rclpy/turtlesim을 불러오지 못했습니다. Humble 설치 및 Python 호환성을 확인하세요.\n' >&2
    exit 1
fi

if ! "$VENV_DIR/bin/python" -c 'import pytest' >/dev/null 2>&1; then
    "$VENV_DIR/bin/python" -m pip install pytest
fi

printf 'venv: %s\n' "$VENV_DIR"
if [[ "$created" -eq 1 ]]; then
    printf 'status: created\n'
else
    printf 'status: existing\n'
fi
"$VENV_DIR/bin/python" -c 'import sys; print("python:", sys.executable, sys.version.split()[0])'
printf '다음 명령으로 환경을 적용하세요:\n'
printf '  export ROS2_VENV=%q\n' "$VENV_DIR"
printf '  source %q\n' "$SCRIPT_DIR/use_env.sh"
