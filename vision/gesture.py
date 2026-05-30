"""Nod gesture detection using face Y-position tracking."""

import time
import logging
from typing import Optional

from reachy_mini.media.media_manager import MediaManager

from vision.face_detection import detect_in_frame

log = logging.getLogger(__name__)

# Fraction of image height that counts as a nod dip — lower = more sensitive
NOD_THRESHOLD = 0.04
# EMA smoothing factor (0=no smoothing, 1=instant)
EMA_ALPHA = 0.3


def detect_nods(
    media: MediaManager,
    duration: float = 8.0,
    sample_fps: float = 5.0,
    required_nods: int = 2,
) -> bool:
    """Sample frames for `duration` seconds and return True if `required_nods` nods detected.

    A nod is defined as the face Y-center dropping below baseline by NOD_THRESHOLD
    (head tilts down) and then recovering back up.
    """
    interval = 1.0 / sample_fps
    deadline = time.monotonic() + duration

    y_history: list[float] = []
    baseline: Optional[float] = None

    while time.monotonic() < deadline:
        t0 = time.monotonic()

        frame = media.get_frame()
        if frame is not None:
            result = detect_in_frame(frame)
            if result.face_detected and result.boxes:
                x, y, w, h = max(result.boxes, key=lambda b: b[2] * b[3])
                y_norm = (y + h / 2) / frame.shape[0]
                y_history.append(y_norm)
                if baseline is None:
                    baseline = y_norm
                    log.debug("Nod baseline set: %.3f", baseline)

        elapsed = time.monotonic() - t0
        wait = interval - elapsed
        if wait > 0:
            time.sleep(wait)

    if baseline is None or len(y_history) < 4:
        log.info("Not enough face samples for nod detection (%d frames)", len(y_history))
        return False

    nod_count = _count_nods(y_history, baseline)
    log.info("Nod detection complete — %d nods detected (need %d)", nod_count, required_nods)
    return nod_count >= required_nods


def _count_nods(y_values: list[float], baseline: float) -> int:
    """Count down-then-up cycles in a normalised Y time series."""
    # EMA smoothing
    smoothed = [y_values[0]]
    for y in y_values[1:]:
        smoothed.append(smoothed[-1] * (1 - EMA_ALPHA) + y * EMA_ALPHA)

    nods = 0
    in_nod = False
    for y in smoothed:
        if not in_nod and y > baseline + NOD_THRESHOLD:
            in_nod = True
        elif in_nod and y < baseline + NOD_THRESHOLD * 0.4:
            in_nod = False
            nods += 1

    return nods
