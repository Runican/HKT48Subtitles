#!/usr/bin/env python3
"""After asr.json exists: cleanup_ja → build_cues_from_asr (EN filled externally).

Invokes the copies of those scripts that sit next to this file, using the
current interpreter (no hardcoded venv path).
"""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def run(cmd):
    print('+', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit(r.returncode)

def seg_dir(work: Path, slug: str, layout: str) -> Path:
    if layout == 'segments':
        return work / 'segments' / slug
    return work / slug

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, default=Path('.'), help='Job directory (default: cwd)')
    ap.add_argument('--glossary', type=Path, default=None,
                    help='Glossary JSON. Default: <work>/glossary.json. '
                         'Public example: assets/hkt48/glossary.json')
    ap.add_argument('--layout', choices=['segments', 'flat'], default='segments',
                    help='segments: <work>/segments/<slug>/ ; flat: <work>/<slug>/')
    ap.add_argument('slugs', nargs='+', help='Segment slugs to process')
    args = ap.parse_args()
    work = args.work.resolve()
    gloss = args.glossary
    if gloss is None:
        cand = work / 'glossary.json'
        if not cand.exists():
            raise SystemExit('pass --glossary (example: assets/hkt48/glossary.json)')
        gloss = cand
    gloss = gloss.resolve()
    py = sys.executable
    for slug in args.slugs:
        d = seg_dir(work, slug, args.layout)
        asr = d / 'asr.json'
        if not asr.exists():
            print('SKIP no asr', slug)
            continue
        run([py, str(HERE / 'cleanup_ja.py'), str(asr), '--glossary', str(gloss), '-o', str(asr)])
        run([py, str(HERE / 'build_cues_from_asr.py'), str(d)])
        print(slug, 'ready for EN fill → cues_ja.json')
    print('DONE shells')

if __name__ == '__main__':
    main()
