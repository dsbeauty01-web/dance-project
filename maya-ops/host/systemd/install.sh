#!/usr/bin/env bash
# run on the pod as root:  bash systemd/install.sh
set -e
cp systemd/maya-*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable maya-render maya-stream maya-router maya-host maya-push
systemctl start maya-render && sleep 90 && systemctl start maya-stream maya-router maya-host maya-push
( crontab -l 2>/dev/null | grep -v maya-health ; echo "* * * * * /workspace/maya-ops/host/systemd/maya-health.sh" ) | crontab -
echo "installed. status:"; systemctl --no-pager status maya-render maya-stream maya-router maya-host maya-push | grep -E "maya-|Active"
