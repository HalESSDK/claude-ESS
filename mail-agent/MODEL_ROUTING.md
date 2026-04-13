# Model routing (Victor setup)

## Goal
Use cheaper model for normal/simple tasks, switch to Codex for complex tasks.

## Rules
- **Default model:** Sonnet
- **Escalate to Codex when task is complex**, e.g.:
  - architecture/design decisions
  - debugging/root-cause
  - code generation or refactors
  - security-sensitive workflows
  - multi-step automation with tool orchestration

## Practical usage
- Quick check via script:
  ```bash
  /home/victor/mail-agent/bin/choose_model.py "<task text>"
  ```
- Returns JSON with recommended model.

## OpenClaw aliases
- Codex: `openai-codex/gpt-5.3-codex`
- Sonnet: `anthropic/claude-sonnet-4-5`
- Opus: `anthropic/claude-opus-4-6`

## Safety gate
Even if model is "cheap", do not auto-send external messages without approval.
