# Claude ESS — AI-opsætning for Eco Silicate Systems

Dette repo indeholder Claude Code-konfiguration og AI-værktøjer brugt i ESS Denmark.

## Indhold

### mail-agent/
Automatiseret mail-håndtering via Microsoft 365 / Outlook.
- `bin/` — scripts til at hente, bearbejde og sende emails
- `config.filter.json` — filtreringsregler for indkommende mails
- `.env.example` — skabelon for miljøvariabler (kopier til `.env` og udfyld)
- `MODEL_ROUTING.md` — dokumentation for AI-model routing

### skills/
Claude Code skills/værktøjer.
- `github/` — GitHub-integration
- `outlook-api/` — Outlook API-integration

### .claude/settings.json
Claude Code konfiguration og tilladelser.

## Kom i gang

```bash
# Kopiér og udfyld miljøvariabler
cp mail-agent/.env.example mail-agent/.env

# Installér Python-afhængigheder
cd mail-agent && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Kontakt
Victor Hertz — vh@essdenmark.dk
