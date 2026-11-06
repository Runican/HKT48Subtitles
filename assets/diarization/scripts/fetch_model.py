#!/usr/bin/env python3
"""Download the WeSpeaker ResNet293-LM ONNX speaker-embedding model (CC BY 4.0, ~114 MB) and verify its sha256.

  python scripts/fetch_model.py            # -> model/voxceleb_resnet293_LM.onnx
  python scripts/fetch_model.py --out /some/dir/model.onnx

The URL is pinned to a Hugging Face commit so the bytes cannot change under us; the sha256 is the one every bank
embedding in bank/ was made with. The model file itself is not committed (see model/MODEL.md).
"""
import argparse, hashlib, json, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SPEC = json.load(open(HERE / "model" / "model.json", encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "model" / SPEC["filename"]))
    ap.add_argument("--url", default=SPEC["url_pinned"])
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists() and hashlib.sha256(out.read_bytes()).hexdigest() == SPEC["sha256"]:
        print("already present and verified:", out); return
    out.parent.mkdir(parents=True, exist_ok=True); tmp = out.with_suffix(out.suffix + ".part")
    h = hashlib.sha256(); n = 0
    print("downloading", a.url)
    with urllib.request.urlopen(a.url) as r, open(tmp, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b); h.update(b); n += len(b)
    if h.hexdigest() != SPEC["sha256"]:
        tmp.unlink(missing_ok=True)
        sys.exit(f"sha256 mismatch: got {h.hexdigest()}, expected {SPEC['sha256']}")
    tmp.replace(out); print(f"ok {out} ({n} bytes, sha256 verified)")


if __name__ == "__main__":
    main()
