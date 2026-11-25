"""Phase B: pull frames out of your recorded clips for labeling.

Usage:  python scripts/extract_frames.py clips dataset_own/frames --every 8
Each clip gets its own sub-folder, so you can split train/val BY CLIP later.
"""
import argparse
from pathlib import Path

import cv2

p = argparse.ArgumentParser()
p.add_argument("clips_dir")
p.add_argument("out_dir")
p.add_argument("--every", type=int, default=8, help="keep every Nth frame")
args = p.parse_args()

out_root = Path(args.out_dir)
for clip in sorted(Path(args.clips_dir).glob("*")):
    if clip.suffix.lower() not in {".mp4", ".mov", ".avi", ".mkv"}:
        continue
    out = out_root / clip.stem
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(clip))
    i = kept = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % args.every == 0:
            cv2.imwrite(str(out / f"{clip.stem}_{i:06d}.jpg"), frame)
            kept += 1
        i += 1
    cap.release()
    print(f"{clip.name}: kept {kept} of {i} frames")
