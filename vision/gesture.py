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
    """Return True if a raised fist is held for CONFIRM_FRAMES consecutive frames.

    Gesture: make a fist (3+ fingertips curled below their PIP knuckles).
    Works at any camera angle and position.
    """
    interval = 1.0 / sample_fps
    deadline = time.monotonic() + duration
    consecutive = 0

    log.info("Waiting for fist gesture")

    while time.monotonic() < deadline:
        t0 = time.monotonic()

        frame = media.get_frame()
        if frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = _hands.process(rgb)

            if res.multi_hand_landmarks:
                lm = res.multi_hand_landmarks[0].landmark
                # Fist: each fingertip (8,12,16,20) curled below its PIP knuckle (6,10,14,18)
                # Y increases downward, so curled = tip_y > pip_y
                finger_pairs = [(8, 6), (12, 10), (16, 14), (20, 18)]
                curled = sum(lm[tip].y > lm[pip].y for tip, pip in finger_pairs)
                is_fist = curled >= 3
                log.info("Hand detected — curled_fingers=%d/4 fist=%s streak=%d",
                         curled, is_fist, consecutive)
                if is_fist:
                    consecutive += 1
                    if consecutive >= CONFIRM_FRAMES:
                        log.info("Fist confirmed after %d frames", consecutive)
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
