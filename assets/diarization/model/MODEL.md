# Speaker-embedding model

The hints and every bank embedding use **WeSpeaker ResNet293-LM** (VoxCeleb), ONNX runtime export.
The file is ~114 MB and is **not committed**. Fetch and verify it with:

```bash
python assets/diarization/scripts/fetch_model.py
```

| | |
|---|---|
| Source | https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet293-LM (official WeSpeaker upload; listed in https://github.com/wenet-e2e/wespeaker/blob/master/docs/pretrained.md) |
| Pinned file | `resolve/6e6bffe5bf3d772a1f143dc6dbfea58a0799ea83/voxceleb_resnet293_LM.onnx` |
| sha256 | `dbb1ccc7754caff552ebc46347a51aaee2669bb24efc740e665d1a1133d20e98` (114,336,285 bytes) |
| Output | 256-d embedding; the scripts L2-normalise it |
| Front end | 80-bin Kaldi fbank, 16 kHz, 25/10 ms, hamming, no dither, per-utterance mean subtraction (`scripts/diar_common.py`) |
| Training data | VoxCeleb2 dev, 5,994 speakers |
| License | **CC BY 4.0**. WeSpeaker states that its VoxCeleb models follow the VoxCeleb dataset license. |

## Attribution (CC BY 4.0)

- H. Wang et al., *WeSpeaker: A Research and Production oriented Speaker Embedding Learning Toolkit*, ICASSP 2023, arXiv:2210.17016. https://github.com/wenet-e2e/wespeaker
- J. S. Chung, A. Nagrani, A. Zisserman, *VoxCeleb2: Deep Speaker Recognition*, Interspeech 2018. https://mm.kaist.ac.kr/datasets/voxceleb/

The VoxCeleb page describes the dataset as available "for research purposes" under CC BY 4.0, with the copyright of the source videos staying with their owners. Neither license says anything specific about embeddings computed from other audio. The bank in `../bank/` contains no VoxCeleb data: it holds embeddings of HKT48 show audio, computed with this model.
