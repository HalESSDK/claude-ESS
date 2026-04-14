#!/usr/bin/env python3
"""
Telegram-bot der videresender beskeder til Claude CLI.
Husker samtalehistorik pr. chat. Brug /reset for at starte forfra.
"""
import os
import subprocess
import time
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USERS = set(
    int(uid) for uid in os.environ.get("ALLOWED_USER_IDS", "7204930765").split(",")
)
CLAUDE_CMD = os.environ.get("CLAUDE_CMD", "claude")
POLL_TIMEOUT = 30
MAX_HISTORY = 10  # antal tidligere udvekslinger der huskes

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Samtalehistorik pr. chat: { chat_id: [{"role": "user"|"assistant", "content": str}, ...] }
history: dict[int, list[dict]] = {}


def api(method, http_timeout=15, **params):
    r = requests.post(f"{BASE_URL}/{method}", json=params, timeout=http_timeout)
    r.raise_for_status()
    return r.json()


def send(chat_id, text):
    for i in range(0, len(text), 4096):
        api("sendMessage", chat_id=chat_id, text=text[i:i + 4096])


def build_prompt(chat_id: int, user_message: str) -> str:
    """Byg prompt med samtalehistorik."""
    msgs = history.get(chat_id, [])
    if not msgs:
        return user_message

    lines = []
    for m in msgs[-(MAX_HISTORY * 2):]:
        prefix = "Bruger" if m["role"] == "user" else "Claude"
        lines.append(f"{prefix}: {m['content']}")
    lines.append(f"Bruger: {user_message}")

    return (
        "Du er en hjælpsom assistent. Fortsæt nedenstående samtale naturligt.\n\n"
        + "\n".join(lines)
        + "\n\nClaude:"
    )


def update_history(chat_id: int, user_msg: str, assistant_msg: str):
    if chat_id not in history:
        history[chat_id] = []
    history[chat_id].append({"role": "user", "content": user_msg})
    history[chat_id].append({"role": "assistant", "content": assistant_msg})
    # Behold kun de seneste MAX_HISTORY udvekslinger
    history[chat_id] = history[chat_id][-(MAX_HISTORY * 2):]


def ask_claude(prompt: str) -> str:
    result = subprocess.run(
        [CLAUDE_CMD, "-p", "--dangerously-skip-permissions", prompt],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=os.path.expanduser("~"),
    )
    output = result.stdout.strip()
    if not output and result.stderr:
        output = result.stderr.strip()
    return output or "(ingen svar)"


def transcribe_voice(update_id: int) -> str | None:
    """Returnerer transskriberet tekst eller None ved fejl."""
    return None  # sættes under behandling


def main():
    log.info("Bot starter. Tilladte brugere: %s", ALLOWED_USERS)
    offset = None

    while True:
        try:
            updates = api(
                "getUpdates",
                http_timeout=POLL_TIMEOUT + 5,
                offset=offset,
                timeout=POLL_TIMEOUT,
            ).get("result", [])
        except Exception as e:
            log.warning("getUpdates fejl: %s", e)
            time.sleep(5)
            continue

        for upd in updates:
            offset = upd["update_id"] + 1
            msg = upd.get("message") or upd.get("channel_post")
            if not msg:
                continue

            chat_id = msg["chat"]["id"]
            user_id = msg.get("from", {}).get("id")

            if user_id not in ALLOWED_USERS:
                log.info("Ignorerer bruger %s", user_id)
                continue

            # /reset — ryd samtalehistorik
            if msg.get("text", "").strip().lower() == "/reset":
                history.pop(chat_id, None)
                send(chat_id, "Samtalehistorik ryddet. Starter forfra!")
                continue

            # Talebesked
            if "voice" in msg:
                file_id = msg["voice"]["file_id"]
                info = api("getFile", file_id=file_id)
                file_path = info["result"]["file_path"]
                audio_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                local_path = f"/tmp/tg_voice_{upd['update_id']}.ogg"

                r = requests.get(audio_url, timeout=30)
                with open(local_path, "wb") as f:
                    f.write(r.content)

                log.info("Transskriberer lydfil: %s", local_path)
                try:
                    tr = subprocess.run(
                        [
                            os.path.expanduser("~/whisper-venv/bin/python"),
                            os.path.expanduser("~/bin/transcribe.py"),
                            local_path,
                            "da",
                        ],
                        capture_output=True, text=True, timeout=120,
                    )
                    user_text = tr.stdout.strip() or "(kunne ikke transskribere)"
                except Exception as e:
                    user_text = f"(transskriberingsfejl: {e})"
                finally:
                    try:
                        os.remove(local_path)
                    except Exception:
                        pass
                log.info("Transskription: %s", user_text)

            # Tekstbesked
            elif "text" in msg:
                user_text = msg["text"]
            else:
                continue

            log.info("Spørger Claude: %s", user_text[:80])
            prompt = build_prompt(chat_id, user_text)

            try:
                reply = ask_claude(prompt)
            except subprocess.TimeoutExpired:
                reply = "Claude tog for lang tid at svare."
            except Exception as e:
                reply = f"Fejl: {e}"

            update_history(chat_id, user_text, reply)
            send(chat_id, reply)


if __name__ == "__main__":
    main()
