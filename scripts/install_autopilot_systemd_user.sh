#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_NAME="thesis-research-autopilot"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

mkdir -p "${SYSTEMD_USER_DIR}"

cat > "${SYSTEMD_USER_DIR}/${UNIT_NAME}.service" <<EOF
[Unit]
Description=thesis-research autopilot (paper collector + brief writer)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=${REPO_ROOT}
EnvironmentFile=${REPO_ROOT}/.env
ExecStart=/usr/bin/env python3 ${REPO_ROOT}/scripts/autopilot.py --run-hours 6 --cycle-sleep-mins 30
Nice=10
EOF

cat > "${SYSTEMD_USER_DIR}/${UNIT_NAME}.timer" <<EOF
[Unit]
Description=Run thesis-research autopilot periodically

[Timer]
OnBootSec=5m
OnUnitActiveSec=6h
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now "${UNIT_NAME}.timer"

echo "Installed and started: ${UNIT_NAME}.timer"
echo "Status: systemctl --user status ${UNIT_NAME}.timer"
