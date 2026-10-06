# Pipeline scripts

Public copies of the Japanese→English subtitle pipeline. These are the runnable tools (not just the skill write-up). When the live copies under `/workspace/scripts/` change, re-publish scrubbed copies here so this folder stays the public mirror.

No show audio, cue JSON, or ASS intermediates belong in this directory. Scripts take paths on the command line; they do not hardcode a job directory.

## Per-segment tools

| Script | Role |
| --- | --- |
| `asr_whisper.py` | faster-whisper JA ASR with word timestamps and checkpoints |
| `asr_chunked.py` | Same, in overlapping chunks for long files |
| `asr_all.py` | ASR every segment, then silence-aware dropout repair |
| `find_gaps.py` | Flag ASR gaps that are not silence |
| `cleanup_ja.py` | Glossary + domain replacements on `text_ja` |
| `assign_speakers.py` | Heuristic speaker labels (name patterns + optional time windows) |
| `assign_speakers_ramune.py` | Same heuristics, Kenkyuusei Ramune 7th-gen cast nick patterns |
| `build_cues.py` | Merge ASR segments into phrase cues |
| `build_cues_from_asr.py` | Split ASR into JA cue shells (`cues_ja.json`); EN filled later |
| `pipeline_after_asr.py` | `cleanup_ja` then `build_cues_from_asr` for a list of slugs |
| `snap_cues.py` | Cap duration and insert a minimum gap |
| `check_cues.py` | Machine gates: empty EN, overlaps, copy-forward, optional glossary / silence / ASS |
| `write_ass.py` | Write offset ASS; refuses empty English |
| `stitch.py` | Concatenate per-segment `*_EN_offset.ass` into `full_EN_offset.ass` |
| `divergence.py` | Compare a fresh ASS to a gold ASS (IoU + text similarity) |

`assign_speakers.py` and `cleanup_ja.py` still ship a small built-in cast/ASR-mush list from the shared toolset. Prefer `assets/hkt48/glossary.json` for locks; pass it with `--glossary`.

## Examples

From a checkout of this repo:

```bash
python assets/scripts/check_cues.py path/to/cues.json --dur 180 \
  --glossary assets/hkt48/glossary.json

python assets/scripts/write_ass.py path/to/segment_dir --title "Show EN"

python assets/scripts/pipeline_after_asr.py --work path/to/job \
  --glossary assets/hkt48/glossary.json --layout segments mc1 mc2

python assets/scripts/asr_all.py --work path/to/job --layout segments --order mc1 mc2

python assets/scripts/stitch.py --work path/to/job --layout segments --order mc1 mc2

python assets/scripts/divergence.py --fresh fresh.ass --gold gold.ass --out-dir path/to/qc
```

On the box, the same files also live at `/workspace/scripts/`. For a job, copy this folder into `work/<slug>/scripts/` or call the repo copies in place. `pipeline_after_asr.py` always runs the scripts beside itself via `sys.executable`.
