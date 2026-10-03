#!/usr/bin/env python3
"""Merge ASR segments into phrase-unit cues (JA only or with EN map)."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

MAX_DUR = 6.5
PREF_MAX = 5.5
PREF_MIN = 1.2
MERGE_GAP = 0.45  # merge if gap smaller and same-ish speaker

def should_split_text(t: str) -> bool:
    return bool(re.search(r"[。！？!?]$", t.strip()))

def merge_segments(segs):
    cues = []
    buf = None
    for seg in segs:
        text = (seg.get("text_ja") or "").strip()
        if not text:
            continue
        start, end = float(seg["start"]), float(seg["end"])
        spk = seg.get("speaker") or "Generic"
        if buf is None:
            buf = {"start": start, "end": end, "speaker": spk, "text_ja": text,
                   "words": list(seg.get("words") or [])}
            continue
        gap = start - buf["end"]
        dur_if = end - buf["start"]
        can_merge = (
            gap <= MERGE_GAP
            and dur_if <= PREF_MAX
            and spk == buf["speaker"]
            and not should_split_text(buf["text_ja"])
        )
        # also merge very short follow-ups
        if gap <= 0.25 and dur_if <= MAX_DUR and spk == buf["speaker"]:
            can_merge = True
        if can_merge and dur_if <= MAX_DUR:
            joiner = "" if buf["text_ja"].endswith(("、", "。", "！", "？", "!", "?")) else ""
            # Japanese usually no space
            buf["text_ja"] = buf["text_ja"] + joiner + text
            buf["end"] = end
            buf["words"].extend(seg.get("words") or [])
        else:
            cues.append(buf)
            buf = {"start": start, "end": end, "speaker": spk, "text_ja": text,
                   "words": list(seg.get("words") or [])}
    if buf:
        cues.append(buf)
    # split overlong
    out = []
    for c in cues:
        dur = c["end"] - c["start"]
        if dur <= MAX_DUR or not c.get("words"):
            out.append(c)
            continue
        words = c["words"]
        # split by word midpoints into ~PREF_MAX chunks
        chunk_start_i = 0
        while chunk_start_i < len(words):
            w0 = words[chunk_start_i]
            end_i = chunk_start_i
            while end_i + 1 < len(words) and words[end_i + 1]["end"] - w0["start"] <= PREF_MAX:
                end_i += 1
            if end_i == chunk_start_i and end_i + 1 < len(words):
                end_i += 1
            chunk_words = words[chunk_start_i:end_i + 1]
            text = "".join(w["word"] for w in chunk_words).strip()
            out.append({
                "start": float(chunk_words[0]["start"]),
                "end": float(chunk_words[-1]["end"]),
                "speaker": c["speaker"],
                "text_ja": text or c["text_ja"],
                "words": chunk_words,
            })
            chunk_start_i = end_i + 1
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asr")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--en-map", default=None, help="optional JSON list/dict of EN by id or text_ja")
    args = ap.parse_args()
    data = json.loads(Path(args.asr).read_text(encoding="utf-8"))
    segs = data["segments"]
    merged = merge_segments(segs)
    en_map = {}
    if args.en_map and Path(args.en_map).exists():
        raw = json.loads(Path(args.en_map).read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            en_map = raw
        elif isinstance(raw, list):
            for i, item in enumerate(raw):
                if isinstance(item, str):
                    en_map[str(i)] = item
                elif isinstance(item, dict):
                    en_map[str(item.get("id", i))] = item.get("text") or item.get("text_en")
    cues = []
    for i, c in enumerate(merged):
        item = {
            "id": i,
            "start": round(c["start"], 3),
            "end": round(c["end"], 3),
            "speaker": c["speaker"],
            "style": "Generic" if c["speaker"] == "Generic" else "Default",
            "text_ja": c["text_ja"],
            "text": en_map.get(str(i)) or en_map.get(c["text_ja"]) or "",
        }
        cues.append(item)
    out = {
        "offset_sec_note": "clip-relative; OFFSET_SEC applied only at ASS/SRT export",
        "cues": cues,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"built {len(cues)} cues from {len(segs)} segs -> {args.out}")

if __name__ == "__main__":
    main()
