# 모듈 2 — turtlesim ROS 2 패키지

Ubuntu 22.04 / ROS 2 Humble에서 `ros2-humble` 가상환경 Python으로 실행하는 과제 폴더임. 구현과 문제별 실험 기록은 [report.md](report.md)에 정리함.

다른 PC에서 GitHub를 클론해도 **venv와 빌드 결과는 따라오지 않음.** 아래 순서로 가상환경과 워크스페이스를 그 기계에서 다시 만듦.

## 1. 다른 PC에서 처음 설정

Ubuntu 22.04(WSL2 포함)의 **Bash 터미널에서 ROS 2 Humble을 설치한 뒤** 진행함. 새 Ubuntu라면 먼저 [ROS 2 Humble 공식 설치 안내](https://github.com/ros2/ros2_documentation/blob/humble/source/Installation/Ubuntu-Install-Debs.rst)의 저장소 설정과 Desktop 설치를 완료함. ROS 패키지 저장소를 등록하기 전에는 `apt install ros-humble-desktop`만으로 설치할 수 없음.

Humble 설치 후 빌드 도구와 가상환경 도구를 준비함.

```bash
sudo apt update
sudo apt install -y ros-dev-tools python3-colcon-common-extensions python3-venv python3-pytest git
```

접근 권한이 있는 계정으로 저장소를 클론한 뒤 모듈 2 폴더로 이동함.

```bash
git clone https://github.com/SpartaPA/physicalai-lv1-choi-sungjin.git
cd physicalai-lv1-choi-sungjin/lv1_module2
```

가상환경을 만들고 워크스페이스를 빌드함. 기본 venv 경로는 `$HOME/.venvs/ros2-humble`임.

```bash
bash scripts/setup_venv.sh
source scripts/use_env.sh
bash scripts/build_ws.sh
source scripts/use_env.sh
python -c 'import sys; print(sys.executable)'
bash scripts/check_env.sh
```

`setup_venv.sh`는 Ubuntu 22.04의 `/usr/bin/python3`(Python 3.10)와 `--system-site-packages`로 venv를 만들어 apt로 설치한 ROS 패키지를 사용함. 기존 venv도 Python 버전, 시스템 Python과의 연결, 시스템 패키지 사용 여부, ROS 패키지 import를 검사함. 호환되지 않으면 해당 환경을 덮어쓰지 않고 중단함. ROS 바이너리와 같은 시스템 Python을 사용하는 이유는 [공식 Python 환경 안내](https://github.com/ros2/ros2_documentation/blob/humble/source/How-To-Guides/Using-Python-Packages.rst)에 설명되어 있음.

`use_env.sh`는 가상환경 → ROS 2 Humble → 현재 `ros2_ws/install` 순서로 환경을 적용함. 설정 파일을 읽다가 실패하면 오류를 반환하므로 다음 명령을 진행하기 전에 오류를 해결함. 빌드 전에는 설치 결과가 없어도 기본 환경을 적용할 수 있음.

통신은 [fastdds_loopback.xml](config/fastdds_loopback.xml)로 UDP를 `127.0.0.1`에 제한함. 같은 PC 안의 터미널끼리 실행하는 설정이며, 여러 PC에서 각자 과제를 재현할 수 있음. 서로 다른 PC의 노드를 연결하는 네트워크 설정은 포함하지 않음.

`check_env.sh`는 Python·ROS 환경, 패키지와 실행 파일, 계산 함수 테스트를 확인함. turtlesim 창이나 실제 노드 통신, 다각형 완주는 검사하지 않으므로 3절의 실행도 별도로 확인함.

`requirements.txt`는 원래 과제 PC의 `pip freeze` 스냅샷임. 시스템 패키지와 그 기계의 빌드 경로가 들어 있으므로 새 venv에서 `pip install -r requirements.txt`를 실행하지 않음.

### 가상환경 경로 지정

다른 경로에 만들려면 아래처럼 생성과 환경 선택을 함께 지정함.

```bash
bash scripts/setup_venv.sh --venv "$HOME/.venvs/module2-humble"
export ROS2_VENV="$HOME/.venvs/module2-humble"
source scripts/use_env.sh
bash scripts/build_ws.sh
source scripts/use_env.sh
bash scripts/check_env.sh
```

`setup_venv.sh` 실행 뒤 출력되는 `export ROS2_VENV=...`와 `source ...` 명령도 같은 역할을 함. 가상환경을 만드는 스크립트는 현재 터미널의 환경 변수를 직접 바꿀 수 없으므로 출력된 명령을 직접 실행함.

`ROS2_VENV`가 지정되어 있으면 그 경로를 사용함. 지정한 경로가 잘못되거나 호환되지 않으면 다른 환경으로 넘어가지 않고 중단함. 변수를 지정하지 않은 경우 `$HOME/.venvs/ros2-humble`, 이 모듈 폴더의 `.venv` 순서로 찾음. 자동 탐색으로 돌아가려면 `unset ROS2_VENV`를 실행함.

### 빌드 경로와 재빌드

한글이 포함된 중간 파일 경로에서는 Humble 인터페이스 생성 단계가 실패할 수 있음. `build_ws.sh`는 빌드 중간 파일을 아래 ASCII 경로에 두고, 소스와 `install/`은 현재 모듈 폴더에 유지함.

```text
$HOME/physicalai_lv1_build/module2/<경로 해시>/build
```

해시는 현재 워크스페이스와 가상환경의 실제 절대 경로로 계산함. 다른 폴더에 클론하거나 다른 venv로 바꾸면 별도 빌드 경로를 사용함. 이 방식으로 이전 복사본의 설치 경로나 Python 실행 경로가 재사용되는 것을 막음.

홈 경로에 한글이 있거나 빌드 위치를 직접 정하려면, 쓰기 권한이 있는 ASCII 경로를 지정함. 아래는 UID로 사용자별 경로를 나누는 예시임. 다른 복사본이나 가상환경에는 다른 이름을 사용함.

```bash
export MODULE2_BUILD_BASE="/tmp/physicalai-lv1-$UID/module2-copy-a/build"
bash scripts/build_ws.sh
source scripts/use_env.sh
bash scripts/check_env.sh
```

직접 지정하는 경로는 절대 경로와 상대 경로를 지원하며, 실제 절대 경로 전체가 ASCII여야 함. 기존 캐시가 다른 워크스페이스·venv의 것이거나 소유 정보 없이 파일이 들어 있으면 재사용을 거부함. 이 경우 기존 파일을 삭제하는 대신 새 빈 빌드 경로를 지정함.

`--symlink-install`을 사용하므로 설치 결과 일부가 빌드 폴더를 가리킴. 빌드 폴더를 지우면 실행이 깨질 수 있음. 특히 `/tmp`는 재부팅이나 정리 작업으로 비워질 수 있으므로 장기 사용에는 보존되는 ASCII 경로를 권장함. 빌드 폴더가 사라졌거나 venv를 바꾼 뒤에는 `build_ws.sh`로 재빌드하고 `use_env.sh`를 다시 적용함. 빌드 스크립트는 현재 워크스페이스의 기존 설치 환경을 적용하지 않고 빌드하여, 깨진 설치 결과가 있어도 재빌드를 시도할 수 있음.

사용하는 환경 변수는 다음과 같음.

| 변수 | 기본값 | 역할 |
| --- | --- | --- |
| `ROS2_VENV` | 미지정 시 기본 venv → 모듈 `.venv` 순서로 탐색 | 명시하면 해당 가상환경만 사용함 |
| `MODULE2_BUILD_BASE` | `$HOME/physicalai_lv1_build/module2/<경로 해시>/build` | 워크스페이스·venv별 colcon 중간 파일 경로 |
| `MODULE2_DOMAIN_ID` | `62` | ROS domain. 화면 캡처 실험은 `63` |

## 2. 이미 환경이 있는 터미널

새 터미널마다 모듈 2 폴더로 이동한 뒤 아래를 실행함. 기본 경로가 아닌 venv를 사용한다면 `export ROS2_VENV="사용한 가상환경 경로"`도 먼저 적용함.

```bash
source scripts/use_env.sh
python -c 'import sys; print(sys.executable)'
bash scripts/check_env.sh
```

Python 출력이 선택한 venv의 `bin/python`을 가리키는지 확인함. 모든 실행 터미널에 같은 venv와 `MODULE2_DOMAIN_ID`를 적용함.

## 3. 터미널 입력으로 다각형 그리기

첫 번째 터미널에서 시뮬레이터와 액션 서버를 실행함.

```bash
source scripts/use_env.sh
ros2 launch turtle_py turtle_system.launch.py
```

두 번째 터미널에서 입력 프로그램을 실행함.

```bash
source scripts/use_env.sh
ros2 run turtle_py draw_polygon_client --interactive
```

예를 들어 첫 질문에 `3`, 두 번째 질문에 `1.5`를 입력함.

```text
변의 개수를 입력하세요 (3 이상 정수): 3
한 변의 길이를 입력하세요 (m, 0보다 큰 수): 1.5
```

| 변 개수 | 그리는 도형 | 한 변을 그린 후 회전하는 각도 |
| ---: | --- | ---: |
| 3 | 삼각형 | 120° |
| 4 | 사각형 | 90° |
| 5 | 오각형 | 72° |
| 8 | 팔각형 | 45° |

변의 개수는 3 이상의 정수, 길이는 0보다 큰 유한한 수로 입력함. 잘못된 입력은 다시 물어봄. 시뮬레이터 화면 안에서 도형을 보기 위해 처음에는 길이 1~1.5로 실행함.

[draw_polygon_server.py](ros2_ws/src/turtle_py/turtle_py/draw_polygon_server.py)의 `for side_index in range(sides)`가 입력한 변의 개수만큼 반복함. 각 반복에서 한 변을 전진하고 진행률을 보내며, 외각 `360 / sides`만큼 회전함. 전진과 회전 중에는 현재 자세를 계속 읽어 목표에 도달했는지 확인함.

변을 마칠 때 `completed`와 `progress`가 출력되고, 마지막에는 `SUCCEEDED`와 실제 자세 변화로 누적한 `total_distance`가 출력됨. 제어 허용 오차가 있으므로 총 이동 거리는 `변 개수 × 길이`와 약간 다를 수 있음.

다른 도형을 새 화면에 그릴 때는 아래 명령으로 위치와 선을 초기화한 다음 입력 프로그램을 다시 실행함.

```bash
ros2 service call /reset std_srvs/srv/Empty '{}'
ros2 run turtle_py draw_polygon_client --interactive
```

입력 질문 없이 값을 명령에 직접 넣는 방식도 지원함.

```bash
ros2 run turtle_py draw_polygon_client --ros-args -p sides:=5 -p side_length:=1.5
```

turtlesim 창은 디스플레이가 있는 환경(WSLg 포함)에서 열림.

## 4. 폴더 구성

- `cpp_basics/`: 문제 1·2 C++ 구현
- `ros2_ws/src/turtle_py/`: Python 노드와 테스트
- `ros2_ws/src/turtle_cpp/`: C++ 거리 발행·구독 노드
- `ros2_ws/src/turtle_interfaces/`: 메시지·서비스·액션 정의
- `evidence/20260907/`: 실행 로그
- `screenshots/20260907/`: 실행 화면
- `bags/`: 기록·재생 실험 데이터
- `config/`, `scripts/`: 실행 환경 설정
  - `scripts/setup_venv.sh`: ros2-humble 가상환경 생성
  - `scripts/use_env.sh`: 가상환경·Humble·워크스페이스 적용
  - `scripts/build_ws.sh`: colcon 빌드
  - `scripts/check_env.sh`: 환경과 패키지 확인

`turtle_interfaces`의 필드 규격은 배포 예제와 일치함. `turtle_examples`는 구현을 참고하는 예제 패키지이며, 이 폴더의 실행 패키지는 `turtle_py`와 `turtle_cpp`임.
