#!/usr/bin/env bash
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo ./backup.sh [output-file]"; exit 1; }
backup_dir=/var/lib/zebra-rfid-server/backups
timestamp=$(date +%Y%m%d-%H%M%S)
output=${1:-"$backup_dir/zebra-rfid-server-$timestamp.dump"}

install -d -m 0770 -o zebra-rfid-server -g postgres "$backup_dir"
sudo -u postgres pg_dump --format=custom --file="$output" zebra_rfid_server
chown zebra-rfid-server:zebra-rfid-server "$output"
chmod 0640 "$output"
printf 'Backup created: %s\n' "$output"