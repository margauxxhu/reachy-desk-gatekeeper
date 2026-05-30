"""Camera capture and Haar-cascade face detection using Reachy Mini's onboard camera."""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from reachy_mini.media.media_manager import MediaManager, MediaBackend

HAAR_CASCADE = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


@dataclass
class DetectionResult:
    face_detected: bool
    face_count: int
    frame: Optional[np.ndarray] = field(default=None, repr=False)
    # Bounding boxes: list of (x, y, w, h)
    boxes: list = field(default_factory=list)


def init_media() -> MediaManager:
    """Create and return a long-lived MediaManager. Call once at startup."""
    return MediaManager(backend=MediaBackend.LOCAL)


def detect_in_frame(frame: np.ndarray) -> DetectionResult:
    """Run face detection on a pre-captured frame."""
    detector = cv2.CascadeClassifier(HAAR_CASCADE)
    if detector.empty():
        raise RuntimeError(f"Failed to load Haar cascade from {HAAR_CASCADE}")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
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
    for x, y, w, h in result.boxes:
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
    return annotated
