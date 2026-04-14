# Email Agent — ESS Denmark — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Byg en AI-agent der henter ulæste emails fra Outlook, kategoriserer dem (🔴/🟡/⚪), drafter svar via Claude API og lægger kladder direkte i Outlook Drafts.

**Architecture:** Agenten kører som et Python-script på serveren. Den henter emails via Microsoft Graph API (`graph_client.py`), filtrerer spam/notifikationer via den eksisterende `config.filter.json`, kalder Claude API for kategorisering og drafting, og skriver resultater til lokale JSON-filer + Outlook Drafts for høj/medium prioritet.

**Tech Stack:** Python 3.12, MSAL (Microsoft Graph auth), Anthropic Python SDK (Claude API), Microsoft Graph REST API

---

## Filstruktur

| Fil | Status | Ansvar |
|-----|--------|--------|
| `bin/graph_client.py` | ✅ eksisterer | Graph API auth + HTTP klient |
| `bin/mail_pull.py` | ⚠️ opdateres | Hent ulæste emails — skift fra Maton til Graph API |
| `bin/mail_get_message.py` | ⚠️ opdateres | Hent enkelt email med body — skift fra Maton til Graph API |
| `bin/mail_agent.py` | 🆕 oprettes | Hovedorkestrering: pull → filter → AI → draft → Outlook |
| `config/agent_prompt.md` | 🆕 oprettes | ESS Denmark system-prompt til Claude |
| `requirements.txt` | ⚠️ opdateres | Tilføj `anthropic` |

---

## Task 1: Opdatér requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Tilføj anthropic SDK**

Erstat indholdet af `requirements.txt`:
```
msal>=1.28.0
anthropic>=0.40.0
```

- [ ] **Step 2: Installér**

```bash
cd /home/victor/mail-agent
venv/bin/pip install anthropic
```

Forventet output: `Successfully installed anthropic-x.x.x`

- [ ] **Step 3: Commit**

```bash
git add mail-agent/requirements.txt
git commit -m "deps: add anthropic SDK for email agent"
```

---

## Task 2: Opdatér mail_pull.py til Graph API

**Files:**
- Modify: `bin/mail_pull.py`

- [ ] **Step 1: Erstat hele filen**

```python
#!/usr/bin/env python3
"""
Hent ulæste emails fra Outlook Inbox via Microsoft Graph.
Gemmer resultater i mail-agent/inbox/
"""
import json, pathlib, datetime, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from graph_client import graph_request

TOP = 20
FILTER = "isRead eq false"
SELECT = "id,subject,from,receivedDateTime,bodyPreview,isRead"

params = f"?$top={TOP}&$select={SELECT}&$orderby=receivedDateTime desc&$filter={FILTER}"
data = graph_request("GET", f"/me/mailFolders/Inbox/messages{params}")

messages = data.get("value", [])
out_dir = pathlib.Path("/home/victor/mail-agent/inbox")
out_dir.mkdir(parents=True, exist_ok=True)

stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
out_file = out_dir / f"messages-{stamp}.json"
out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

print(f"Gemt: {out_file}")
print(f"Beskeder: {len(messages)}")
for i, m in enumerate(messages, 1):
    sender = (((m.get("from") or {}).get("emailAddress") or {}).get("address")) or "ukendt"
    subj = (m.get("subject") or "(intet emne)").replace("\n", " ")
    dt = m.get("receivedDateTime", "")
    print(f"{i:02d}. {dt} | {sender} | {subj}")
```

- [ ] **Step 2: Test**

```bash
cd /home/victor/mail-agent
set -a && source .env && set +a && venv/bin/python bin/mail_pull.py
```

Forventet output: Liste af ulæste emails uden Maton-fejl.

- [ ] **Step 3: Commit**

```bash
git add mail-agent/bin/mail_pull.py
git commit -m "refactor: mail_pull.py bruger nu Graph API direkte (ingen Maton)"
```

---

## Task 3: Opdatér mail_get_message.py til Graph API

**Files:**
- Modify: `bin/mail_get_message.py`

- [ ] **Step 1: Erstat hele filen**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add mail-agent/bin/mail_get_message.py
git commit -m "refactor: mail_get_message.py bruger nu Graph API direkte (ingen Maton)"
```

---

## Task 4: Opret agent_prompt.md

**Files:**
- Create: `config/agent_prompt.md`

- [ ] **Step 1: Opret config-mappe og prompt-fil**

```bash
mkdir -p /home/victor/mail-agent/config
```

Indhold af `config/agent_prompt.md`:

```markdown
# ESS Denmark — Email Agent

## Virksomhed
ESS Denmark sælger bæredygtige byggematerialer og gulvløsninger.
Primære kunder er arkitekter og rådgivere i byggebranchen.

## Tone og stil
- Professionel og formel dansk
- Varm men saglig — vi er eksperter men aldrig arrogante
- Brug "Med venlig hilsen" som afslutning
- Undgå forkortelser og slang
- Svar på samme sprog som afsenderen

## Kategorisering

### 🔴 Høj prioritet — svar inden for 24 timer
- Kundehenvendelser om produkter, prøver eller projekter
- Tilbud der afventer svar
- Mødeforslag fra kunder eller partnere
- Spørgsmål fra arkitekter og rådgivere

### 🟡 Medium prioritet — svar inden for 48 timer
- Opfølgning på igangværende projekter
- Interne mails fra teamet
- Leverandørkorrespondance

### ⚪ Lav prioritet — ingen handling nødvendig
- Automatiske notifikationer og kvitteringer
- Nyhedsbreve
- System-mails (login, betalinger, etc.)

## Når du drafter svar

