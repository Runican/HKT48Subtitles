#!/usr/bin/env python3
"""Find ASR dropouts vs silence map."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

def parse_silence(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", text)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", text)]
    return list(zip(starts, ends))

def covered_by_silence(a, b, silences, slack=0.5):
    # if most of [a,b] is inside some silence interval(s)
    for s, e in silences:
        if a >= s - slack and b <= e + slack:
            return True
        # substantial overlap
        ov = max(0.0, min(b, e) - max(a, s))
        if (b - a) > 0 and ov / (b - a) >= 0.7:
            return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asr")
    ap.add_argument("--silence", required=True)
    ap.add_argument("--dur", type=float, required=True)
    ap.add_argument("--threshold", type=float, default=8.0)
    ap.add_argument("--near", type=float, default=3.0)
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.asr).read_text(encoding="utf-8"))
    segs = data["segments"]
    silences = parse_silence(Path(args.silence))
    gaps = []
    near = []
    prev_end = 0.0
    for seg in segs:
        start = float(seg["start"])
        if start - prev_end >= args.threshold:
            gaps.append({"start": round(prev_end, 3), "end": round(start, 3), "gap": round(start - prev_end, 3),
                         "is_silence": covered_by_silence(prev_end, start, silences)})
        elif start - prev_end >= args.near:
            near.append({"start": round(prev_end, 3), "end": round(start, 3), "gap": round(start - prev_end, 3),
                         "is_silence": covered_by_silence(prev_end, start, silences)})
        prev_end = max(prev_end, float(seg["end"]))
    if args.dur - prev_end >= args.threshold:
        gaps.append({"start": round(prev_end, 3), "end": round(args.dur, 3), "gap": round(args.dur - prev_end, 3),
                     "is_silence": covered_by_silence(prev_end, args.dur, silences)})
    elif args.dur - prev_end >= args.near:
        near.append({"start": round(prev_end, 3), "end": round(args.dur, 3), "gap": round(args.dur - prev_end, 3),
                     "is_silence": covered_by_silence(prev_end, args.dur, silences)})

    dropouts = [g for g in gaps if not g["is_silence"]]
    out = {
        "dropout_threshold_sec": args.threshold,
        "silence_events": len(silences),
        "silences": [{"start": s, "end": e} for s, e in silences],
        "empty_asr_ge_threshold": gaps,
        "dropouts_found": dropouts,
        "dropouts_repaired": [],
        "near_miss_gaps_3_to_8s": near,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"gaps>={args.threshold}s: {len(gaps)} (dropouts non-quiet: {len(dropouts)}); near: {len(near)}")
    for d in dropouts:
        print(" DROPOUT", d)

if __name__ == "__main__":
    main()
