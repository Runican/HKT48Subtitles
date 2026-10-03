#!/usr/bin/env python3
"""Write ASS with OFFSET applied to clip-relative cue times.

Hard gate: every cue must have non-empty EN after resolving text|en|text_en.
Normalizes cue['text'] to that EN before write. Refuses to ship blank Dialogue Text.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

MAX_DUR = 6.5
GAP = 0.08


def cue_en(c: dict) -> str:
    for k in ("text", "en", "text_en"):
        v = c.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def ts_ass(sec: float) -> str:
    if sec < 0:
        sec = 0.0
    total_cs = int(round(sec * 100))
    h = total_cs // 360000
    rem = total_cs % 360000
    m = rem // 6000
    rem = rem % 6000
    s = rem // 100
    cs = rem % 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def snap_cues(cues):
    cues = sorted((dict(c) for c in cues), key=lambda c: c["start"])
    out = []
    empty = []
    for i, c in enumerate(cues):
        en = cue_en(c)
        if not en:
            empty.append((i, c.get("start"), c.get("text_ja") or c.get("ja") or ""))
            continue
        c["text"] = en
        c["en"] = en
        c["text_en"] = en
        if c["end"] <= c["start"]:
            continue
        c["end"] = min(float(c["end"]), float(c["start"]) + MAX_DUR)
        out.append(c)
    if empty:
        msg = "write_ass REFUSED: empty EN on cues (resolve text|en|text_en):\n"
        msg += "\n".join(f"  idx={i} start={s} ja={j[:60]!r}" for i, s, j in empty[:20])
        raise SystemExit(msg)
    for i in range(len(out) - 1):
        a, b = out[i], out[i + 1]
        if a.get("overlap_ok") and b.get("overlap_ok"):
            continue
        if a["end"] > b["start"] - GAP:
            new_end = b["start"] - GAP
            min_end = a["start"] + 0.35
            if new_end >= min_end:
                a["end"] = new_end
            else:
                a["end"] = min_end
                b["start"] = a["end"] + GAP
                if b["end"] <= b["start"] + 0.3:
                    b["end"] = b["start"] + 0.5
    return [c for c in out if c["end"] > c["start"] + 0.05]


def write_ass(cues, offset, path: Path, title: str = "HKT48 EN"):
    cues = snap_cues(cues)
    header = f"""[Script Info]
Title: {title}
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,56,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for c in cues:
        layer = int(c.get("layer", 0) or 0)
        mv = int(c.get("margin_v", 60) or 60)
        name = c.get("name") or c.get("speaker") or ""
        text = cue_en(c).replace("\n", r"\N")
        if not text.strip():
            raise SystemExit("write_ass internal error: blank text after snap")
        start = ts_ass(float(c["start"]) + offset)
        end = ts_ass(float(c["end"]) + offset)
        lines.append(f"Dialogue: {layer},{start},{end},Default,{name},0,0,{mv},,{text}\n")
    path.write_text("".join(lines), encoding="utf-8")
    return cues


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cues_or_segment", help="cues.json path OR segment directory with cues.json+meta.json")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--offset", type=float, default=None)
    ap.add_argument("--title", default="HKT48 EN")
    args = ap.parse_args()

    p = Path(args.cues_or_segment)
    if p.is_dir():
        cues_path = p / "cues.json"
        meta = json.loads((p / "meta.json").read_text(encoding="utf-8"))
        offset = float(meta["offset_sec"]) if args.offset is None else args.offset
        out = Path(args.out) if args.out else p / f"{p.name}_EN_offset.ass"
        title = args.title
    else:
        cues_path = p
        offset = 0.0 if args.offset is None else args.offset
        out = Path(args.out) if args.out else p.with_suffix(".ass")
        title = args.title

    data = json.loads(cues_path.read_text(encoding="utf-8"))
    cues = data if isinstance(data, list) else data.get("cues", [])
    snapped = write_ass(cues, offset, out, title=title)
    # normalize cues.json beside output when segment dir
    if p.is_dir():
        meta = json.loads((p / "meta.json").read_text(encoding="utf-8"))
        (p / "cues.json").write_text(
            json.dumps({"offset_sec": offset, "dur": meta.get("dur"), "cues": snapped}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(f"Wrote ASS {out} ({len(snapped)} cues, offset={offset})")


if __name__ == "__main__":
    main()
