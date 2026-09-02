#!/usr/bin/env bash
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo ./restore.sh <backup-file>"; exit 1; }
[[ $# -eq 1 && -f $1 ]] || { echo "Backup file not found"; exit 1; }
systemctl stop zebra-rfid-server.service
sudo -u postgres pg_restore --clean --if-exists --no-owner --dbname=zebra_rfid_server "$1"
systemctl start zebra-rfid-server.service