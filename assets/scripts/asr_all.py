#!/usr/bin/env python3
"""Pass B+D: ASR every segment with faster-whisper, then dropout repair.

Layout:
  segments (default): <work>/segments/<slug>/{original.wav,meta.json}
  flat:               <work>/<slug>/{original.wav,meta.json}

Writes silence.json, asr_pass1.json, asr.json under each segment dir,
and asr_summary.json in the work dir. Skips a slug when asr.json exists
unless --force.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path

GAP_THRESH = 8.0
NEAR_MISS = 3.0

def seg_dir(work: Path, slug: str, layout: str) -> Path:
    if layout == 'segments':
        return work / 'segments' / slug
    return work / slug

def silence_map(wav: Path):
    cmd = ['ffmpeg', '-i', str(wav), '-af', 'silencedetect=noise=-30dB:d=1.2', '-f', 'null', '-']
    r = subprocess.run(cmd, capture_output=True, text=True)
    silences = []
    cur = None
    for line in r.stderr.splitlines():
        if 'silence_start:' in line:
            try:
                cur = float(line.split('silence_start:')[1].strip().split()[0])
            except Exception:
                cur = None
        elif 'silence_end:' in line and cur is not None:
            try:
                end = float(line.split('silence_end:')[1].strip().split()[0])
                silences.append((cur, end))
            except Exception:
                pass
            cur = None
    return silences

def span_is_mostly_silent(silences, a, b, frac=0.7):
    if b <= a:
        return True
    covered = 0.0
    for s, e in silences:
        covered += max(0.0, min(e, b) - max(s, a))
    return covered / (b - a) >= frac

def run_asr(model, wav: Path, vad=True):
    segs = []
    segments, _info = model.transcribe(
        str(wav),
        language='ja',
        word_timestamps=True,
        vad_filter=vad,
        beam_size=5,
        condition_on_previous_text=True,
    )
    for s in segments:
        words = []
        if s.words:
            for w in s.words:
                words.append({'start': float(w.start), 'end': float(w.end), 'word': w.word})
        text = (s.text or '').strip()
        if not text:
            continue
        segs.append({
            'start': float(s.start),
            'end': float(s.end),
            'speaker': 'SPEAKER_00',
            'text_ja': text,
            'words': words,
            'avg_logprob': float(getattr(s, 'avg_logprob', 0) or 0),
            'no_speech_prob': float(getattr(s, 'no_speech_prob', 0) or 0),
        })
    return segs

def find_gaps(segs, dur, silences):
    gaps = []
    if not segs:
        if not span_is_mostly_silent(silences, 0, dur):
            gaps.append((0.0, dur, 'full'))
        return gaps
    if segs[0]['start'] >= NEAR_MISS and not span_is_mostly_silent(silences, 0, segs[0]['start']):
        kind = 'dropout' if segs[0]['start'] >= GAP_THRESH else 'nearmiss'
        gaps.append((0.0, segs[0]['start'], kind))
    for a, b in zip(segs, segs[1:]):
        gap = b['start'] - a['end']
        if gap >= NEAR_MISS and not span_is_mostly_silent(silences, a['end'], b['start']):
            kind = 'dropout' if gap >= GAP_THRESH else 'nearmiss'
            gaps.append((a['end'], b['start'], kind))
    if dur - segs[-1]['end'] >= NEAR_MISS and not span_is_mostly_silent(silences, segs[-1]['end'], dur):
        kind = 'dropout' if dur - segs[-1]['end'] >= GAP_THRESH else 'nearmiss'
        gaps.append((segs[-1]['end'], dur, kind))
    return gaps

def cut_gap(wav: Path, a: float, b: float, out: Path):
    pad = 0.3
    ss = max(0.0, a - pad)
    t = (b + pad) - ss
    out.parent.mkdir(exist_ok=True)
    cmd = ['ffmpeg', '-y', '-ss', str(ss), '-t', str(t), '-i', str(wav), '-ac', '1', '-ar', '16000', str(out)]
    subprocess.run(cmd, capture_output=True)
    return ss

def merge_gap_asr(parent_segs, gap_segs, cut_abs_start, gap_a, gap_b):
    added = []
    for s in gap_segs:
        ns = dict(s)
        ns['start'] = s['start'] + cut_abs_start
        ns['end'] = s['end'] + cut_abs_start
        if ns['end'] < gap_a - 0.5 or ns['start'] > gap_b + 0.5:
            continue
        words = []
        for w in s.get('words') or []:
            words.append({**w, 'start': w['start'] + cut_abs_start, 'end': w['end'] + cut_abs_start})
        ns['words'] = words
        ns['from_gap'] = True
        added.append(ns)
    all_segs = parent_segs + added
    all_segs.sort(key=lambda x: x['start'])
    return all_segs

def process_slug(model, work, slug, layout, model_name, hush, nearmiss_cap, hush_nearmiss_cap):
    d = seg_dir(work, slug, layout)
    wav = d / 'original.wav'
    meta = json.loads((d / 'meta.json').read_text(encoding='utf-8'))
    dur = float(meta['dur'])
    t0 = time.time()
    print(f'\n=== ASR {slug} dur={dur:.1f}s ===', flush=True)
    silences = silence_map(wav)
    (d / 'silence.json').write_text(json.dumps(silences), encoding='utf-8')
    print(f'  silence spans: {len(silences)}', flush=True)

    segs = run_asr(model, wav, vad=True)
    print(f'  pass1 segments: {len(segs)} in {time.time()-t0:.0f}s', flush=True)
    (d / 'asr_pass1.json').write_text(json.dumps({
        'engine': 'faster-whisper', 'model': model_name, 'language': 'ja',
        'slug': slug, 'dur': dur, 'offset_sec': float(meta.get('offset_sec') or 0),
        'segments': segs, 'phase': 'pass1',
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print('  checkpointed pass1 -> asr_pass1.json', flush=True)

    gaps = find_gaps(segs, dur, silences)
    dropouts = [g for g in gaps if g[2] == 'dropout']
    nearmiss = [g for g in gaps if g[2] == 'nearmiss']
    cap = hush_nearmiss_cap if slug in hush else nearmiss_cap
    to_repair = dropouts[:] + nearmiss[:cap]
    print(f'  gaps: {len(dropouts)} dropout, {len(nearmiss)} nearmiss; repairing {len(to_repair)}', flush=True)

    repaired = []
    for a, b, kind in to_repair:
        cur = a
        chunks = []
        while cur < b:
            chunks.append((cur, min(cur + 45.0, b)))
            cur += 45.0
        for ca, cb in chunks:
            gpath = d / 'gaps' / f'gap_{ca:.2f}_{cb:.2f}.wav'
            cut_abs = cut_gap(wav, ca, cb, gpath)
            gsegs = run_asr(model, gpath, vad=False)
            if not gsegs:
                gsegs = run_asr(model, gpath, vad=True)
            print(f'    gap {ca:.1f}-{cb:.1f} ({kind}): +{len(gsegs)} segs', flush=True)
            if gsegs:
                segs = merge_gap_asr(segs, gsegs, cut_abs, ca, cb)
                repaired.append({'a': ca, 'b': cb, 'kind': kind, 'n': len(gsegs)})
            else:
                repaired.append({'a': ca, 'b': cb, 'kind': kind, 'n': 0})

    segs.sort(key=lambda x: x['start'])
    deduped = []
    for s in segs:
        if deduped and abs(s['start'] - deduped[-1]['start']) < 0.35 and s['text_ja'] == deduped[-1]['text_ja']:
            continue
        if slug in hush and s.get('no_speech_prob', 0) > 0.6 and s.get('avg_logprob', 0) < -1.0:
            continue
        deduped.append(s)
    segs = deduped

    out = {
        'engine': 'faster-whisper',
        'model': model_name,
        'language': 'ja',
        'vad_filter_pass1': True,
        'slug': slug,
        'dur': dur,
        'offset_sec': float(meta.get('offset_sec') or 0),
        'segments': segs,
        'repairs': repaired,
        'elapsed_sec': time.time() - t0,
    }
    (d / 'asr.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  FINAL {len(segs)} segs, elapsed {out["elapsed_sec"]:.0f}s', flush=True)
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, default=Path('.'), help='Job directory (default: cwd)')
    ap.add_argument('--layout', choices=['segments', 'flat'], default='segments')
    ap.add_argument('--order', nargs='*', default=None,
                    help='Segment slugs. Default: slugs in <work>/segments_plan.json')
    ap.add_argument('--plan', type=Path, default=None)
    ap.add_argument('--model', default='large-v3')
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--compute-type', default='int8')
    ap.add_argument('--hush-slugs', default='photo',
                    help='Comma-separated slugs with a smaller nearmiss cap and stricter '
                         'no-speech drop. Default: photo. Empty string disables.')
    ap.add_argument('--nearmiss-cap', type=int, default=12)
    ap.add_argument('--hush-nearmiss-cap', type=int, default=4)
    ap.add_argument('--force', action='store_true', help='Re-run even if asr.json exists')
    args = ap.parse_args()
    work = args.work.resolve()
    order = list(args.order or [])
    if not order:
        plan = args.plan
        if plan is None and (work / 'segments_plan.json').exists():
            plan = work / 'segments_plan.json'
        if plan is None:
            raise SystemExit('pass --order SLUG ... or provide segments_plan.json')
        raw = json.loads(plan.read_text(encoding='utf-8'))
        if isinstance(raw, dict):
            raw = raw.get('segments') or raw.get('order') or []
        for item in raw:
            if isinstance(item, str):
                order.append(item)
            elif isinstance(item, dict) and item.get('slug'):
                order.append(item['slug'])
    hush = {s.strip() for s in args.hush_slugs.split(',') if s.strip()}
    from faster_whisper import WhisperModel
    print('Loading model...', flush=True)
    t0 = time.time()
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    print(f'Model loaded in {time.time()-t0:.0f}s', flush=True)
    summary = {}
    for slug in order:
        asr_path = seg_dir(work, slug, args.layout) / 'asr.json'
        if asr_path.exists() and not args.force:
            data = json.loads(asr_path.read_text(encoding='utf-8'))
            print(f'skip {slug} (exists, {len(data.get("segments", []))} segs)')
            summary[slug] = len(data.get('segments', []))
            continue
        try:
            out = process_slug(
                model, work, slug, args.layout, args.model, hush,
                args.nearmiss_cap, args.hush_nearmiss_cap,
            )
            summary[slug] = len(out['segments'])
        except Exception as e:
            import traceback
            print(f'FAIL {slug}: {e}', flush=True)
            traceback.print_exc()
            summary[slug] = f'FAIL: {e}'
            fail = seg_dir(work, slug, args.layout) / 'ASR_FAIL.txt'
            fail.parent.mkdir(parents=True, exist_ok=True)
            fail.write_text(str(e), encoding='utf-8')
    (work / 'asr_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('ALL DONE', summary, flush=True)

if __name__ == '__main__':
    main()
