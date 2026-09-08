#!/usr/bin/env bash
# Build ros2_ws with the active ros2-humble venv Python.
# Usage: bash scripts/build_ws.sh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
MODULE2_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)

# shellcheck disable=SC1091
MODULE2_SKIP_OVERLAY=1 source "$SCRIPT_DIR/use_env.sh" || exit $?

if ! command -v python >/dev/null 2>&1; then
    printf 'python이 PATH에 없습니다. source scripts/use_env.sh 를 먼저 확인하세요.\n' >&2
    exit 1
fi

if [[ ! -x /usr/bin/colcon ]]; then
    printf 'colcon이 없습니다: /usr/bin/colcon\n설치: sudo apt install python3-colcon-common-extensions\n' >&2
    exit 1
fi

PYTHON_BIN="$(command -v python)"
WORKSPACE=$(cd -- "$MODULE2_ROOT/ros2_ws" && pwd -P)
# Both the source location and Python environment are embedded in build outputs.
BUILD_KEY=$(printf '%s\n%s\n' "$WORKSPACE" "$ROS2_VENV" | sha256sum)
BUILD_KEY=${BUILD_KEY%% *}
BUILD_BASE="${MODULE2_BUILD_BASE:-$HOME/physicalai_lv1_build/module2/$BUILD_KEY/build}"
BUILD_BASE=$(realpath -m -- "$BUILD_BASE")
if ! python - "$BUILD_BASE" <<'PY'
import sys
if not sys.argv[1].isascii():
    sys.exit('빌드 중간 파일 경로는 ASCII 문자만 사용해야 합니다. MODULE2_BUILD_BASE에 별도 ASCII 경로를 지정하세요.')
PY
then
    exit 1
fi
mkdir -p "$BUILD_BASE"
OWNER_FILE="$BUILD_BASE/.module2-build-owner"
if [[ -f "$OWNER_FILE" ]]; then
    if [[ "$(cat -- "$OWNER_FILE")" != "$BUILD_KEY" ]]; then
        printf '다른 워크스페이스 또는 venv가 사용한 빌드 경로입니다: %s\nMODULE2_BUILD_BASE에 새로운 빈 경로를 지정하세요.\n' "$BUILD_BASE" >&2
        exit 1
    fi
elif [[ -n "$(find "$BUILD_BASE" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    printf '출처를 확인할 수 없는 기존 빌드 파일이 있습니다: %s\nMODULE2_BUILD_BASE에 새로운 빈 경로를 지정하세요. 기존 파일은 삭제하지 않습니다.\n' "$BUILD_BASE" >&2
    exit 1
else
    printf '%s\n' "$BUILD_KEY" > "$OWNER_FILE"
fi

cd "$WORKSPACE"
python /usr/bin/colcon build \
    --build-base "$BUILD_BASE" \
    --symlink-install \
    --cmake-args -DPython3_EXECUTABLE="$PYTHON_BIN"

printf 'build-base: %s\nPython: %s\n' "$BUILD_BASE" "$PYTHON_BIN"
printf '빌드 후 같은 터미널에서 다시 source scripts/use_env.sh 를 실행하세요.\n'
