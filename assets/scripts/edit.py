#!/usr/bin/env python3
"""Apply review edits to a finished ASS and its stitched cues JSON in lockstep.

usage: edit.py ops.jsonl --ass SHOW.ass --cues stitched_cues.json [--log edits.jsonl]

Each line of ops.jsonl is one JSON op, matched on the Dialogue Start string
(e.g. "0:19:10.31"):
  {"op":"retime","start":"0:19:10.31","s":"0:19:10.50","e":"0:19:12.00"}
  {"op":"drop","start":"..."}
  {"op":"set_text","start":"...","text":"New English"}
  {"op":"set_speaker","start":"...","name":"Speaker Name"}
  {"op":"insert_after","start":"...","s":"..","e":"..","name":"..","text":"..",
   "ja":"optional JA","before":true}   # "before": insert before the matched cue

The ASS Dialogue lines and cues["cues"] must be in the same order and count.
Matched lines are all looked up before any change, so a retime of one cue does
not break matching of later ops in the same file. Re-run check_cues.py and
onset_gate.py afterwards.
"""
import argparse
import json


def to_sec(x):
    h, m, s = x.split(":")
    return round(int(h) * 3600 + int(m) * 60 + float(s), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ops")
    ap.add_argument("--ass", required=True)
    ap.add_argument("--cues", required=True)
    ap.add_argument("--log", help="append applied ops to this JSONL file")
    a = ap.parse_args()

    lines = open(a.ass, encoding="utf-8").read().split("\n")
    cues = json.load(open(a.cues, encoding="utf-8"))
    dl = [i for i, l in enumerate(lines) if l.startswith("Dialogue:")]
    assert len(dl) == len(cues["cues"]), "ASS Dialogue count != cues count"
    idx = {lines[i].split(",")[1]: (i, k) for k, i in enumerate(dl)}
    log = open(a.log, "a", encoding="utf-8") if a.log else None
    drop, ins, n = set(), [], 0

    for ln in open(a.ops, encoding="utf-8"):
        if not ln.strip():
            continue
        o = json.loads(ln)
        i, k = idx[o["start"]]
        p = lines[i].split(",", 9)
        c = cues["cues"][k]
        op = o["op"]
        if op == "retime":
            p[1], p[2] = o["s"], o["e"]
            c["start"], c["end"] = to_sec(o["s"]), to_sec(o["e"])
        elif op == "drop":
            drop.add((i, k))
        elif op == "set_text":
            p[9] = o["text"]
            c["text"] = c["en"] = c["text_en"] = o["text"]
        elif op == "set_speaker":
            p[4] = o["name"]
            c["name"] = c["speaker"] = o["name"]
        elif op == "insert_after":
            q = list(p)
            q[1], q[2], q[4], q[9] = o["s"], o["e"], o["name"], o["text"]
            c2 = dict(c)
            c2.update(start=to_sec(o["s"]), end=to_sec(o["e"]), name=o["name"],
                      speaker=o["name"], text=o["text"], en=o["text"],
                      text_en=o["text"])
            c2["text_ja"] = o.get("ja", c2.get("text_ja", ""))
            pos = (i - 1, k - 1) if o.get("before") else (i, k)
            ins.append((pos[0], pos[1], ",".join(q), c2))
            n += 1
            if log:
                log.write(ln.strip() + "\n")
            continue
        else:
            raise SystemExit("unknown op: %r" % op)
        lines[i] = ",".join(p)
        n += 1
        if log:
            log.write(ln.strip() + "\n")

    for i, k in sorted(drop, reverse=True):
        del lines[i]
        del cues["cues"][k]
    for i, k, l2, c2 in sorted(ins, key=lambda x: -x[0]):
        lines.insert(i + 1, l2)
        cues["cues"].insert(k + 1, c2)

    open(a.ass, "w", encoding="utf-8").write("\n".join(lines))
    json.dump(cues, open(a.cues, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("applied", n, "dropped", len(drop))


if __name__ == "__main__":
    main()
