#!/usr/bin/env python3
"""Pass B: Japanese ASR with faster-whisper (word timestamps) + checkpoints."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

def write_out(path: Path, engine: dict, normalized: list, raw_segs: list | None, raw_path: Path | None):
    out = {"engine": engine, "segments": normalized}
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if raw_path is not None and raw_segs is not None:
        raw_path.write_text(
            json.dumps({"engine": engine, "segments": raw_segs}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--model", default="medium")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--compute-type", default="int8")
    ap.add_argument("--language", default="ja")
    ap.add_argument("--raw", default=None, help="also write raw segments JSON")
    ap.add_argument("--vad-filter", default="true", choices=["true", "false"])
    ap.add_argument("--checkpoint-every", type=int, default=25)
    ap.add_argument("--beam-size", type=int, default=5)
    args = ap.parse_args()

    from faster_whisper import WhisperModel

    vad = args.vad_filter.lower() == "true"
    t0 = time.time()
    print(
        f"Loading model={args.model} device={args.device} compute={args.compute_type} vad={vad}",
        flush=True,
    )
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    print("Transcribing...", flush=True)
    kwargs = dict(
        language=args.language,
        word_timestamps=True,
        vad_filter=vad,
        beam_size=args.beam_size,
        best_of=args.beam_size,
    )
    if vad:
        kwargs["vad_parameters"] = dict(min_silence_duration_ms=400)
    segments_iter, info = model.transcribe(args.audio, **kwargs)

    raw_segs = []
    normalized = []
    out_path = Path(args.out)
    raw_path = Path(args.raw) if args.raw else None
    ckpt_path = out_path.with_suffix(".ckpt.json")

    engine = {
        "name": "faster-whisper",
        "version": __import__("faster_whisper").__version__,
        "model": args.model,
        "device": args.device,
        "compute_type": args.compute_type,
        "language": args.language,
        "word_timestamps": True,
        "vad_filter": vad,
        "beam_size": args.beam_size,
        "detected_language": getattr(info, "language", args.language),
        "language_probability": getattr(info, "language_probability", None),
        "duration": getattr(info, "duration", None),
        "elapsed_sec": None,
        "status": "running",
    }

    for i, seg in enumerate(segments_iter):
        words = []
        if seg.words:
            for w in seg.words:
                words.append({
                    "start": round(float(w.start), 3),
                    "end": round(float(w.end), 3),
                    "word": w.word,
                    "prob": round(float(w.probability), 4) if w.probability is not None else None,
                })
        item = {
            "id": i,
            "start": round(float(seg.start), 3),
            "end": round(float(seg.end), 3),
            "text": (seg.text or "").strip(),
            "avg_logprob": round(float(seg.avg_logprob), 4) if seg.avg_logprob is not None else None,
            "no_speech_prob": round(float(seg.no_speech_prob), 4) if seg.no_speech_prob is not None else None,
            "words": words,
        }
        raw_segs.append(item)
        normalized.append({
            "id": i,
            "start": item["start"],
            "end": item["end"],
            "speaker": "Generic",
            "text_ja": item["text"],
            "words": words,
            "text_ja_raw": item["text"],
        })
        print(f"  [{item['start']:.2f}-{item['end']:.2f}] {item['text'][:80]}", flush=True)
        if (i + 1) % args.checkpoint_every == 0:
            engine["elapsed_sec"] = round(time.time() - t0, 2)
            engine["segments_so_far"] = i + 1
            engine["last_end"] = item["end"]
            write_out(ckpt_path, engine, normalized, raw_segs, raw_path.with_suffix(".ckpt.json") if raw_path else None)
            # also write partial asr.json so progress isn't lost
            write_out(out_path, engine, normalized, raw_segs, raw_path)
            print(f"  checkpoint {i+1} segs @ {item['end']:.1f}s elapsed={engine['elapsed_sec']}s", flush=True)

    elapsed = time.time() - t0
    engine["elapsed_sec"] = round(elapsed, 2)
    engine["status"] = "complete"
    engine.pop("segments_so_far", None)
    engine.pop("last_end", None)
    write_out(out_path, engine, normalized, raw_segs, raw_path)
    if ckpt_path.exists():
        ckpt_path.unlink(missing_ok=True)
    print(f"Wrote {args.out} ({len(normalized)} segs) in {elapsed:.1f}s", flush=True)

if __name__ == "__main__":
    main()
