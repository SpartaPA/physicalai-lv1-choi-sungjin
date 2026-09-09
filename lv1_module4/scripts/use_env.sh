#!/usr/bin/env bash
# Run in each Ubuntu terminal: source scripts/use_env.sh
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    printf 'source scripts/use_env.sh 로 실행하세요.\n' >&2
    exit 1
fi

_module4_source() {
    local restore_nounset=0 source_status=0
    if [[ -o nounset ]]; then
        restore_nounset=1
        set +u
    fi
    if source "$1"; then
        source_status=0
    else
        source_status=$?
    fi
    if [[ "$restore_nounset" -eq 1 ]]; then
        set -u
    fi
    return "$source_status"
}

_module4_activate() {
    local module_root venv_dir candidate
    module_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)" || return 1
    if [[ ! -f /opt/ros/humble/setup.bash ]]; then
        printf 'ROS 2 Humble이 없습니다. README 2단계에 따라 Ubuntu 22.04에 먼저 설치하세요.\n' >&2
        return 1
    fi
    if [[ -n "${ROS_DISTRO:-}" && "$ROS_DISTRO" != humble ]]; then
        printf '현재 ROS_DISTRO=%s입니다. 다른 ROS 배포판을 불러오지 않은 Ubuntu 22.04 터미널에서 실행하세요.\n' "$ROS_DISTRO" >&2
        return 1
    fi

    venv_dir="${MODULE4_VENV:-}"
    if [[ -z "$venv_dir" ]]; then
        for candidate in "$module_root/.venv" "$HOME/.venvs/physicalai-lv1-math"; do
            if [[ -f "$candidate/pyvenv.cfg" && -f "$candidate/bin/activate" && -x "$candidate/bin/python" ]]; then
                venv_dir="$candidate"
                break
            fi
        done
    fi
    if [[ ! -f "$venv_dir/pyvenv.cfg" || ! -f "$venv_dir/bin/activate" || ! -x "$venv_dir/bin/python" ]]; then
        printf '수학 가상환경을 찾지 못했습니다. README 2단계대로 .venv를 만들거나 MODULE4_VENV를 지정하세요.\n' >&2
        return 1
    fi
    venv_dir="$(cd -- "$venv_dir" && pwd -P)" || return 1
    if ! "$venv_dir/bin/python" - "$venv_dir" <<'PY'
import pathlib
import sys

os_info = dict(line.split('=', 1) for line in pathlib.Path('/etc/os-release').read_text().splitlines() if '=' in line)
valid = (os_info.get('ID', '').strip('"') == 'ubuntu'
         and os_info.get('VERSION_ID', '').strip('"') == '22.04'
         and sys.version_info[:2] == (3, 10)
         and sys.prefix != sys.base_prefix
         and pathlib.Path(sys.prefix).resolve() == pathlib.Path(sys.argv[1]).resolve())
if not valid:
    sys.exit('Ubuntu 22.04와 Python 3.10 가상환경이 필요합니다. README 1~2단계를 확인하세요.')
PY
    then
        return 1
    fi

    _module4_source "$venv_dir/bin/activate" || return $?
    if [[ "$(command -v python)" != "$venv_dir/bin/python" ]]; then
        printf '선택한 가상환경 경로와 활성화된 Python이 다릅니다. 옮긴 가상환경은 새로 생성하세요.\n' >&2
        return 1
    fi
    _module4_source /opt/ros/humble/setup.bash || return $?
    if [[ "${ROS_DISTRO:-}" != humble ]] || ! python -c 'import rclpy, turtlesim.msg' >/dev/null 2>&1; then
        printf 'Humble을 현재 가상환경에서 불러오지 못했습니다. ROS 설치 상태를 확인하세요.\n' >&2
        return 1
    fi

    # Keep apt-installed ROS packages out of the notebook's pip freeze output.
    export PIP_LOCAL=1
    # Keep the existing venv directory and packages; only shorten its shell label.
    if [[ -z "${_OLD_VIRTUAL_PS1+x}" ]]; then
        _OLD_VIRTUAL_PS1="${PS1:-}"
    fi
    PS1="(venv) ${_OLD_VIRTUAL_PS1}"
    export PS1 VIRTUAL_ENV_PROMPT='(venv) '
    printf 'Ubuntu: 22.04 (jammy)\nROS_DISTRO: %s\nPython: %s\nPrompt: (venv)\n' "$ROS_DISTRO" "$(command -v python)"
}

if _module4_activate; then
    unset -f _module4_activate _module4_source
else
    unset -f _module4_activate _module4_source
    return 1
fi
