#!/usr/bin/env bash
# Bootstrap idempotente di GestLab SaaS su Ubuntu (Lightsail).
# Eseguire come root (sudo bash setup-server.sh ...).
set -euo pipefail

APP_DIR="/opt/gestlab/app"
ENV_DIR="/etc/gestlab"
ENV_FILE="${ENV_DIR}/gestlab.env"
ENV_SRC="${ENV_SRC:-/tmp/gestlab.env}"
GIT_REPO="${GIT_REPO:-https://github.com/AleLuzzi/GestLab2.git}"
GIT_REF="${GIT_REF:-main}"
SOURCE_MODE="${SOURCE_MODE:-git}"
BUNDLE_PATH="${BUNDLE_PATH:-/tmp/gestlab-src.tgz}"
SERVER_NAME="${SERVER_NAME:-_}"
ENABLE_HTTPS="${ENABLE_HTTPS:-0}"
APP_USER="${APP_USER:-ubuntu}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) GIT_REPO="$2"; shift 2 ;;
    --ref) GIT_REF="$2"; shift 2 ;;
    --source) SOURCE_MODE="$2"; shift 2 ;;
    --bundle) BUNDLE_PATH="$2"; shift 2 ;;
    --server-name) SERVER_NAME="$2"; shift 2 ;;
    --env-src) ENV_SRC="$2"; shift 2 ;;
    --app-user) APP_USER="$2"; shift 2 ;;
    --https) ENABLE_HTTPS=1; shift ;;
    -h|--help)
      echo "Uso: sudo bash setup-server.sh [--source git|local] [--repo URL] [--ref BRANCH]"
      echo "         [--bundle PATH] [--server-name NOME] [--env-src PATH] [--https]"
      exit 0
      ;;
    *)
      echo "Argomento sconosciuto: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Eseguire come root: sudo bash $0 ..." >&2
  exit 1
fi

if [[ "$APP_USER" == "root" ]]; then
  APP_USER="ubuntu"
fi

sql_escape() {
  printf '%s' "$1" | sed "s/'/''/g"
}

require_env() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "$value" ]]; then
    echo "Variabile obbligatoria mancante: $name" >&2
    exit 1
  fi
}

export DEBIAN_FRONTEND=noninteractive

echo "==> Aggiornamento pacchetti e installazione componenti"
apt-get update -y
apt-get upgrade -y
apt-get install -y python3 python3-venv python3-pip git nginx mariadb-server curl
if [[ "$ENABLE_HTTPS" == "1" ]]; then
  apt-get install -y certbot python3-certbot-nginx
fi

systemctl enable --now mariadb
systemctl enable --now nginx

if [[ ! -f "$ENV_SRC" ]]; then
  echo "File env non trovato: $ENV_SRC" >&2
  exit 1
fi

install -d -m 750 "$ENV_DIR"
install -m 640 "$ENV_SRC" "$ENV_FILE"
chown root:"$APP_USER" "$ENV_FILE"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

require_env DB_NAME
require_env DB_USER
require_env DB_PWD
require_env JWT_SECRET
require_env GESTLAB_ADMIN_EMAIL
require_env GESTLAB_ADMIN_PASSWORD

if [[ ! "$DB_NAME" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "DB_NAME non valido" >&2
  exit 1
fi
if [[ ! "$DB_USER" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "DB_USER non valido" >&2
  exit 1
fi

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
GESTLAB_TENANT_NOME="${GESTLAB_TENANT_NOME:-Laboratorio Test AWS}"

echo "==> Database e utente applicativo"
DB_USER_ESC="$(sql_escape "$DB_USER")"
DB_PWD_ESC="$(sql_escape "$DB_PWD")"

mariadb <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER_ESC}'@'127.0.0.1' IDENTIFIED BY '${DB_PWD_ESC}';
ALTER USER '${DB_USER_ESC}'@'127.0.0.1' IDENTIFIED BY '${DB_PWD_ESC}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER_ESC}'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

echo "==> Codice applicazione in ${APP_DIR}"
install -d -m 755 /opt/gestlab
chown "$APP_USER:$APP_USER" /opt/gestlab

if [[ "$SOURCE_MODE" == "local" ]]; then
  if [[ ! -f "$BUNDLE_PATH" ]]; then
    echo "Archivio locale non trovato: $BUNDLE_PATH" >&2
    exit 1
  fi
  install -d -m 755 "$APP_DIR"
  tar -xzf "$BUNDLE_PATH" -C "$APP_DIR"
elif [[ "$SOURCE_MODE" == "git" ]]; then
  if [[ -d "$APP_DIR/.git" ]]; then
    sudo -u "$APP_USER" git -C "$APP_DIR" fetch --all --prune
    sudo -u "$APP_USER" git -C "$APP_DIR" checkout "$GIT_REF"
    sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only origin "$GIT_REF" || \
      sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only
  else
    rm -rf "$APP_DIR"
    sudo -u "$APP_USER" git clone --branch "$GIT_REF" --depth 1 "$GIT_REPO" "$APP_DIR" || \
      sudo -u "$APP_USER" git clone "$GIT_REPO" "$APP_DIR"
    sudo -u "$APP_USER" git -C "$APP_DIR" checkout "$GIT_REF" || true
  fi
else
  echo "SOURCE_MODE non valido: $SOURCE_MODE (usare git o local)" >&2
  exit 1
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"
install -m 640 "$ENV_FILE" "$APP_DIR/.env"
chown "$APP_USER:$APP_USER" "$APP_DIR/.env"

echo "==> Ambiente Python"
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python3" -m pip install --upgrade pip
if [[ -f "$APP_DIR/requirements-web.txt" ]]; then
  sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements-web.txt"
else
  grep -viE '^(kivy|kivymd)' "$APP_DIR/requirements.txt" > /tmp/gestlab-req-web.txt
  sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -r /tmp/gestlab-req-web.txt
fi

echo "==> Bootstrap schema SaaS"
sudo -u "$APP_USER" bash -c "cd '$APP_DIR' && set -a && . '$ENV_FILE' && set +a && . .venv/bin/activate && python -m saas.bootstrap"

echo "==> Servizio systemd"
cat > /etc/systemd/system/gestlab.service <<UNIT
[Unit]
Description=GestLab SaaS FastAPI
After=network.target mariadb.service
Requires=mariadb.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${APP_DIR}/.venv/bin/python3 -m uvicorn saas.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now gestlab
systemctl restart gestlab

echo "==> Nginx reverse proxy"
cat > /etc/nginx/sites-available/gestlab <<NGINX
server {
    listen 80;
    server_name ${SERVER_NAME};

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

ln -sfn /etc/nginx/sites-available/gestlab /etc/nginx/sites-enabled/gestlab
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

if [[ "$ENABLE_HTTPS" == "1" ]]; then
  if [[ "$SERVER_NAME" == "_" || "$SERVER_NAME" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "HTTPS richiesto ma SERVER_NAME non e' un dominio: $SERVER_NAME" >&2
    exit 1
  fi
  LE_EMAIL="${LETSENCRYPT_EMAIL:-$GESTLAB_ADMIN_EMAIL}"
  certbot --nginx -d "$SERVER_NAME" --non-interactive --agree-tos --email "$LE_EMAIL" --redirect
fi

echo "==> Verifica locale"
sleep 2
curl -fsS http://127.0.0.1:8000/health
echo
curl -fsSI http://127.0.0.1:8000/ | head -n 5

echo "==> Deploy completato"
systemctl --no-pager --full status gestlab || true
