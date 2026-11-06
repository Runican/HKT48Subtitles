# Speaker hints (voice matching) for HKT48 show subtitles

This folder holds everything needed to reproduce the **speaker hints** used in the HKT48 JA→EN subtitle work. The method proposes, for each ASS line tagged `Member`, which cast member is speaking, with a confidence tier. A human reviewer then accepts or fixes each hint in the player. The hints never edit an ASS by themselves.

```
diarization/
  README.md                 this playbook
  requirements.txt          pinned Python deps (CPU only)
  model/                    model.json + MODEL.md (source, sha256, license); the .onnx is downloaded, not committed
  bank/                     cross-show voice bank: one <id>.npz + <id>.json per show/batch, plus index.json
  scripts/
    diar_common.py          embedder (WeSpeaker ONNX + Kaldi fbank), ASS parser, bank loader
    fetch_model.py          download + sha256-verify the model
    make_hints.py           per-show hint generator (config-driven)
    bank_add.py             add a reviewed show to the bank (new file pair, append-only)
    score_review.py         score shipped hints against the reviewer's decisions
  examples/                 show configs (261031 H6, 261031 KIV4) and a bank-add config (261030 H6)
```

## Quick start

```bash
pip install -r assets/diarization/requirements.txt
python assets/diarization/scripts/fetch_model.py          # ~114 MB, sha256-checked
cd /path/to/job/<show>                                    # job folder with the pre-hint ASS + 16 kHz wav
python /path/to/repo/assets/diarization/scripts/make_hints.py show.json
```

Show audio isn't in git. You need your own copy of the recording, decoded to a **16 kHz WAV**, on the same timeline as the ASS.

## Inputs (`make_hints.py` config, paths relative to the config file)

| key | meaning |
|---|---|
| `show_id`, `title` | identifiers. `show_id` is also excluded from the bank by default |
| `ass` | **pre-hint** ASS. Speaker tags (ASS Name field) are full names, nicknames, or `Member`/`Crowd`/`All`/`Unknown`/`Multiple`. Segments come from `; ===== name =====` comment lines |
| `audio` | 16 kHz WAV (mono, or stereo that gets downmixed) |
| `cache` | optional embedding cache JSON (`"H:MM:SS.cc|H:MM:SS.cc": [256 floats]`), filled on first run |
| `cast` | the night's lineup, full names (family name first, as in `assets/hkt48/cast_index.json`) |
| `nicknames` | map from tag to full name, for ASS files tagged with nicknames |
| `segments` / `intro` | used only if the ASS has no `; =====` markers: `[[name,start,end],...]` or `[start,end]` for the intro (self-introduction MC) |
| `ja_cues` | optional stitched cue JSON (`{"cues":[{"start","text_ja"}]}`), used to show Japanese text in the review TSV |
| `expected_cues` | optional safety assert on the ASS line count |
| `exclude_bank_shows` | bank show ids to ignore (default: `[show_id]`) |
| `unknown_spots` | optional `[[label,start,end],...]`. Lines in these spans are always emitted, flagged `UNKNOWN_SPOT` |
| `params` | overrides of the tier thresholds (see below) |

## Outputs (in `out_dir`, default `diarization/`)

- **`diar_hints.json`**: one object per `Member`/`Crowd` line with `start, end, dur, segment, current_tag, text, ja_text, hint_name, confidence, top_candidate, score, margin, runner_up, seed_source (A = same-show seeds | bank), note, unknown_spot`.
- **`speaker_hints_review_fullname.tsv`**: the review sheet, 10 tab-separated columns:
  `start, end, segment, current_tag, ja_text, hint_name, confidence, top_cos, margin, runner_up`. Times use ASS format and all names are full names. `hint_name` is `unsure` when there's no hint.
- `speaker_hints_full.tsv` (all fields), `named_cues_loo.tsv` and `named_cue_disagreements_hm.tsv` (self-check on named lines), `roster.json` (seed counts per member, capped/unseeded), `stats.json` (totals, per-segment and per-name counts, LOO evaluation, bank usage, ASS sha256 at start and end).

## Method

1. **Embeddings.** Every ASS line except `All` is embedded with WeSpeaker ResNet293-LM (256-d, L2-normalised) over exactly the line's start–end span.
2. **Seeds.** Lines the pre-hint ASS already attributes to a cast member (≥0.7 s; mostly the self-introduction MC) are that member's same-show seeds. Each member's seed centroid is the normalised mean.
3. **Hint.** A `Member` line gets the member with the highest cosine to its centroid. `margin` = top − runner-up cosine.
4. **Self-check (LOO ±10 s).** Each named line is re-scored against centroids built without any seed within ±10 s of it, which approximates hinting it blind. A stricter cross-segment variant (`xseg`) also drops the member's seeds from the same segment. Results go to `stats.json` → `eval`.
5. **Leave-speaker-out.** Each member is removed in turn, and the script records who would absorb her lines, which shows the risk if a member were unseeded.
6. **Read-only on the ASS.** sha256 and mtime are checked at start and end. If the ASS changed during the run, nothing is written.

### Tiers

