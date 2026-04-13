#!/usr/bin/env bash
set -euo pipefail
[ -f /home/victor/.profile ] && source /home/victor/.profile || true
[ -f /home/victor/.bashrc ] && source /home/victor/.bashrc || true
[ -f /home/victor/mail-agent/.env ] && set -a && source /home/victor/mail-agent/.env && set +a || true
exec /home/victor/mail-agent/bin/mail_pull.py "$@"
