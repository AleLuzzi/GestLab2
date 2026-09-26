#!/usr/bin/env bash
# Aggiorna il codice sul server e riavvia GestLab.
# Eseguire come root.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/gestlab/app}"
APP_USER="${APP_USER:-ubuntu}"
SOURCE_MODE="${SOURCE_MODE:-git}"
GIT_REF="${GIT_REF:-main}"
BUNDLE_PATH="${BUNDLE_PATH:-/tmp/gestlab-src.tgz}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE_MODE="$2"; shift 2 ;;
    --ref) GIT_REF="$2"; shift 2 ;;
    --bundle) BUNDLE_PATH="$2"; shift 2 ;;
    --app-user) APP_USER="$2"; shift 2 ;;
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

if [[ ! -d "$APP_DIR" ]]; then
  echo "Applicazione non trovata in $APP_DIR. Eseguire prima setup-server.sh." >&2
  exit 1
fi

if [[ "$SOURCE_MODE" == "local" ]]; then
  tar -xzf "$BUNDLE_PATH" -C "$APP_DIR"
  chown -R "$APP_USER:$APP_USER" "$APP_DIR"
elif [[ "$SOURCE_MODE" == "git" ]]; then
  sudo -u "$APP_USER" git -C "$APP_DIR" fetch --all --prune
  sudo -u "$APP_USER" git -C "$APP_DIR" checkout "$GIT_REF"
  sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only origin "$GIT_REF" || \
    sudo -u "$APP_USER" git -C "$APP_DIR" pull --ff-only
else
  echo "SOURCE_MODE non valido: $SOURCE_MODE" >&2
  exit 1
fi

if [[ -f "$APP_DIR/requirements-web.txt" ]]; then
  sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements-web.txt"
fi

systemctl restart gestlab
sleep 2
curl -fsS http://127.0.0.1:8000/health
echo
systemctl --no-pager --full status gestlab || true
