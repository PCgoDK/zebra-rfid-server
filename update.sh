#!/usr/bin/env bash
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo ./update.sh"; exit 1; }
bash "$(dirname "${BASH_SOURCE[0]}")/install.sh"
systemctl restart zebra-rfid-server.service
systemctl is-active --quiet zebra-rfid-server.service
systemctl show zebra-rfid-server.service -p MainPID -p ExecMainStartTimestamp