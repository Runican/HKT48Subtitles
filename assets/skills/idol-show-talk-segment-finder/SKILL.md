---
name: Idol-show talk segment finder
description: >-
  Use when finding talk/MC/sketch time ranges in a long idol performance audio
  without human segment timestamps, or when iterating a blind talk-map against a
  known grade key. Default method: stage template + energy + short VAD + sparse
  lyric probes (not energy-only, not full-show Whisper).
---
# Idol-show talk segment finder

Find **talk / MC / sketch** time ranges in a long performance recording. Do **not** translate here — only propose segment bounds for a later JA→EN ASS job.

## Goal

From full-show audio (+ stage template when known), output a candidate segment list:

```json
{
  "segments": [
    {"type": "talk|sketch|photo|intro|mc|post_song_sketch|outro|encore_call|end_greetings|unknown", "start": 0.0, "end": 0.0, "confidence": "high|med|low", "translate": true, "note": ""}
  ],
  "method": "short description of heuristics used",
  "template_id": "hkt48-himawarigumi-4th-saka-agari|null",
  "limitations": []
}
```

Times are seconds on the **original** timeline. Set `translate: false` for slots the user skips (encore call, end greetings) even if detected.

## Hard limits (stay performant)

- Prefer the **v3 stack** below; never use full-show `large-v3` as a segment finder.
- Lyric ASR: `tiny` or `base` on **short crops only** (prefer total crop budget ≲15–20 min of audio).
- VAD/speech-density: **5–45s windows** after candidate song ends — not whole-show.
- One bounded experiment / ≤2 systematic tweaks vs a grade key unless the user asks for more.
- Stop and report **not converging** if main talk blocks stay poor after that.
- Never invent song lyrics or translate in this skill.
- Do not treat one show’s IoU as production-ready; iterate across a few shows before trusting drafts.

## Stage templates

Formulaic stages live under:

`assets/hkt48/stage_templates/`

Example: `himawarigumi_4th_saka_agari.json` (domain-verifier-verified Saka Agari / 逆上がり).

A template holds ordered songs + talk slots, duration **ranges**, `translate` vs `skip`, and finder hints. Walk the timeline **in order**. After song block A, photo = **earliest** bursty hush — not the longest hush in the show.

## Default method (v3)

Proven stack on Himawarigumi 2025-05-11 grade (mean IoU ~0.86; reference only — re-grade on new shows):

1. **Template walk + energy** — load stage template; RMS ~0.5s hop; place song blocks and talk gaps in template order; detect `encore_call` / `end_greetings` as skip (`translate: false`).
2. **Short VAD** — webrtcvad (or similar) on 5–45s crops after song-like ends inside unit blocks to catch thin `post_song_sketch`; refine MC edges vs song beds / applause.
2b. **Optional sketch gate** — before `post_song_sketch` gets `translate: true`, require short VAD/speech-density evidence of talk.
3. **Sparse lyric probes** — faster-whisper tiny/base on energy-guided ~20–30s crops near soft boundaries (unit-block→MC, encore songs). Fuzzy-match ASR to public lyric/title fingerprints from the setlist; confidence floor; ignore prompt-hallucinated title dumps.
4. **Landmark refine** — use song hits to cut talk spans (e.g. mc1 ends before next group song; mc3 between encore pair and finale announce). Keep strong template/VAD slots unless a landmark clearly moves a boundary.
5. Emit candidates + `song_landmarks.json` when probes ran; confidence + limitations.

Paired MCs (e.g. user `mc2` = two cast-group talk halves): one merged span or two adjacent halves both OK vs grade.

### Fallback (no template)

Energy/silence discovery only (v1). Expect more false islands; do not promote to ASS cuts without review.

### Energy-only (discouraged)

Use only for scaffolding experiments. Known weak on thin post-song talk and MC edges.

## Blind vs graded

**Blind:** do not read human `show.json` / segment timestamps until candidates are written. Templates, public setlists, and lyric fingerprints are allowed.

**Graded (optional):** after blind write, score translate segments (best IoU, Δstart/Δend), short misses (<30s), false translate FPs, skip-slot discipline. Write `REPORT_*.md`. Compare to prior passes on the same show when iterating method.

## Outputs

Under `work/<slug>/segment_finder/`:

- `candidates_*.json` — blind before grade peek
- `song_landmarks.json` — when lyric probes ran
- `score_vs_grade_*.json` + `REPORT_*.md` — if graded
- Stage template copy; reuse `rms_*.json` when present


## Lesson — Ramune / birthday LOD (2025-05-10 grade, mean IoU ~0.95 after 1 tweak)

- **No opening sketch** on Kenkyuusei「ラムネの飲み方」— do not invent a Saka-Agari-style コント slot.
- **Photo** often starts at **post–block-A settle / greeting**, not only the deepest hush core; end at **自己紹介 handoff** (photo-sale → intros). Prefer ASR handoff cue when hush is short.
- **Birthday expands MC4** (user `mc3_birthday`): keep a **late open talk slot** with high `dur_s.max`. Cut at **title-announce** (“最後の曲” / “タイトル”) or first **M16 lyric** — title may be **mid-energy** so RMS alone can swallow it into birthday talk.
- Detect `encore_call` (deep post–握手の愛 hush) and `end_greetings` with `translate: false`; outro is **late closing speech**, not a mid-greetings energy island.


- **Optional `post_song_sketch` → ASS:** emit `translate:true` only if a short **speech-density / VAD** gate shows clear talk (not song bed / cheer mush). Otherwise `translate:false` or omit from the JA→EN cut list. Blind Ramune 2026-09-29: optional sketch FP vs gold with no human counterpart.

## Lesson — spoken bits inside song beds

- Some setlist songs embed a short spoken letter, radio-name reading, or end-of-song sketch in the song bed. When birthday or letter context applies, probe those songs for spoken prose; do not assume the bed is lyric-only.

## Do not

- Replace a human segment map with finder candidates for production ASS without review
- Load these heuristics into the JA→EN subtitle skill — keep this skill separate
- Run unbounded overnight ASR loops or full-show large-v3 for segment finding
- Use longest-hush as photo when a template says earliest post–block-A hush
- Translate encore_call or end_greetings unless the user explicitly asks
