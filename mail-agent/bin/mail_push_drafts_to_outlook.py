#!/usr/bin/env python3
import os, json, urllib.request, pathlib, datetime, html

api = os.environ.get('MATON_API_KEY')
cid = os.environ.get('MATON_CONNECTION_ID')
if not api or not cid:
    raise SystemExit('Missing MATON env vars')

SIGNATURE = (
    'Med venlig hilsen / Best regards,\n'
    'Victor Hertz\n'
    'Customer Relations & Project Management\n'
    '+45 24 22 22 27\n'
    'vh@essdenmark.dk\n'
    'www.ecosilicatesystems.dk'
)


def text_to_html_with_italic_signature(text: str) -> str:
    """Convert plain text to HTML and italicize the approved signature block."""
    text = (text or '').replace('\r\n', '\n')

    # Escape HTML, then insert <br>
    esc = html.escape(text)

    # Find signature block and wrap in <i>...</i>
    sig_esc = html.escape(SIGNATURE)
    if sig_esc in esc:
        esc = esc.replace(sig_esc, f'<i>{sig_esc}</i>')

    return esc.replace('\n', '<br>')



draft_dir = pathlib.Path('/home/victor/mail-agent/drafts')
files = sorted(draft_dir.glob('draft-*.json'))
count = 0
for f in files:
    d = json.loads(f.read_text(encoding='utf-8'))
    if d.get('status') != 'needs_approval':
        continue
    if d.get('outlookDraftId'):
        continue

    body_html = text_to_html_with_italic_signature(d.get('draftText', ''))

    body = {
        'subject': d.get('subject', ''),
        'body': {'contentType': 'HTML', 'content': body_html},
        'toRecipients': d.get('to', []),
        'ccRecipients': d.get('cc', [])
    }
    req = urllib.request.Request(
        'https://gateway.maton.ai/outlook/v1.0/me/messages',
        data=json.dumps(body).encode(),
        method='POST'
    )
    req.add_header('Authorization', f'Bearer {api}')
    req.add_header('Maton-Connection', cid)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=30) as r:
        created = json.load(r)

    d['outlookDraftId'] = created.get('id')
    d['outlookDraftCreatedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    d['status'] = 'needs_approval'  # unchanged
    f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    count += 1
    print(f'{f.name} -> {d["outlookDraftId"]}')

print(f'Pushed drafts: {count}')
