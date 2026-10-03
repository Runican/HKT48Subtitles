#!/usr/bin/env python3
"""Stitch per-segment ASS files into full_EN_offset.ass with slug markers."""
from __future__ import annotations
import argparse, json
from pathlib import Path

EVENTS = (
    "[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
)

def load_order(work: Path, order, plan: Path | None):
    slugs = list(order or [])
    if slugs:
        return slugs
    if plan is None:
        cand = work / 'segments_plan.json'
        if cand.exists():
            plan = cand
    if plan is None:
        raise SystemExit('pass --order SLUG ... or --plan segments_plan.json')
    raw = json.loads(plan.read_text(encoding='utf-8'))
    if isinstance(raw, dict):
        raw = raw.get('segments') or raw.get('order') or []
    out = []
    for item in raw:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict) and item.get('slug'):
            out.append(item['slug'])
    if not out:
        raise SystemExit(f'no slugs in {plan}')
    return out

def seg_ass(work: Path, slug: str, layout: str) -> Path:
    base = (work / 'segments' / slug) if layout == 'segments' else (work / slug)
    return base / f'{slug}_EN_offset.ass'

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, default=Path('.'), help='Job directory (default: cwd)')
    ap.add_argument('--order', nargs='*', default=None, help='Segment slugs in stitch order')
    ap.add_argument('--plan', type=Path, default=None,
                    help='JSON list (or {segments:[...]}) of slugs. '
                         'Default: <work>/segments_plan.json when --order is omitted')
    ap.add_argument('--layout', choices=['flat', 'segments'], default='flat',
                    help='flat: <work>/<slug>/<slug>_EN_offset.ass ; '
                         'segments: <work>/segments/<slug>/...')
    ap.add_argument('--out', type=Path, default=None, help='Default: <work>/full_EN_offset.ass')
    args = ap.parse_args()
    work = args.work.resolve()
    order = load_order(work, args.order, args.plan)
    header = None
    body_parts = []
    for slug in order:
        p = seg_ass(work, slug, args.layout)
        if not p.exists():
            print('MISSING', p)
            continue
        text = p.read_text(encoding='utf-8')
        if header is None:
            if '[Events]' not in text:
                raise SystemExit(f'no [Events] in {p}')
            header = text.split('[Events]')[0] + EVENTS
        lines = [line for line in text.splitlines() if line.startswith('Dialogue:')]
        body_parts.append(f"; ===== {slug} =====\n" + "\n".join(lines) + "\n")
    if header is None:
        raise SystemExit('no segment ASS files found')
    out_text = header + "\n".join(body_parts)
    out_path = args.out.resolve() if args.out else (work / 'full_EN_offset.ass')
    out_path.write_text(out_text, encoding='utf-8')
    n = sum(1 for line in out_text.splitlines() if line.startswith('Dialogue:'))
    print('wrote', out_path, 'cues', n, 'bytes', len(out_text.encode()))

if __name__ == '__main__':
    main()
