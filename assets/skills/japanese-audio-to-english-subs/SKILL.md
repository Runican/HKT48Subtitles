---
name: Japanese audio to English subs
description: >-
  Use this when turning Japanese audio or video into timed English ASS
  subtitles, especially multi-speaker idol/show content with offset sections,
  jargon, intro catchphrase chants, and a need for multipass ASR so long silent
  gaps in the subs do not appear. Default local ASR is faster-whisper large-v3.
  Deliver ASS only (no SRT). Default no visual overlap; dual lines need Layer +
  MarginV. After each delivery, send the user a short doubt list (or say none).
---
# Japanese audio → English timed subtitles (ASS)

Agent-readable runbook. Execute in order. Do **not** skip the watch/timing pass to save time — that is where this job fails.

## Goal

From a **section** of a longer Japanese recording (or a full file), produce English **ASS** subtitles that:

- are timed to the **original** timeline (`OFFSET_SEC` applied to every cue at export only)
- survive niche jargon / nicknames via a glossary + targeted lookup
- use **separate cues** when people talk at once or back-to-back (never merge overlapping speech into one line)
- keep each cue on screen roughly as long as the speech it covers (no long-parking that queues later cues)

**Not required:** voice-print identification or per-speaker colors. Colors in ASS are a neat optional plus. Speaker labels may come from dialogue cues (intros, names said aloud); unlabeled speech stays a generic style. Keep ASS **Name** tags when useful for review (user preference); most players hide them.

**Main failure mode to prevent:** minutes of speech with no subtitles while silence-detect shows little real quiet. Multipass dropout repair is mandatory.

**Secondary failure mode:** cues that last far longer than their speech, so later lines wait in a queue and feel lagged.

Do **not** emit one English paragraph per 6–8s ASR window.

**Deliverable format:** **ASS only.** Do not write SRT unless the user explicitly asks for a compatibility export. ASS supports styles, dual layers for overlap, positioning, and speaker colors.

## Inputs the human must provide

Required:

- Audio or video of the **section** (or full file + cut points)
- `OFFSET_SEC` — section start on the original timeline (float seconds OK)
- Target language (default `en`)
- Domain hint (e.g. `HKT48`) so names/nicks can be researched

Optional (end-state workflow):

- Full-performance cast list, and/or per-segment cast (high value for Name tags and ASR name traps)
- Segment timestamps on a longer show
- Known song timestamps to skip or mark as `[song]`
- ASS colors / styles (default plain; colors only if asked)
- Research teammate for glossary (recommended for idol groups)
- ASR model override (default `large-v3` when local whisper is used)

Topic notes (“what this bit is about”) are **not** required. Prefer cast + glossary locks over asking for plot spoilers.

## Outputs

Always write under `work/<slug>/`:

- `original.wav` (16 kHz mono) or `original.aac`
- `asr.json` — word-level times + speaker ids if available; record which engine produced it
- `speakers.json` — `SPEAKER_01` → label or `generic` (dialogue-cue mapping only; never invent voice IDs)
- `glossary.json`
- `cues.json` — canonical cues in **clip-relative** seconds
- `<slug>_EN_offset.ass` on the **original** timeline (**ASS only**; no SRT by default)
- `gaps.json` — ranges with speech but no usable text
- `NOTES.md` — residual risks, glossary guesses, remaining dropouts
- `doubts.md` (or a section in NOTES) — short review flags for the user

Optional: per-gap clips under `gaps/`. SRT only if the user explicitly requests it.

### User-facing delivery (mandatory)

With every ASS send (or when a **segment review arc** finishes):

1. Attach `<slug>_EN_offset.ass` as a **normal file attachment** (not an image-slot preview — `.ass` can show as "Image unavailable")
2. Send a **doubt list** in chat (and mirror it in `doubts.md` / NOTES): for each item, **timestamp (original timeline)**, cue text or gist, and **why unsure**
3. If nothing shaky, say **no doubts** / empty list — still acknowledge it so the habit is visible

**Multi-segment show review:** do **not** re-attach ASS after every fix batch. Patch ASS + cues, **always** post a short chat postmortem with each fix batch (patterns + process tweak), and attach the file only when that segment (or the full-show stitch) is signed off.

