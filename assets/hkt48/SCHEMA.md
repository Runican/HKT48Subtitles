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

Open research checklists / Q notes are optional local working files — not part of this public tree. Prefer leaving unresolved items as `provisional` in the glossary until a public source confirms them.
