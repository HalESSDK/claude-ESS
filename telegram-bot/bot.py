#!/usr/bin/env python3
"""
Simpel Telegram-bot der videresender beskeder til Claude CLI og svarer tilbage.
Kræver ingen API-nøgle — bruger 'claude -p' via din Claude Code-konto.
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

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def api(method, timeout=15, **params):
    r = requests.post(f"{BASE_URL}/{method}", json=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def send(chat_id, text):
    # Telegram max 4096 tegn pr. besked
    for i in range(0, len(text), 4096):
        api("sendMessage", chat_id=chat_id, text=text[i:i+4096])


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


def main():
    log.info("Bot starter. Tilladte brugere: %s", ALLOWED_USERS)
    offset = None

    while True:
        try:
            updates = api("getUpdates", timeout=POLL_TIMEOUT + 5, offset=offset, timeout=POLL_TIMEOUT).get("result", [])
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
                        ],
                        capture_output=True, text=True, timeout=120,
                    )
                    text = tr.stdout.strip() or "(kunne ikke transskribere)"
                except Exception as e:
                    text = f"(transskriberingsfejl: {e})"
                finally:
                    try:
                        os.remove(local_path)
                    except Exception:
                        pass

                log.info("Transskription: %s", text)
                prompt = text

            # Tekstbesked
            elif "text" in msg:
                prompt = msg["text"]
            else:
                continue

            log.info("Spørger Claude: %s", prompt[:80])
            try:
                reply = ask_claude(prompt)
            except subprocess.TimeoutExpired:
                reply = "Claude tog for lang tid at svare."
            except Exception as e:
                reply = f"Fejl: {e}"

            send(chat_id, reply)


if __name__ == "__main__":
    main()
