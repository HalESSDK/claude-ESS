#!/usr/bin/env python3
"""
Approve and optionally send a draft via Microsoft Graph.

Usage:
  python bin/mail_approve.py <draft-file>          # approve only
  python bin/mail_approve.py <draft-file> --send   # approve + send
"""
import json, pathlib, datetime, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from graph_client import graph_request

if len(sys.argv) < 2:
    print("Usage: mail_approve.py <draft-file> [--send]")
    sys.exit(2)

path = pathlib.Path(sys.argv[1])
send = "--send" in sys.argv

if not path.exists():
    print("Draft file not found")
    sys.exit(1)

data = json.loads(path.read_text(encoding="utf-8"))
if data.get("status") not in ("needs_approval", "edited", "in_outlook_drafts"):
    print("Draft not in approvable state")
    sys.exit(1)

if not send:
    data["status"] = "approved_pending_send"
    data["approvedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Approved (not sent). Re-run with --send to send.")
    sys.exit(0)

outlook_id = data.get("outlookDraftId")

if outlook_id:
    # Send the existing Outlook draft
    graph_request("POST", f"/me/messages/{outlook_id}/send")
else:
    # Draft not yet in Outlook — send directly
    message = {
        "message": {
            "subject": data.get("subject", ""),
            "body": {
                "contentType": "Text",
                "content": data.get("draftText", ""),
            },
            "toRecipients": data.get("to", []),
        },
        "saveToSentItems": True,
    }
    if data.get("cc"):
        message["message"]["ccRecipients"] = data["cc"]
    graph_request("POST", "/me/sendMail", message)

data["status"] = "sent"
data["sentAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

approved_dir = pathlib.Path("/home/victor/mail-agent/approved")
approved_dir.mkdir(parents=True, exist_ok=True)
path.replace(approved_dir / path.name)
print("Sent and moved to approved/")
