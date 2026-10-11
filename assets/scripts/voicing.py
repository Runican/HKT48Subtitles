#!/usr/bin/env python3
"""voicing.py SEGDIR|WAV a-b ... : single-voice check for short windows (seconds, clip-relative).
SEGDIR must hold original.wav (16 kHz mono PCM). Prints a 50 ms strip, VOICE / LOUD-UNVOICED runs and silero VAD spans.
Use it to time short stock phrases next to crowd cheers: the speaker's line is a VOICE run; a cheer is LOUD-UNVOICED.
voicing = max normalized autocorrelation for F0 120-500 Hz (single voice ~0.6-0.95; crowd cheer/applause < ~0.4).
Also silero VAD (faster_whisper) speech spans."""
import sys, wave, numpy as np
from faster_whisper.vad import get_speech_timestamps, VadOptions
import os
d = sys.argv[1]
w = wave.open(d if d.endswith('.wav') else os.path.join(d, 'original.wav')); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
def frames(a, b, hop=0.05, win=0.04):
    out = []
    t = a
    while t < b:
        s = x[int(t * sr): int((t + win) * sr)]
        s = s - s.mean(); e = float(np.sqrt((s ** 2).mean()) + 1e-9)
        ac = np.correlate(s, s, 'full')[len(s) - 1:]
        lo, hi = int(sr / 500), int(sr / 120)
        v = float(ac[lo:hi].max() / (ac[0] + 1e-9)) if ac[0] > 0 else 0
        out.append((t, 20 * np.log10(e), v)); t += hop
    return out
for wdef in sys.argv[2:]:
    a, b = map(float, wdef.split('-'))
    F = frames(a, b)
    peak = max(f[1] for f in F)
    runs = []; cur = None
    for t, db, v in F:
        on = v >= 0.55 and db > peak - 25
        if on: cur = [t, t + 0.05] if cur is None else [cur[0], t + 0.05]
        else:
            if cur and cur[1] - cur[0] >= 0.25: runs.append(cur)
            cur = None
    if cur and cur[1] - cur[0] >= 0.25: runs.append(cur)
    seg = x[int(a * sr): int(b * sr)]
    vad = get_speech_timestamps(seg, VadOptions(min_silence_duration_ms=150, speech_pad_ms=30))
    strip = ''.join('#' if v >= 0.55 and db > peak - 25 else ('~' if db > peak - 15 else '.') for t, db, v in F)
    print(f'== {wdef}  (#=voiced single voice, ~=loud unvoiced/cheer, .=quiet; 1 char=50ms)')
    # run-length view: merge '#' runs separated by <=2 non-# chars into 'V' (voice), '~' runs >=4 into 'C' (cheer/loud unvoiced)
    import re as _re
    ev = []
    for m in _re.finditer(r'#(?:[.~]{0,2}#)*', strip):
        if m.end() - m.start() >= 5: ev.append((a + m.start() * 0.05, a + m.end() * 0.05, 'VOICE'))
    for m in _re.finditer(r'~{4,}', strip): ev.append((a + m.start() * 0.05, a + m.end() * 0.05, 'LOUD-UNVOICED'))
    for s0, e0, k in sorted(ev): print(f'   {k:13s} {s0:.2f}-{e0:.2f}')
    print('  voiced runs:', [f'{r[0]:.2f}-{r[1]:.2f}' for r in runs])
    print('  vad:', [f"{a + v['start'] / sr:.2f}-{a + v['end'] / sr:.2f}" for v in vad])
