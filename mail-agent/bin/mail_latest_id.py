#!/usr/bin/env python3
import json, pathlib, sys
files=sorted(pathlib.Path('/home/victor/mail-agent/inbox').glob('messages-*.json'))
if not files:
    print('ERROR: no inbox snapshots found', file=sys.stderr); sys.exit(1)
latest=files[-1]
data=json.loads(latest.read_text(encoding='utf-8'))
msgs=data.get('value',[])
if not msgs:
    print('ERROR: no messages in latest snapshot', file=sys.stderr); sys.exit(2)
print(msgs[0].get('id',''))
