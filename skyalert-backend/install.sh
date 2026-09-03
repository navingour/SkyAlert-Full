#!/usr/bin/env bash
# SkyAlert Standalone Backend installer for Debian.
# Usage: sudo bash install.sh
set -euo pipefail

APP_DIR="/opt/skyalert-backend"
SERVICE="skyalert-backend.service"
PORT="${PORT:-8091}"

echo "==> Installing SkyAlert backend to ${APP_DIR}"
mkdir -p "${APP_DIR}"
cp -r app config importer run.py requirements.txt "${APP_DIR}/"

echo "==> Creating virtualenv"
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "==> Installing systemd service"
cp systemd/${SERVICE} /etc/systemd/system/${SERVICE}
systemctl daemon-reload
systemctl enable ${SERVICE}
systemctl restart ${SERVICE}

echo ""
echo "SkyAlert backend running on port ${PORT}."
echo "  Dashboard API : http://<host>:${PORT}/api/dashboard"
echo "  Live aircraft : http://<host>:${PORT}/api/live-aircraft"
echo "  Compat HTML   : http://<host>:${PORT}/skyalert/"
echo ""
echo "To import your existing recording:"
echo "  SQLite : sudo -u skyalert ${APP_DIR}/venv/bin/python -m importer.import_sqlite /path/to/old/skyalert_relational.db"
echo "  Postgres: DATABASE_URL=... OLD_DATABASE_URL=... ${APP_DIR}/venv/bin/python -m importer.import_postgres"
