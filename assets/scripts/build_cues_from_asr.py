#!/usr/bin/env python3
"""Split ASR segments into phrase-unit cue shells (JA only; EN filled later).

Differs from build_cues.py: this splits long JA on punctuation into empty-EN
shells (cues_ja.json). build_cues.py merges short same-speaker segments.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

MAX_DUR = 5.8
TARGET = 4.0

def split_ja(text):
    text = (text or '').strip()
    if not text:
        return []
    parts = re.split(r'(?<=[。！？!?])', text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) > 40:
            sub = re.split(r'(?<=[、,])', p)
            buf = ''
            for s in sub:
                if len(buf) + len(s) > 28 and buf:
                    out.append(buf.strip())
                    buf = s
                else:
                    buf += s
            if buf.strip():
                out.append(buf.strip())
        else:
            out.append(p)
    return out or [text]

def allocate_times(seg, n_parts):
    words = seg.get('words') or []
    start, end = float(seg['start']), float(seg['end'])
    if n_parts <= 1:
        return [(start, end)]
    if words and len(words) >= n_parts:
        per = max(1, len(words) // n_parts)
        spans = []
        for i in range(n_parts):
            a = i * per
            b = (i + 1) * per if i < n_parts - 1 else len(words)
            ws = words[a:b]
            if not ws:
                continue
            spans.append((float(ws[0]['start']), float(ws[-1]['end'])))
        if len(spans) == n_parts:
            return spans
    dur = end - start
    step = dur / n_parts
    return [(start + i * step, start + (i + 1) * step) for i in range(n_parts)]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('segment_dir', type=Path, help='Directory with asr.json and meta.json')
    args = ap.parse_args()
    d = args.segment_dir
    asr = json.loads((d / 'asr.json').read_text(encoding='utf-8'))
    cues = []
    for seg in asr['segments']:
        parts = split_ja(seg.get('text_ja', ''))
        dur = float(seg['end']) - float(seg['start'])
        if dur <= MAX_DUR and len(seg.get('text_ja', '')) <= 35:
            parts = [seg['text_ja']]
        spans = allocate_times(seg, len(parts))
        for (a, b), ja in zip(spans, parts):
            if b - a > MAX_DUR:
                b = a + MAX_DUR
            if b <= a:
                continue
            cues.append({
                'start': round(a, 3),
                'end': round(b, 3),
                'text_ja': ja,
                'text': '',
                'speaker': seg.get('speaker', 'SPEAKER_00'),
                'name': '',
            })
    cues.sort(key=lambda c: c['start'])
    meta = json.loads((d / 'meta.json').read_text(encoding='utf-8'))
    out = {'offset_sec': meta['offset_sec'], 'dur': meta['dur'], 'cues': cues}
    (d / 'cues_ja.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(d.name, 'ja_cues', len(cues), 'from_asr', len(asr['segments']))

if __name__ == '__main__':
    main()
