#!/usr/bin/env python3
"""Score shipped speaker hints against the reviewer's final speakers.

  python score_review.py --hints diarization/speaker_hints_review_fullname.tsv --review speaker_confirm.jsonl \
      [--edit-ops edit_ops.jsonl] [--exclude mc3=1:18:42-1:30:12] [--out review_score.json]

A hint counts when its tier is high or medium and the reviewer left a confirm/fix decision on that cue
(matched on the cue start string). Correct = final speaker equals the hinted full name. Cues the reviewer split
(a review "split" action, or an {"op":"split"} in --edit-ops) are listed separately and not scored. Rows are broken down into intro / outside-intro by the hint TSV segment.
"""
import argparse, json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diar_common import t2s  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hints", required=True); ap.add_argument("--review", required=True)
    ap.add_argument("--exclude", action="append", default=[], help="label=H:MM:SS-H:MM:SS span left out of the score")
    ap.add_argument("--edit-ops", help="editor ops JSONL; cues with op=split are not scored")
    ap.add_argument("--out")
    a = ap.parse_args()
    ex = []
    for e in a.exclude:
        lab, rng = e.split("=", 1); x, y = rng.split("-"); ex.append((lab, t2s(x), t2s(y)))
    H = {}
    lines = open(a.hints, encoding="utf-8").read().splitlines(); hdr = lines[0].split("\t")
    for l in lines[1:]:
        r = dict(zip(hdr, l.split("\t"))); H[r["start"]] = r
    dec, splits = {}, {}
    for l in open(a.review, encoding="utf-8"):
        d = json.loads(l)
        if d.get("action") in ("confirm", "fix"): dec[d["cue_start"]] = d
        elif d.get("action") == "split": splits[d.get("cue_start", d["parts"][0]["start"])] = [p["speaker"] for p in d["parts"]]
    if a.edit_ops:
        for l in open(a.edit_ops, encoding="utf-8"):
            d = json.loads(l)
            if d.get("op") == "split": splits[d["start"]] = [p.get("name", p.get("speaker")) for p in d["parts"]]
    res = {t: dict(correct=0, checked=0, intro=[0, 0], outside=[0, 0]) for t in ("high", "medium")}
    misses, split_rows, excluded = [], [], Counter()
    for st, h in H.items():
        t = h["confidence"]
        if t not in res: continue
        s = t2s(st)
        lab = next((l for l, x, y in ex if x <= s < y), None)
        if lab: excluded[lab] += 1; continue
        if st in splits:
            split_rows.append(dict(t=st, conf=t, hint=h["hint_name"], parts=splits[st], final=dec.get(st, {}).get("speaker"))); continue
        if st not in dec: continue
        ok = dec[st]["speaker"] == h["hint_name"]; k = "intro" if h["segment"] == "intro" else "outside"
        res[t]["checked"] += 1; res[t]["correct"] += ok; res[t][k][1] += 1; res[t][k][0] += ok
        if not ok: misses.append(dict(t=st, conf=t, hint=h["hint_name"], user=dec[st]["speaker"], seg=h["segment"]))
    out = dict(**{t: dict(correct=v["correct"], checked=v["checked"], intro="%d/%d" % tuple(v["intro"]), outside="%d/%d" % tuple(v["outside"])) for t, v in res.items()},
               excluded=dict(excluded), split_not_scored=split_rows, misses=misses,
               miss_pairs=dict(Counter(f"{m['hint']}->{m['user']}" for m in misses)))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if a.out: json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