**Full-show stitch:** when all segments are signed off, rebuild `full_EN_offset.ass` from the reviewed segment files. Insert `; ===== <segment> =====` comment markers and one–two blank lines between segments for navigation.

Flag when any of these apply (do **not** rely only on Whisper confidence):

- Low ASR confidence or mushy audio
- Name/nick not on the night’s cast list, or clashes with a known trap (e.g. いおり↔ゆい↔ゆうり)
- Glossary / domain verifier still open, or `locked: false` guess
- Chant / catchphrase edges, repaired dropout spans, near-miss gaps
- Line that does not fit surrounding dialogue even if ASR sounds fluent
- Ambiguous speaker for Name tag when voices overlap
- Overlap / dual-voice collapse (Whisper mashed two speakers into one fluent line)
- Ghost speech in quiet / post-chant stretches (photo hush, outro applause)
- 1st vs 3rd person / I've vs you've when the speaker is narrating someone else
- Literal calques of stage riffs (e.g. 辛味が新鮮) that read unnatural in EN

## Cleanup (user policy)

**When starting the next clip**, scrub the previous finished job’s heavy audio:

1. Delete `original.wav` / `.aac`, everything under `gaps/` and `spot/` (wav/mp3/…), and that job’s chat-attached source MP3.
2. **Keep** `<slug>_EN_offset.ass`, `cues.json`, `glossary.json`, `NOTES.md`, `doubts.md`, `speakers.json`, `asr.json` / related small JSON.
3. **Never** delete `assets/hkt48/`.
4. If a beat needs re-listening later, ask the user to re-send that audio.

Trigger is **start of next clip**, not ASS acceptance. Do not keep finished-clip WAVs “just in case.”

## Notes hygiene

- NOTES / REVIEW_FIXES / doubts.md are agent-owned working memory. Write them for your own reuse and scan. At end of a show or long review arc, optionally distill lasting lessons into this skill’s Do-not-repeat and into shared glossary locks; do not block mid-batch user review on note cleanup.

## Toolchain (preferred order)

ASR (Japanese + timestamps):

1. Grok Speech-to-Text API if keyed — JA, word times, diarization
2. `faster-whisper` local — default **`large-v3`** (cpu `int8` OK). Use `medium` only if the user asks for speed or `large-v3` cannot load. `small` last resort.
3. Never treat a chat-attached transcript’s block times as final cue times — hint only

Other: `ffmpeg` / `ffprobe`, an LLM for translation + glossary, Python to snap cues and write ASS. Prefer a project venv (e.g. `/workspace/.venv`) over system pip.

Pin the ASR engine used for each `asr.json` / `asr_pass2.json` in NOTES or in the JSON metadata.

## Hard rules

- Times in `cues.json` are **clip-relative**. Add `OFFSET_SEC` only when writing ASS.
- Never invent dialogue for a span with no ASR text. Cut and re-ASR it.
- A cue still on screen while later Japanese is already spoken is a defect.
- Default: **no visual overlap.** Tiny accidental overlaps (even ~80–250 ms) paint on the same baseline and look “overimpressed” — **de-collide** them (trim earlier `end` or delay later `start`) with ≥ **60–80 ms** gap. Do **not** keep tiny overlaps just because Layer differs.
- True concurrent speech (`overlap_ok=true`): separate ASS **Layer** values **and** different vertical placement (`MarginV` or `\an`/`\pos`) so lines do not share one baseline. Layer alone is not enough.
- Separate cues for adjacent different speakers even when they do not overlap in time — do not merge into one line.
- Max cue duration ≈ **5.5–6.5 s**. Prefer **2–5 s** phrase units. Target on-screen time ≈ speech duration for that cue.
- Gap between consecutive non-overlap cues ≥ **60–80 ms**.
- Empty ASR windows of ~8s+ on audio that silence-detect says is not quiet are **dropouts**, not songs.
- Idol **intro catchphrase chants** (call-and-response before a name line) are not optional decoration — transcribe and subtitle them. Do not skip as “song” without confirming.
- Songs: mark `[song]` only after confirming; do not park one line on a whole chorus.
- Reading speed guard: flag English cues over ~21 characters/sec. If the user says snug-but-readable is OK, keep them; otherwise split or rephrase.
- Density guards: if `cues < DUR/8`, something is still collapsed; if `cues > DUR/1.5`, over-fragmented — review.

