# Schema

## glossary.json entry
```json
{
  "id": "yasui-hina",
  "ja": ["安井妃奈", "ひな", "ひなたん"],
  "en": "Hina-tan",
  "en_full": "Yasui Hina",
  "type": "member|nick|catchphrase|show|jargon|lookalike-trap",
  "team": "KIV",
  "reject": ["Aoki Hinako", "青木ひなた"],
  "note": "…",
  "confidence": "locked|provisional|rejected",
  "locked": true,
  "updated": "ISO-8601",
  "updated_by": "verifier|subtitler|editor|human"
}
```


## What belongs in glossary.json

**In (thin durable canon):**
- Stable JA forms, EN defaults, `en_full`, rejects, team, and `locked` for members / nicks / teams / group
- Canonical catchphrase JA stacks + preferred EN + rejects; one short note on meaning / traps / standing scope
- Lookalike-trap patterns only (くる↔くれ, チーム慶応→KIV, Sae≠Saaya, etc.)
- Song / stage jargon that is not date-stamped
- Show type for stage *titles* (Saka Agari, Tenshi, Ramune, Mokugekisha) — not a single night’s cast

**Out (belongs in `sources/q-*.md` or dies with the job workdir):**
- Per-show / night casts (`show-cast-*` style dumps)
- Cue times, photo frame numbers, LOD anecdote timestamps
- Verify diaries / changelogs (“Applied q-…”, “Locked 2026-…”, agent names, `/workspace` paths)
- One-off ASR anecdotes for a single date
- Full night cast name lists inside member or catch notes

**Note field rules:**
- Member `note` = identity + standing traps — not a timeline of shows
- Catch `note` may state standing scope (e.g. “Saaya live 3rd beat is show-name; published 熊本だけん is alternate”) — never a single LOD anecdote with cue times
- Prefer `sources/` for verify writeups; keep glossary notes short

## cast_index.json member
```json
{
  "id": "yasui-hina",
  "en_full": "Yasui Hina",
  "ja": "安井妃奈",
  "nicks": ["Hina-tan", "ひな", "ひなたん"],
  "team": "KIV",
  "lookalikes": [{"name": "Aoki Hinako", "why": "ASR often hears 青木ひなた"}],
  "status": "active|graduate|research",
  "gen": "7th|null",
  "shows": ["Saka Agari"]
}
```

Per-show verify writeups live under `sources/` (e.g. `q-*.md`). Prefer leaving unresolved items as `provisional` in the glossary until a public source confirms them. Do not park night casts, cue times, or verify diaries in `glossary.json`.
