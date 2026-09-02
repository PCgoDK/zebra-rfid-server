#!/usr/bin/env bash
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo ./uninstall.sh"; exit 1; }
systemctl disable --now zebra-rfid-server.service 2>/dev/null || true
rm -f /etc/systemd/system/zebra-rfid-server.service
systemctl daemon-reload
rm -rf /opt/zebra-rfid-server
echo "Application removed. PostgreSQL database, configuration, logs, and data were preserved."