#!/usr/bin/env python3
"""Shared helpers for the HKT48 speaker-hint tools: WeSpeaker ONNX embedder (Kaldi fbank front end),
ASS parsing, time helpers and the npz/json voice-bank loader. No job paths are hardcoded here."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

SR = 16000
NONPERSON = {"", "All", "Crowd", "Multiple", "Member", "Unknown", "Host"}
MODEL_SHA256 = "dbb1ccc7754caff552ebc46347a51aaee2669bb24efc740e665d1a1133d20e98"
DEFAULT_MODEL = Path(__file__).resolve().parent.parent / "model" / "voxceleb_resnet293_LM.onnx"


# ---------------- time / files ----------------
def t2s(t: str) -> float:
    """ASS H:MM:SS.cc -> seconds."""
    h, m, s = t.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def s2t(x: float) -> str:
    cs = int(round(x * 100)); h, cs = divmod(cs, 360000); m, cs = divmod(cs, 6000); s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def fhash(p) -> tuple[str, int]:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest(), os.stat(p).st_mtime_ns


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def nz(e) -> np.ndarray:
    v = np.asarray(e, np.float32)
    return v / np.linalg.norm(v)


# ---------------- embedder (WeSpeaker ResNet293-LM, ONNX) ----------------
def fbank_feats(wave: np.ndarray, sr: int = SR) -> np.ndarray:
    """80-bin Kaldi fbank, 25 ms / 10 ms, hamming, no dither, per-utterance mean normalisation (WeSpeaker front end)."""
    import kaldi_native_fbank as knf
    opts = knf.FbankOptions()
    opts.frame_opts.samp_freq = float(sr)
    opts.frame_opts.frame_length_ms = 25.0
    opts.frame_opts.frame_shift_ms = 10.0
    opts.frame_opts.dither = 0.0
    opts.frame_opts.window_type = "hamming"
    opts.frame_opts.snip_edges = True
    opts.mel_opts.num_bins = 80
    opts.mel_opts.low_freq = 20.0
    opts.mel_opts.high_freq = 0.0
    opts.use_energy = False
    fb = knf.OnlineFbank(opts)
    fb.accept_waveform(sr, wave.astype(np.float32).tolist())
    fb.input_finished()
    n = fb.num_frames_ready
    if n < 9:
        return np.zeros((0, 80), dtype=np.float32)
    feats = np.stack([np.array(fb.get_frame(i), dtype=np.float32) for i in range(n)], axis=0)
    return feats - feats.mean(axis=0, keepdims=True)


def load_embedder(model_path=DEFAULT_MODEL, verify: bool = True):
    import onnxruntime as ort
    model_path = Path(model_path)
    if not model_path.exists():
        raise SystemExit(f"model not found: {model_path} - run scripts/fetch_model.py first")
    if verify and sha256(model_path) != MODEL_SHA256:
        raise SystemExit(f"model sha256 mismatch for {model_path} (expected {MODEL_SHA256})")
    sess = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    return sess, sess.get_inputs()[0].name, sess.get_outputs()[0].name


def embed_chunk(sess, in_name, out_name, wave: np.ndarray):
    """L2-normalised 256-d embedding, or None if the chunk gives <9 fbank frames."""
    feats = fbank_feats(wave)
    if feats.shape[0] < 9:
        return None
    out = sess.run([out_name], {in_name: feats[np.newaxis, :, :]})[0]
    emb = out[0].astype(np.float32)
    return emb / (np.linalg.norm(emb) + 1e-9)


class AudioEmbedder:
    """Lazy embedder over one 16 kHz wav (mono or downmixed)."""
    def __init__(self, wav, model_path=DEFAULT_MODEL):
        self.wav = str(wav); self.model_path = model_path; self.sess = None

    def __call__(self, a: float, b: float):
        import soundfile as sf
        if self.sess is None:
            self.sess = load_embedder(self.model_path)
        w, sr = sf.read(self.wav, start=int(a * SR), stop=int(b * SR), dtype="float32")
        assert sr == SR, f"audio must be 16 kHz, got {sr}"
        if w.ndim > 1:
            w = w.mean(1)
        return embed_chunk(*self.sess, w) if len(w) >= 1600 else None


# ---------------- ASS ----------------
def parse_ass(path, nick: dict | None = None):
    """Dialogue cues with segment names taken from '; ===== name =====' comment markers (None before the first)."""
    nick = nick or {}
    cues, seg = [], None
    txt = Path(path).read_text(encoding="utf-8-sig")
    for ln in txt.splitlines():
        if ln.startswith("; ====="):
            seg = ln.strip("; =").strip(); continue
        if not ln.startswith("Dialogue:"):
            continue
        x = ln.split(",", 9)
        tag = x[4].strip()
        c = dict(start_str=x[1], end_str=x[2], start=t2s(x[1]), end=t2s(x[2]), tag=nick.get(tag, tag), ass_tag=tag, text=x[9], seg=seg)
        c["dur"] = c["end"] - c["start"]
        cues.append(c)
    return txt, cues


# ---------------- voice bank ----------------
def load_bank(bank_dir, verify: bool = True):
    """Return list of row dicts (metadata + 'emb') from every file listed in bank/index.json."""
    bank_dir = Path(bank_dir)
    idx = json.load(open(bank_dir / "index.json", encoding="utf-8"))
    rows = []
    for f in idx["files"]:
        npz, js = bank_dir / f["npz"], bank_dir / f["json"]
        if verify and (sha256(npz) != f["sha256_npz"] or sha256(js) != f["sha256_json"]):
            raise SystemExit(f"bank file hash mismatch: {f['id']}")
        E = np.load(npz, allow_pickle=False)["emb"]
        meta = json.load(open(js, encoding="utf-8"))["rows"]
        assert len(meta) == len(E), f["id"]
        for m, e in zip(meta, E):
            rows.append(dict(m, emb=e, bank_file=f["id"]))
    return rows
