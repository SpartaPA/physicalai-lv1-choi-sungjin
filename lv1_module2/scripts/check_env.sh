#!/usr/bin/env bash
# Verify environment, installed packages, and calculation tests (no live nodes).
# Usage: bash scripts/check_env.sh
set -u

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
MODULE2_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
pass=0
fail=0

report() {
    local status="$1"
    local name="$2"
    local detail="${3:-}"
    if [[ "$status" == PASS ]]; then
        pass=$((pass + 1))
        printf 'PASS  %s\n' "$name"
    else
        fail=$((fail + 1))
        printf 'FAIL  %s\n' "$name"
    fi
    if [[ -n "$detail" ]]; then
        printf '      %s\n' "$detail"
    fi
}

# shellcheck disable=SC1091
if ! source "$SCRIPT_DIR/use_env.sh"; then
    report FAIL "source scripts/use_env.sh" "venv 또는 ROS 2 Humble을 찾지 못함"
    printf '결과: PASS %s  FAIL %s\n' "$pass" "$fail"
    exit 1
fi
report PASS "source scripts/use_env.sh" "venv=$ROS2_VENV"

PYTHON_BIN="$(command -v python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
    report FAIL "python on PATH"
else
    report PASS "python on PATH" "$PYTHON_BIN"
fi

if [[ "$PYTHON_BIN" == "$ROS2_VENV/bin/python" || "$PYTHON_BIN" == "$ROS2_VENV/bin/python3" ]]; then
    report PASS "python is the ros2-humble venv"
else
    report FAIL "python is the ros2-humble venv" "expected $ROS2_VENV/bin/python, got $PYTHON_BIN"
fi

if [[ -f /opt/ros/humble/setup.bash ]]; then
    report PASS "ROS 2 Humble setup.bash" "/opt/ros/humble/setup.bash"
else
    report FAIL "ROS 2 Humble setup.bash"
fi

if python -c 'import rclpy, turtlesim' >/dev/null 2>&1; then
    report PASS "import rclpy and turtlesim"
else
    report FAIL "import rclpy and turtlesim"
fi

if python -c 'import pytest' >/dev/null 2>&1; then
    report PASS "import pytest"
else
    report FAIL "import pytest"
fi

if [[ -x /usr/bin/colcon ]]; then
    report PASS "colcon executable" "/usr/bin/colcon"
else
    report FAIL "colcon executable"
fi

if [[ -f "$MODULE2_ROOT/ros2_ws/install/setup.bash" ]]; then
    report PASS "workspace install/setup.bash"
else
    report FAIL "workspace install/setup.bash" "bash scripts/build_ws.sh 를 먼저 실행하세요"
fi

pkg_list="$(ros2 pkg list 2>/dev/null || true)"
for pkg in turtle_interfaces turtle_py turtle_cpp; do
    pkg_prefix="$(ros2 pkg prefix "$pkg" 2>/dev/null || true)"
    expected_prefix="$MODULE2_ROOT/ros2_ws/install/$pkg"
    if [[ -n "$pkg_prefix" && "$(realpath -m -- "$pkg_prefix")" == "$(realpath -m -- "$expected_prefix")" ]] && \
       printf '%s\n' "$pkg_list" | grep -qx "$pkg"; then
        report PASS "current workspace package $pkg" "$pkg_prefix"
    else
        report FAIL "current workspace package $pkg" "expected $expected_prefix, got ${pkg_prefix:-<없음>}"
    fi
done
if printf '%s\n' "$pkg_list" | grep -qx turtlesim; then
    report PASS "ros2 pkg list turtlesim"
else
    report FAIL "ros2 pkg list turtlesim"
fi

if ros2 interface show turtle_interfaces/action/DrawPolygon >/dev/null 2>&1; then
    report PASS "ros2 interface show DrawPolygon"
else
    report FAIL "ros2 interface show DrawPolygon"
fi

executables="$(ros2 pkg executables turtle_py 2>/dev/null || true)"
if printf '%s\n' "$executables" | grep -q 'draw_polygon_client'; then
    report PASS "turtle_py draw_polygon_client executable"
else
    report FAIL "turtle_py draw_polygon_client executable"
fi

if [[ -x "$MODULE2_ROOT/ros2_ws/install/turtle_cpp/lib/turtle_cpp/distance_publisher" ]]; then
    report PASS "turtle_cpp distance_publisher binary"
else
    report FAIL "turtle_cpp distance_publisher binary"
fi

pytest_out="$(
    cd "$MODULE2_ROOT/ros2_ws/src/turtle_py"
    python -m pytest test/test_calculations.py -q --tb=line 2>&1
)" && pytest_rc=0 || pytest_rc=$?
if [[ "$pytest_rc" -eq 0 ]]; then
    report PASS "pytest test_calculations.py" "$(printf '%s' "$pytest_out" | tail -n 1)"
else
    report FAIL "pytest test_calculations.py" "$(printf '%s' "$pytest_out" | tail -n 5)"
fi

printf '결과: PASS %s  FAIL %s\n' "$pass" "$fail"
if [[ "$fail" -ne 0 ]]; then
    exit 1
fi
exit 0