## Passes (mandatory)

### Pass A — ingest

```bash
ffprobe -hide_banner SRC
ffmpeg -y -i SRC -ac 1 -ar 16000 work/<slug>/original.wav
```

Record `DUR`. If SRC is the full show, cut the section first; keep `OFFSET_SEC` as the original start.

Silence map:

```bash
ffmpeg -i work/<slug>/original.wav -af silencedetect=noise=-30dB:d=1.2 -f null -
```

If silence is rare but ASR later has long empty blocks → Pass D.

### Pass B — ASR

- Prefer `large-v3` when using faster-whisper
- `language=ja`
- word timestamps on
- diarization on if available (ids are not names)
- short-ish segments; reject engines that emit one caption per ~8s of mixed speech
- If `vad_filter=True` creates empty blocks that silence-detect says are not quiet, re-ASR those spans with `vad_filter=False`

Normalize entries to:

```json
{"start": 12.4, "end": 15.1, "speaker": "SPEAKER_01", "text_ja": "…"}
```

### Pass C — glossary + Japanese cleanup

1. Collect proper nouns from intros (prefecture, age, team, nickname, catchphrase).
2. Research domain sources when a domain hint is given (e.g. HKT48). Official nicknames and published catchcopies beat ASR soup. Enlist a research teammate if available and the domain is dense.
3. Write `glossary.json` (stable romanizations + catchphrase JA/EN when known).
4. Rewrite `text_ja` with glossary. **Do not translate yet.**
5. Build `speakers.json` from dialogue cues only; unmapped → `generic`.

### Pass D — dropout repair (highest priority after first ASR)

For each pair where `next.start - this.end >= 8` **and** silence-detect says the span is not quiet:

1. Cut the span (pad ±0.3s) to `gaps/gap_START_END.wav`
2. Re-ASR that file only (same `large-v3` default); add `START` to every new timestamp
3. Merge into `asr.json`; retry once with `vad_filter` flipped or `medium` if still empty
4. Chunk long dropouts into ≤45s pieces if the engine collapses again
5. If still empty after two engines → blank + `NOTES.md`. Do not hallucinate.

Also inspect **3–8s near-miss gaps** around intros — they often hide catchphrase chants.

**If only one extra pass is possible: do Pass D before polish or colors.**

### Pass E — translate in phrase units

- Translate one breath / one clause at a time — **each cue’s EN must cover that cue’s JA**, not a shared topic noun for the whole story
- Keep glossary nick forms stable across the file
- Catchphrases: prefer glossary EN; keep the joke/pun when it lands; else romanize + short gloss
- Ban paragraph cues. Long JA story → several English cues
- Split on Japanese clause boundaries first; snap each English cue to matching word spans. Only stretch when word times are missing
- Mind JP→EN word-order: edit so the English is readable **without** leaving the cue on screen past its speech
- **Ban topic-noun paste:** never fill a multi-cue anecdote/island/story with the same short EN (e.g. `bean sprouts` / `pillow` / `frying pan` / `Anywhere Door` / a name) while JA advances. Stock openers (`What I'd take to a deserted island…`) only when that cue’s JA is literally the opener without the item yet
- **Themed intros (deserted-island, etc.):** translate **per member block** (catch → name → island → closer), not one giant batch for the whole segment — long parallel stories invite summarization collapse

### Pass F — timing snap

1. Sort by `start`
2. `end = min(end, start + MAX_DUR)`
3. Prefer `end` ≈ end of the words that cue covers (speech-duration targeting)
4. If not `overlap_ok` and `end > next.start - GAP`: `end = max(start+0.6, next.start - GAP)`
5. Drop `end <= start`
6. **Default:** eliminate all time overlaps (de-collide). Only keep simultaneous times when speech truly overlaps and set `overlap_ok`, distinct `layer`, and distinct `margin_v` (e.g. lower line MarginV 60, upper 140).
7. Machine-check ASS: zero unintended overlaps; intentional dual lines must differ in Layer **and** MarginV/`\pos`.

