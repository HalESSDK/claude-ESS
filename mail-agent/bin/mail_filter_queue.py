#!/usr/bin/env python3
import json, pathlib, re, datetime
from zoneinfo import ZoneInfo

base = pathlib.Path('/home/victor/mail-agent')
inbox = base/'inbox'
state_file = base/'state.json'
queue_file = base/'queue.jsonl'
log_file = base/'logs'/'filter.log'
conf_file = base/'config.filter.json'

conf = json.loads(conf_file.read_text(encoding='utf-8')) if conf_file.exists() else {}
my_email = conf.get('my_email','').lower()
block_sender = [s.lower() for s in conf.get('block_sender_contains',[])]
block_subject = [s.lower() for s in conf.get('block_subject_contains',[])]
block_body = [s.lower() for s in conf.get('block_body_contains',[])]
allow_domains = [d.lower() for d in conf.get('allow_domains',[])]
require_human_name = bool(conf.get('require_human_name', True))

state = {"seen_ids": []}
if state_file.exists():
    try:
        state = json.loads(state_file.read_text(encoding='utf-8'))
    except Exception:
        pass

now_dt = datetime.datetime.now(datetime.timezone.utc)
now = now_dt.isoformat()
TZ = ZoneInfo('Europe/Copenhagen')
now_local = now_dt.astimezone(TZ)

# Baseline mode: only process NEW mail from now on.
# First run sets startedAt and ignores older existing inbox content.
if not state.get('startedAt'):
    state['startedAt'] = now
    state.setdefault('seen_ids', [])
    state_file.write_text(json.dumps(state, indent=2), encoding='utf-8')
    print('Baseline set. Will only process new incoming inbox emails from now on.')
    raise SystemExit(0)

started_at = datetime.datetime.fromisoformat(state['startedAt'].replace('Z', '+00:00'))
seen = set(state.get('seen_ids', []))

snapshots = sorted(inbox.glob('messages-*.json'))
if not snapshots:
    print('No snapshots found')
    raise SystemExit(0)

latest = snapshots[-1]
data = json.loads(latest.read_text(encoding='utf-8'))
msgs = data.get('value', [])

queue_file.parent.mkdir(parents=True, exist_ok=True)
log_file.parent.mkdir(parents=True, exist_ok=True)
added = 0

def parse_received(dt_s: str):
    if not dt_s:
        return None
    try:
        return datetime.datetime.fromisoformat(dt_s.replace('Z', '+00:00'))
    except Exception:
        return None

def is_personal(m):
    frm = ((m.get('from') or {}).get('emailAddress') or {})
    addr = (frm.get('address') or '').lower()
    name = (frm.get('name') or '').strip()
    subj = (m.get('subject') or '').lower()
    preview = (m.get('bodyPreview') or '').lower()

    if not addr or addr == my_email:
        return False, 'self-or-empty'
    if any(x in addr for x in block_sender):
        return False, 'blocked-sender'
    if any(x in subj for x in block_subject):
        return False, 'blocked-subject'
    if any(x in preview for x in block_body):
        return False, 'blocked-body'
    if allow_domains:
        domain = addr.split('@')[-1] if '@' in addr else ''
        if domain not in allow_domains:
            return False, 'domain-not-allowed'
    if require_human_name and (not name or re.search(r'no\s*reply|security|system|support', name, re.I)):
        return False, 'non-human-name'

    rdt = parse_received(m.get('receivedDateTime'))
    if not rdt:
        return False, 'missing-receivedDateTime'
    # Only queue messages received today (from midnight DK time)
    if rdt.astimezone(TZ).date() != now_local.date():
        return False, 'not-today'

    # Baseline: allow today's messages even if they arrived before startedAt
    if rdt <= started_at:
        return True, 'ok'

    return True, 'ok'

with queue_file.open('a', encoding='utf-8') as q, log_file.open('a', encoding='utf-8') as lg:
    for m in msgs:
        mid = m.get('id')
        if not mid or mid in seen:
            continue
        ok, reason = is_personal(m)
        frm = ((m.get('from') or {}).get('emailAddress') or {})
        entry = {
            'ts': now,
            'id': mid,
            'subject': m.get('subject'),
            'from': frm,
            'receivedDateTime': m.get('receivedDateTime'),
            'bodyPreview': m.get('bodyPreview'),
            'status': 'queued' if ok else 'ignored',
            'reason': reason
        }
        lg.write(json.dumps(entry, ensure_ascii=False) + '\n')
        if ok:
            q.write(json.dumps(entry, ensure_ascii=False) + '\n')
            added += 1
        seen.add(mid)

state['seen_ids'] = list(seen)[-5000:]
state_file.write_text(json.dumps(state, indent=2), encoding='utf-8')
print(f'Processed: {len(msgs)} | queued: {added}')
