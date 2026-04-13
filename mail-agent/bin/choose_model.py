#!/usr/bin/env python3
import sys, re, json
text = ' '.join(sys.argv[1:]).lower()

complex_markers = [
  'arkitektur','architecture','kompleks','complex','fejlsøg','debug','integration',
  'api','automation','script','kode','code','security','sikkerhed','migrering',
  'database','model routing','agent struktur','incident','root cause','design'
]

simple_markers = [
  'kort svar','quick reply','opsummer','summary','oversæt','translate',
  'rewrite','omskriv','mail draft','draft','proofread','stavning'
]

score = 0
for w in complex_markers:
    if w in text: score += 2
for w in simple_markers:
    if w in text: score -= 1

if len(text) > 500: score += 1

if score >= 2:
    out = {"complexity":"high","model":"Codex","reason":"complex task markers"}
elif score <= -1:
    out = {"complexity":"low","model":"Sonnet","reason":"simple drafting/transform task"}
else:
    out = {"complexity":"medium","model":"Sonnet","reason":"default efficient path"}

print(json.dumps(out, ensure_ascii=False))
