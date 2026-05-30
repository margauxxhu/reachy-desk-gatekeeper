"""Hand-raise gesture detection using MediaPipe Hands."""

import time
import logging

import mediapipe as mp

from reachy_mini.media.media_manager import MediaManager

log = logging.getLogger(__name__)

_hands = mp.solutions.hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5,
)

# Fraction of frame height — wrist must be above this to count as raised
RAISE_THRESHOLD = 0.4
# How many consecutive frames with hand raised to confirm the gesture
CONFIRM_FRAMES = 3


def detect_hand_raise(
    media: MediaManager,
    duration: float = 8.0,
    sample_fps: float = 10.0,
) -> bool:
    """Return True if a raised hand is held for CONFIRM_FRAMES consecutive frames.

    Raise = wrist landmark Y-coordinate above RAISE_THRESHOLD (top 40% of frame).
    MediaPipe Y is 0 at top, 1 at bottom, so raised hand → small Y value.
    """
    interval = 1.0 / sample_fps
    deadline = time.monotonic() + duration
    consecutive = 0

    while time.monotonic() < deadline:
        t0 = time.monotonic()

        frame = media.get_frame()
        if frame is not None:
            import cv2
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = _hands.process(rgb)

            if res.multi_hand_landmarks:
                # wrist is landmark 0
                wrist_y = res.multi_hand_landmarks[0].landmark[0].y
                if wrist_y < RAISE_THRESHOLD:
                    consecutive += 1
                    log.debug("Hand raised — wrist_y=%.3f, streak=%d", wrist_y, consecutive)
                    if consecutive >= CONFIRM_FRAMES:
                        log.info("Hand raise confirmed after %d frames", consecutive)
                        return True
                else:
                    consecutive = 0
            else:
                consecutive = 0

        elapsed = time.monotonic() - t0
        wait = interval - elapsed
        if wait > 0:
            time.sleep(wait)

    log.info("Hand raise not detected within %.1fs", duration)
    return False
