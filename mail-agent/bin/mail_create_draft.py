#!/usr/bin/env python3
"""
Create a draft email directly in Outlook Drafts folder via Microsoft Graph.

Usage:
  python bin/mail_create_draft.py <draft-json-file>

The draft JSON file must contain:
  subject, draftText, to (list of {emailAddress:{address:...}})
  Optionally: cc
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from graph_client import graph_request

if len(sys.argv) < 2:
    print("Usage: mail_create_draft.py <draft-json-file>")
    sys.exit(2)

path = pathlib.Path(sys.argv[1])
if not path.exists():
    print(f"File not found: {path}")
    sys.exit(1)

data = json.loads(path.read_text(encoding="utf-8"))

message = {
    "subject": data.get("subject", ""),
    "body": {
        "contentType": "Text",
        "content": data.get("draftText", ""),
    },
    "toRecipients": data.get("to", []),
}
if data.get("cc"):
    message["ccRecipients"] = data["cc"]

result = graph_request("POST", "/me/messages", message)

outlook_id = result.get("id", "")
print(f"Draft created in Outlook: {result.get('subject','')}")
print(f"Outlook message ID: {outlook_id}")

# Save the Outlook message ID back to the local draft file
data["outlookDraftId"] = outlook_id
data["status"] = "in_outlook_drafts"
path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
