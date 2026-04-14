#!/usr/bin/env python3
"""
Transskriberer en lydfil til tekst ved hjælp af faster-whisper (lokalt, gratis).
Brug: python3 transcribe.py <lydfil>
"""
import sys
import os

def transcribe(audio_path: str, language: str = "da", model_size: str = "small") -> str:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, language=language, beam_size=5)

    text = " ".join(segment.text.strip() for segment in segments)
    return text.strip()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Brug: transcribe.py <lydfil>", file=sys.stderr)
        sys.exit(1)

    audio_path = sys.argv[1]
    if not os.path.exists(audio_path):
        print(f"Fil ikke fundet: {audio_path}", file=sys.stderr)
        sys.exit(1)

    language = sys.argv[2] if len(sys.argv) > 2 else "da"

    result = transcribe(audio_path, language=language)
    print(result)
