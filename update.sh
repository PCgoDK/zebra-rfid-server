#!/usr/bin/env bash
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo ./update.sh"; exit 1; }
exec bash "$(dirname "${BASH_SOURCE[0]}")/install.sh"