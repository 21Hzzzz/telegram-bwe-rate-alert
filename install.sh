#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="https://github.com/21Hzzzz/telegram-bwe-rate-alert.git"
APP_DIR="/opt/telegram-bwe-rate-alert"
CONFIG_DIR="/etc/telegram-bwe-rate-alert"
STATE_DIR="/var/lib/telegram-bwe-rate-alert"
SERVICE="telegram-bwe-rate-alert"

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
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

"${APP_DIR}/venv/bin/python" "${APP_DIR}/app.py" configure \
  --config "${CONFIG_DIR}/config.json" \
  --session "${STATE_DIR}/telegram"

install -m 0644 "${APP_DIR}/telegram-bwe-rate-alert.service" "/etc/systemd/system/${SERVICE}.service"
systemctl daemon-reload
systemctl enable --now "${SERVICE}"
echo "Installed and running. Check with: systemctl status ${SERVICE}"
