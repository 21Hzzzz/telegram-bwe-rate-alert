#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="https://github.com/21Hzzzz/telegram-bwe-rate-alert.git"
APP_DIR="/opt/telegram-bwe-rate-alert"
CONFIG_DIR="/etc/telegram-bwe-rate-alert"
STATE_DIR="/var/lib/telegram-bwe-rate-alert"
SERVICE="telegram-bwe-rate-alert"

ensure_low_memory_swap() {
  local memory_kb swap_kb
  memory_kb="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
  swap_kb="$(awk '/SwapTotal:/ {print $2}' /proc/meminfo)"

  # pip's dependency resolver can briefly need more memory than a small VPS has.
  # Keep a persistent swap file so upgrades remain safe as well.
  if (( memory_kb < 786432 && swap_kb < 262144 )); then
    if [[ -e /swapfile ]]; then
      echo "Low memory and no usable swap detected; /swapfile already exists, so it will not be changed." >&2
      return
    fi
    echo "Low-memory VPS detected; creating a 512 MiB swap file for reliable installation."
    fallocate -l 512M /swapfile
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    if ! grep -qE '^/swapfile[[:space:]]' /etc/fstab; then
      echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
  fi
}

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer as root." >&2
  exit 1
fi
if [[ ! -r /etc/os-release ]]; then
  echo "Only Ubuntu and Debian are supported." >&2
  exit 1
fi
. /etc/os-release
if [[ "${ID}" != "ubuntu" && "${ID}" != "debian" ]]; then
  echo "Only Ubuntu and Debian are supported." >&2
  exit 1
fi

ensure_low_memory_swap
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y git python3 python3-venv

SOURCE_DIR="$(mktemp -d)"
trap 'rm -rf "${SOURCE_DIR}"' EXIT
git clone --depth 1 "${REPOSITORY}" "${SOURCE_DIR}/source"

systemctl stop "${SERVICE}" 2>/dev/null || true
mkdir -p "${APP_DIR}" "${CONFIG_DIR}" "${STATE_DIR}"
find "${APP_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
cp -a "${SOURCE_DIR}/source/." "${APP_DIR}/"
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --no-cache-dir --disable-pip-version-check --no-compile -r "${APP_DIR}/requirements.txt"

"${APP_DIR}/venv/bin/python" "${APP_DIR}/app.py" configure \
  --config "${CONFIG_DIR}/config.json" \
  --session "${STATE_DIR}/telegram"

install -m 0644 "${APP_DIR}/telegram-bwe-rate-alert.service" "/etc/systemd/system/${SERVICE}.service"
systemctl daemon-reload
systemctl enable --now "${SERVICE}"
echo "Installed and running. Check with: systemctl status ${SERVICE}"
