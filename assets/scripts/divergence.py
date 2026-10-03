#!/usr/bin/env python3
"""Compare a fresh ASS against a gold ASS. Writes metrics JSON + a short report.

Matching is time-overlap (IoU), not text. Useful as a QC helper after a
blind re-run. Does not read or depend on any particular show path.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from difflib import SequenceMatcher

def parse_ts(t):
    parts = t.split(':')
    h, m = int(parts[0]), int(parts[1])
    s = float(parts[2])
    return h * 3600 + m * 60 + s

def parse_ass(path: Path):
    cues = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        if not line.startswith('Dialogue:'):
            continue
        parts = line[len('Dialogue:'):].split(',', 9)
        if len(parts) < 10:
            continue
        cues.append({
            'start': parse_ts(parts[1].strip()),
            'end': parse_ts(parts[2].strip()),
            'text': parts[9].strip(),
            'name': parts[4].strip(),
        })
    return cues

def norm(s):
    s = s.lower()
    s = re.sub(r'\{.*?\}', '', s)
    s = re.sub(r'\\n', ' ', s, flags=re.I)
    s = re.sub(r"[^a-z0-9\s']+", ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def tokens(s):
    return set(norm(s).split())

def iou(a0, a1, b0, b1):
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    return inter / union if union > 0 else 0

def match_cues(fresh, gold, iou_thresh=0.25):
    used_g = set()
    pairs = []
    for i, f in enumerate(fresh):
        best = None
        best_iou = 0
        for j, g in enumerate(gold):
            if j in used_g:
                continue
            if abs(f['start'] - g['start']) > 8 and iou(f['start'], f['end'], g['start'], g['end']) < 0.05:
                continue
            v = iou(f['start'], f['end'], g['start'], g['end'])
            if abs(f['start'] - g['start']) < 1.5:
                v = max(v, 0.3)
            if v > best_iou:
                best_iou = v
                best = j
        if best is not None and best_iou >= iou_thresh:
            used_g.add(best)
            pairs.append((i, best, best_iou))
    unmatched_f = [i for i in range(len(fresh)) if i not in {p[0] for p in pairs}]
    unmatched_g = [j for j in range(len(gold)) if j not in used_g]
    return pairs, unmatched_f, unmatched_g

def edit_sim(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()

def jaccard(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

def is_close(f, g, iou_v):
    es = edit_sim(f['text'], g['text'])
    jac = jaccard(f['text'], g['text'])
    dt = abs(f['start'] - g['start'])
    return (es >= 0.55 or jac >= 0.5) and dt <= 0.5 and iou_v >= 0.3

def bucket(f, g):
    fn, gn = norm(f['text']), norm(g['text'])
    ft, gt = f['text'], g['text']
    if ft.strip() in ('[song]', '') or gt.strip().startswith('[song]'):
        return 'invented/stub'
    if ('not' in fn) != ('not' in gn) and edit_sim(ft, gt) < 0.5:
        return 'polarity'
    if (f.get('name') or '') != (g.get('name') or '') and (f.get('name') or g.get('name')):
        return 'speaker Name'
    if ft.rstrip().endswith(('—', '…', '-')) and len(gt) > len(ft) + 10:
        return 'truncated'
    if abs(f['start'] - g['start']) <= 0.5 and edit_sim(ft, gt) >= 0.7:
        return 'timing-only'
    if edit_sim(ft, gt) < 0.35:
        return 'other'
    return 'phrasing'

def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fresh', type=Path, required=True, help='Fresh ASS to score')
    ap.add_argument('--gold', type=Path, required=True, help='Reference ASS')
    ap.add_argument('--out-dir', type=Path, default=Path('.'),
                    help='Where to write divergence_metrics.json and DIVERGENCE.md (default: cwd)')
    args = ap.parse_args()
    fresh_p = args.fresh.resolve()
    gold_p = args.gold.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    fresh, gold = parse_ass(fresh_p), parse_ass(gold_p)
    pairs, um_f, um_g = match_cues(fresh, gold)

    start_deltas, end_deltas, ious, edits, jacs = [], [], [], [], []
    close_n = 0
    examples = {k: [] for k in [
        'invented/stub', 'polarity', 'speaker Name', 'truncated',
        'timing-only', 'phrasing', 'other',
    ]}
    for i, j, iv in pairs:
        f, g = fresh[i], gold[j]
        start_deltas.append(abs(f['start'] - g['start']))
        end_deltas.append(abs(f['end'] - g['end']))
        ious.append(iv)
        es = edit_sim(f['text'], g['text'])
        jac = jaccard(f['text'], g['text'])
        edits.append(es)
        jacs.append(jac)
        if is_close(f, g, iv):
            close_n += 1
        b = bucket(f, g)
        if len(examples[b]) < 6:
            examples[b].append((f, g))

    n_gold = len(gold)
    n_fresh = len(fresh)
    n_pairs = len(pairs)
    div_n = n_pairs - close_n
    exact = sum(1 for i, j, _ in pairs if norm(fresh[i]['text']) == norm(gold[j]['text']))
    missing_n = len(um_g)
    extra_n = len(um_f)
    metrics = {
        'fresh_cues': n_fresh,
        'gold_cues': n_gold,
        'matched_pairs': n_pairs,
        'unmatched_fresh_extra': extra_n,
        'unmatched_gold_missing': missing_n,
        'exact_match_pct_of_pairs': round(100 * exact / n_pairs, 1) if n_pairs else 0,
        'mean_iou': round(mean(ious), 3),
        'mean_abs_dstart': round(mean(start_deltas), 3),
        'mean_abs_dend': round(mean(end_deltas), 3),
        'mean_edit_similarity': round(mean(edits), 3),
        'mean_token_jaccard': round(mean(jacs), 3),
        'pct_close_of_gold': round(100 * close_n / n_gold, 1) if n_gold else 0,
        'pct_divergent_of_gold': round(100 * div_n / n_gold, 1) if n_gold else 0,
        'pct_missing_of_gold': round(100 * missing_n / n_gold, 1) if n_gold else 0,
        'pct_extra_vs_gold': round(100 * extra_n / n_gold, 1) if n_gold else 0,
        'close_count': close_n,
        'divergent_count': div_n,
    }
    (out_dir / 'divergence_metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')

    lines = [
        '# Divergence report — fresh vs gold ASS',
        '',
        f'- Fresh: `{fresh_p.name}`',
        f'- Gold: `{gold_p.name}`',
        '',
        '## Headline metrics',
        f'- Cue counts: fresh **{n_fresh}** vs gold **{n_gold}**',
        f'- Matched pairs (time-overlap): **{n_pairs}**',
        f'- Unmatched fresh (extra): **{extra_n}** | Unmatched gold (missing): **{missing_n}**',
        f"- Exact match rate (of pairs): **{metrics['exact_match_pct_of_pairs']}%**",
        f"- Mean IoU: **{metrics['mean_iou']}**",
        f"- Mean |Δstart|: **{metrics['mean_abs_dstart']}s** | Mean |Δend|: **{metrics['mean_abs_dend']}s**",
        f"- Mean edit similarity: **{metrics['mean_edit_similarity']}** | Mean token Jaccard: **{metrics['mean_token_jaccard']}**",
        '',
        '## Rough % of gold cues',
        f"- Close (gist + timing ≤0.5s): **{metrics['pct_close_of_gold']}%** ({close_n})",
        f"- Divergent (matched but not close): **{metrics['pct_divergent_of_gold']}%** ({div_n})",
        f"- Missing in fresh: **{metrics['pct_missing_of_gold']}%** ({missing_n})",
        f"- Extra in fresh (count / gold): **{metrics['pct_extra_vs_gold']}%** ({extra_n})",
        '',
        '## Category examples',
    ]
    for cat, items in examples.items():
        if not items:
            continue
        lines.append(f'### {cat}')
        for f, g in items[:5]:
            lines.append(f"  F[{f['start']:.1f}-{f['end']:.1f}] {f['text'][:100]}")
            lines.append(f"  G[{g['start']:.1f}-{g['end']:.1f}] {g['text'][:100]}")
            lines.append('')
    lines.append('## Sample unmatched gold (missing in fresh)')
    for j in um_g[:12]:
        g = gold[j]
        lines.append(f"- G[{g['start']:.1f}] {g['text'][:100]}")
    lines.append('')
    lines.append('## Sample unmatched fresh (extra)')
    for i in um_f[:12]:
        f = fresh[i]
        lines.append(f"- F[{f['start']:.1f}] {f['text'][:100]}")
    lines.append('')
    lines.append('## Method notes')
    lines.append('- Matching: time-window IoU / start-proximity (≥0.25 IoU or |Δstart|<1.5s).')
    lines.append('- Close = edit≥0.55 or Jaccard≥0.5 AND |Δstart|≤0.5s AND IoU≥0.3.')
    (out_dir / 'DIVERGENCE.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(metrics, indent=2))

if __name__ == '__main__':
    main()
