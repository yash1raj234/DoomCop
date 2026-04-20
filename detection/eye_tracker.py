import cv2
import numpy as np
import time
import threading
import os
from PyQt6.QtCore import QObject, pyqtSignal

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets", "face_landmarker.task"
)

# Face mesh landmark indices (478-point model)
NOSE_TIP = 4
CHIN = 152
LEFT_EAR = 234
RIGHT_EAR = 454
# Iris indices (only present with output_face_blendshapes or refine)
LEFT_IRIS_CENTER = 468
RIGHT_IRIS_CENTER = 473
LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374


class EyeTracker(QObject):
    frame_ready = pyqtSignal(object)          # numpy BGR frame
    doomscroll_detected = pyqtSignal(float)   # confidence 0-1
    doomscroll_ended = pyqtSignal()
    status_update = pyqtSignal(str, float, str)  # angle, confidence, gaze

    def __init__(self):
        super().__init__()
        self._running = False
        self._thread = None

        self.is_doomscrolling = False
        self.confidence = 0.0
        self.head_angle = 0.0
        self.gaze_direction = "center"

        self._doom_start_time = None
        self._doom_threshold_seconds = 3.0
        self._pitch_threshold = 20.0
        self._currently_triggered = False

        self.cap = None
        self._landmarker = None

    def _init_landmarker(self):
        if not MEDIAPIPE_AVAILABLE:
            return False
        if not os.path.exists(MODEL_PATH):
            return False
        try:
            base_opts = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
            opts = mp_vision.FaceLandmarkerOptions(
                base_options=base_opts,
                running_mode=mp_vision.RunningMode.VIDEO,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=True,
            )
            self._landmarker = mp_vision.FaceLandmarker.create_from_options(opts)
            return True
        except Exception as e:
            print(f"[EyeTracker] Landmarker init failed: {e}")
            return False

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        if self.cap:
            self.cap.release()
            self.cap = None
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None

    def _run(self):
        has_model = self._init_landmarker()

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.cap = None
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        ts_ms = 0

        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            annotated = frame.copy()
            h, w = frame.shape[:2]

            face_found = False

            if has_model and self._landmarker:
                ts_ms += 33
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                try:
                    result = self._landmarker.detect_for_video(mp_img, ts_ms)
                except Exception:
                    result = None

                if result and result.face_landmarks:
                    face_found = True
                    lm = result.face_landmarks[0]

                    def pt(idx):
                        return np.array([lm[idx].x * w, lm[idx].y * h])

                    nose = pt(NOSE_TIP)
                    chin_pt = pt(CHIN)

                    # Head pitch from transformation matrix if available
                    if result.facial_transformation_matrixes:
                        mat = np.array(result.facial_transformation_matrixes[0].data).reshape(4, 4)
                        # Extract pitch from rotation matrix (row 1, col 2 = sin(pitch))
                        pitch_rad = np.arcsin(np.clip(-mat[1][2], -1.0, 1.0))
                        self.head_angle = float(np.degrees(pitch_rad))
                    else:
                        # Fallback: angle of nose-to-chin vs vertical
                        vec = chin_pt - nose
                        angle_rad = np.arctan2(vec[0], vec[1])
                        self.head_angle = float(np.degrees(angle_rad))

                    # Iris/gaze from landmark positions (indices 468-477 present in 478-point model)
                    try:
                        if len(lm) > 474:
                            l_iris = pt(LEFT_IRIS_CENTER)
                            l_eye_top = pt(LEFT_EYE_TOP)
                            l_eye_bot = pt(LEFT_EYE_BOTTOM)
                            eye_h = max(l_eye_bot[1] - l_eye_top[1], 1)
                            ratio = (l_iris[1] - l_eye_top[1]) / eye_h
                            if ratio > 0.65:
                                self.gaze_direction = "down"
                            elif ratio < 0.35:
                                self.gaze_direction = "up"
                            else:
                                self.gaze_direction = "center"
                        else:
                            self.gaze_direction = "center"
                    except Exception:
                        self.gaze_direction = "center"

                    # Draw key points
                    for idx in [NOSE_TIP, CHIN]:
                        p = pt(idx).astype(int)
                        cv2.circle(annotated, tuple(p), 4, (0, 255, 0), -1)

                    # Doomscroll logic
                    # Head pitched down = positive pitch angle (looking down)
                    head_down = self.head_angle > self._pitch_threshold

                    if head_down:
                        if self._doom_start_time is None:
                            self._doom_start_time = time.time()
                        elapsed = time.time() - self._doom_start_time
                        self.confidence = min(elapsed / self._doom_threshold_seconds, 1.0)

                        if elapsed >= self._doom_threshold_seconds and not self._currently_triggered:
                            self._currently_triggered = True
                            self.is_doomscrolling = True
                            self.doomscroll_detected.emit(self.confidence)
                    else:
                        if self._currently_triggered:
                            self.doomscroll_ended.emit()
                        self._doom_start_time = None
                        self.confidence = 0.0
                        self._currently_triggered = False
                        self.is_doomscrolling = False

                    # Overlay HUD
                    color = (0, 0, 255) if self.is_doomscrolling else (0, 220, 0)
                    cv2.putText(annotated, f"Pitch: {self.head_angle:.1f}",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    cv2.putText(annotated, f"Gaze: {self.gaze_direction}",
                                (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    if self.confidence > 0:
                        pct = int(self.confidence * 100)
                        cv2.putText(annotated, f"Doom: {pct}%",
                                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)

                    if self.is_doomscrolling:
                        overlay = annotated.copy()
                        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 180), -1)
                        cv2.addWeighted(overlay, 0.25, annotated, 0.75, 0, annotated)
                        cv2.putText(annotated, "DOOMSCROLL!", (w // 2 - 140, h // 2),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

            if not face_found:
                # No face — reset doom state
                if self._currently_triggered:
                    self.doomscroll_ended.emit()
                self._doom_start_time = None
                self.confidence = 0.0
                self._currently_triggered = False
                self.is_doomscrolling = False

                if not has_model:
                    cv2.putText(annotated, "No model - demo mode",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                else:
                    cv2.putText(annotated, "No face detected",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)

            self.status_update.emit(
                str(round(self.head_angle, 1)),
                self.confidence,
                self.gaze_direction
            )
            self.frame_ready.emit(annotated)
            time.sleep(0.033)

        if self.cap:
            self.cap.release()
            self.cap = None
