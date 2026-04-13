#!/usr/bin/env python3
import json, pathlib, sys, datetime
if len(sys.argv)<3:
    print('Usage: mail_edit.py <draft-file> <text-file>')
    raise SystemExit(2)
draft=pathlib.Path(sys.argv[1]); textf=pathlib.Path(sys.argv[2])
if not draft.exists() or not textf.exists():
    print('Missing files'); raise SystemExit(1)
d=json.loads(draft.read_text(encoding='utf-8'))
d['draftText']=textf.read_text(encoding='utf-8').strip()+"\n"
d['status']='edited'
d['editedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
draft.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
# training log
tr=pathlib.Path('/home/victor/mail-agent/training')
tr.mkdir(parents=True, exist_ok=True)
out=tr/f"train-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
out.write_text(json.dumps({
 'subject': d.get('subject'),
 'from': d.get('from'),
 'sourcePreview': d.get('sourcePreview'),
 'agentDraftBeforeEdit': d.get('sourceSnippet',''),
 'finalDraft': d.get('draftText'),
 'language': d.get('language'),
 'ts': d.get('editedAt')
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Edited draft saved. Training sample: {out}')
