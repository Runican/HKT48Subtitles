#!/usr/bin/env python3
"""Pass C: glossary-driven JA cleanup on ASR segments."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

# Ordered replacements: longer / more specific first
DEFAULT_FIXES = [
    # team / show
    (r"チーム警報", "チームKIV"),
    (r"チームケイフォー", "チームKIV"),
    (r"チームけいふぉー", "チームKIV"),
    (r"ちゆめいち", "チームH"),
    (r"チームエイチ", "チームH"),
    (r"さかあがり公演", "逆上がり公演"),
    (r"坂上がり", "逆上がり"),
    (r"サカアガリ", "逆上がり"),
    # members / nicks (ASR mush)
    (r"イクノリラ", "生野莉奈"),
    (r"イクノリナ", "生野莉奈"),
    (r"生野りな", "生野莉奈"),
    (r"いくのちゃん", "イクノちゃん"),
    (r"アミュー", "あみゆん"),
    (r"アミユン", "あみゆん"),
    (r"あみゅん", "あみゆん"),
    (r"ミーナ子と仲のミナミ", "ミーナこと中野ミナミ"),
    (r"ミーナこと中野ミナミ", "ミーナこと中野ミナミ"),
    (r"中野ミナミ", "中野南実"),
    (r"みーな", "ミーナ"),
    (r"ゆいぱん", "ゆいぱん"),
    (r"ユイパン", "ゆいぱん"),
    (r"松永ゆい", "松永悠良"),
    (r"森崎沙彩", "森崎冴彩"),
    (r"森崎さあや", "森崎冴彩"),
    (r"チーム警報の森崎", "チームKIVの森崎"),
    (r"田中より", "田中イオリ"),
    (r"田中伊織", "田中伊桜莉"),
    (r"田中いおり", "田中伊桜莉"),
    (r"いーこ", "イーコ"),
    (r"野菜の火", "野菜の日"),
    (r"ご好きなわきゅうりバイ", "だご好きなもんはキュウリばい"),
    (r"好きなもんはきゅうりばい", "だご好きなもんはキュウリばい"),
    (r"好きなものはきゅうり", "だご好きなもんはキュウリばい"),
    # KILLED 2026-10-03: (r"血液型", "誕生日") — meaning rewrite
]

# Safer additional blacklist for blood-type false positive in Ii-ko catchphrase
IIKO_BLOOD_FIXES = []  # KILLED 2026-10-03 — blood→birthday templates

def apply_fixes(text: str, glossary_entries) -> str:
    t = text
    # glossary ja forms: prefer canonical first ja token when mush matches nick
    for e in glossary_entries:
        ja = e.get("ja") or []
        if not ja:
            continue
    for pat, rep in DEFAULT_FIXES:
        t = re.sub(pat, rep, t)
    # Ii-ko catchphrase corrections
    if "イーコ" in t or "伊桜莉" in t or "イオリ" in t or "田中" in t:
        for pat, rep in IIKO_BLOOD_FIXES:
            t = re.sub(pat, rep, t)
    return t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asr")
    ap.add_argument("--glossary", required=True)
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()
    data = json.loads(Path(args.asr).read_text(encoding="utf-8"))
    gloss = json.loads(Path(args.glossary).read_text(encoding="utf-8"))
    entries = gloss.get("entries", [])
    n_changed = 0
    for seg in data["segments"]:
        raw = seg.get("text_ja_raw") or seg.get("text_ja") or ""
        if "text_ja_raw" not in seg:
            seg["text_ja_raw"] = raw
        cleaned = apply_fixes(raw, entries)
        if cleaned != seg.get("text_ja"):
            n_changed += 1
        seg["text_ja"] = cleaned
    if "engine" in data:
        data["engine"]["cleanup"] = "glossary+domain_replacements_v2_large-v3"
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"cleanup done; segments touched≈{n_changed} -> {args.out}")

if __name__ == "__main__":
    main()