ASS export: PlayRes 1920x1080; optional Style per mapped speaker; times = `ts(clip_sec + OFFSET_SEC)` as `H:MM:SS.cc` (no 60.00 overflow). Writer honors cue `layer` / `margin_v`.

### Pass G — check (do not ship without this)

Machine:

- No cue longer than `MAX_DUR + 0.05` unless `overlap_ok` justification
- **No unintended time overlap** (count must be 0, or every remaining pair is intentional dual with Layer+MarginV)
- First cue start ≈ `OFFSET_SEC`; last end ≤ `OFFSET_SEC + DUR + 0.5`
- Density and reading-speed guards above
- Every former dropout range either has cues or is listed in `NOTES.md`
- **Copy-forward / topic-paste gate (must FAIL before ship):** run `scripts/check_cues.py` (or equivalent). Fail when (a) identical EN appears on ≥3 cues whose JA strings are not all equal, or (b) consecutive identical EN ≥3 except allowlisted ritual closers (`Thank you!` / `Yay!` / `Okay!` / よろしくお願いします-class) **and** JA matches the ritual, or (c) EN is a short topic noun/phrase (≤~3 words) while JA is long and not that noun. Soft-flagging these into doubts is **not** enough — repair first

Watch-through (agent):

- Burn ASS onto a review cut **or** play audio while logging cue text vs timestamp
- Spot-check 3 random minutes **and** every former dropout range
- Spot-check every member intro for catchphrase completeness
- Note constant early/late bias per range and shift if needed
- Run **Pass H** (conversation coherence) and repair flagged spans before shipping
- Build the **doubt list** from this pass + Pass H residuals + glossary open items before shipping

## Definition of done

- Deliverable is `<slug>_EN_offset.ass` synced on the **full** original file at `OFFSET_SEC` (no SRT unless asked)
- **Doubt list sent with the ASS** (or explicit “no doubts”)
- No multi-minute speech gaps without NOTES explanation
- Reading a cue does not collide with the next spoken line (no queue lag from overlong cues)
- Overlapping / adjacent speakers are separate cues
- Intro catchphrases present when spoken
- Glossary-stable names; no invented lines
- Copy-forward / topic-paste machine gate **PASS** (no identical-EN + changing-JA clusters left unrepaired)
- `NOTES.md` lists remaining dropouts and uncertain glossary entries

## Suggested layout

```
work/<slug>/
  original.wav
  asr.json
  asr_pass2.json
  speakers.json
  glossary.json
  cues.json
  gaps/
  NOTES.md
  doubts.md
  <slug>_EN_offset.ass
  REVIEW_FIXES.md
  full_EN_offset.ass          # stitched after all segments signed off
  <segment>/…_EN_offset.ass  # per-segment workdirs when doing a full show
scripts/
  asr_whisper.py
  cut_gaps.py
  snap_cues.py
  write_ass.py
```

## Do not repeat (lessons from live attempts)

### HARD-FAIL / ship defects (Mokugekisha 2026-09-30)

- **Placeholder collapses:** EN is only `Mm.` / `Haha!` / `…` / `Okay—` (or similar stub) when JA has real words → restore from JA or delete the ghost cue.
- **Identical adjacent EN clones** (same EN, different JA) → merge into one cue or differentiate EN from each cue’s JA.
- **Bare trailing em-dash / name+em-dash stubs** (`Aichi—`, `Airi—`, half-thought `—`) with fuller JA → complete from JA or split (Pass H truncation-stub).
- **"N songs in a row"** / song-list announce that only names fewer titles than N → re-ASR neighbors; **also at segment opens** (titles before the “N songs” summary). First title often in a timing hole.
- **Segment cut ending before audio talk ends** → extend cut/`OFFSET` end to the real speech end before shipping.

### GLOSSARY / EN defaults (point at shared `assets/hkt48/glossary.json`)

