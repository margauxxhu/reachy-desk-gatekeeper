"""Hand-raise gesture detection using MediaPipe Hands."""

import time
import logging

import cv2
import mediapipe as mp

from reachy_mini.media.media_manager import MediaManager

log = logging.getLogger(__name__)

_hands = mp.solutions.hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5,
)

# How many consecutive frames with hand above face to confirm the gesture
CONFIRM_FRAMES = 2


def detect_hand_raise(
    media: MediaManager,
    face_y_norm: float,
    duration: float = 8.0,
    sample_fps: float = 10.0,
) -> bool:
    """Return True if wrist is above the face Y position for CONFIRM_FRAMES frames.

    Uses the face Y-centre from the search phase as the threshold so detection
    is robust to any camera angle — raise your hand above your face to signal.
    MediaPipe Y is 0 at top, 1 at bottom, so above face → wrist_y < face_y_norm.
    """
    interval = 1.0 / sample_fps
    deadline = time.monotonic() + duration
    consecutive = 0

    log.info("Waiting for hand raise — face_y=%.3f (raise wrist above this)", face_y_norm)

    while time.monotonic() < deadline:
        t0 = time.monotonic()

        frame = media.get_frame()
        if frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = _hands.process(rgb)

            if res.multi_hand_landmarks:
                wrist_y = res.multi_hand_landmarks[0].landmark[0].y
                log.info("Hand detected — wrist_y=%.3f face_y=%.3f raised=%s streak=%d",
                         wrist_y, face_y_norm, wrist_y < face_y_norm, consecutive)
                if wrist_y < face_y_norm:
                    consecutive += 1
                    if consecutive >= CONFIRM_FRAMES:
                        log.info("Hand raise confirmed after %d frames", consecutive)
                        return True
                else:
                    consecutive = 0
            else:
                log.debug("No hand detected this frame")
                consecutive = 0

        elapsed = time.monotonic() - t0
        wait = interval - elapsed
        if wait > 0:
            time.sleep(wait)

    log.info("Hand raise not detected within %.1fs", duration)
    return False
