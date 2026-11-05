#!/usr/bin/env python3
"""Split ASR segments into phrase-unit cue shells (JA only; EN filled later).

Differs from build_cues.py: this splits long JA on punctuation into empty-EN
shells (cues_ja.json). build_cues.py merges short same-speaker segments.

Timing rules (2026-10-31, from the 250405 timing review):
- Multi-part segments: each part gets the words covering its share of the
  segment's characters (cumulative char count), not an equal word count.
- Cap: a word-anchored cue up to HARD_MAX (6.5 s, the downstream limit) stays one
  cue. A longer one is split at word boundaries into a head cue and
  tail cue(s), preferring clause punctuation, then the largest word gap. The text
  is split at the matching character position. If the only cut would leave a
  head under 1 s, or a tail span has no speech on original.wav (word times past
  the cap can drift), the old hard cut at MAX_DUR is kept.
- Lone first word: if the first word is followed by a gap >= LEAD_GAP s and that
  gap is silent or applause/crowd on the segment's mono original.wav, the cue
  starts at the next word. If the gap holds speech, or original.wav is missing,
  the start is kept.
- Overlong guard: segments longer than BALLOON_DUR s at fewer than BALLOON_CPS
  chars/s have unreliable word times (they drift to the segment end). They keep
  the old behaviour: segment start, hard cut at MAX_DUR, no re-anchoring.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

MAX_DUR = 5.8
TARGET = 4.0
LEAD_GAP = 1.5          # s, gap after a lone first word
GAP_SPEECH_MAX = 0.35   # max fraction of speech-like frames for a gap to count as silent/applause
HARD_MAX = 6.5          # downstream max (snap_cues/write_ass/check_cues): a re-anchored cue up to this stays one cue
TAIL_SPEECH_MIN = 0.3   # min speech-like fraction for a tail cue to be emitted
BALLOON_DUR = 6.0
BALLOON_CPS = 1.5
NORM = re.compile(r'[\s、。,.!?！？「」『』…〜~・ー]')
CLAUSE = re.compile(r'[、。,.!?！？]$')

def nchars(s):
    return len(NORM.sub('', s or ''))

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

# ---------- audio check for the lone-first-word gap (mono 16 kHz, no stereo needed) ----------
class GapAudio:
    """Speech-like frame test on the segment's mono wav: frame is speech-like if voiced
    (autocorrelation peak in 80-400 Hz >= 0.5) and within 15 dB of the segment's speech level.
    Silence and applause/crowd (unvoiced, broadband) fail the test."""
    def __init__(self, wav: Path):
        self.ok = False
        try:
            import numpy as np, soundfile as sf
        except ImportError:
            return
        if not wav.exists():
            return
        self.np, self.sf, self.wav = np, sf, wav
        self.sr = sf.info(str(wav)).samplerate
        self.ok = True

    def _frames(self, a, b):
        np, sf = self.np, self.sf
        sr = self.sr; hop = int(0.02 * sr); win = 2 * hop
        x, _ = sf.read(str(self.wav), start=max(0, int(a * sr)), stop=int(b * sr) + win, dtype='float32', always_2d=True)
        x = x.mean(1)
        n = (len(x) - win) // hop + 1
        if n <= 0:
            return np.zeros(0), np.zeros(0)
        idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
        X = np.fft.rfft(x[idx] * np.hanning(win), axis=1)
        P = np.abs(X) ** 2 + 1e-12
        f = np.fft.rfftfreq(win, 1 / sr)
        band = (f >= 300) & (f < 3400)
        e = 10 * np.log10(P[:, band].sum(1))
        ac = np.fft.irfft(P, n=win, axis=1)
        voi = ac[:, sr // 400:sr // 80].max(1) / ac[:, 0]
        return e, voi

    def gap_is_quiet(self, gap_a, gap_b, speech_a, speech_b):
        if not self.ok or gap_b <= gap_a:
            return False
        np = self.np
        es, _ = self._frames(speech_a, speech_b)
        if len(es) == 0:
            return False
        ref = float(np.median(es))
        e, voi = self._frames(gap_a, gap_b)
        if len(e) == 0:
            return False
        speechlike = ((voi > 0.5) & (e > ref - 15)).mean()
        return speechlike < GAP_SPEECH_MAX

    def span_has_speech(self, a, b, ref_a, ref_b):
        """True if [a,b] has at least TAIL_SPEECH_MIN speech-like frames (ref level from [ref_a,ref_b])."""
        if not self.ok or b <= a:
            return True
        np = self.np
        es, _ = self._frames(ref_a, ref_b)
        e, voi = self._frames(a, b)
        if len(es) == 0 or len(e) == 0:
            return True
        ref = float(np.median(es))
        return ((voi > 0.5) & (e > ref - 15)).mean() >= TAIL_SPEECH_MIN

# ---------- timing ----------
def part_word_ranges(parts, words):
    """Map each text part to a contiguous word range by cumulative character share."""
    n = len(parts)
    wc = [max(1, nchars(w.get('word', ''))) for w in words]
    total_w = float(sum(wc))
    pc = [max(1, nchars(p)) for p in parts]
    total_p = float(sum(pc))
    cum_w = []
    acc = 0
    for c in wc:
        acc += c
        cum_w.append(acc / total_w)          # fraction of chars up to and including word i
    ranges = []
    lo = 0
    acc_p = 0
    for i in range(n):
        acc_p += pc[i]
        if i == n - 1:
            hi = len(words)
        else:
            frac = acc_p / total_p
            # word boundary nearest the part's char boundary; keep >=1 word for this and each later part
            hi = min(range(lo + 1, len(words) - (n - 1 - i) + 1),
                     key=lambda j: abs(cum_w[j - 1] - frac))
        ranges.append((lo, hi))
        lo = hi
    return ranges

def allocate_times(seg, parts, guarded=False):
    """Returns [(start, end, word_list_or_None)] per part."""
    words = seg.get('words') or []
    start, end = float(seg['start']), float(seg['end'])
    n_parts = len(parts)
    if n_parts <= 1:
        return [(start, end, None if guarded else words)]
    if words and len(words) >= n_parts and not guarded:
        out = []
        for lo, hi in part_word_ranges(parts, words):
            ws = words[lo:hi]
            out.append((float(ws[0]['start']), float(ws[-1]['end']), ws))
        return out
    if words and len(words) >= n_parts:      # guarded: old equal-count split
        per = max(1, len(words) // n_parts)
        spans = []
        for i in range(n_parts):
            a = i * per
            b = (i + 1) * per if i < n_parts - 1 else len(words)
            ws = words[a:b]
            if ws:
                spans.append((float(ws[0]['start']), float(ws[-1]['end']), None))
        if len(spans) == n_parts:
            return spans
    dur = end - start
    step = dur / n_parts
    return [(start + i * step, start + (i + 1) * step, None) for i in range(n_parts)]

def split_text_at(text, frac):
    """Split JA text at the character fraction frac, nudged to the nearest clause punctuation within +-4 chars."""
    if not text:
        return '', ''
    k = max(1, min(len(text) - 1, int(round(len(text) * frac))))
    best = None
    for d in range(0, 5):
        for j in (k + d, k - d):
            if 1 <= j < len(text) and text[j - 1] in '、。,.!?！？ ':
                best = j
                break
        if best:
            break
    j = best or k
    return text[:j].strip(), text[j:].strip()

def cap_split(a, b, ws, ja):
    """Split one cue longer than MAX_DUR into <=MAX_DUR pieces at word boundaries.
    Returns [(start, end, ja)]."""
    out = []
    ws = list(ws)
    text = ja
    while ws and float(ws[-1]['end']) - a > MAX_DUR and len(ws) > 1:
        # candidate cut after word i: head ends at ws[i].end <= a+MAX_DUR, head >= 1.0 s
        cands = [i for i in range(len(ws) - 1)
                 if float(ws[i]['end']) - a <= MAX_DUR and float(ws[i]['end']) - a >= 1.0]
        if not cands:
            return None          # only cut would leave a head under 1 s (lone word): caller keeps the old hard cut
        def score(i):
            gap = float(ws[i + 1]['start']) - float(ws[i]['end'])
            punct = 1.0 if CLAUSE.search(ws[i].get('word', '').strip()) else 0.0
            near = -abs((float(ws[i]['end']) - a) - TARGET) * 0.05
            return punct * 2 + gap + near
        i = max(cands, key=score)
        head, rest = ws[:i + 1], ws[i + 1:]
        hc = sum(max(1, nchars(w.get('word', ''))) for w in head)
        tc = sum(max(1, nchars(w.get('word', ''))) for w in ws)
        t_head, t_rest = split_text_at(text, hc / tc)
        out.append((a, float(head[-1]['end']), t_head))
        ws, text = rest, t_rest
        a = float(ws[0]['start'])
    if ws:
        out.append((a, min(float(ws[-1]['end']), a + MAX_DUR) if len(ws) == 1 else float(ws[-1]['end']), text))
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('segment_dir', type=Path, help='Directory with asr.json and meta.json (original.wav optional)')
    args = ap.parse_args()
    d = args.segment_dir
    asr = json.loads((d / 'asr.json').read_text(encoding='utf-8'))
    audio = GapAudio(d / 'original.wav')
    cues = []
    for seg in asr['segments']:
        text = seg.get('text_ja', '')
        parts = split_ja(text)
        dur = float(seg['end']) - float(seg['start'])
        if dur <= MAX_DUR and len(text) <= 35:
            parts = [text]
        if not parts:
            continue
        guarded = dur > BALLOON_DUR and nchars(text) / max(dur, 0.1) < BALLOON_CPS
        spans = allocate_times(seg, parts, guarded=guarded)
        words_all = seg.get('words') or []
        for k, ((a, b, ws), ja) in enumerate(zip(spans, parts)):
            if ws is None and not guarded and len(parts) == 1:
                ws = words_all
            # lone first word (only the first part of a segment can start on one)
            if ws and k == 0 and len(ws) > 1 and not guarded:
                g0, g1 = float(ws[0]['end']), float(ws[1]['start'])
                if g1 - g0 >= LEAD_GAP and audio.gap_is_quiet(g0, g1, g1, float(ws[-1]['end'])):
                    ws = ws[1:]
                    a = float(ws[0]['start'])
            pieces = []
            if ws and not guarded and MAX_DUR < b - a <= HARD_MAX:
                pieces = [(a, b, ja)]      # small overflow: one cue, within the downstream 6.5 s limit
            elif b - a > MAX_DUR:
                if ws and not guarded:
                    pieces = cap_split(a, b, ws, ja)
                    # tails must hold speech; word times past the cap sometimes drift into silence/applause
                    if pieces and len(pieces) > 1 and audio.ok and not all(
                            audio.span_has_speech(pa, pb, pieces[0][0], pieces[0][1]) for pa, pb, _ in pieces[1:]):
                        pieces = None
                if not pieces:
                    pieces = [(a, a + MAX_DUR, ja)]
            else:
                pieces = [(a, b, ja)]
            for pa, pb, pj in pieces:
                if pb <= pa:
                    continue
                cues.append({
                    'start': round(pa, 3),
                    'end': round(pb, 3),
                    'text_ja': pj,
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
