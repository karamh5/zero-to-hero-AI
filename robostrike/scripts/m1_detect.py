"""M1 demo: run the baseline armor detector on a camera, a video file, or the screen.

Usage (from C:\\Users\\Karam Hammouda\\robostrike_cv):
  python scripts/m1_detect.py 0                 # camera / capture card index
  python scripts/m1_detect.py clip.mp4          # video file
  python scripts/m1_detect.py screen            # screen-capture (left half of screen)
Options: --conf 0.30  --save demo.mp4  --weights models/m1_baseline_armor.pt
Press q to quit.
"""
import argparse
import time
from pathlib import Path

import cv2
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent

p = argparse.ArgumentParser()
p.add_argument("source", nargs="?", default="0")
p.add_argument("--weights", default=str(ROOT / "models" / "m1_baseline_armor.pt"))
p.add_argument("--conf", type=float, default=0.30)
p.add_argument("--imgsz", type=int, default=640)
p.add_argument("--all-classes", action="store_true",
               help="also show the 'other' class (hidden by default; only red_3/blue_3 are shown)")
p.add_argument("--save", default=None, help="write annotated video to this path")
args = p.parse_args()

model = YOLO(args.weights)

if args.source == "screen":
    import mss
    import numpy as np
    sct = mss.mss()
    full = sct.monitors[1]
    # Capture only the LEFT HALF of the screen: put the video there, and the
    # detector window opens on the right half so it never films itself.
    monitor = {"left": full["left"], "top": full["top"],
               "width": full["width"] // 2, "height": full["height"]}

    def read():
        shot = np.array(sct.grab(monitor))
        return True, cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)
else:
    cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    if not cap.isOpened():
        raise SystemExit(f"Could not open source: {args.source}")
    read = cap.read

writer = None
moved = False
last = time.time()
while True:
    ok, frame = read()
    if not ok:
        break
    r = model(frame, conf=args.conf, imgsz=args.imgsz, device=0, verbose=False,
                 classes=None if args.all_classes else [0, 1])[0]
    out = r.plot()
    now = time.time()
    fps = 1.0 / max(now - last, 1e-6)
    last = now
    cv2.putText(out, f"{len(r.boxes)} plate(s)  {fps:.0f} fps  conf>={args.conf}",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    if args.save:
        if writer is None:
            h, w = out.shape[:2]
            writer = cv2.VideoWriter(args.save, cv2.VideoWriter_fourcc(*"mp4v"), 30, (w, h))
        writer.write(out)
    cv2.imshow("M1 armor detector (q to quit)", out)
    if args.source == "screen" and not moved:
        cv2.moveWindow("M1 armor detector (q to quit)", monitor["width"], 0)
        moved = True
    if cv2.waitKey(1) == ord("q"):
        break

if writer:
    writer.release()
cv2.destroyAllWindows()
