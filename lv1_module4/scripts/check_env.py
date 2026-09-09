"""모듈 4의 Ubuntu, 가상환경, ROS 2 Humble 및 노트북 환경을 검사한다."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys


DEPENDENCIES = (
    "numpy", "scipy", "matplotlib", "PIL", "pytest",
    "ipykernel", "jupyterlab", "nbclient", "nbformat", "rclpy", "turtlesim.msg",
)


def normalized_path(value):
    # python 실행 파일의 심볼릭 링크를 풀면 venv 경로가 사라지므로 풀지 않는다.
    return os.path.normcase(os.path.abspath(value))


def package_name(value):
    return re.sub(r"[-_.]+", "-", value).lower()


def frozen_package_names(text):
    names = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-e "):
            match = re.search(r"[#&]egg=([^&]+)", line)
            if match:
                names.add(package_name(match.group(1)))
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)(?:===|==|\s+@\s+)", line)
        if match:
            names.add(package_name(match.group(1)))
    return names


def visible_ros_packages():
    names = {"rclpy", "turtlesim"}
    for distribution in metadata.distributions():
        location = Path(distribution.locate_file("")).resolve()
        if location.is_relative_to(Path("/opt/ros")):
            name = distribution.metadata.get("Name")
            if name:
                names.add(package_name(name))
    return names


def inspect_environment():
    checks = []

    def record(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    try:
        release = platform.freedesktop_os_release()
    except OSError:
        release = {}
    os_info = {key: release.get(key, "") for key in (
        "ID", "PRETTY_NAME", "VERSION_ID", "VERSION_CODENAME",
    )}
    record(
        "ubuntu_22_04_jammy",
        os_info["ID"] == "ubuntu" and os_info["VERSION_ID"] == "22.04"
        and os_info["VERSION_CODENAME"] == "jammy",
        f"{os_info['PRETTY_NAME'] or platform.system()}; "
        f"OS codename={os_info['VERSION_CODENAME'] or 'unknown'} (ROS 이름과 별개)",
    )
    record("python_3_10", sys.version_info[:2] == (3, 10), platform.python_version())
    record("python_is_venv", sys.prefix != sys.base_prefix, sys.executable)
    activated = os.environ.get("VIRTUAL_ENV", "")
    record(
        "activated_venv_matches_python",
        bool(activated) and normalized_path(activated) == normalized_path(sys.prefix),
        {"active": activated, "python_prefix": sys.prefix},
    )
    record("ros_humble", os.environ.get("ROS_DISTRO") == "humble",
           os.environ.get("ROS_DISTRO", "not sourced"))
    record("pip_local", os.environ.get("PIP_LOCAL") == "1",
           "PIP_LOCAL=1" if os.environ.get("PIP_LOCAL") == "1" else "PIP_LOCAL=1 설정 필요")

    versions = {}
    for name in DEPENDENCIES:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", "")
            versions[name] = version
            record(f"import_{name}", True, version or "import OK")
        except Exception as error:
            detail = type(error).__name__
            if isinstance(error, ModuleNotFoundError):
                detail += f": {error.name}"
            record(f"import_{name}", False, detail)

    try:
        freeze = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        frozen = frozen_package_names(freeze.stdout)
        leaked = sorted(frozen & visible_ros_packages())
        record(
            "pip_freeze_excludes_ros",
            freeze.returncode == 0 and not leaked,
            {"returncode": freeze.returncode, "package_count": len(frozen),
             "ros_packages_in_freeze": leaked},
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        record("pip_freeze_excludes_ros", False, type(error).__name__)

    # 별도 프로세스에서만 생성하고 즉시 종료한다. 사용자 노드나 커널을 종료하지 않는다.
    probe = """
import os
import rclpy
from rclpy.context import Context
context = Context()
node = None
try:
    rclpy.init(context=context)
    node = rclpy.create_node(
        'module4_environment_check_' + str(os.getpid()), context=context,
        enable_rosout=False, start_parameter_services=False,
    )
    node.get_topic_names_and_types()
    print('RCLPY_NODE_OK')
finally:
    if node is not None:
        node.destroy_node()
    if context.ok():
        context.shutdown()
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True, text=True, timeout=20, check=False,
        )
        record("rclpy_node_lifecycle", result.returncode == 0
               and "RCLPY_NODE_OK" in result.stdout.splitlines(),
               {"returncode": result.returncode, "operation": "create/query/destroy"})
    except (OSError, subprocess.TimeoutExpired) as error:
        record("rclpy_node_lifecycle", False, type(error).__name__)

    passed = sum(check["passed"] for check in checks)
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "module_root": str(Path(__file__).resolve().parents[1]),
        "os": os_info,
        "python": {"executable": sys.executable, "prefix": sys.prefix,
                   "base_prefix": sys.base_prefix, "version": platform.python_version()},
        "ros_distro": os.environ.get("ROS_DISTRO", ""),
        "package_versions": versions,
        "checks": checks,
        "summary": {"passed": passed, "failed": len(checks) - passed},
        "ok": passed == len(checks),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="검사 결과를 저장할 JSON 경로")
    args = parser.parse_args()
    receipt = inspect_environment()
    for check in receipt["checks"]:
        detail = check["detail"]
        if not isinstance(detail, str):
            detail = json.dumps(detail, ensure_ascii=False)
        print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}: {detail}")
    print(f"PASS {receipt['summary']['passed']} / FAIL {receipt['summary']['failed']}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(f"JSON: {args.output}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
