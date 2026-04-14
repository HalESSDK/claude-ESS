#!/usr/bin/env python3
import os, json, urllib.request, urllib.parse, pathlib, datetime, re, html
import anthropic
from zoneinfo import ZoneInfo

BASE = pathlib.Path('/home/victor/mail-agent')
QUEUE = BASE / 'queue.jsonl'
DRAFTS = BASE / 'drafts'
STATE = BASE / 'draft_state.json'
LOG = BASE / 'logs' / 'draft.log'

MATON_API_KEY = os.environ.get('MATON_API_KEY')
MATON_CONNECTION_ID = os.environ.get('MATON_CONNECTION_ID')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

MY_EMAIL = 'vh@essdenmark.dk'
TZ = ZoneInfo('Europe/Copenhagen')

SIGNATURE = (
    'Med venlig hilsen / Best regards,\n'
    'Victor Hertz\n'
    'Customer Relations & Project Management\n'
    '+45 24 22 22 27\n'
    'vh@essdenmark.dk\n'
    'www.ecosilicatesystems.dk'
)

DRAFTS.mkdir(parents=True, exist_ok=True)
LOG.parent.mkdir(parents=True, exist_ok=True)

if not MATON_API_KEY or not MATON_CONNECTION_ID:
    print('ERROR: MATON env vars missing')
    raise SystemExit(1)
if not ANTHROPIC_API_KEY:
    print('ERROR: ANTHROPIC_API_KEY missing')
    raise SystemExit(1)
if not QUEUE.exists():
    print('No queue file yet')
    raise SystemExit(0)

state = {'drafted_ids': []}
if STATE.exists():
    try:
        state = json.loads(STATE.read_text(encoding='utf-8'))
    except Exception:
        pass

seen = set(state.get('drafted_ids', []))


def graph_req(path: str, *, method='GET', data=None, timeout=30):
    url = 'https://gateway.maton.ai/outlook/v1.0' + path
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', f'Bearer {MATON_API_KEY}')
    req.add_header('Maton-Connection', MATON_CONNECTION_ID)
    if data is not None:
        req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_message(mid: str):
    sel = 'id,subject,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview,body,conversationId'
    return graph_req('/me/messages/' + urllib.parse.quote(mid) + '?$select=' + urllib.parse.quote(sel, safe=','))


def create_reply_draft(mid: str):
    # Returns a message object for the created reply draft
    return graph_req('/me/messages/' + urllib.parse.quote(mid) + '/createReply', method='POST', data=b'{}')


def patch_message(mid: str, payload: dict):
    graph_req('/me/messages/' + urllib.parse.quote(mid), method='PATCH', data=json.dumps(payload).encode('utf-8'))


def strip_html(s: str) -> str:
    txt = re.sub(r'(?is)<(script|style).*?>.*?</\\1>', ' ', s or '')
    txt = re.sub(r'(?s)<[^>]+>', ' ', txt)
    txt = txt.replace('&nbsp;', ' ').replace('&amp;', '&')
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt


def pick_language(subject: str, preview: str):
    s = (subject or '') + ' ' + (preview or '')
    s_low = s.lower()
    da_hits = ['hej', 'venlig', 'hilsen', 'forlængelse', 'gulv', 'kan du', 'tak', 'mvh', 'med venlig']
    en_hits = ['hello', 'regards', 'thanks', 'could you', 'please', 'kind regards']
    da = sum(1 for w in da_hits if w in s_low)
    en = sum(1 for w in en_hits if w in s_low)
    return 'da' if da >= en else 'en'


def sender_first_name(from_name: str):
    if not from_name:
        return ''
    return re.split(r'\s+|/|,', from_name.strip())[0]


def load_training_examples(max_examples=10):
    # Uses the last10 training file if present
    tdir = BASE / 'training'
    files = sorted(tdir.glob('sent-*-training-*.json'))
    if not files:
        return []
    data = json.loads(files[-1].read_text(encoding='utf-8'))
    ex = []
    for item in data[:max_examples]:
        subj = (item.get('subject') or '').strip()
        body = (item.get('bodyText') or '').strip()
        if subj and body:
            ex.append({'subject': subj, 'body': body})
    return ex


