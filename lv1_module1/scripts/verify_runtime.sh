#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C.UTF-8
export TZ=Asia/Seoul
base=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
stage=${1:?Usage: bash scripts/verify_runtime.sh env|services|keysetup|ssh|scp|tty|udev}
key=/home/chsjh/.ssh/physicalai_lv1_module1_completion_ed25519
ssh_opts=(-i "$key" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes)
printf 'stage=%s time=%s\n' "$stage" "$(date -Iseconds)"

case "$stage" in
env)
  cd "$base"
  whoami
  hostname
  grep '^PRETTY_NAME=' /etc/os-release
  uname -r
  pwd
  source /home/chsjh/.venvs/ros2-humble/bin/activate
  which python
  python --version
  python -c 'import sys; print("venv_active=" + str(sys.prefix != sys.base_prefix)); assert sys.prefix != sys.base_prefix'
  printf '[PASS] Ubuntu and existing Python venv verified\n'
  ;;
services)
  [[ $EUID -eq 0 ]]
  systemctl start ssh systemd-udevd
  dpkg-query -W -f='${Package} ${Version} ${Status}\n' openssh-server
  systemctl status ssh --no-pager --lines=3
  systemctl is-active ssh systemd-udevd
  ss -tlnp | grep ':22'
  systemctl is-active --quiet ssh
  ss -tln '( sport = :22 )' | grep -q LISTEN
  printf '[PASS] SSH service active and TCP port 22 listening\n'
  ;;
keysetup)
  [[ $(id -un) == chsjh ]]
  if [[ ! -e "$key" && ! -e "$key.pub" ]]; then
    ssh-keygen -t ed25519 -f "$key" -N '' -C physicalai-lv1-module1-completion
  else
    printf 'Existing completion key reused; no key overwritten\n'
  fi
  if ! grep -qxF "$(cat "$key.pub")" /home/chsjh/.ssh/authorized_keys; then
    ssh-copy-id -f -i "$key.pub" -o IdentityFile=/home/chsjh/.ssh/physicalai_lv1_module1_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes chsjh@localhost
  else
    printf 'Public key already registered; duplicate append skipped\n'
  fi
  ssh-keygen -lf "$key.pub"
  ;;
ssh)
  [[ $(id -un) == chsjh ]]
  test -f "$key"
  ssh-keygen -lf "$key.pub"
  ssh -tt "${ssh_opts[@]}" chsjh@localhost 'source /home/chsjh/.venvs/ros2-humble/bin/activate; which python; tty; who; printf "SSH_CONNECTION=%s\n" "$SSH_CONNECTION"; test -n "$SSH_CONNECTION" && echo "[PASS] key-only SSH session verified"'
  ssh "${ssh_opts[@]}" chsjh@localhost 'uname -a'
  ;;
scp)
  target=/tmp/physicalai_module1_20260907
  ssh "${ssh_opts[@]}" chsjh@localhost "mkdir -p '$target'"
  scp "${ssh_opts[@]}" "$base/rules/99-robot-sensor.rules" "chsjh@localhost:$target/99-robot-sensor.rules"
  sha256sum "$base/rules/99-robot-sensor.rules"
  ssh "${ssh_opts[@]}" chsjh@localhost "sha256sum '$target/99-robot-sensor.rules'"
  local_hash=$(sha256sum "$base/rules/99-robot-sensor.rules" | cut -d' ' -f1)
  remote_hash=$(ssh "${ssh_opts[@]}" chsjh@localhost "sha256sum '$target/99-robot-sensor.rules'" | cut -d' ' -f1)
  [[ "$local_hash" == "$remote_hash" ]]
  printf '[PASS] scp source and destination SHA256 match\n'
  ;;
tty)
  ssh "${ssh_opts[@]}" chsjh@localhost 'ls -l /dev/tty*'
  ;;
udev)
  [[ $EUID -eq 0 ]]
  sensor_dir=/home/chsjh/fake_sensors_physicalai_lv1
  lidar_image=$sensor_dir/lidar.img
  imu_image=$sensor_dir/imu.img
  install -d -o chsjh -g chsjh "$sensor_dir"
  for spec in 'lidar:16777216' 'imu:25165824'; do
    name=${spec%:*}; size=${spec#*:}; file=$sensor_dir/$name.img
    [[ ! -L "$file" ]]
    if [[ ! -e "$file" ]]; then
      truncate -s "$size" "$file"
      chown chsjh:chsjh "$file"
    fi
    [[ -f "$file" && $(stat -c %s "$file") -eq $size ]]
  done
  detach_own() {
    local image device
    for image in "$lidar_image" "$imu_image"; do
      while IFS=: read -r device _; do
        [[ -n "$device" ]] || continue
        [[ $(losetup -n -O BACK-FILE "$device") == "$image" ]]
        [[ -z $(lsblk -n -o MOUNTPOINTS "$device" | tr -d '[:space:]') ]]
        losetup -d "$device"
      done < <(losetup -j "$image")
    done
    udevadm settle --timeout=10
  }
  trigger_pair() {
    udevadm trigger --action=change --sysname-match="${lidar_device#/dev/}"
    udevadm trigger --action=change --sysname-match="${imu_device#/dev/}"
    udevadm settle --timeout=10
  }
  check_pair() {
    local name expected device backing
    for name in lidar imu; do
      expected=$sensor_dir/$name.img
      device=$(readlink -f "/dev/robot_$name")
      backing=$(losetup -n -O BACK-FILE "$device")
      printf 'robot_%s -> %s backing=%s\n' "$name" "$device" "$backing"
      [[ "$backing" == "$expected" ]]
      [[ $(stat -c '%a:%G' "$device") == '660:disk' ]]
    done
    [[ $(readlink -f /dev/robot_lidar) == "$lidar_device" ]]
    [[ $(readlink -f /dev/robot_imu) == "$imu_device" ]]
  }
  detach_own
  systemctl start systemd-udevd
  install -m 0644 "$base/rules/99-robot-sensor.rules" /etc/udev/rules.d/99-robot-sensor.rules
  udevadm control --reload-rules
  lidar_device=$(losetup -f --show "$lidar_image")
  imu_device=$(losetup -f --show "$imu_image")
  trigger_pair
  mkdir -p "$base/evidence"
  udevadm info --attribute-walk --name="$lidar_device" > "$base/evidence/udev_lidar_attributes.txt"
  udevadm info --attribute-walk --name="$imu_device" > "$base/evidence/udev_imu_attributes.txt"
  printf 'FIRST: lidar=%s imu=%s\n' "$lidar_device" "$imu_device"
  cat "/sys/class/block/${lidar_device#/dev/}/loop/backing_file"
  cat "/sys/class/block/${imu_device#/dev/}/loop/backing_file"
  ls -l /dev/robot_lidar /dev/robot_imu
  check_pair
  first_lidar=$lidar_device; first_imu=$imu_device
  printf '[PASS] first attachment links and mode/group verified\n'
  detach_own
  imu_device=$(losetup -f --show "$imu_image")
  lidar_device=$(losetup -f --show "$lidar_image")
  trigger_pair
  printf 'REVERSED: imu=%s lidar=%s\n' "$imu_device" "$lidar_device"
  ls -l /dev/robot_lidar /dev/robot_imu
  check_pair
  [[ "$first_lidar" == "$imu_device" && "$first_imu" == "$lidar_device" ]]
  printf '[PASS] loop numbers exchanged; fixed links still identify correct sensors\n'
  printf '[PASS] only this assignment images detached; no mounted device touched\n'
  ;;
*) printf 'Unknown stage\n' >&2; exit 2 ;;
esac
