#!/usr/bin/env python3
"""Speaker heuristics for Ramune 7th-gen cast."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

NAME_PATTERNS = [
    (r"生野|いくの|イクノ", "Ikuno-chan"),
    (r"ミーナ|みーな|中野南実|中野ミナミ|ミナミにシート", "Mii-na"),
    (r"ゆいぱん|ユイパン|松永|悠良", "Yui"),
    (r"あみゆん|アミユン|歩実優", "Amiyun"),
    (r"石井|あーたん|アータン|彩音", "Aa-tan"),
    (r"もかぴ|モカピ|松本苺花|苺花", "Moka-pi"),
    (r"めいめい|メイメイ|吉田めい|吉田メイ", "Mei-mei"),
    (r"ららぱ|ララパ|長野らら|ららパーセント|ららぱーせんと", "Rara-pa"),
    (r"りーりたん|リーリタン|猪島|莉玲亜|リリア|りりあ|エジマ", "Rii-ritan"),
    (r"ゆうか|江浦|優香", "Yuuka"),
    (r"さらちゃん|片平|紗麗", "Sara"),
    (r"ゆうちゃん|呉優菜|呉", "Yuu-chan"),
    (r"なっち|ナッチ|靏川|鶴川|那智", "Nacchi"),
    (r"まりたん|マリタン|山川|万里愛", "Mari-tan"),
    (r"あやちゃん|龍頭|綺音|りゅうと", "Aya-chan"),
    (r"Dリターン|ディーリターン|リリアターン", "Rii-ritan"),
]

HOST_PAT = re.compile(r"(自己紹介|お題は|お願いします|マイクを向けたら|次は|では、|一人ずつ)")

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
    args = ap.parse_args()
    data = json.loads(Path(args.asr).read_text(encoding="utf-8"))
    current = "Host"
    seen = {"Host", "Generic"}
    for seg in data["segments"]:
        t = seg.get("text_ja") or ""
        name = detect_name(t)
        if name and re.search(r"(です|と言います|といいます|こと)", t):
            current = name
            seen.add(name)
            seg["speaker"] = name
            continue
        if HOST_PAT.search(t) and len(t) < 50 and not (name and "こと" in t):
            seg["speaker"] = "Host"
            current = "Host"
            continue
        if len(t) <= 10 and re.search(r"[ー！!]+$", t):
            seg["speaker"] = "Generic"
            continue
        if name and current == "Host" and not re.search(r"(です|こと)", t):
            # host naming next / chant cue
            seg["speaker"] = "Host"
            continue
        seg["speaker"] = current if current else "Generic"
        seen.add(seg["speaker"])
    speakers = [{"id": s, "label": s} for s in sorted(seen)]
    Path(args.speakers_out).write_text(json.dumps({
        "speakers": speakers,
        "assignment": "ramune 7th-gen dialogue-cue heuristics"
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"speakers={sorted(seen)}")

if __name__ == "__main__":
    main()
