#!/usr/bin/env python3
"""Per-cue speaker hints for one show (WeSpeaker ResNet293-LM, nearest same-show seed centroid).

Config-driven (see ../examples/*.json). For every ASS cue tagged `Member` (or `Crowd`, always unsure) the script
proposes a cast member with a confidence tier, using as seeds the cues the pre-hint ASS already names
(self-intros etc.). The voice bank is a fallback only for cast members with no same-show seed.

Tiers (defaults; override under "params" in the config):
  high   = top cosine >= 0.50 and margin to runner-up >= 0.10, and the member has >=3 seeds in each of >=2 segments
           (otherwise high is capped to medium)
  medium = top cosine >= 0.40 and margin >= 0.05
  unsure = everything else, cues < 0.7 s, and every Crowd cue
  bank fallback (unseeded cast only, >=15 clean bank lines, target show excluded): medium at most, and only if cos >= 0.60

Self-check: leave-one-out over the named cues (exclude the cue's own +/-10 s) -> stats.json.
The ASS is read only; its sha256+mtime are checked at start and end and nothing is written if it changed.

Outputs in --out (default: <config dir>/diarization):
  diar_hints.json, speaker_hints_review_fullname.tsv (10 columns), speaker_hints_full.tsv,
  named_cues_loo.tsv, named_cue_disagreements_hm.tsv, roster.json, stats.json
"""
import argparse, json, sys, time
from pathlib import Path
from collections import Counter
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diar_common import AudioEmbedder, DEFAULT_MODEL, fhash, load_bank, nz, parse_ass, t2s, NONPERSON as _NP  # noqa: E402

DEFAULTS = dict(min_dur=0.7, min_seeds_per_seg=3, high=[0.50, 0.10], medium=[0.40, 0.05], loo_exclude_s=10.0,
                bank_min_lines=15, bank_min_cos=0.60, bank_allow_unknown_clean=True, bank_exclude_outro=True)
