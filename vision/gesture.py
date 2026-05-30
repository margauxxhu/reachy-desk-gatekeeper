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
    """Return True if the hand is pointing upward for CONFIRM_FRAMES consecutive frames.

    Gesture: index fingertip (landmark 8) is above the wrist (landmark 0) in frame.
    Works at any camera angle — no absolute position required.
    """
    interval = 1.0 / sample_fps
    deadline = time.monotonic() + duration
    consecutive = 0

    log.info("Waiting for hand raise gesture (point hand upward)")

    while time.monotonic() < deadline:
        t0 = time.monotonic()

        frame = media.get_frame()
        if frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = _hands.process(rgb)

            if res.multi_hand_landmarks:
                lm = res.multi_hand_landmarks[0].landmark
                wrist_y = lm[0].y       # landmark 0 = wrist
                fingertip_y = lm[8].y   # landmark 8 = index fingertip
                pointing_up = fingertip_y < wrist_y
                log.info("Hand detected — wrist_y=%.3f tip_y=%.3f pointing_up=%s streak=%d",
                         wrist_y, fingertip_y, pointing_up, consecutive)
                if pointing_up:
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
