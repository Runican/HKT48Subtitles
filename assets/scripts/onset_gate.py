#!/usr/bin/env python3
"""Pass G timing gate (from the 250416 review: 10 of 11 user retimes had one of these two signatures).

Uses faster-whisper word timestamps (asr.json), not energy (energy was useless under crowd/BGM).
  LEAD  - the cue's first word is orphaned: next word in the same ASR segment starts >= 1.5 s later.
          Whisper pinned the line start to a breath/cheer. Fix: start = next word - 0.5 s.
  STUB  - a whole cue that is one long word with a ~0.36-0.44 s stub duration
          (e.g. ありがとうございます in 0.36 s). Real timing unknown: ear-check / VAD-off re-ASR.
Usage: onset_gate.py ASS --asr seg/asr.json:OFFSET [--asr ...] [--fix OUT.ass] [--json report.json]
Exit 1 on any LEAD when --fix is not given (hard gate); STUB is an ear-check list only
(~20% precision on 250416: 5 of 25 were real).
"""
import argparse, json, re, sys

def ts(t):
    h, m, s = t.split(':'); return int(h)*3600 + int(m)*60 + float(s)
def fmt(x):
    cs = int(round(x*100)); return f"{cs//360000}:{cs%360000//6000:02d}:{cs%6000//100:02d}.{cs%100:02d}"
KANA = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('ass')
    ap.add_argument('--asr', action='append', default=[], help='path:offset_seconds')
    ap.add_argument('--gap', type=float, default=1.5); ap.add_argument('--pre', type=float, default=0.5)
    ap.add_argument('--fix'); ap.add_argument('--json')
    a = ap.parse_args()
    words = []  # (abs_start, abs_end, word, next_word_start_in_segment or None)
    for spec in a.asr:
        p, off = spec.rsplit(':', 1); off = float(off)
        for s in json.load(open(p))['segments']:
            W = s.get('words') or []
            for i, w in enumerate(W):
                nxt = W[i+1]['start'] + off if i+1 < len(W) else None
                words.append((w['start']+off, w['end']+off, w['word'], nxt, len(W)))
    L = open(a.ass, encoding='utf-8-sig').read().split('\n')
    flags = []
    for i, l in enumerate(L):
        if not l.startswith('Dialogue:'): continue
        p = l.split(',', 9); s, e = ts(p[1]), ts(p[2])
        w = min(words, key=lambda x: abs(x[0]-s), default=None)
        if not w or abs(w[0]-s) > 0.06: continue
        ws, we, wt, nxt, nw = w
        why = None
        if nxt is not None and nxt - we >= a.gap and nxt < e:
            why = 'LEAD'; new = max(s, nxt - a.pre)
            if a.fix: p[1] = fmt(new); L[i] = ','.join(p)
        elif len(KANA.findall(wt)) >= 5 and 0.3 <= we - ws <= 0.45 and e - s < 0.8:
            why = 'STUB'; new = None
        if why:
            flags.append({'line': i+1, 'start': fmt(s), 'why': why, 'new_start': fmt(new) if new else None,
                          'speaker': p[4], 'text': p[9], 'word': wt})
    for f in flags:
        print(f"{f['start']} {f['why']:4s} -> {f['new_start'] or 'ear-check'}  {f['speaker']}: {f['text'][:50]}")
    print(f"onset_gate: {len(flags)} flagged (LEAD {sum(f['why']=='LEAD' for f in flags)}, STUB {sum(f['why']=='STUB' for f in flags)})")
    if a.json: json.dump(flags, open(a.json, 'w'), ensure_ascii=False, indent=1)
    if a.fix: open(a.fix, 'w', encoding='utf-8-sig').write('\n'.join(L))
    elif any(f['why']=='LEAD' for f in flags): sys.exit(1)

if __name__ == '__main__': main()