NONPERSON = {"All", "Crowd", "Multiple", "Member", "Unknown"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config"); ap.add_argument("--out"); ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--bank", help="bank dir (default: ../bank next to scripts/)")
    a = ap.parse_args()
    cfgp = Path(a.config).resolve(); C = json.load(open(cfgp, encoding="utf-8")); base = cfgp.parent
    P = dict(DEFAULTS, **C.get("params", {}))
    rp = lambda k: (base / C[k]) if C.get(k) else None
    ASS, WAV, CACHEF = rp("ass"), rp("audio"), rp("cache")
    OUT = Path(a.out) if a.out else (rp("out_dir") or base / "diarization"); OUT.mkdir(parents=True, exist_ok=True)
    BANKDIR = Path(a.bank) if a.bank else (rp("bank_dir") or Path(__file__).resolve().parent.parent / "bank")
    CAST = list(C["cast"]); NICK = dict(C.get("nicknames", {})); NICK.update({n: n for n in CAST})
    assert len(set(CAST)) == len(CAST), "duplicate cast names"
    SR_MIN, MINSEG = P["min_dur"], P["min_seeds_per_seg"]; HIGH, MED, EXC = tuple(P["high"]), tuple(P["medium"]), P["loo_exclude_s"]
    UNKNOWN_SPOTS = [(lab, t2s(x) if isinstance(x, str) else x, t2s(y) if isinstance(y, str) else y) for lab, x, y in C.get("unknown_spots", [])]
    EXCL = [str(s) for s in C.get("exclude_bank_shows", [C.get("show_id", "")]) if s]

    H0 = fhash(ASS); print("ASS start", H0, time.strftime("%H:%M:%S"), flush=True)
    txt, cues = parse_ass(ASS, NICK)
    if not P.get("allow_override_tags", False):
        assert "{" not in txt, "override tags present"
    for k in ("diar", "[hint", "hint:"):
        assert k not in txt.lower().replace("the hint is:", ""), f"applied-hint marker present: {k}"
    if C.get("expected_cues") is not None:
        assert len(cues) == C["expected_cues"], (len(cues), C["expected_cues"])
    # segments: ASS '; =====' markers win; else config "segments" [[name,start,end],...]; else "intro" [start,end]
    if all(c["seg"] is None for c in cues):
        segs = [(n, t2s(x) if isinstance(x, str) else x, t2s(y) if isinstance(y, str) else y) for n, x, y in C.get("segments", [])]
        if not segs and C.get("intro"):
            x, y = C["intro"]; segs = [("intro", t2s(x) if isinstance(x, str) else x, t2s(y) if isinstance(y, str) else y)]
        for c in cues:
            c["seg"] = next((n for n, x, y in segs if x <= c["start"] < y), "other")
    unk_tags = sorted({c["tag"] for c in cues} - set(CAST) - NONPERSON)
    assert not unk_tags, f"ASS speaker tags not in cast/nicknames: {unk_tags}"
    # Japanese text (optional): stitched cue JSON {"cues":[{"start":..,"text_ja":..}]}
    if C.get("ja_cues"):
        st = json.load(open(rp("ja_cues"), encoding="utf-8"))["cues"]; SS = np.array([s["start"] for s in st])
        for c in cues:
            i = int(np.argmin(abs(SS - c["start"]))); c["ja"] = (st[i].get("text_ja") or "") if abs(SS[i] - c["start"]) < 0.6 else ""
    else:
        for c in cues: c["ja"] = ""

    # ---- embeddings (cache keyed "start|end" as written in the ASS) ----
    emb_audio = AudioEmbedder(WAV, a.model) if WAV else None
    mc = json.load(open(CACHEF)) if (CACHEF and CACHEF.exists()) else {}; n = 0
    for c in cues:
        if c["tag"] in ("All",): continue
        k = c["start_str"] + "|" + c["end_str"]
        if k not in mc:
            if emb_audio is None: raise SystemExit(f"cache miss {k} and no audio configured")
            e = emb_audio(c["start"], c["end"]); mc[k] = None if e is None else [float(v) for v in e]; n += 1
            if CACHEF and n % 200 == 0: json.dump(mc, open(CACHEF, "w")); print("embedded", n, flush=True)
    if CACHEF and n: json.dump(mc, open(CACHEF, "w"))
    print("embedded total", n, flush=True)
    for c in cues:
        e = mc.get(c["start_str"] + "|" + c["end_str"]); c["emb"] = None if e is None else nz(e)

    names = CAST
    named = [c for c in cues if c["tag"] in CAST and c["emb"] is not None and c["dur"] >= SR_MIN]
    NE = np.array([c["emb"] for c in named]); NI = np.array([names.index(c["tag"]) for c in named])
    NSG = np.array([c["seg"] for c in named]); NT = np.array([c["start"] for c in named])
    seed_info = {nm: {s: int(v) for s, v in Counter(NSG[NI == k]).items()} for k, nm in enumerate(names)}
    seeded = [nm for nm in names if sum(seed_info[nm].values()) > 0]; unseeded = [nm for nm in names if nm not in seeded]
    cap = {nm for nm in names if sum(v >= MINSEG for v in seed_info[nm].values()) < 2}

    def protos(mask, drop=()):
        Pp = {}
        for k, nm in enumerate(names):
            if nm in drop: continue
            E = NE[mask & (NI == k)]
            if len(E): m = E.mean(0); Pp[nm] = m / np.linalg.norm(m)
        return Pp

    def score(e, Pp):
        sc = sorted(((float(e @ p), nm) for nm, p in Pp.items()), reverse=True)
        return sc[0][1], sc[0][0], sc[0][0] - sc[1][0], sc[1][1]

    def band_of(s, m):
        if s >= HIGH[0] and m >= HIGH[1]: return "high"
        if s >= MED[0] and m >= MED[1]: return "medium"
        return "unsure"

    def capb(b, nm): return "medium" if (b == "high" and nm in cap) else b

    def run(kind):
        R = []
        for i, c in enumerate(named):
            m = np.abs(NT - c["start"]) > EXC
            if kind == "xseg":
                if len(set(NSG[NI == NI[i]])) < 2: continue
                m &= ~((NI == NI[i]) & (NSG == NSG[i]))
            Pp = protos(m)
            if c["tag"] in Pp and len(Pp) > 1:
                nm, s, mg, ru = score(c["emb"], Pp); R.append((c, nm, s, mg, ru, capb(band_of(s, mg), nm)))
        return R

    def acc(R, f=lambda h: True):
        r = [h for h in R if f(h)]
        return dict(n=len(r), agree=sum(h[1] == h[0]["tag"] for h in r), acc=round(sum(h[1] == h[0]["tag"] for h in r) / len(r), 4) if r else None)

    EV = dict(seed_info=seed_info, capped=sorted(cap), unseeded=unseeded); LOO = {}
    for kind in ("w10", "xseg"):
        R = run(kind); LOO[kind] = R
        ev = dict(top1=acc(R), **{b: acc(R, lambda h, b=b: h[5] == b) for b in ("high", "medium", "unsure")})
        for lab, f in (("intro_only", lambda h: h[0]["seg"] == "intro"), ("non_intro", lambda h: h[0]["seg"] != "intro")):
            ev[lab] = dict(top1=acc(R, f), **{b: acc(R, lambda h, b=b, f=f: f(h) and h[5] == b) for b in ("high", "medium", "unsure")})
        ev["by_truth"] = {nm: acc(R, lambda h, nm=nm: h[0]["tag"] == nm) for nm in names}
        ev["by_pred_hm"] = {nm: dict(high=acc(R, lambda h, nm=nm: h[1] == nm and h[5] == "high"), medium=acc(R, lambda h, nm=nm: h[1] == nm and h[5] == "medium")) for nm in names}
        ev["confusions"] = dict(Counter(f"{h[0]['tag']}=>{h[1]}" for h in R if h[1] != h[0]["tag"]).most_common(30))
        ev["wrong_high_medium"] = [(h[0]["start_str"], h[0]["seg"], h[0]["tag"], h[1], round(h[2], 3), round(h[3], 3), h[5]) for h in R if h[5] != "unsure" and h[1] != h[0]["tag"]]
        EV[kind] = ev
    # leave-speaker-out: absorption risk if a member were unseeded / mis-seeded
    R2 = []
    for c in named:
        m = np.abs(NT - c["start"]) > EXC; Pp = protos(m, drop=(c["tag"],)); k, s, mg, ru = score(c["emb"], Pp); R2.append((c["tag"], k, capb(band_of(s, mg), k)))
    EV["leave_speaker_out"] = dict(n=len(R2), **{b: sum(h[2] == b for h in R2) for b in ("high", "medium", "unsure")},
        by_member={nm: dict(n=sum(h[0] == nm for h in R2), high=sum(h[0] == nm and h[2] == "high" for h in R2), medium=sum(h[0] == nm and h[2] == "medium" for h in R2),
            absorbed_by=dict(Counter(h[1] for h in R2 if h[0] == nm and h[2] != "unsure").most_common(3))) for nm in names})

    # ---- voice bank: fallback ONLY for cast members with no same-show seed ----
    XS = dict(used=False, unseeded=unseeded)
    if unseeded:
        bank = load_bank(BANKDIR); BANK = {}
        for nm in unseeded:
            E = [nz(b["emb"]) for b in bank if b["speaker"] == nm
                 and (b["clean"] is True or (P["bank_allow_unknown_clean"] and b["clean"] == "unknown"))
                 and not (P["bank_exclude_outro"] and b.get("segment") == "outro")
                 and not any(x in str(b["show"]) for x in EXCL)
                 and (b["end"] - b["start"]) >= SR_MIN]
            XS[nm] = len(E)
            if len(E) >= P["bank_min_lines"]: m = np.mean(E, 0); BANK[nm] = m / np.linalg.norm(m)
        XS["bank_members_used"] = sorted(BANK); XS["used"] = bool(BANK); XS["excluded_shows"] = EXCL
    else:
        BANK = {}; XS["reason"] = f"all {len(names)} lineup members have same-show seeds; bank not needed"
    EV["cross_show_check"] = XS

    # ---- shipped hints (Member rows; Crowd rows forced unsure) ----
    Pf = protos(np.ones(len(named), bool))
    def spot_of(c):
        for lab, x, y in UNKNOWN_SPOTS:
            if c["start"] < y and c["end"] > x: return lab
        return ""
    rows = []
    for c in cues:
        if c["tag"] not in ("Member", "Crowd") and not spot_of(c): continue
        r = dict(ass_tag=c["ass_tag"], start=c["start_str"], end=c["end_str"], dur=round(c["dur"], 2), segment=c["seg"], current_tag=c["tag"], text=c["text"], ja_text=c["ja"],
                 hint_name="unsure", confidence="unsure", top_candidate="", score="", margin="", runner_up="", seed_source="", note="", unknown_spot=spot_of(c))
        if c["emb"] is not None:
            k, s, mg, ru = score(c["emb"], {**Pf, **BANK}); r.update(top_candidate=k, score=round(s, 3), margin=round(mg, 3), runner_up=ru)
            bd = "unsure"
            if c["dur"] >= SR_MIN:
                bd = band_of(s, mg)
                if bd == "high" and k in cap: bd = "medium"; r["note"] = "capped_to_medium"
                if k in BANK:
                    bd = "medium" if (bd != "unsure" and s >= P["bank_min_cos"]) else "unsure"; r["note"] = "bank_fallback"
            if c["tag"] == "Crowd": bd = "unsure"; r["note"] = "crowd_forced_unsure"
            if c["tag"] in CAST: bd = "unsure"; r["note"] = (r["note"] + ";" if r["note"] else "") + "named_in_ass_not_hinted"
            if bd != "unsure": r.update(hint_name=k, confidence=bd, seed_source=("bank" if k in BANK else "A"))
        elif c["dur"] < 0.1: r["note"] = "too_short_to_embed"
        if r["unknown_spot"]: r["note"] = (r["note"] + ";" if r["note"] else "") + "UNKNOWN_SPOT " + r["unknown_spot"]
        rows.append(r)
    named_rows = [dict(start=h[0]["start_str"], end=h[0]["end_str"], segment=h[0]["seg"], ass_name=h[0]["tag"], top=h[1], score=round(h[2], 3), margin=round(h[3], 3),
                       runner_up=h[4], confidence=h[5], agree=h[1] == h[0]["tag"], ja_text=h[0]["ja"]) for h in LOO["w10"]]

    H1 = fhash(ASS); print("ASS end", H1, time.strftime("%H:%M:%S")); same = (H1 == H0)
    if not same:
        print("ASS CHANGED during run -> NOT writing outputs"); json.dump(dict(H0=H0, H1=H1), open(OUT / "ASS_CHANGED.json", "w")); sys.exit(2)

    def clean(v): return str(v).replace("\t", " ").replace("\n", " ")
    rc = ["start", "end", "segment", "current_tag", "ja_text", "hint_name", "confidence", "top_cos", "margin", "runner_up"]
    with open(OUT / "speaker_hints_review_fullname.tsv", "w", encoding="utf-8") as f:
        f.write("\t".join(rc) + "\n")
        for r in rows: q = dict(r, top_cos=r["score"]); f.write("\t".join(clean(q[k]) for k in rc) + "\n")
    json.dump(rows, open(OUT / "diar_hints.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    cols = ["start", "end", "dur", "segment", "current_tag", "text", "ja_text", "hint_name", "confidence", "top_candidate", "score", "margin", "runner_up", "seed_source", "note"]
    with open(OUT / "speaker_hints_full.tsv", "w", encoding="utf-8") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows: f.write("\t".join(clean(r[k]) for k in cols) + "\n")
    hdr = ["start", "end", "segment", "ass_name", "top", "score", "margin", "runner_up", "confidence", "agree", "ja_text"]
    for fn, flt in (("named_cues_loo.tsv", lambda r: True), ("named_cue_disagreements_hm.tsv", lambda r: r["confidence"] != "unsure" and not r["agree"])):
        with open(OUT / fn, "w", encoding="utf-8") as f:
            f.write("\t".join(hdr) + "\n")
            for r in named_rows:
                if flt(r): f.write("\t".join(clean(r[x]) for x in hdr) + "\n")
    segs = list(dict.fromkeys(c["seg"] for c in cues))
    by_span = {s: dict(rows=len([r for r in rows if r["segment"] == s]), **dict(Counter(r["confidence"] for r in rows if r["segment"] == s and r["current_tag"] == "Member"))) for s in segs}
    by_name = {nm: dict(high=sum(r["hint_name"] == nm and r["confidence"] == "high" for r in rows), medium=sum(r["hint_name"] == nm and r["confidence"] == "medium" for r in rows),
                        top_any=sum(r["top_candidate"] == nm for r in rows if r["current_tag"] == "Member")) for nm in names}
    roster = [dict(name=nm, seeds_total=sum(seed_info[nm].values()), seeds_by_span=seed_info[nm], spans_with_ge3=sum(v >= MINSEG for v in seed_info[nm].values()),
                   capped_to_medium=nm in cap, unseeded=nm in unseeded, ass_tag_count=sum(c["tag"] == nm for c in cues)) for nm in names]
    json.dump(roster, open(OUT / "roster.json", "w"), indent=1, ensure_ascii=False)
    stats = dict(show=C.get("title", C.get("show_id", "")), ass=Path(ASS).name, ass_sha256_start=H0[0], ass_mtime_ns_start=H0[1], ass_sha256_end=H1[0], ass_mtime_ns_end=H1[1], ass_unchanged=same,
                 params=P, n_cues=len(cues), tags=dict(Counter(c["tag"] for c in cues)), n_rows=len(rows), conf_totals=dict(Counter(r["confidence"] for r in rows)),
                 conf_member=dict(Counter(r["confidence"] for r in rows if r["current_tag"] == "Member")),
                 member_short_lt_0p7=sum(r["dur"] < 0.7 for r in rows if r["current_tag"] == "Member"), by_span_member=by_span, by_name=by_name,
                 unknown_spots=[{k: r[k] for k in ("start", "end", "current_tag", "ja_text", "text", "hint_name", "confidence", "top_candidate", "score", "margin", "runner_up", "unknown_spot")} for r in rows if r["unknown_spot"]],
                 eval=EV)
    json.dump(stats, open(OUT / "stats.json", "w"), indent=1, default=str, ensure_ascii=False)
    print(json.dumps(dict(totals=stats["conf_totals"], member=stats["conf_member"], by_span=by_span, capped=sorted(cap), unseeded=unseeded), indent=1))
    for k in ("w10", "xseg"): print(k, {x: EV[k][x] for x in ("top1", "high", "medium", "unsure")})
    print("ASS UNCHANGED")


if __name__ == "__main__":
    main()
