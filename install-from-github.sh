#!/usr/bin/env bash
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo ./install-from-github.sh"; exit 1; }

repository_url=${ZEBRA_RFID_REPOSITORY_URL:-https://github.com/PCgoDK/zebra-rfid-server.git}
branch=${ZEBRA_RFID_BRANCH:-main}
source_dir=$(mktemp -d)
trap 'rm -rf "$source_dir"' EXIT

apt-get update
apt-get install -y git
git clone --depth 1 --branch "$branch" "$repository_url" "$source_dir"
bash "$source_dir/install.sh"