| tier | rule |
|---|---|
| **high** | top cos ≥ 0.50 **and** margin ≥ 0.10, **and** the member has ≥3 seeds in each of ≥2 segments (otherwise capped to medium) |
| **medium** | top cos ≥ 0.40 and margin ≥ 0.05 |
| **unsure** | everything else; any line < 0.7 s; every `Crowd` line |

### Bank policy (fallback only)

The bank is consulted **only for lineup members with no same-show seed**. For such a member:
- her centroid is built from bank lines that are clean (or `clean: "unknown"` legacy rows), not outro, ≥0.7 s, and **not from the target show**;
- she needs **≥15** such lines, or she gets no centroid;
- a bank-based hint is **medium at most**, and only when its cosine is **≥0.60**. Anything else is unsure.

On the last four shows (261028–261031) every lineup member had intro lines, so the bank wasn't needed.

### Adding a show to the bank (`bank_add.py`)

After the user review, run `bank_add.py <config>` (see `examples/bank_add_261030_h6.json`). Only **clean** lines enter the bank:
- a person label (not All/Crowd/Multiple/Member/Unknown/Host), not in the outro, ≥0.7 s;
- no line by a *different* speaker within 0.3 s on either side;
- and either an **intro** line (user-labelled, or pre-hint ASS-named when no user label overlaps it) **or** a user-reviewed line whose shipped hint was **high and correct** and ≥1.5 s;
- lines that were retimed or split in review, or that fall in a span rebuilt after hints (`rebuilt_spans`), are re-embedded from the audio at their final times.

The bank is **append-only**: each show adds a new `<show_id>_review.npz/.json` pair, and the script refuses to overwrite an existing one. `bank/index.json` gets a new entry with sha256 hashes and updated totals, and `diar_common.load_bank` checks those hashes on load.

### Scoring a review (`score_review.py`)

```bash
python scripts/score_review.py --hints diarization/speaker_hints_review_fullname.tsv \
  --review speaker_confirm.jsonl --edit-ops edit_ops.jsonl --exclude mc3=1:18:42-1:30:12
```
Only hints whose tier is high or medium are scored, and only where the reviewer made a decision (confirm/fix) on that line. Lines that were split are listed but not scored. The output includes an intro/outside-intro breakdown, the misses, and hint→truth miss pairs.

## Bank format

- `bank/<id>.npz`: one array `emb`, float32, shape N×256, L2-normalised rows. Load with `np.load(..., allow_pickle=False)`.
- `bank/<id>.json`: show metadata (title, published ASS, timeline, clean rule, embedder) plus `rows[i]` = `{row, speaker (full name), start, end (s), show, segment, clean (true | "unknown"), clean_reason (clean_intro | clean_hc | null), label_source, shipped_hint, shipped_conf, emb_src, rebuilt_span?, also_in?}`. Row *i* matches `emb[i]`.
- `bank/index.json`: embedder id, dim, per-file rows, sha256 and per-member counts, per-member totals.

Contents at packaging time: 12 files, 4,975 lines, 41 members.
- `*_legacy`: the 2025 reviews 250405–250416, user-graded rows plus pre-hint ASS-named lines. These have **`clean: "unknown"`**: no clean check was recorded, and they include overlapped talk and outro lines.
- `*_legacyintro`: ASS-named self-intro lines from 250411/250416. 32 lines appear in both a legacy and a legacyintro file; they are marked `also_in` and kept, matching how the bank has been used.
- `*_review`: 261028, 261029, 261030, built with the clean rule above.
- **261028 is on its old review timeline.** The published ASS was later retimed: add +0.03 s before 1:31:07 and +300.68 s after it.

## Measured accuracy (user-reviewed shows)

| show | high | medium |
|---|---|---|
| 261028 KIV4 | 18/18 | 123/126 |
| 261029 KIV4 | 113/113 | 120/124 |
| 261030 H6 (mc3 excluded: rebuilt after hints) | 99/99 | 77/84 |

High hints have been right every time so far. Medium hints are right about 93–97% of the time. The reviewer should still check medium hints whose content contradicts the voice match.

## Known failure modes

- **LOO underestimates outside-intro medium.** The self-check is dominated by intro lines. Medium hints in later MCs land somewhat lower than the LOO numbers suggest, so read `stats.json` → `eval.non_intro`.
- **Absorption.** A member with few or noisy seeds can "absorb" a similar-sounding voice (seen: Matsunaga↔Fujino, Airi↔Mei, Shibui↔Ikuno). `leave_speaker_out` in `stats.json` shows who would absorb whom.
- **Low-level audio.** Encore calls, off-mic announcements and quiet backstage audio give no usable match. Expect unsure, or a wrong medium.
- **Overlapping talk.** Talk-overs and chorus lines (`All`) cut cosine by roughly 0.2. A medium hint on a talk-over usually names whoever is louder.
- **Outro boom mic.** Outro lines sit at ~0.5 cosine to the same member's stage voice, so outro lines are never added to the bank.

## Note on the voice bank

The embeddings are speaker fingerprints of public performers (HKT48 members), computed from their published show recordings and labelled with their names. They **cannot be turned back into audio or speech**. They can, however, be used to recognise these members' voices in other recordings. Use them only for subtitling and speaker attribution.

## License / attribution

The model is WeSpeaker ResNet293-LM, CC BY 4.0. See `model/MODEL.md` for attribution and the pinned download.