- Spoken **あいちー** → EN **Aichi** on address/Name (not bare Airi); full **Ichimura Airi** only for full name; **Ai-chii** ok in catch chant text only. (`ichimura-airi`)
- **リハ** → EN **rehearsal** (not romaji *riha*, not *reh*); 着リハ → costume rehearsal. (`riha`)
- **シンポジ/新ポジ** → EN **new position** (NOT symposium, NOT romaji *shin posi*). After jargon swap, short EN coherence rewrite — never blind replace-only. (`shin-posi`)
- **Sae-san ≠ Sayashi**; がんばりました *to* someone = **You did your best** (praise), not “I did my best.” (`kurihara-sae`)
- **ASS EN-only:** cues in English — no unglossed JA/romaji shorthand (gen slang, リハ→rehearsal, シンポジ→new position, 研究生→trainees, シューン→whoosh, etc.). Rare untranslatable puns may keep JA **with an on-screen note**. Do **not** lock everyday JA (e.g. アホ虫, 村民) into shared glossary — gloss in the ASS only.
- **Generation shorthand** ロッキー／ななき／N期 → EN **Nth gen** / **Nth gens** — never **Rokky/Rokki/Nanaki** in ASS. (`rokky-6th-gen`, `nanaki-7th-gen`)

### PROCESS (Mokugekisha review arc 2026-09-30)

- Mid-review: patch ASS + chat postmortem each fix batch; **attach ASS only** when the segment (or full-show stitch) is done.
- **Partial fixes:** when the user asks to insert/split one missing beat, **edit only that beat** — do not rewrite/replace a neighboring cue that was already good. Diff the before/after window. (mc1: 楽しんでますか split ate the song-title line.)
- Re-ASR/sync can undo locks — **re-verify critical locks** after any sync/retime.
- Optimize with segment splits + background workers; say early if the task is too big for one pass.
- Pre-ship cheap scan: leftover romaji/JA shorthand + “does first/last cue of each segment still match JA?”

### FINAL WORKFLOW REVIEW (Mokugekisha H6 250510 — accepted ~8/10)

1. Partial fixes only (see PROCESS).
2. ASS EN-only (see GLOSSARY).
3. Hard-fail “N songs named in JA, fewer in EN” at **segment opens** too, not just encore.
4. **Crowd name-calls** after catchphrases: Crowd gets the given name (`Yuina!` / `Rinka!`), not nick mush or catch repeats.
5. **Reported speech:** when Host narrates what someone said, keep quote + first person (`she said, "…my nerves"`), don’t flatten into Host’s own voice.
6. **Speaker check on outro banter:** short “I” lines after a member jumps in are often still that member (Kokoha/Fujikoko), not Host.
7. Segment split + mid-review patch/postmortem worked; intro rebuild as its own job was right.


- **Yuina ≠ Yuuna (hard):** Ishimatsu **Yuina** (ゆいな) ≠ Yamauchi **Yuuna** (ゆうな/ゆーな). Whisper collapses them to ゆうな / ゆういな / Yuna; the EN pass then spreads one spelling through Name tags. Same show can need **both** in different arcs — never global-replace; disambiguate per beat like いおり↔ゆい; ambiguous → doubt list, not silent pick. ASS default nick forms: **Yuina** / **Yuuna** (not bare Yuna).

- Whisper confusing いおりさん↔ゆいさん (and ゆうり) — verify against cast/context; clip3 Mei-mei story was Iori not Yui
- ASR いくのちゃん vs user ななきちゃん (七期) — gen nick lookalike; do not assume speaker from mush alone
- Trusting chat-ASR block times (6–8s or 60–120s) as cue times
- Treating 1–2 minute empty blocks as songs when silence-detect shows almost no silence
- Skipping idol intro catchphrase chants as if they were optional music
- Abusing `overlap_ok` to stack unrelated lines
- Keeping ~0.1–0.25s time overlaps with Layer 0/1 but same MarginV — players overimpress them
- Parking one placeholder on a ~50s span
- Translating before nickname / cast mapping
- Mishearing published catchphrases (e.g. 野菜の日 → blood type) — verify against glossary/wiki
- Romanizing stage titles wrong (e.g. Sakagari instead of **Saka Agari**)
- Emitting SRT by default when ASS is the agreed deliverable
- Shipping ASS without a user-facing doubt list
- Inventing English interjections (Whoa/Wow/…) not licensed by JA — drop them; map いやいや only when that beat is actually in the cue
- Don't turn sketch gag **だご** into place-names (名古屋/Nagoya); keep romaji **dago** when it's the Hakata intensifier callback
- Don't paste catchphrase bits (e.g. おはよう from おはようおやすみ) onto the post-name thank-you beat; re-listen — often just **Name-saaan!** + Thank you
- Silent ASR "fixes" like 声を見て→ここを見て that still miss the line — in crowdhype/gesture beats prefer 辺/方/舞台 and keep as an explicit doubt; EN = watch/spectate that show/bit + get hyped, not generic "look over here"

