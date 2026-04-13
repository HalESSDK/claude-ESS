#!/usr/bin/env python3
import os, json, urllib.request, urllib.parse, datetime, pathlib, sys

API_KEY = os.environ.get("MATON_API_KEY")
CONN_ID = os.environ.get("MATON_CONNECTION_ID")
TOP = int(os.environ.get("MAIL_PULL_TOP", "10"))
ONLY_UNREAD = os.environ.get("MAIL_PULL_UNREAD", "1") != "0"

if not API_KEY:
    print("ERROR: MATON_API_KEY is not set", file=sys.stderr)
    sys.exit(1)
if not CONN_ID:
    print("ERROR: MATON_CONNECTION_ID is not set", file=sys.stderr)
    sys.exit(1)

select = "id,subject,from,receivedDateTime,bodyPreview,isRead"
params = {
    "$top": str(TOP),
    "$select": select,
    "$orderby": "receivedDateTime desc",
}
if ONLY_UNREAD:
    params["$filter"] = "isRead eq false"

# IMPORTANT: only read Inbox (never JunkEmail)
url = "https://gateway.maton.ai/outlook/v1.0/me/mailFolders/Inbox/messages?" + urllib.parse.urlencode(params)
req = urllib.request.Request(url)
req.add_header("Authorization", f"Bearer {API_KEY}")
req.add_header("Maton-Connection", CONN_ID)

with urllib.request.urlopen(req, timeout=30) as r:
    data = json.load(r)

messages = data.get("value", [])
out_dir = pathlib.Path("/home/victor/mail-agent/inbox")
out_dir.mkdir(parents=True, exist_ok=True)

stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
out_file = out_dir / f"messages-{stamp}.json"
out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

print(f"Saved: {out_file}")
print(f"Messages: {len(messages)}")
for i, m in enumerate(messages, 1):
    sender = (((m.get("from") or {}).get("emailAddress") or {}).get("address")) or "unknown"
    subj = (m.get("subject") or "(no subject)").replace("\n", " ")
    dt = m.get("receivedDateTime", "")
    unread = "UNREAD" if not m.get("isRead", False) else "READ"
    print(f"{i:02d}. [{unread}] {dt} | {sender} | {subj}")
