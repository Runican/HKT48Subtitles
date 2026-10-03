#!/usr/bin/env python3
"""Pass G machine checks + Pass H copy-forward / topic-paste gate.

Hard fails (photo-regression gates):
- empty EN (after resolving text|en|text_en)
- unintended overlaps (unless overlap_ok on both)
- copy-forward / topic-paste
- over-max duration
- optional: ASS empty Text (--ass)
- optional: glossary reject forms on EN (--glossary)
- optional: speech holes vs silence map (--silence): gap>=min-hole with little silence → FAIL
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

RITUAL_EN = {
    "thank you!", "thank you", "thank you, thank you!", "yay!", "yay", "okay!", "okay", "ok!", "ok",
    "please take care of me today!", "please take care of me!",
    "please take care of us!", "please take care of us today!",
    "please look after us!", "please look after us today!",
    "happy birthday!", "happy birthday", "happy birthday to you!", "happy birthday to you",
    "congrats!", "congratulations!", "congratulations.",
    "se-no!", "se-no", "ready — se-no!", "here we go — se-no!",
}
RITUAL_JA_HINTS = ("ありがとう", "よろしく", "はい", "わー", "イェー", "おー", "せーの")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def cue_en(c: dict) -> str:
    """Canonical on-screen EN. Prefer text, then en, then text_en."""
    for k in ("text", "en", "text_en"):
        v = c.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def cue_ja(c: dict) -> str:
    for k in ("text_ja", "ja"):
        v = c.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def is_ritual(en: str, ja: str, cue: dict | None = None) -> bool:
    """True for known call-outs, or cue.ritual_ok (this-job intentional repeats)."""
    if cue and cue.get("ritual_ok"):
        return True
    e = norm(en)
    if e not in RITUAL_EN and e.rstrip(".") not in RITUAL_EN:
        return False
    j = ja or ""
    return (not j.strip()) or any(h in j for h in RITUAL_JA_HINTS) or len(j) <= 8


def load_silence_intervals(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        out = []
        for x in data:
            if isinstance(x, (list, tuple)) and len(x) >= 2:
                out.append((float(x[0]), float(x[1])))
            elif isinstance(x, dict):
                out.append((float(x["start"]), float(x["end"])))
        return out
    if isinstance(data, dict):
        for key in ("silence", "intervals", "bands"):
            if key in data:
                return load_silence_intervals_from(data[key])
    return []


def load_silence_intervals_from(data):
    out = []
    for x in data:
        if isinstance(x, (list, tuple)) and len(x) >= 2:
            out.append((float(x[0]), float(x[1])))
        elif isinstance(x, dict):
            out.append((float(x["start"]), float(x["end"])))
    return out


def silence_coverage(a: float, b: float, bands) -> float:
    """Fraction of [a,b] covered by silence bands."""
    if b <= a:
        return 1.0
    cov = 0.0
    for s, e in bands:
        lo, hi = max(a, s), min(b, e)
        if hi > lo:
            cov += hi - lo
    return min(1.0, cov / (b - a))


def check_ass_empty(path: Path):
    bad = []
    for i, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not ln.startswith("Dialogue:"):
            continue
        parts = ln.split(",", 9)
        if len(parts) < 10 or not parts[9].strip():
            bad.append((i, ln[:80]))
    return bad


def load_glossary_entries(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("entries", data if isinstance(data, list) else [])


def _word_hit(hay: str, needle: str) -> bool:
    """Whole-token match; avoids reh⊂rehearsal. Case-sensitive if needle has uppercase."""
    if not needle or not hay:
        return False
    flags = 0 if any(c.isupper() for c in needle) else re.IGNORECASE
    # Escape; allow flexible spaces inside multiword needles
    pat = r"\b" + re.escape(needle).replace(r"\ ", r"\s+") + r"\b"
    try:
        return re.search(pat, hay, flags) is not None
    except re.error:
        return needle in hay


def glossary_reject_hits(cues, entries):
    """JA-anchored: only apply an entry's reject/avoid when cue JA hits that entry's ja forms.
    Prevents global false positives (heart in English, reh in rehearsal, Kokoha on Fujino lines).
    """
    hits = []
    prepared = []
    for e in entries:
        jas = [j for j in (e.get("ja") or []) if isinstance(j, str) and j.strip()]
        rejects = [r.strip() for r in (e.get("reject") or []) + (e.get("avoid") or []) if isinstance(r, str) and r.strip()]
        if not jas or not rejects:
            continue
        prepared.append((e.get("id"), jas, rejects, e.get("en") or ""))
    for idx, c in enumerate(cues):
        ja = cue_ja(c)
        en = cue_en(c)
        if not ja or not en:
            continue
        for eid, jas, rejects, allowed_en in prepared:
            if not any(j in ja for j in jas):
                continue
            for r in rejects:
                if len(r) <= 1:
                    continue
                if not _word_hit(en, r):
                    continue
                # If EN already uses this entry's allowed en form as a whole token, skip
                # short reject noise when the locked form is present (e.g. rehearsal vs reh).
                if allowed_en and _word_hit(en, allowed_en.split("/")[0].strip()):
                    # still flag if reject is a multiword wrong identity (Eguchi Kokoha)
                    if " " not in r and len(r) <= 6 and r.lower() in (allowed_en or "").lower():
                        continue
                    if r.lower() == "reh" and "rehearsal" in en.lower():
                        continue
                hits.append((idx, eid, r, en[:50]))
                break
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cues")
    ap.add_argument("--dur", type=float, default=None,
                    help="Segment duration seconds (reads meta.json beside cues if omitted)")
    ap.add_argument("--max-dur", type=float, default=6.5)
    ap.add_argument("--cps", type=float, default=21.0)
    ap.add_argument("--strict-copyforward", action="store_true", default=True)
    ap.add_argument("--ass", type=Path, default=None, help="Also fail on empty ASS Dialogue Text")
    ap.add_argument("--glossary", type=Path, default=None, help="Fail if EN contains glossary reject/avoid")
    ap.add_argument("--silence", type=Path, default=None,
                    help="silence.json — fail large inter-cue gaps that are mostly NOT silence")
    ap.add_argument("--min-hole", type=float, default=8.0,
                    help="Min inter-cue gap (s) to treat as speech-hole candidate")
    ap.add_argument("--silence-cover", type=float, default=0.55,
                    help="Gap must be >= this fraction silence to allow empty (else FAIL)")
    args = ap.parse_args()

    cues_path = Path(args.cues)
    data = json.loads(cues_path.read_text(encoding="utf-8"))
    cues = data if isinstance(data, list) else data.get("cues", [])
    n = len(cues)

    dur = args.dur
    if dur is None:
        meta = cues_path.parent / "meta.json"
        if meta.exists():
            m = json.loads(meta.read_text(encoding="utf-8"))
            dur = float(m.get("dur") or (m.get("end", 0) - m.get("start", 0)) or 0) or None
        if dur is None and isinstance(data, dict) and data.get("dur"):
            dur = float(data["dur"])
        if dur is None:
            dur = 300.0
            print("WARN dur defaulted to 300 — pass --dur or meta.json")

    density = n / (dur / 60.0) if dur else 0
    expected_min = dur / 8.0

    empty_en, overs, overlaps, fast = [], [], [], []
    for i, c in enumerate(cues):
        en = cue_en(c)
        if not en.strip():
            empty_en.append((i, round(c.get("start", 0), 2), round(c.get("end", 0), 2), cue_ja(c)[:40]))
        d = float(c["end"]) - float(c["start"])
        if d > args.max_dur + 0.01:
            overs.append((i, d, en[:40]))
        cps = len(en) / d if d > 0 else 999
        if en and cps > args.cps + 2:
            fast.append((i, round(cps, 1), en[:40]))
        if i > 0:
            p = cues[i - 1]
            if (not c.get("overlap_ok") or not p.get("overlap_ok")) and c["start"] < p["end"] - 0.01:
                overlaps.append((i - 1, i, round(p["end"] - c["start"], 3)))

    # Copy-forward / topic paste
    copy_groups = []
    i = 0
    while i < n:
        j = i + 1
        en_i = cue_en(cues[i])
        while j < n and cue_en(cues[j]) == en_i and en_i.strip():
            j += 1
        if j - i >= 3:
            jas = {cue_ja(cues[k]) for k in range(i, j)}
            if not all(is_ritual(en_i, cue_ja(cues[k]), cues[k]) for k in range(i, j)):
                if len(jas) >= 2 or not is_ritual(en_i, next(iter(jas)) if jas else "", cues[i]):
                    copy_groups.append(("consecutive", i, j - 1, en_i[:60], len(jas)))
        i = j

    by_en = defaultdict(list)
    for idx, c in enumerate(cues):
        en = cue_en(c)
        if en.strip():
            by_en[en].append(idx)
    for en, idxs in by_en.items():
        if len(idxs) < 3:
            continue
        jas = [cue_ja(cues[k]) for k in idxs]
        if len(set(jas)) < 2:
            continue
        if all(is_ritual(en, cue_ja(cues[k]), cues[k]) for k in idxs):
            continue
        copy_groups.append(("identical_en_diff_ja", idxs[0], idxs[-1], en[:60], len(set(jas))))

    topic_only = []
    for idx, c in enumerate(cues):
        en = cue_en(c).strip()
        ja = cue_ja(c).strip()
        if not en or not ja:
            continue
        words = en.split()
        if len(words) <= 3 and len(ja) >= 15 and norm(en) not in norm(ja) and not is_ritual(en, ja, c):
            if len(by_en.get(en, [])) >= 2:
                topic_only.append((idx, en[:40], ja[:40]))

    speech_holes = []
    if args.silence and args.silence.exists():
        bands = load_silence_intervals(args.silence)
        # leading / trailing / inter-cue
        edges = []
        if cues:
            edges.append((0.0, float(cues[0]["start"]), "lead"))
            for i in range(len(cues) - 1):
                edges.append((float(cues[i]["end"]), float(cues[i + 1]["start"]), f"gap@{i}"))
            edges.append((float(cues[-1]["end"]), float(dur), "trail"))
        for a, b, tag in edges:
            gap = b - a
            if gap < args.min_hole:
                continue
            cov = silence_coverage(a, b, bands)
            if cov < args.silence_cover:
                speech_holes.append((tag, round(a, 2), round(b, 2), round(gap, 1), round(cov, 2)))

    ass_empty = check_ass_empty(args.ass) if args.ass else []

    reject_hits = []
    if args.glossary and args.glossary.exists():
        reject_hits = glossary_reject_hits(cues, load_glossary_entries(args.glossary))

    # Internal markup must never ship on-screen (e.g. [song], [songs])
    markup_re = re.compile(r"\[songs?\]", re.I)
    markup_tags = []
    for idx, c in enumerate(cues):
        en = cue_en(c)
        if markup_re.search(en):
            markup_tags.append((idx, round(c.get("start", 0), 2), en[:60]))

    print(f"cues={n} dur={dur} density={density:.2f}/min expected_min~{expected_min:.1f}")
    print(f"empty_en={len(empty_en)} over_max_dur={len(overs)} overlap_flags={len(overlaps)} high_cps={len(fast)}")
    print(f"copyforward_groups={len(copy_groups)} topic_only_flags={len(topic_only)}")
    print(f"speech_holes={len(speech_holes)} ass_empty={len(ass_empty)} glossary_rejects={len(reject_hits)} markup_tags={len(markup_tags)}")
    for x in empty_en[:12]:
        print(" EMPTY_EN", x)
    for x in overs[:8]:
        print(" OVER", x)
    for x in overlaps[:8]:
        print(" OVERLAP", x)
    for x in fast[:8]:
        print(" CPS", x)
    for x in copy_groups[:20]:
        print(" COPY", x)
    for x in topic_only[:12]:
        print(" TOPIC", x)
    for x in speech_holes[:20]:
        print(" SPEECH_HOLE", x)
    for x in ass_empty[:12]:
        print(" ASS_EMPTY", x)
    for x in reject_hits[:12]:
        print(" REJECT", x)  # idx, entry_id, reject, en
    for x in markup_tags[:12]:
        print(" MARKUP", x)

    reasons = []
    if empty_en:
        reasons.append("empty_en")
    if overs:
        reasons.append("over_max_dur")
    if overlaps:
        reasons.append("overlap")
    if args.strict_copyforward and copy_groups:
        reasons.append("copyforward_or_topic_paste")
    if speech_holes:
        reasons.append("speech_hole_vs_silence")
    if ass_empty:
        reasons.append("ass_empty_text")
    if reject_hits:
        reasons.append("glossary_reject_on_en")
    if markup_tags:
        reasons.append("internal_markup_in_en")
    # density soft for hush segments: only fail if empty_en already covered; keep old half-min as soft warn
    if n < expected_min * 0.5 and not speech_holes:
        print(f"WARN low_density cues={n} expected_min~{expected_min:.1f}")

    ok = not reasons
    print("PASS" if ok else "FAIL")
    if reasons:
        print("FAIL_REASON=" + ",".join(reasons))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
