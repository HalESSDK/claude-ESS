#!/usr/bin/env python3
"""
ESS Denmark Email Agent
Henter ulæste emails, kategoriserer og drafter svar via Claude API,
og lægger kladder direkte i Outlook Drafts.

Usage: venv/bin/python bin/mail_agent.py [--limit N]
"""
import anthropic, json, os, pathlib, datetime, sys, urllib.parse, re
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from graph_client import graph_request

# --- Konfiguration ---
DRAFTS_DIR  = pathlib.Path("/home/victor/mail-agent/drafts")
FILTER_FILE = pathlib.Path("/home/victor/mail-agent/config.filter.json")
PROMPT_FILE = pathlib.Path("/home/victor/mail-agent/config/agent_prompt.md")
MY_EMAIL    = "vh@essdenmark.dk"
LIMIT       = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10

DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

# --- Indlæs filter og prompt ---
filters = json.loads(FILTER_FILE.read_text(encoding="utf-8"))
system_prompt = PROMPT_FILE.read_text(encoding="utf-8")


def should_skip(msg: dict) -> bool:
    """Returnerer True hvis emailen skal filtreres fra."""
    sender = (((msg.get("from") or {}).get("emailAddress") or {}).get("address") or "").lower()
    subject = (msg.get("subject") or "").lower()
    preview = (msg.get("bodyPreview") or "").lower()

    for pattern in filters.get("block_sender_contains", []):
        if pattern.lower() in sender:
            return True
    for pattern in filters.get("block_subject_contains", []):
        if pattern.lower() in subject:
            return True
    for pattern in filters.get("block_body_contains", []):
        if pattern.lower() in preview:
            return True

    # Spring over egne sendte mails
    if sender == MY_EMAIL.lower():
        return True

    return False


def fetch_full_body(message_id: str) -> str:
    """Henter fuld email-body som plain text."""
    encoded = urllib.parse.quote(message_id, safe="")
    data = graph_request("GET", f"/me/messages/{encoded}?$select=body,bodyPreview")
    body = data.get("body", {})
    content = body.get("content", data.get("bodyPreview", ""))
    # Fjern HTML-tags hvis contentType er HTML
    if body.get("contentType", "").lower() == "html":
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"\s+", " ", content).strip()
    return content[:4000]  # Maks 4000 tegn til Claude


def call_claude(email_data: dict, body: str) -> dict:
    """Sender email til Claude og returnerer struktureret JSON-svar."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    sender_name  = (((email_data.get("from") or {}).get("emailAddress") or {}).get("name") or "Ukendt")
    sender_email = (((email_data.get("from") or {}).get("emailAddress") or {}).get("address") or "")
    subject      = email_data.get("subject", "(intet emne)")
    received     = email_data.get("receivedDateTime", "")

    user_message = f"""Fra: {sender_name} <{sender_email}>
Emne: {subject}
Modtaget: {received}

--- Email indhold ---
{body}
"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    # Udtræk JSON fra svaret
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Ingen JSON i Claude-svar: {raw[:200]}")
    return json.loads(match.group())


def push_to_outlook(email_data: dict, draft_text: str) -> str:
    """Opretter kladde i Outlook Drafts og returnerer Outlook message ID."""
    sender_email = (((email_data.get("from") or {}).get("emailAddress") or {}).get("address") or "")
    sender_name  = (((email_data.get("from") or {}).get("emailAddress") or {}).get("name") or "")
    subject = email_data.get("subject", "")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    message = {
        "subject": subject,
        "body": {"contentType": "Text", "content": draft_text},
        "toRecipients": [{"emailAddress": {"address": sender_email, "name": sender_name}}],
    }
    result = graph_request("POST", "/me/messages", message)
    return result.get("id", "")


def save_draft(email_data: dict, ai_result: dict, outlook_id: str) -> pathlib.Path:
    """Gemmer draft som lokal JSON-fil."""
    mid   = email_data.get("id", "unknown")[:12]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = DRAFTS_DIR / f"draft-{stamp}-{mid}.json"

    data = {
        "createdAt":             datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "messageId":             email_data.get("id"),
        "subject":               email_data.get("subject"),
        "from":                  email_data.get("from", {}).get("emailAddress", {}),
        "priority":              ai_result.get("priority"),
        "priority_emoji":        ai_result.get("priority_emoji"),
        "summary":               ai_result.get("summary"),
        "draftText":             ai_result.get("draft"),
        "action_items":          ai_result.get("action_items", []),
        "status":                "needs_approval",
        "outlookDraftId":        outlook_id or None,
        "outlookDraftCreatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat() if outlook_id else None,
        "to":                    [{"emailAddress": email_data.get("from", {}).get("emailAddress", {})}],
        "cc":                    [],
    }
    filename.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return filename


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY er ikke sat", file=sys.stderr)
        sys.exit(1)

    # Hent ulæste emails
    select = "id,subject,from,receivedDateTime,bodyPreview,isRead"
    params = f"?$top={LIMIT}&$select={select}&$orderby=receivedDateTime desc&$filter=isRead eq false"
    data = graph_request("GET", f"/me/mailFolders/Inbox/messages{params}")
    messages = data.get("value", [])

    print(f"Fandt {len(messages)} ulæste emails")

    processed = 0
    for msg in messages:
        sender  = (((msg.get("from") or {}).get("emailAddress") or {}).get("address") or "ukendt")
        subject = msg.get("subject", "(intet emne)")

        if should_skip(msg):
            print(f"  ⚪ SPRING OVER: {sender} | {subject}")
            continue

        print(f"\n  Behandler: {sender} | {subject}")

        try:
            body      = fetch_full_body(msg["id"])
            ai_result = call_claude(msg, body)
            priority  = ai_result.get("priority", "low")
            emoji     = ai_result.get("priority_emoji", "⚪")

            outlook_id = ""
            if priority in ("high", "medium") and ai_result.get("draft"):
                outlook_id = push_to_outlook(msg, ai_result["draft"])
                print(f"  → Draft lagt i Outlook Drafts")

            draft_path = save_draft(msg, ai_result, outlook_id)

            print(f"  {emoji} {ai_result.get('summary', '')}")
            for item in ai_result.get("action_items", []):
                print(f"     {item}")
            print(f"  → Gemt: {draft_path.name}")

            processed += 1

        except Exception as e:
            print(f"  FEJL: {e}", file=sys.stderr)
            continue

    print(f"\nFærdig — behandlede {processed} emails")


if __name__ == "__main__":
    main()
