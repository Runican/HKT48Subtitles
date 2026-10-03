#!/usr/bin/env python3
"""Pass F helpers: snap cue timings — max dur, min gap, phrase units."""
from __future__ import annotations
import argparse, json, copy
from pathlib import Path

MAX_DUR = 6.5
MIN_DUR = 0.6
MIN_GAP = 0.07  # 70ms midway in 60-80ms
TARGET_MAX = 5.5

def snap(cues):
    cues = sorted(copy.deepcopy(cues), key=lambda c: (c["start"], c["end"]))
    for c in cues:
        if c["end"] < c["start"]:
            c["end"] = c["start"] + MIN_DUR
        dur = c["end"] - c["start"]
        if dur > MAX_DUR:
            c["end"] = c["start"] + MAX_DUR
        if dur < MIN_DUR:
            c["end"] = c["start"] + MIN_DUR
    # enforce gaps between non-overlapping consecutive cues
    for i in range(1, len(cues)):
        prev, cur = cues[i-1], cues[i]
        # overlapping allowed if intentional; only gap non-overlap
        if cur["start"] >= prev["end"]:
            gap = cur["start"] - prev["end"]
            if gap < MIN_GAP:
                # shrink prev end slightly if possible
                new_end = cur["start"] - MIN_GAP
                if new_end - prev["start"] >= MIN_DUR:
                    prev["end"] = round(new_end, 3)
                else:
                    cur["start"] = round(prev["end"] + MIN_GAP, 3)
                    if cur["end"] < cur["start"] + MIN_DUR:
                        cur["end"] = round(cur["start"] + MIN_DUR, 3)
        # still overlapping too much is OK (adjacency/overlap cues)
    for c in cues:
        c["start"] = round(float(c["start"]), 3)
        c["end"] = round(float(c["end"]), 3)
    return cues

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cues_in")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()
    data = json.loads(Path(args.cues_in).read_text(encoding="utf-8"))
    cues = data if isinstance(data, list) else data.get("cues", data.get("segments", []))
    snapped = snap(cues)
    out = {"cues": snapped} if not isinstance(data, list) else snapped
    if isinstance(data, dict) and "cues" in data:
        data["cues"] = snapped
        Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        Path(args.out).write_text(json.dumps({"cues": snapped}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapped {len(snapped)} cues -> {args.out}")

if __name__ == "__main__":
    main()
