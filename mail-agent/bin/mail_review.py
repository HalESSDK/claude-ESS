#!/usr/bin/env python3
import json, pathlib, sys
D=pathlib.Path('/home/victor/mail-agent/drafts')
files=sorted(D.glob('draft-*.json'), reverse=True)
if not files:
    print('No drafts')
    raise SystemExit(0)
for i,f in enumerate(files[:20],1):
    d=json.loads(f.read_text(encoding='utf-8'))
    subj=d.get('subject','')
    frm=(d.get('from') or {}).get('address','')
    status=d.get('status','')
    print(f"{i:02d}. {f.name} | {status} | {frm} | {subj}")