- Don't swap idol surname address (〜ちゃん on family name) for the given-name nick without audio proof
- Catchphrase percent puns (ららパーセント) ≠ crowd numeric % answers — keep the pun in EN
- Finalizing a first-seen member intro chant/name without verifying with domain research (surname vs nick, ららパーセント lisp, etc.)
- Rara-pa **ららパーセント** lisp → ASR invents **7%/200%**; answer cues are **“Rara percent!”**, not numerals. Confirm numeric percent cues before keeping them.
- Prefaces 〜県出身 → "From X Prefecture", not bare prefecture name
- Watch-through must catch short cross-talk retorts in ≤2s gaps between cues (Pass G)

- Don't invent compound nick calls from elongated vowels/particles (e.g. ここはーと → **Koko-heart**); host ここはと is quotative と + name call **Kokoha**
- Don't replace spoken **ふじここさん / Fujikoko-san** with bare given-name Kokoha when the member is being named/addressed
- Don't fold hometown (〜県出身 / 熊本だけん) into an intro catchphrase from glossary habit when the live third beat is stage/show (逆上がり公演よろしくね / Saka Agari show) and hometown already sits on the name line. ASR 公園/この辺 are traps for 公演 (kouen).


- Overlap mash: when human ear hears two voices, split cues even if re-ASR / L-R still returns one line (e.g. それが最低 + …わかるでしょう). Trust ear over Whisper for those beats.
- Quiet / applause ghosts: if the user says nobody is speaking, **delete** the cue — do not keep polite stock lines (“Thank you for all your support!”).
- ホラー vs ほらー: in a horror-thread context, prefer ホラー; don't render as hey/look.
- Person & deixis: “I've been talking” vs “you've”; “she only said…” when A narrates B; “You spoke!?” (しゃべった) as reaction, not “I really talked.”
- Stage puns: keep **Aichi-ru** (あいちる ≈ 愛してる) lightly glossed rather than flattening to “I love you”; keep **dago**, **oseji**, etc. as locked gag forms.
- Sae (さえ) vs Saaya (さあや): Whisper swaps them; lock from ear + cast, not ASR kana alone.
- Ballet ≠ volleyball; don't invent post-name catchphrase leftovers (e.g. Risaki “mornings”).
- After a wrong nick locks, re-scan **nearby Name tags and -san/-chan lines** in that beat — consistency pass spreads errors.
- VM / box updates wipe `/workspace/.venv` — **don’t wait for the user to warn.** Before any ASR job (and immediately when import fails), verify `faster-whisper` imports; if broken, recreate the venv and reinstall `faster-whisper`, then continue.
- Pass G energy continuity: cheap RMS/VAD flags for hot-after-cue, yay-glued starts, silent holes in hot bands — **hints only**, softer in cheer/HB/photo zones.
- Pass H conversation coherence: walk cues in order; structural non sequitur / EN stub / copy-forward / mashed JA → **auto re-ASR+repair** until the stretch makes sense (soft on stammer/overlap/nonsense; no inventing over silence).
- Trailing EN `—`/`…` with fuller JA = truncation stub — complete or split before ship (Pass H). Bare **name+em-dash** (`Airi—`) with JA continuing (〜さんが…) counts as dubious stub.
- Two-/N-song encore announce: if EN/JA says "two songs" / 2曲 but only one title is named, **re-ASR** — first title is often in a timing hole (Mokugekisha I'm Crying + Zutto Zutto).
- Trailing EN name+`—` alone (e.g. `Airi—` / `Aichi—`) with fuller JA (あいちーさんが…) = **dubious stub** — complete from JA or split; Pass H truncation-stub gate.
- Never paste a prior denial/catchphrase forward onto the next speaker’s window; force Name from in-window context.
- Chorus / group lines: light Name tags are enough; don't demand perfect speaker IDs unless the user volunteers one.

- Topic-repeat then answer: when JA restates the topic then answers, **split** EN — don't collapse into one answer-only cue.
- Host stammer/restart mashed into a clean invented topic EN → **delete** the invent; keep the real later statement.
- Stop/restart same intent: truncate incomplete first-attempt EN; keep the completed second — don't paste the full sentence onto both.
- Self-interrupt catchphrase: merge duplicate full EN once; re-ASR the restart window for the **real continuation** (don't paste the catchphrase again).
- Complete-looking EN with leftover JA on the same cue (esp. after emotional peaks) → diff JA remainder and **split/insert**.
- Short vocative EN that matches an earlier cue while JA is a different clause → **re-ASR before delete** (template invent ≠ silence).
- Host anecdote that *names* a member ≠ that member speaking — don't peel name mentions out of Host narrative as separate-speaker dialogue.
- Wide ASR windows echo prior lines or flip polarity (変わる↔変わんない); prefer **tight clips** for polarity/nicks/retorts.
- Don't invent ages/numbers from confident ASR over stammer; drop the numeral if ear/cast don't support it.
- Raw JA left in the EN field is a ship defect — translate or flag.




- Blind 2026-09-29 Ramune: EN default for 江浦優香 / ゆうか is **Yuka** / Yuka-chan / Eura Yuka — do **not** ship **Yuuka** / Eura Yuuka in ASS (JA nick still ゆうか).
- Letter / long emotional MC: do **not** delete mid-gap bridges on Whisper-loop suspicion alone — run a **second tight-clip ASR** (or Pass H silent-hole repair) before dropping 思い出は-style lines; over-delete drove high missing vs gold.
- Finder optional `post_song_sketch`: only feed into this ASS pipeline when speech-density/VAD clears talk; otherwise skip / `translate:false` (Ramune FP extras vs gold).

## Pass G add-on — cheap energy / speech continuity (optional, default on)

**Goal:** catch mistimed or truncated cues without another full ASR pass.

After cues exist, for each segment WAV compute a cheap **RMS energy envelope** (e.g. 50–100 ms hop) and optional short VAD/speech band. Flag for re-listen (doubt list / Pass G), **do not auto-retiming**:

1. **Hot-after-cue:** cue ends while energy stays elevated for ≥~0.4–0.6 s with no following cue covering that span → possible truncated EN or early `end`.
2. **Cold-under-cue / early start:** cue `start` sits in a loud burst that looks like applause/cheer while speech onset is later (common intro/yay glue).
3. **Silent hole in hot band:** gap between cues ≥~0.8–1.5 s while energy stays speech-like → missing line candidate (same family as ≤2s cross-talk gaps).

**Cheer / laugh / cake zones:** intros with catchphrase chants, HB singing, photo hush, birthday candles — raise thresholds or treat flags as low-confidence only; raw energy will foul. Prefer “energy hot **and** Whisper words in window” when re-checking those spans.

**Cost:** seconds per segment on CPU; fine to run every job. Skip only if the user asks for speed-only. Folder optional: `energy_flags.json` under the segment.

## Pass H — conversation coherence (default on)

**Goal:** catch missing lines, mid-clause truncations, and speaker/copy-forward errors that look “fine” cue-by-cue but break the talk when read in order.

**When:** after Pass E/F (EN + timing exist), before shipping / with Pass G. Habit on every job.

### How (keep it cheap)

Walk the cue list **in timeline order** (plus JA when present). Do **not** run another full-show Whisper. Flag only spans that fail a short coherence check, then **repair those spans** (tight-clip re-ASR → peel mashed JA → split speakers → complete EN stubs). Loop until the stretch reads as one conversation, or the residual is an explicit doubt.

### Flag triggers (repair, don’t ignore)

1. **Non sequitur:** cue does not follow prior speaker/topic, or Host/letter anecdote jumps mid-story.
2. **Truncation stub:** EN ends with `—` / `…` / a half thought, and the next cue does not finish that thought (or JA continues past EN).
3. **Copy-forward / false repeat:** EN matches a cue 1–3 back (denial, catchphrase, “I've got one!”) while JA/ASR in-window differs.
4. **Q without A / A without Q:** question with no nearby answer, or punchline with no setup in the prior few cues.
5. **Name/polarity clash:** punchline glued under the wrong Name; or polarity (`変わる`/`変わんない`) that contradicts the next Host beat.
6. **N-song announce undercount:** cue says "two/N songs" (or JA `2曲`/`N曲`) but names fewer titles than N — re-ASR neighbors (first title often dropped).
7. **Letter / anecdote hole:** mid-letter or Host story with a speech-like gap and no cue — treat as structural missing (same repair path), not “loop → delete.”


### Soft / high false-alarm zones (raise the bar)

Idol talk is often hectic on purpose: stammer/restart, stop–start mid sentence, talk-over, young/unclear speech, playful nonsense, cheer stacks. In those zones:

- Prefer **structural** flags (stub + fuller JA; exact EN duplicate; mashed multi-clause JA under one Name) over “this sounds odd.”
- Do **not** flag mere stutter restarts, overlapping cheers, or deliberately silly lines.
- Birthday/photo hush, HB singing, chant walls: same soft rule as Pass G energy — need JA/ASR corroboration, not vibe alone.

### On flag → force sense (mandatory)

A Pass H flag is **not** a doubt-only hint. Automatically:

1. Tight-clip re-ASR the window (and neighbors ±1–2 s); prefer tight before wide for polarity/nicks.
2. Peel mashed JA into separate cues; complete EN stubs from JA/ASR; drop invented paste.
3. Retag speakers from context + ear/ASR, not the previous live speaker alone.
4. Re-read the fixed stretch in order; if still broken, widen once more. Only then leave an explicit user-facing doubt.

**Do not** “make sense” by inventing plot or polite filler when energy/ASR show silence — delete ghosts. **Do not** flatten real stammer into one fake smooth sentence if two restart cues are honest.

### Cost

Seconds–minutes per segment (LLM walk + a few spot ASR clips). Skip only if the user asks for speed-only.

## Acceptance → docs + public repo


When the user says the ASS (segment or full-show) is **accepted**:

1. Distill that review arc’s postmortems into this skill’s **Do-not-repeat** (and shared glossary locks if any).
2. Update related private notes only as needed for reuse; do not ask the user to curate them.
3. Publish in **one** commit batch to the public repo checkout `(this repo)` (push with the usual bot git identity): accepted ASS under `shows/stages/[year]/` (or `subs/[type]/[year]/` as agreed), plus scrubbed skill/glossary/docs under `assets/` — no mid-progress NOTES, packets, or bot names.
4. Do **not** commit on every fix batch; only on acceptance (or an explicit “commit now”).

## Domain verification (HKT lore)

When domain hint is HKT48 (or similarly dense idol jargon), do **not** silently resolve disputed names/catchphrases.

Shared repo (box): `assets/hkt48/`

- **First-time member intro (mandatory):** The first time a given member’s self-intro / catchphrase chant appears in a job (or the first time that member appears in an `intro` segment), do **not** finalize chant + name + 〜県出身 lines from ASR alone. Collect provisional JA/EN + spoken forms (surname-ちゃん vs nick, percent-puns, lisp traps), append an open_questions packet (or one batch packet per intro block), and ask the domain verifier  to verify before locking. Re-patch ASS after locks. Skip only if that member’s intro catchphrase+name forms are already `locked: true` in shared glossary for this exact use.

- Before Pass E finalize: read `glossary.json` locks; never override `locked: true` without human approval.
- When unsure (ASR name clash, cast inconsistency, catchphrase mush, pun): append a packet to `open_questions.json` per `SCHEMA.md`, then verify with domain research / teammate before locking with the packet id.
- After domain verification: merge locks into the project `glossary.json`, then re-translate only the affected cues.
- Seed/sync: project glossary may copy from the shared repo; shared repo is the durable store across clips.

