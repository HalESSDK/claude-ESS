#!/usr/bin/env bash
set -euo pipefail
[ -f /home/victor/mail-agent/.env ] && set -a && source /home/victor/mail-agent/.env && set +a
/home/victor/mail-agent/bin/mail_pull.py >/dev/null
/home/victor/mail-agent/bin/mail_filter_queue.py
/home/victor/mail-agent/bin/mail_make_drafts.py
/home/victor/mail-agent/bin/mail_push_drafts_to_outlook.py
