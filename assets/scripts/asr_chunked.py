#!/usr/bin/env python3
"""Chunked faster-whisper ASR for long files (avoids OOM). Merges with offsets."""
from __future__ import annotations
import argparse, json, subprocess, sys, time, tempfile, shutil
from pathlib import Path

def ffprobe_dur(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())

def cut(src: Path, start: float, dur: float, dst: Path):
    subprocess.run(
        ["ffmpeg","-y","-ss",f"{start:.3f}","-t",f"{dur:.3f}","-i",str(src),"-ac","1","-ar","16000",str(dst)],
        capture_output=True, check=True,
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("-o","--out", required=True)
    ap.add_argument("--chunk", type=float, default=180.0)
    ap.add_argument("--overlap", type=float, default=1.0)
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--compute-type", default="int8")
    ap.add_argument("--vad-filter", default="true", choices=["true","false"])
    ap.add_argument("--beam-size", type=int, default=5)
    ap.add_argument("--workdir", default=None)
    args = ap.parse_args()

    from faster_whisper import WhisperModel

    src = Path(args.audio)
    out = Path(args.out)
    dur = ffprobe_dur(src)
    vad = args.vad_filter == "true"
    work = Path(args.workdir) if args.workdir else out.parent / "_asr_chunks"
    work.mkdir(parents=True, exist_ok=True)

    print(f"chunked ASR dur={dur:.1f}s chunk={args.chunk} model={args.model}", flush=True)
    t0 = time.time()
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    normalized = []
    raw_segs = []
    sid = 0
    starts = []
    t = 0.0
    while t < dur - 0.05:
        starts.append(t)
        t += args.chunk - args.overlap

    for ci, cstart in enumerate(starts):
        clen = min(args.chunk, dur - cstart)
        cpath = work / f"chunk_{ci:03d}_{cstart:.1f}.wav"
        if not cpath.exists() or cpath.stat().st_size < 1000:
            cut(src, cstart, clen, cpath)
        print(f"=== chunk {ci+1}/{len(starts)} @{cstart:.1f}+{clen:.1f} ===", flush=True)
        kwargs = dict(language="ja", word_timestamps=True, vad_filter=vad, beam_size=args.beam_size, best_of=args.beam_size)
        if vad:
            kwargs["vad_parameters"] = dict(min_silence_duration_ms=400)
        segs_iter, info = model.transcribe(str(cpath), **kwargs)
        chunk_items = []
        for seg in segs_iter:
            words = []
            if seg.words:
                for w in seg.words:
                    words.append({
                        "start": round(float(w.start) + cstart, 3),
                        "end": round(float(w.end) + cstart, 3),
                        "word": w.word,
                        "prob": round(float(w.probability), 4) if w.probability is not None else None,
                    })
            item = {
                "id": sid,
                "start": round(float(seg.start) + cstart, 3),
                "end": round(float(seg.end) + cstart, 3),
                "text": (seg.text or "").strip(),
                "avg_logprob": round(float(seg.avg_logprob), 4) if seg.avg_logprob is not None else None,
                "no_speech_prob": round(float(seg.no_speech_prob), 4) if seg.no_speech_prob is not None else None,
                "words": words,
                "chunk": ci,
                "chunk_start": cstart,
            }
            # Overlap dedupe: skip segments whose midpoint falls in previous chunk's exclusive zone
            # Keep if midpoint >= cstart + overlap/2 for chunks after first, OR always for first
            mid = (item["start"] + item["end"]) / 2
            if ci > 0 and mid < cstart + args.overlap / 2:
                print(f"  skip-overlap [{item['start']:.2f}-{item['end']:.2f}] {item['text'][:50]}", flush=True)
                continue
            chunk_items.append(item)
            print(f"  [{item['start']:.2f}-{item['end']:.2f}] {item['text'][:80]}", flush=True)
            sid += 1
        for item in chunk_items:
            raw_segs.append(item)
            normalized.append({
                "id": item["id"],
                "start": item["start"],
                "end": item["end"],
                "speaker": "Generic",
                "text_ja": item["text"],
                "words": item["words"],
                "text_ja_raw": item["text"],
            })
        # checkpoint
        engine = {
            "name": "faster-whisper",
            "version": __import__("faster_whisper").__version__,
            "model": args.model,
            "device": args.device,
            "compute_type": args.compute_type,
            "language": "ja",
            "word_timestamps": True,
            "vad_filter": vad,
            "beam_size": args.beam_size,
            "chunk_sec": args.chunk,
            "overlap_sec": args.overlap,
            "duration": dur,
            "elapsed_sec": round(time.time()-t0, 2),
            "status": "running",
            "chunks_done": ci+1,
            "chunks_total": len(starts),
        }
        out.write_text(json.dumps({"engine": engine, "segments": normalized}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  checkpoint segs={len(normalized)} elapsed={engine['elapsed_sec']}s", flush=True)

    engine["status"] = "complete"
    engine["elapsed_sec"] = round(time.time()-t0, 2)
    out.write_text(json.dumps({"engine": engine, "segments": normalized}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out} ({len(normalized)} segs) in {engine['elapsed_sec']}s", flush=True)

if __name__ == "__main__":
    main()
