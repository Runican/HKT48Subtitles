#!/usr/bin/env python3
"""Add one user-reviewed show to the voice bank as a NEW append-only file pair: bank/<show_id>_review.{npz,json}.

Inputs (config JSON; paths relative to the config file):
  show_id, title, timeline (free text: which audio timeline the times are on)
  audio            16 kHz wav of the show (same timeline as the review)
  cache            make_hints.py embedding cache (show_emb.json, keys "H:MM:SS.cc|H:MM:SS.cc")
  review_jsonl     reviewer speaker decisions: {"action":"confirm"|"fix","cue_start","cue_end","speaker"} or
                   {"action":"split","parts":[{"start","end","speaker"},...]}
  edit_ops_jsonl   optional; {"op":"retime","start":<old start>,"new_start","new_end"} moves a reviewed cue
  hints_tsv        make_hints.py speaker_hints_review_fullname.tsv (shipped hint + confidence per cue start)
  named_cues_tsv   make_hints.py named_cues_loo.tsv (pre-hint ASS-named cues; intro rows are used)
  segments         [[name,start_s,end_s],...] or a path to such a JSON file
  rebuilt_spans    optional [[label,start_s,end_s],...]: spans re-cut after hints; their rows are always re-embedded
  published_ass    optional, informational

Clean rule (only clean rows enter the bank):
  person label (not All/Crowd/Multiple/Member/Unknown/Host), segment != outro, >= 0.7 s,
  no different-speaker neighbour within 0.3 s, and either an intro line (user label, or pre-hint ASS-named intro
  cue when no user label overlaps it) or a user-reviewed line whose shipped hint was high and equal to the
  final speaker and >= 1.5 s.
Never rewrites an existing bank file; updates bank/index.json (adds one entry, recomputes totals).
"""
import argparse, json, sys
from collections import Counter
from pathlib import Path
import io
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diar_common import AudioEmbedder, DEFAULT_MODEL, NONPERSON, sha256, t2s  # noqa: E402

EMBEDDER = "wespeaker/voxceleb_resnet293_LM (onnx, sha256 dbb1ccc7754caff552ebc46347a51aaee2669bb24efc740e665d1a1133d20e98)"
CLEAN_RULE = ("clean = person label, >=0.7 s, not outro, no different-speaker neighbour within 0.3 s, and either an intro line "
              "(user-labelled or pre-hint ASS-named; user label wins) or a user-confirmed line whose shipped hint was high and correct and >=1.5 s.")


