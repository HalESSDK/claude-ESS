#!/usr/bin/env bash
cat <<'EOF'
Mail draft flow
1) List drafts:
   /home/victor/mail-agent/bin/mail_review.py
2) Open a draft:
   cat /home/victor/mail-agent/drafts/<file>.json
3) Approve without send:
   source /home/victor/mail-agent/.env && /home/victor/mail-agent/bin/mail_approve.py /home/victor/mail-agent/drafts/<file>.json
4) Send approved draft:
   source /home/victor/mail-agent/.env && /home/victor/mail-agent/bin/mail_approve.py /home/victor/mail-agent/drafts/<file>.json --send
5) Edit draft text first:
   nano /home/victor/mail-agent/tmp-reply.txt
   /home/victor/mail-agent/bin/mail_edit.py /home/victor/mail-agent/drafts/<file>.json /home/victor/mail-agent/tmp-reply.txt
EOF
