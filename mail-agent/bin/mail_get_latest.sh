#!/usr/bin/env bash
set -euo pipefail
[ -f /home/victor/mail-agent/.env ] && set -a && source /home/victor/mail-agent/.env && set +a
/home/victor/mail-agent/bin/mail_pull.py >/tmp/mail_pull.out
MID=$(/home/victor/mail-agent/bin/mail_latest_id.py)
/home/victor/mail-agent/bin/mail_get_message.py "$MID"
