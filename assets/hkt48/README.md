# HKT48 shared knowledge base

Shared knowledge for HKT48 Japanese→English subtitling: glossary locks, cast lookalikes, and stage templates. Useful for any **subtitler**, **domain verifier**, or **human** editor.

## Layout

```
hkt48/
  README.md              # this file
  SCHEMA.md              # field definitions
  glossary.json          # locked + candidate terms (names/nicks/catchphrases)
  cast_index.json        # members: full name, nick, team, lookalikes, status
  sources/               # curated research notes + URLs
  stage_templates/       # per-stage setlist + talk-slot priors for segment finding
```

## Roles

- **Subtitler**: ASR → cues. When unsure (name clash, catchphrase mush, pun), leave the item provisional / note it for review. Before final EN, re-read `glossary.json` locks and never override a `locked: true` entry without human say-so.
- **Domain verifier**: owns locks in `glossary.json` / `cast_index.json`. Research public sources; write short notes under `sources/`; promote confirmed forms to `locked`. Prefer small schema edits over rewrites.
- **Human**: final authority on disputed locks and delivery.

## Rules

1. Prefer official / wiki-stable romanizations over ASR soup.
2. **Do not lock from ASR alone.** Clip ASR (and prompted ASR rewrites) is only a pointer to what to research. Verify catchphrases, names, and disputed lines from **official** sources (hkt48.jp profiles, interviews, schedule) **and unofficial fan sources** (member/fan posts, blogs, show reports). If no public source confirms a live variant, mark `provisional` or ask the human — do not promote ASR text to `locked`.
3. Always record lookalike traps (e.g. Yasui Hina ≠ Aoki Hinako).
4. Catchphrases: JA canon + EN gloss or romaji; do not force bad English. Note published vs live variants when they differ.
5. Confidence: `locked` | `provisional` | `rejected`.
6. Cite at least one source URL in `sources/` when locking a disputed name (prefer non-ASR evidence).

## Recent locks (2026-09-30 Mokugekisha)
- EN defaults: **Aichi**; **rehearsal** (リハ — not riha/reh); **new position** (シンポジ — not shin posi / symposium); Sae-san ≠ Sayashi. No everyday JA (村民).
- Gen shorthand **ロッキー／ななき** → ASS EN **6th gen(s)** / **7th gen(s)** — never Rokky/Nanaki romaji in ASS.
