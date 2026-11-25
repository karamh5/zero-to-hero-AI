"""Convert a multi-class RoboMaster dataset into YOUR 3 classes.

  Red_3  -> red_3   (class 0)
  Blue_3 -> blue_3  (class 1)
  everything else (other numbers, base, outpost, sentry...) -> other (class 2)

Usage (from robostrike_cv):
  python scripts/remap_to_3_classes.py PATH_TO_DOWNLOADED_DATASET number_data
Then train with:  data=number_data/data.yaml
Images with no boxes are kept on purpose (they teach it what is NOT a plate).
"""
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
cfg = yaml.safe_load((src / "data.yaml").read_text())
names = cfg["names"]
names = [names[i] for i in sorted(names)] if isinstance(names, dict) else list(names)

NEW = ["red_3", "blue_3", "other"]


def new_id(name):
    n = name.strip().lower().replace("-", "_").replace(" ", "_")
    if re.fullmatch(r"red_?3", n):
        return 0
    if re.fullmatch(r"blue_?3", n):
        return 1
    return 2


mapping = {i: new_id(n) for i, n in enumerate(names)}
print("Class mapping:")
for i, n in enumerate(names):
    print(f"  {i:2d} {n:15s} -> {NEW[mapping[i]]}")
if 0 not in mapping.values() or 1 not in mapping.values():
    sys.exit("No red_3/blue_3 class found in data.yaml names - check the names above.")

before, after = Counter(), Counter()
for split in ("train", "valid", "val", "test"):
    img_dir, lbl_dir = src / split / "images", src / split / "labels"
    if not img_dir.exists():
        continue
    out_img, out_lbl = dst / split / "images", dst / split / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)
    for img in img_dir.iterdir():
        shutil.copy2(img, out_img / img.name)
        lbl = lbl_dir / (img.stem + ".txt")
        lines = []
        if lbl.exists():
            for line in lbl.read_text().splitlines():
                parts = line.split()
                if not parts:
                    continue
                old = int(float(parts[0]))
                before[names[old]] += 1
                new = mapping[old]
                after[NEW[new]] += 1
                lines.append(" ".join([str(new)] + parts[1:]))
        (out_lbl / (img.stem + ".txt")).write_text("\n".join(lines) + ("\n" if lines else ""))

val_dir = "valid" if (dst / "valid").exists() else "val"
(dst / "data.yaml").write_text(
    f"path: {dst.resolve().as_posix()}\n"
    f"train: train/images\nval: {val_dir}/images\n"
    + ("test: test/images\n" if (dst / "test").exists() else "")
    + f"\nnc: 3\nnames: {NEW}\n"
)
print("\nBoxes per original class:", dict(before))
print("Boxes per NEW class:     ", dict(after))
print(f"\nDone. Train with data={dst / 'data.yaml'}")