1. Læs hele tråden for kontekst
2. Adresser ALLE spørgsmål i mailen
3. Vær konkret — undgå vage svar
4. Hvis du mangler information, skriv [UDFYLD: hvad der mangler]
5. Foreslå altid et næste skridt (møde, opfølgning, leveringstid)
6. Hold svar kortfattede — max 150 ord medmindre emnet kræver mere

## Hvad du ALDRIG må gøre
- Send eller bekræft priser uden at markere det tydeligt med [BEKRÆFT PRIS]
- Forpligt dig til leveringsdatoer uden at markere [BEKRÆFT DATO]
- Draft svar til mails med lav prioritet

## Output format
Du skal ALTID svare med gyldigt JSON i dette format (ingen tekst uden for JSON-blokken):

```json
{
  "priority": "high|medium|low",
  "priority_emoji": "🔴|🟡|⚪",
  "summary": "Én linje der beskriver emailen",
  "draft": "Udkast til svar (kun hvis high eller medium priority, ellers null)",
  "action_items": ["⚡ handlepunkt 1", "⚡ handlepunkt 2"]
}
```
```

- [ ] **Step 2: Commit**

```bash
git add mail-agent/config/agent_prompt.md
git commit -m "feat: tilføj ESS Denmark agent prompt"
```

---

## Task 5: Opret mail_agent.py — hovedscriptet

**Files:**
- Create: `bin/mail_agent.py`

- [ ] **Step 1: Opret scriptet**

```python
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
DRAFTS_DIR   = pathlib.Path("/home/victor/mail-agent/drafts")
FILTER_FILE  = pathlib.Path("/home/victor/mail-agent/config.filter.json")
PROMPT_FILE  = pathlib.Path("/home/victor/mail-agent/config/agent_prompt.md")
MY_EMAIL     = "vh@essdenmark.dk"
LIMIT        = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10

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

    sender_name = (((email_data.get("from") or {}).get("emailAddress") or {}).get("name") or "Ukendt")
    sender_email = (((email_data.get("from") or {}).get("emailAddress") or {}).get("address") or "")
    subject = email_data.get("subject", "(intet emne)")
    received = email_data.get("receivedDateTime", "")

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
    sender_name = (((email_data.get("from") or {}).get("emailAddress") or {}).get("name") or "")
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
    mid = email_data.get("id", "unknown")[:12]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = DRAFTS_DIR / f"draft-{stamp}-{mid}.json"

    data = {
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "messageId": email_data.get("id"),
        "subject": email_data.get("subject"),
        "from": email_data.get("from", {}).get("emailAddress", {}),
        "priority": ai_result.get("priority"),
        "priority_emoji": ai_result.get("priority_emoji"),
        "summary": ai_result.get("summary"),
        "draftText": ai_result.get("draft"),
        "action_items": ai_result.get("action_items", []),
        "status": "needs_approval",
        "outlookDraftId": outlook_id or None,
        "outlookDraftCreatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat() if outlook_id else None,
        "to": [{"emailAddress": email_data.get("from", {}).get("emailAddress", {})}],
        "cc": [],
    }
    filename.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return filename


# --- Hovedloop ---
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
        sender = (((msg.get("from") or {}).get("emailAddress") or {}).get("address") or "ukendt")
        subject = msg.get("subject", "(intet emne)")

        if should_skip(msg):
            print(f"  ⚪ SPRING OVER: {sender} | {subject}")
            continue

        print(f"\n  Behandler: {sender} | {subject}")

        try:
            body = fetch_full_body(msg["id"])
            ai_result = call_claude(msg, body)
            priority = ai_result.get("priority", "low")
            emoji = ai_result.get("priority_emoji", "⚪")

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
            print(f"  ❌ Fejl ved behandling: {e}", file=sys.stderr)
            continue

    print(f"\nFærdig — behandlede {processed} emails")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Tilføj ANTHROPIC_API_KEY til .env**

Åbn `.env`:
```bash
nano /home/victor/mail-agent/.env
```

Tilføj linjen:
```
ANTHROPIC_API_KEY=din-anthropic-api-key-her
```

Gem med `Ctrl+O` → Enter → `Ctrl+X`.

Find din API-nøgle på [console.anthropic.com](https://console.anthropic.com) → API Keys.

- [ ] **Step 3: Test med 3 emails**

```bash
cd /home/victor/mail-agent
set -a && source .env && set +a && venv/bin/python bin/mail_agent.py --limit 3
```

Forventet output:
```
Fandt X ulæste emails
  Behandler: afsender@domain.dk | Emne
  🔴 Kortfattet beskrivelse af emailen
     ⚡ Handlepunkt
  → Draft lagt i Outlook Drafts
  → Gemt: draft-20260413-XXXXXX-XXXXXX.json
Færdig — behandlede X emails
```

- [ ] **Step 4: Tjek Outlook**

Åbn Outlook og bekræft at kladder vises i Drafts-mappen.

- [ ] **Step 5: Commit**

```bash
git add mail-agent/bin/mail_agent.py mail-agent/config/agent_prompt.md
git commit -m "feat: ESS Denmark email agent med Claude AI kategorisering og Outlook Drafts"
```

---

## Opsummering

Når alle tasks er gennemført:

| Kommando | Hvad den gør |
|----------|--------------|
| `venv/bin/python bin/mail_agent.py` | Kør agenten på ulæste emails |
| `venv/bin/python bin/mail_agent.py --limit 5` | Begræns til 5 emails |
| `venv/bin/python bin/mail_review.py` | Se alle lokale kladder |
| `venv/bin/python bin/mail_approve.py drafts/xxx.json --send` | Send en godkendt kladde |

## Fremtidigt næste skridt
- Sæt agenten op til at køre automatisk (cron job hver morgen kl. 08:00)
- Udvid til at håndtere flere medarbejderes postkasser (Application permissions)
