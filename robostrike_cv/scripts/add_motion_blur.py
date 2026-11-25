"""Add motion-blurred copies of some training images (labels stay the same,
because blur does not move the boxes). Helps with fast-spinning plates.

Usage:  python scripts/add_motion_blur.py number_data --fraction 0.3
Only touches train/. Safe to re-run (skips files that already exist).
"""
import argparse
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

p = argparse.ArgumentParser()
p.add_argument("dataset")
p.add_argument("--fraction", type=float, default=0.3)
p.add_argument("--seed", type=int, default=0)
args = p.parse_args()
random.seed(args.seed)

img_dir = Path(args.dataset) / "train" / "images"
lbl_dir = Path(args.dataset) / "train" / "labels"


def motion_kernel(size, angle):
    k = np.zeros((size, size), np.float32)
    k[size // 2, :] = 1.0
    m = cv2.getRotationMatrix2D((size / 2 - 0.5, size / 2 - 0.5), angle, 1.0)
    k = cv2.warpAffine(k, m, (size, size))
    return k / max(k.sum(), 1e-6)


made = 0
for img in sorted(img_dir.glob("*")):
    if img.suffix.lower() not in {".jpg", ".jpeg", ".png"} or img.stem.endswith("_mb"):
        continue
    if random.random() > args.fraction:
        continue
    out = img_dir / f"{img.stem}_mb{img.suffix}"
    if out.exists():
        continue
    frame = cv2.imread(str(img))
    if frame is None:
        continue
    blurred = cv2.filter2D(frame, -1, motion_kernel(random.choice([7, 11, 15, 21, 25]),
                                                    random.uniform(0, 180)))
    cv2.imwrite(str(out), blurred)
    lbl = lbl_dir / f"{img.stem}.txt"
    new_lbl = lbl_dir / f"{img.stem}_mb.txt"
    if lbl.exists():
        shutil.copy2(lbl, new_lbl)
    else:
        new_lbl.write_text("")
    made += 1
print(f"Added {made} motion-blurred copies to {img_dir}")
