#!/usr/bin/env python3
"""
Hent en enkelt email med fuld body via Microsoft Graph.
Usage: python bin/mail_get_message.py <message_id>
"""
import json, pathlib, datetime, sys, urllib.parse
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from graph_client import graph_request

if len(sys.argv) < 2:
    print("Usage: mail_get_message.py <message_id>", file=sys.stderr)
    sys.exit(2)

mid = sys.argv[1]
select = "id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,bodyPreview,conversationId"
encoded_id = urllib.parse.quote(mid, safe="")
data = graph_request("GET", f"/me/messages/{encoded_id}?$select={urllib.parse.quote(select, safe=',')}")

out_dir = pathlib.Path("/home/victor/mail-agent/inbox")
out_dir.mkdir(parents=True, exist_ok=True)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
out = out_dir / f"message-{stamp}-{mid[:12]}.json"
out.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(out)
