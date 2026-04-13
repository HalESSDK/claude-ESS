#!/usr/bin/env python3
import argparse, pathlib, json, datetime
from faster_whisper import WhisperModel

parser=argparse.ArgumentParser()
parser.add_argument('--input', default='latest', help='Path to media file or "latest"')
parser.add_argument('--model', default='small', help='Whisper model size (tiny/base/small/medium)')
parser.add_argument('--lang', default='auto', help='Language code, e.g. da/en or auto')
args=parser.parse_args()

media_root=pathlib.Path('/root/.openclaw/media/inbound')
if args.input=='latest':
    files=[p for p in media_root.glob('*') if p.is_file() and p.suffix.lower() in {'.mp3','.m4a','.wav','.ogg','.oga','.webm','.mp4','.mov','.aac'}]
    if not files:
        raise SystemExit('No media files found in inbound folder')
    inp=max(files, key=lambda p: p.stat().st_mtime)
else:
    inp=pathlib.Path(args.input)

model=WhisperModel(args.model, device='cpu', compute_type='int8')
lang=None if args.lang=='auto' else args.lang
segments, info = model.transcribe(str(inp), language=lang, vad_filter=True)
text=' '.join([s.text.strip() for s in segments]).strip()

out_dir=pathlib.Path('/home/victor/mail-agent/transcripts')
out_dir.mkdir(parents=True, exist_ok=True)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
out=out_dir/f'transcript-{stamp}.json'
out.write_text(json.dumps({
  'source': str(inp),
  'detected_language': info.language,
  'language_probability': info.language_probability,
  'text': text
}, ensure_ascii=False, indent=2), encoding='utf-8')

print(f'Source: {inp}')
print(f'Language: {info.language} ({info.language_probability:.2f})')
print('Text:')
print(text)
print(f'Saved: {out}')