def build_rows(C, base, model):
    rp = lambda k: (base / C[k]) if C.get(k) else None
    segs = C["segments"]
    if isinstance(segs, str): segs = json.load(open(base / segs))
    seg = lambda a: next((n for n, x, y in segs if x <= a < y), "other")
    rebuilt = [(l, float(x), float(y)) for l, x, y in C.get("rebuilt_spans", [])]
    span_of = lambda a: next((l for l, x, y in rebuilt if x <= a < y), None)
    hint = {}
    for i, l in enumerate(open(rp("hints_tsv"), encoding="utf-8")):
        if i == 0: continue
        f = l.rstrip("\n").split("\t"); hint[f[0]] = (f[5], f[6])
    ret = {}
    if C.get("edit_ops_jsonl"):
        for l in open(rp("edit_ops_jsonl"), encoding="utf-8"):
            d = json.loads(l)
            if d.get("op") == "retime": ret[d["start"]] = (d["new_start"], d["new_end"])
    rev = {}
    for l in open(rp("review_jsonl"), encoding="utf-8"):
        d = json.loads(l)
        if d.get("action") in ("confirm", "fix"): rev[(d["cue_start"], d["cue_end"], d["action"], d["speaker"])] = d
        elif d.get("action") == "split":
            for q in d["parts"]: rev[(q["start"], q["end"], "split", q["speaker"])] = q
    lines = []
    for (s, e, act, spk), d in rev.items():
        a, b = t2s(s), t2s(e)
        if act != "split" and s in ret: a, b = t2s(ret[s][0]), t2s(ret[s][1])
        h, c = hint.get(s, ("", ""))
        lines.append(dict(start=round(a, 2), end=round(b, 2), seg=seg(a), ass_label=spk, label=spk, src="user_" + act, hint=h, conf=c, user=act,
                          key=s + "|" + e, ret=(s in ret), span=span_of(a)))
    for i, l in enumerate(open(rp("named_cues_tsv"), encoding="utf-8")):
        if i == 0: continue
        f = l.rstrip("\n").split("\t")
        if f[2] != "intro": continue
        a, b = t2s(f[0]), t2s(f[1])
        if any(abs(x["start"] - a) < 0.05 or (x["start"] < b and a < x["end"]) for x in lines if x["user"]): continue  # user label wins
        lines.append(dict(start=a, end=b, seg="intro", ass_label=f[3], label=f[3], src="ass_named", hint=f[4], conf=f[8], user=None,
                          key=f[0] + "|" + f[1], ret=False, span=None))
    lines.sort(key=lambda r: r["start"])

    def why(i, r):
        if r["label"] in NONPERSON: return "nonperson"
        if r["seg"] == "outro": return "outro"
        if r["end"] - r["start"] < 0.7: return "short"
        for j in (i - 1, i + 1):
            if 0 <= j < len(lines):
                o = lines[j]
                if o["label"] != r["label"] and o["start"] - 0.3 < r["end"] and r["start"] < o["end"] + 0.3: return "adjacent_other"
        if not (r["seg"] == "intro" or (r["conf"] == "high" and r["hint"] == r["label"] and r["end"] - r["start"] >= 1.5)): return "not_clean_class"
        return None

    mc = json.load(open(rp("cache"))) if C.get("cache") else {}
    emb = AudioEmbedder(rp("audio"), model) if C.get("audio") else None
    rows, drop = [], Counter()
    for i, r in enumerate(lines):
        w = why(i, r)
        if w: drop[w] += 1; continue
        force_new = bool(r["span"]) or r["ret"] or r["user"] == "split"   # cache is on the pre-edit cue times
        e = None if force_new else mc.get(r["key"]); r["emb_src"] = "cache"
        if e is None:
            if emb is None: raise SystemExit(f"need audio to embed {r['key']}")
            e = emb(r["start"], r["end"]); r["emb_src"] = "new"
        v = np.asarray(e, np.float32); r["emb"] = v / np.linalg.norm(v)
        r["cat"] = "clean_intro" if r["seg"] == "intro" else "clean_hc"
        rows.append(r)
    return rows, drop, len(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config"); ap.add_argument("--bank", default=str(Path(__file__).resolve().parent.parent / "bank"))
    ap.add_argument("--model", default=str(DEFAULT_MODEL)); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfgp = Path(a.config).resolve(); C = json.load(open(cfgp, encoding="utf-8")); C = dict(C, **C.get("bank_add", {}))
    BANK = Path(a.bank); sid = f"{C['show_id']}_review"
    npz, js = BANK / f"{sid}.npz", BANK / f"{sid}.json"
    if (npz.exists() or js.exists()) and not a.dry_run:
        raise SystemExit(f"{sid} already in the bank - bank files are never rewritten; use a new show_id/batch name")
    rows, drop, n_lines = build_rows(C, cfgp.parent, a.model)
    E = np.stack([r["emb"] for r in rows]).astype(np.float32)
    meta = []
    for r in rows:
        m = dict(row=len(meta), speaker=r["label"], start=float(r["start"]), end=float(r["end"]), show=C["show_id"], segment=r["seg"] or "other",
                 clean=True, clean_reason=r["cat"], label_source=r["src"])
        if r.get("hint"): m["shipped_hint"] = r["hint"]
        if r.get("conf"): m["shipped_conf"] = r["conf"]
        if r.get("span"): m["rebuilt_span"] = r["span"]
        m["emb_src"] = r["emb_src"]
        meta.append(m)
    doc = dict(format="hkt48-voice-bank/1", bank_file=sid, show=C["show_id"], show_title=C.get("title", ""), published_ass=C.get("published_ass", ""),
               batch="review", batch_description="Per-show bank add after user review (bank_add.py rule): clean rows only.", clean_rule=CLEAN_RULE,
               timeline=C.get("timeline", ""), embedder=EMBEDDER, embedding_dim=int(E.shape[1]), n_rows=len(meta), l2_normalised=True,
               source="scripts/bank_add.py", n_review_lines=n_lines, dropped=dict(drop),
               per_member=dict(sorted(Counter(m["speaker"] for m in meta).items())), rows=meta)
    print(json.dumps(dict(id=sid, n_review_lines=n_lines, n_clean=len(meta), dropped=dict(drop), per_member=doc["per_member"],
                          emb_new=sum(m["emb_src"] == "new" for m in meta)), ensure_ascii=False, indent=1))
    if a.dry_run: return
    b = io.BytesIO(); np.savez(b, emb=E); npz.write_bytes(b.getvalue())
    js.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ip = BANK / "index.json"; idx = json.load(open(ip, encoding="utf-8"))
    idx["files"].append(dict(id=sid, show=C["show_id"], batch="review", rows=len(meta), npz=npz.name, json=js.name,
                             sha256_npz=sha256(npz), sha256_json=sha256(js), per_member=doc["per_member"]))
    tot = Counter()
    for f in idx["files"]: tot.update(f["per_member"])
    idx["total_rows"] = sum(f["rows"] for f in idx["files"]); idx["per_member_total"] = dict(sorted(tot.items()))
    idx["per_member_files"] = {m: sorted({f["id"] for f in idx["files"] if m in f["per_member"]}) for m in sorted(tot)}
    ip.write_text(json.dumps(idx, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("added", sid)


if __name__ == "__main__":
    main()
