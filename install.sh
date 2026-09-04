#!/usr/bin/env bash
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run with sudo: sudo ./install.sh"; exit 1; }
source_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
app_dir=/opt/zebra-rfid-server
config_dir=/etc/zebra-rfid-server
data_dir=/var/lib/zebra-rfid-server
log_dir=/var/log/zebra-rfid-server
service_user=zebra-rfid-server
requested_admin_password=${INITIAL_ADMIN_PASSWORD:-}
if [[ -z "$requested_admin_password" && ! -f "$config_dir/server.env" ]]; then
  [[ -t 0 ]] || { echo "INITIAL_ADMIN_PASSWORD must be set for a non-interactive installation"; exit 1; }
  while true; do
    read -r -s -p "Initial administrator password: " requested_admin_password
    printf "\n"
    read -r -s -p "Confirm administrator password: " confirmed_admin_password
    printf "\n"
    [[ "$requested_admin_password" == "$confirmed_admin_password" ]] || {
      echo "Administrator passwords do not match"
      continue
    }
    [[ ${#requested_admin_password} -ge 12 ]] || {
      echo "Administrator password must contain at least 12 characters"
      continue
    }
    break
  done
fi
if [[ -n "$requested_admin_password" && ${#requested_admin_password} -lt 12 ]]; then
  echo "INITIAL_ADMIN_PASSWORD must contain at least 12 characters"
  exit 1
fi

apt-get update
apt-get install -y caddy python3-venv python3-pip postgresql ufw
ufw allow 8080/tcp comment 'Zebra RFID Server API'
ufw allow 5084/tcp comment 'Zebra RFID reader input'
ufw allow 443/tcp comment 'Zebra RFID Server HTTPS'
id "$service_user" &>/dev/null || useradd --system --home-dir "$data_dir" --create-home --shell /usr/sbin/nologin "$service_user"
install -d -o "$service_user" -g "$service_user" "$app_dir" "$data_dir" "$log_dir"
install -d -o "$service_user" -g "$service_user" "$app_dir/app"
cp -a app/. "$app_dir/app/"
chown -R "$service_user":"$service_user" "$app_dir/app"
find "$app_dir/app" -type d -exec chmod 0755 {} +
find "$app_dir/app" -type f -exec chmod 0644 {} +
install -m 0644 requirements.txt "$app_dir/requirements.txt"
install -d -o "$service_user" -g "$service_user" "$app_dir/migrations"
cp -a migrations/. "$app_dir/migrations/"
chown -R "$service_user":"$service_user" "$app_dir/migrations"
install -m 0644 alembic.ini "$app_dir/alembic.ini"
python3 -m venv "$app_dir/.venv"
"$app_dir/.venv/bin/pip" install --upgrade pip
"$app_dir/.venv/bin/pip" install -r "$app_dir/requirements.txt"
install -d -m 0750 -o root -g "$service_user" "$config_dir"
if [[ ! -f "$config_dir/server.env" ]]; then
  install -m 0640 .env.example "$config_dir/server.env"
  db_password=$(openssl rand -hex 32)
  jwt_secret=$(openssl rand -hex 32)
  admin_password=${requested_admin_password:-$(openssl rand -base64 24 | tr -d '\n')}
  sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=$db_password/; s/^JWT_SECRET=.*/JWT_SECRET=$jwt_secret/; s/^INITIAL_ADMIN_PASSWORD=.*/INITIAL_ADMIN_PASSWORD=$admin_password/" "$config_dir/server.env"
fi
sed -i 's/\r$//' "$config_dir/server.env"
if grep -q '^DB_PASSWORD=change-me$' "$config_dir/server.env"; then
  db_password=$(openssl rand -hex 32)
  sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=$db_password/" "$config_dir/server.env"
fi
if grep -q '^JWT_SECRET=replace-with-a-long-random-secret$' "$config_dir/server.env"; then
  jwt_secret=$(openssl rand -hex 32)
  sed -i "s/^JWT_SECRET=.*/JWT_SECRET=$jwt_secret/" "$config_dir/server.env"
fi
if ! grep -q '^INITIAL_ADMIN_USERNAME=' "$config_dir/server.env"; then
  admin_password=$(openssl rand -base64 24 | tr -d '\n')
  printf '\nINITIAL_ADMIN_USERNAME=admin\nINITIAL_ADMIN_PASSWORD=%s\n' "$admin_password" >> "$config_dir/server.env"
fi
if [[ -n "$requested_admin_password" ]]; then
  sed -i "s/^INITIAL_ADMIN_PASSWORD=.*/INITIAL_ADMIN_PASSWORD=$requested_admin_password/" "$config_dir/server.env"
fi
chown root:"$service_user" "$config_dir/server.env"
db_password=$(sed -n 's/^DB_PASSWORD=//p' "$config_dir/server.env")
[[ -n "$db_password" && "$db_password" != "change-me" ]] || { echo "DB_PASSWORD must be configured"; exit 1; }
sudo -u postgres psql -v ON_ERROR_STOP=1 --set=db_password="$db_password" <<'SQL'
SELECT format('CREATE ROLE zebra_rfid_server LOGIN PASSWORD %L', :'db_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'zebra_rfid_server')
\gexec
SQL
sudo -u postgres psql -v ON_ERROR_STOP=1 --set=db_password="$db_password" <<'SQL'
SELECT format('ALTER ROLE zebra_rfid_server PASSWORD %L', :'db_password')
\gexec
SQL
sudo -u postgres createdb --owner=zebra_rfid_server zebra_rfid_server 2>/dev/null || true
set -a
source "$config_dir/server.env"
set +a
export RESET_INITIAL_ADMIN_PASSWORD=$([[ -n "$requested_admin_password" ]] && echo 1 || echo 0)
cd "$app_dir"
"$app_dir/.venv/bin/alembic" upgrade head
"$app_dir/.venv/bin/python" -c '
from sqlalchemy import select
import os
from app.auth import hash_password
from app.database import create_session_factory
from app.config import Settings
from app.models import ApiUser
settings = Settings()
with create_session_factory(settings)() as session:
  user = session.scalar(select(ApiUser).where(ApiUser.username == settings.initial_admin_username))
  if user is None:
    session.add(ApiUser(username=settings.initial_admin_username, password_hash=hash_password(settings.initial_admin_password), role="administrator", enabled=True))
    session.commit()
  elif os.environ["RESET_INITIAL_ADMIN_PASSWORD"] == "1":
    user.password_hash = hash_password(settings.initial_admin_password)
    session.commit()
'
install -m 0644 "$source_dir/systemd/zebra-rfid-server.service" /etc/systemd/system/zebra-rfid-server.service
server_ip=$(ip -4 route get 1.1.1.1 | awk '/src/ {for (field = 1; field <= NF; field++) if ($field == "src") {print $(field + 1); exit}}')
[[ -n "$server_ip" ]] || { echo "Could not determine primary IPv4 address for HTTPS"; exit 1; }
sed "s/__SERVER_IP__/$server_ip/" "$source_dir/deploy/Caddyfile" > /etc/caddy/Caddyfile
caddy fmt --overwrite /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable zebra-rfid-server.service
systemctl restart zebra-rfid-server.service
systemctl enable caddy.service
systemctl restart caddy.service
install -m 0644 /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt "$data_dir/caddy-root.crt"
chown "$service_user":"$service_user" "$data_dir/caddy-root.crt"
printf 'Internal HTTPS: https://%s\nAndroid CA certificate: %s/caddy-root.crt\n' "$server_ip" "$data_dir"