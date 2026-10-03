#!/usr/bin/env python3
"""Heuristic speaker assignment from dialogue windows + glossary names."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

# time windows of self-intro blocks inferred from content; refined after scan
# These are soft defaults; content-based overrides win.

NAME_PATTERNS = [
    (r"生野|いくの|イクノ", "Ikuno-chan"),
    (r"ミーナ|みーな|中野南実|中野ミナミ|ミナミにシート", "Mii-na"),
    (r"ゆいぱん|ユイパン|松永|悠良", "Yui"),
    (r"さあや|サーヤ|森崎|冴彩|さーちゃん|サアヤ", "Saa-chan"),
    (r"イーコ|いーこ|伊桜莉|イオリ|田中イオリ", "Ii-ko"),
    (r"あみゆん|アミユン|歩実優", "Amiyun"),
    (r"石橋|いぶき|イブキ", "Ibuki"),
    (r"北川|ひいろ|ヒイロ", "Hiiro"),
    (r"りの|リノ|坂本", "Rino"),
    (r"りんか|リンカ|大内", "Rinka"),
    (r"石井|綾音|あーたん|アータン", "Aa-tan"),
    (r"ひな(?!た)|青木", "Hina"),
]

HOST_PAT = re.compile(r"(自己紹介|お題は|お願いします|マイクを向けたら|次は|では、)")

def detect_name(text: str):
    for pat, spk in NAME_PATTERNS:
        if re.search(pat, text):
            return spk
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asr")
    ap.add_argument("--speakers-out", required=True)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--windows", default=None, help="optional JSON list of {start,end,speaker}")
    args = ap.parse_args()

    data = json.loads(Path(args.asr).read_text(encoding="utf-8"))
    windows = []
    if args.windows and Path(args.windows).exists():
        windows = json.loads(Path(args.windows).read_text(encoding="utf-8"))

    current = "Host"
    seen = {"Host", "Generic"}
    for seg in data["segments"]:
        t = seg.get("text_ja") or ""
        start = float(seg["start"])
        # window override
        for w in windows:
            if w["start"] <= start < w["end"]:
                current = w["speaker"]
                break
        name = detect_name(t)
        # self-intro pattern: 「〜です」 after name
        if name and re.search(r"(です|と言います|といいます)", t):
            current = name
            seen.add(name)
            seg["speaker"] = name
            continue
        if HOST_PAT.search(t) and len(t) < 40 and not name:
            seg["speaker"] = "Host"
            current = "Host"
            continue
        # short cheers
        if len(t) <= 8 and re.search(r"[ー！!]+$", t):
            seg["speaker"] = "Generic"
            continue
        if name and current == "Host":
            # might be host naming next person
            seg["speaker"] = "Host"
            continue
        seg["speaker"] = current if current else "Generic"
        seen.add(seg["speaker"])

    speakers = [{"id": s, "label": s} for s in sorted(seen)]
    speakers.append({"id": "Generic", "label": "Generic/Crowd", "note": "unmapped short calls"} 
                    if "Generic" not in seen else None)
    speakers = [s for s in speakers if s]
    Path(args.speakers_out).write_text(json.dumps({
        "speakers": speakers,
        "assignment": "dialogue-cue heuristics by time window + phrase; unmapped=Generic"
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"speakers={sorted(seen)} -> {args.out}")

if __name__ == "__main__":
    main()
