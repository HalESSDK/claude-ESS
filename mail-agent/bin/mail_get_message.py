#!/usr/bin/env python3
import os, json, urllib.request, urllib.parse, pathlib, datetime, sys
API_KEY=os.environ.get('MATON_API_KEY')
CONN_ID=os.environ.get('MATON_CONNECTION_ID')
MID = sys.argv[1] if len(sys.argv)>1 else None
if not API_KEY or not CONN_ID:
    print('ERROR: MATON_API_KEY or MATON_CONNECTION_ID missing', file=sys.stderr); sys.exit(1)
if not MID:
    print('Usage: mail_get_message.py <message_id>', file=sys.stderr); sys.exit(2)
select='id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,bodyPreview,internetMessageId,conversationId'
url='https://gateway.maton.ai/outlook/v1.0/me/messages/'+urllib.parse.quote(MID)+"?$select="+urllib.parse.quote(select,safe=',')
req=urllib.request.Request(url)
req.add_header('Authorization', f'Bearer {API_KEY}')
req.add_header('Maton-Connection', CONN_ID)
with urllib.request.urlopen(req, timeout=30) as r:
    data=json.load(r)
out_dir=pathlib.Path('/home/victor/mail-agent/inbox')
out_dir.mkdir(parents=True, exist_ok=True)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
out=out_dir/f'message-{stamp}-{MID[:12]}.json'
out.write_text(json.dumps(data, indent=2), encoding='utf-8')
print(out)
