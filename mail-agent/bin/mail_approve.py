#!/usr/bin/env python3
import os, json, urllib.request, pathlib, datetime, sys
if len(sys.argv)<2:
    print('Usage: mail_approve.py <draft-file> [--send]')
    raise SystemExit(2)
path=pathlib.Path(sys.argv[1])
send='--send' in sys.argv
if not path.exists():
    print('Draft file not found')
    raise SystemExit(1)

data=json.loads(path.read_text(encoding='utf-8'))
if data.get('status') not in ('needs_approval','edited'):
    print('Draft not in approvable state')
    raise SystemExit(1)

if not send:
    data['status']='approved_pending_send'
    data['approvedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Approved (not sent). Re-run with --send to send.')
    raise SystemExit(0)

api=os.environ.get('MATON_API_KEY')
cid=os.environ.get('MATON_CONNECTION_ID')
if not api or not cid:
    print('Missing MATON env vars')
    raise SystemExit(1)

msg={
  'message': {
    'subject': data.get('subject',''),
    'body': {'contentType':'Text','content': data.get('draftText','')},
    'toRecipients': data.get('to',[]),
    'ccRecipients': data.get('cc',[])
  },
  'saveToSentItems': True
}
req=urllib.request.Request('https://gateway.maton.ai/outlook/v1.0/me/sendMail', data=json.dumps(msg).encode(), method='POST')
req.add_header('Authorization', f'Bearer {api}')
req.add_header('Maton-Connection', cid)
req.add_header('Content-Type','application/json')
with urllib.request.urlopen(req, timeout=30) as r:
    _=r.read()

data['status']='sent'
data['sentAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

appr=pathlib.Path('/home/victor/mail-agent/approved')
appr.mkdir(parents=True, exist_ok=True)
path.replace(appr/path.name)
print('Sent and moved to approved/')
