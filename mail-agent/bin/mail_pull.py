#!/usr/bin/env python3
"""
Hent ulæste emails fra Outlook Inbox via Microsoft Graph.
Gemmer resultater i mail-agent/inbox/
"""
import json, pathlib, datetime, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from graph_client import graph_request

TOP = 20
SELECT = "id,subject,from,receivedDateTime,bodyPreview,isRead"
params = f"?$top={TOP}&$select={SELECT}&$orderby=receivedDateTime%20desc&$filter=isRead%20eq%20false"
data = graph_request("GET", f"/me/mailFolders/Inbox/messages{params}")

messages = data.get("value", [])
out_dir = pathlib.Path("/home/victor/mail-agent/inbox")
out_dir.mkdir(parents=True, exist_ok=True)

stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
out_file = out_dir / f"messages-{stamp}.json"
out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

print(f"Gemt: {out_file}")
print(f"Beskeder: {len(messages)}")
for i, m in enumerate(messages, 1):
    sender = (((m.get("from") or {}).get("emailAddress") or {}).get("address")) or "ukendt"
    subj = (m.get("subject") or "(intet emne)").replace("\n", " ")
    dt = m.get("receivedDateTime", "")
    print(f"{i:02d}. {dt} | {sender} | {subj}")
