"""Camera capture and face detection using MediaPipe BlazeFace + Haar fallback."""

import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass, field
from typing import Optional

from reachy_mini.media.media_manager import MediaManager, MediaBackend

_face_detector = mp.solutions.face_detection.FaceDetection(
    model_selection=0,       # short-range model (< 2m) — desk distances
    min_detection_confidence=0.4,
)

HAAR_CASCADE = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


@dataclass
class DetectionResult:
    face_detected: bool
    face_count: int
    frame: Optional[np.ndarray] = field(default=None, repr=False)
    # Bounding boxes: list of (x, y, w, h) in pixel coords
    boxes: list = field(default_factory=list)


def init_media() -> MediaManager:
    """Create and return a long-lived MediaManager. Call once at startup."""
    return MediaManager(backend=MediaBackend.LOCAL)


def detect_in_frame(frame: np.ndarray) -> DetectionResult:
    """Run face detection on a pre-captured frame.

    Primary: MediaPipe BlazeFace — handles angled/bowed faces robustly.
    Fallback: Haar cascade — catches cases MediaPipe misses at low confidence.
    """
    h, w = frame.shape[:2]
    boxes: list = []

    # ── MediaPipe pass ────────────────────────────────────────────────────────
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = _face_detector.process(rgb)
    if res.detections:
        for det in res.detections:
            bb = det.location_data.relative_bounding_box
            x = max(0, int(bb.xmin * w))
            y = max(0, int(bb.ymin * h))
            bw = int(bb.width * w)
            bh = int(bb.height * h)
            boxes.append([x, y, bw, bh])

    # ── Haar fallback (only if MediaPipe found nothing) ───────────────────────
    if not boxes:
        detector = cv2.CascadeClassifier(HAAR_CASCADE)
        if not detector.empty():
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=3, minSize=(50, 50)
            )
            boxes = faces.tolist() if len(faces) > 0 else []

    return DetectionResult(
        face_detected=len(boxes) > 0,
        face_count=len(boxes),
        frame=frame,
        boxes=boxes,
    )


def capture_and_detect(media: MediaManager) -> DetectionResult:
    """Grab one frame from Reachy's onboard camera and run face detection."""
    frame = media.get_frame()
    if frame is None:
        raise RuntimeError("Reachy camera returned no frame — is the media daemon running?")
    return detect_in_frame(frame)


def annotated_frame(result: DetectionResult) -> Optional[np.ndarray]:
    """Return a copy of the frame with bounding boxes drawn (for debugging)."""
    if result.frame is None:
        return None
    annotated = result.frame.copy()
    for x, y, bw, bh in result.boxes:
        cv2.rectangle(annotated, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
    return annotated