def openai_generate_reply(*, lang: str, sender_name: str, subject: str, email_text: str, received_dt: str):
    # Keep input bounded.
    email_text = (email_text or '').strip()
    if len(email_text) > 12000:
        email_text = email_text[:12000] + "\n\n[...truncated...]"

    examples = load_training_examples(max_examples=10)
    ex_txt = ''
    for i, e in enumerate(examples, 1):
        # keep examples compact to avoid bloating prompt
        body = (e['body'][:900] + '…') if len(e['body']) > 900 else e['body']
        ex_txt += f"\n\n--- EKSEMPEL {i} (tidligere sendt stil) ---\nEmne: {e['subject']}\nBody (udsnit):\n{body}\n"

    if lang == 'da':
        system_text = (
            "Du skriver en personlig email-reply som Victor Hertz (ESS). Output er en kladde-tekst, ikke send. "
            "Skriv dansk medmindre indgående mail tydeligt er på engelsk.\n\n"
            "Krav:\n"
            "- Første 1-2 linjer: kort konklusion/status\n"
            "- Referér til mindst 2 konkrete detaljer fra mailen\n"
            "- Skriv KORT: maks 6-10 linjer + maks 3 bullets\n"
            "- Maks 1 afklarende spørgsmål (kun hvis nødvendigt)\n"
            "- Ingen uverificerede garantier, CO2-tal, leveringstider eller certificeringer\n"
            "- Slut med præcis denne signatur (1:1):\n" + SIGNATURE + "\n\n"
            "VIGTIGT: Du skal IKKE citere den originale mail i output (Outlook-reply-draft indeholder allerede tråden).\n"
            "Her er tidligere sendte eksempler på stil/struktur (brug som reference):" + ex_txt + "\n\n"
            "Returnér kun selve email-teksten (ingen forklaringer)."
        )
    else:
        system_text = (
            "Write a personalized reply email as Victor Hertz (ESS). Draft only, never send.\n"
            "Requirements: direct 1-2 line conclusion, reference 2 concrete details, 3-7 bullets, max 1 question, no unverified claims.\n"
            "End with this exact signature:\n" + SIGNATURE + "\n"
            "Do NOT quote the original email in the output (the Outlook reply draft already contains the thread).\n"
            "Return only the email text."
        )

    user_text = (
        f"Sender name: {sender_name}\n"
        f"Received: {received_dt}\n"
        f"Subject: {subject}\n\n"
        "Incoming email (plain text):\n"
        f"{email_text}"
    )

    claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=900,
        system=system_text,
        messages=[{"role": "user", "content": user_text}],
    )

    return next((b.text for b in response.content if b.type == "text"), "").strip()


def text_to_html_with_italic_signature(text: str) -> str:
    text = (text or '').replace('\r\n', '\n')
    esc = html.escape(text)
    sig_esc = html.escape(SIGNATURE)
    if sig_esc in esc:
        esc = esc.replace(sig_esc, f'<i>{sig_esc}</i>')
    return esc.replace('\n', '<br>')


def is_received_today(received_iso: str) -> bool:
    if not received_iso:
        return False
    try:
        dt = datetime.datetime.fromisoformat(received_iso.replace('Z', '+00:00'))
    except Exception:
        return False
    local = dt.astimezone(TZ)
    now_local = datetime.datetime.now(datetime.timezone.utc).astimezone(TZ)
    return local.date() == now_local.date()


added = 0
with QUEUE.open('r', encoding='utf-8') as f, LOG.open('a', encoding='utf-8') as lg:
    for line in f:
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        if e.get('status') != 'queued':
            continue
        mid = e.get('id')
        if not mid or mid in seen:
            continue

        try:
            msg = fetch_message(mid)
            received_dt = msg.get('receivedDateTime') or ''

            # Victor wants drafts only for relevant mails received today (from midnight DK time)
            if not is_received_today(received_dt):
                seen.add(mid)
                continue

            subj = msg.get('subject') or '(no subject)'
            frm = ((msg.get('from') or {}).get('emailAddress') or {})
            from_name = (frm.get('name') or '').strip()
            preview = msg.get('bodyPreview') or ''
            body = (msg.get('body') or {}).get('content') or ''
            body_txt = strip_html(body)
            lang = pick_language(subj, preview)
            first = sender_first_name(from_name)

            draft_text = openai_generate_reply(
                lang=lang,
                sender_name=first or from_name or 'there',
                subject=subj,
                email_text=body_txt,
                received_dt=received_dt
            )

            # If model returns empty/too-short, skip creating any Outlook draft
            if not draft_text or len(draft_text.strip()) < 80:
                seen.add(mid)
                lg.write(json.dumps({'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'id': mid, 'status': 'skipped', 'reason': 'empty-or-too-short'}, ensure_ascii=False) + '\n')
                continue

            # Create an actual Outlook reply draft so the original thread is included
            reply = create_reply_draft(mid)
            outlook_draft_id = reply.get('id')
            existing_body = ((reply.get('body') or {}).get('content') or '')

            response_html = text_to_html_with_italic_signature(draft_text)
            combined = response_html + '<br><br>' + existing_body

            patch_message(outlook_draft_id, {
                'body': {'contentType': 'HTML', 'content': combined}
            })

            out = DRAFTS / f"draft-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')}-{mid[:12]}.json"
            draft_obj = {
                'createdAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'messageId': mid,
                'conversationId': msg.get('conversationId'),
                'subject': subj,
                'from': frm,
                'to': msg.get('toRecipients', []),
                'cc': msg.get('ccRecipients', []),
                'language': lang,
                'status': 'needs_approval',
                'draftText': draft_text,
                'sourcePreview': preview,
                'sourceSnippet': (strip_html(body)[:600] if body else preview[:600]),
                'auto': True,
                'outlookDraftId': outlook_draft_id,
                'outlookDraftCreatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            out.write_text(json.dumps(draft_obj, ensure_ascii=False, indent=2), encoding='utf-8')

            seen.add(mid)
            added += 1
            lg.write(json.dumps({'ts': draft_obj['createdAt'], 'id': mid, 'status': 'drafted', 'outlookDraftId': outlook_draft_id, 'file': str(out)}, ensure_ascii=False) + '\n')

        except Exception as ex:
            lg.write(json.dumps({'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'id': mid, 'status': 'error', 'error': str(ex)}, ensure_ascii=False) + '\n')

state['drafted_ids'] = list(seen)[-5000:]
STATE.write_text(json.dumps(state, indent=2), encoding='utf-8')
print(f'Drafts created: {added}')
