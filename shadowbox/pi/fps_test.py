import time, cv2, mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision

opts = vision.PoseLandmarkerOptions(
    base_options=mpp.BaseOptions(model_asset_path="pose_landmarker_lite.task"),
    running_mode=vision.RunningMode.VIDEO)
lm = vision.PoseLandmarker.create_from_options(opts)
cap = cv2.VideoCapture(0)
t0 = time.time(); n = 0
while time.time() - t0 < 60:
    ok, frame = cap.read()
    if not ok: continue
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    lm.detect_for_video(img, int((time.time() - t0) * 1000))
    n += 1
print("avg FPS:", n / 60)