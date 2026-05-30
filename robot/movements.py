"""Reachy Mini movement routines for the Desk Gatekeeper."""

import logging
import time
from typing import Optional, Tuple

from reachy_mini import ReachyMini
from reachy_mini.media.media_manager import MediaManager

from vision.face_detection import detect_in_frame, DetectionResult

log = logging.getLogger(__name__)

# Antenna positions in radians. 0 = upright, ±3.05 = fully drooped.
_ANTENNAS_ALERT = [ 0.0,   0.0  ]   # fully perked
_ANTENNAS_IDLE  = [-0.6,   0.6  ]   # slightly drooped
_ANTENNAS_INIT  = [-0.1745, 0.1745] # SDK default

# World-space scan points (x=forward, y=left, z=up) in metres.
# Tune y-values if the sweep feels too narrow or wide on your desk.
_SCAN_POSITIONS = [
    (0.5,  0.4,  0.05),   # look left
    (0.5,  0.0,  0.05),   # look centre
    (0.5, -0.4,  0.05),   # look right
]


def search_for_face(
    robot: ReachyMini,
    media: MediaManager,
    frames_per_position: int = 3,
    frame_interval: float = 0.2,
) -> Optional[DetectionResult]:
    """Sweep left→centre→right, sampling multiple frames per stop.

    Taking several frames per position makes detection robust against
    single-frame misses from blur or Haar-cascade variance.
    """
    log.info("Searching for face...")

    # Wait for camera pipeline to produce its first frame (up to 10s after startup)
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        if media.get_frame() is not None:
            break
        time.sleep(0.2)
    else:
        log.warning("Camera not ready after 10s — aborting search")
        return None

    robot.goto_target(antennas=_ANTENNAS_IDLE, duration=0.3)

    for x, y, z in _SCAN_POSITIONS:
        try:
            robot.look_at_world(x=x, y=y, z=z, duration=0.5)
        except Exception as exc:
            log.warning("look_at_world failed: %s", exc)
        time.sleep(0.6)  # let head settle before sampling

        for _ in range(frames_per_position):
            frame = media.get_frame()
            if frame is not None:
                result = detect_in_frame(frame)
                if result.face_detected:
                    log.info("Face found at scan position (%.1f, %.1f, %.1f)", x, y, z)
                    return result
            time.sleep(frame_interval)

    log.info("No face found after full scan")
    reset_head(robot)
    return None


def hold_gaze(robot: ReachyMini, face_center: Tuple[int, int]) -> None:
    """Lock gaze onto the detected face and perk antennas — hold during nod window."""
    u, v = face_center
    try:
        robot.look_at_image(u=u, v=v, duration=0.4)
    except Exception as exc:
        log.warning("look_at_image failed: %s", exc)
    robot.goto_target(antennas=_ANTENNAS_ALERT, duration=0.3)


def reset_head(robot: ReachyMini) -> None:
    """Return head to neutral forward position and antennas to idle."""
    try:
        robot.look_at_world(x=0.5, y=0.0, z=0.05, duration=0.5)
    except Exception as exc:
        log.warning("reset_head look_at_world failed: %s", exc)
    robot.goto_target(antennas=_ANTENNAS_IDLE, duration=0.5)


def react_busy(robot: ReachyMini) -> None:
    """No hand raise — signal busy with a slow antenna droop, then reset head."""
    log.info("Reacting: busy")
    robot.goto_target(antennas=[-1.2, 1.2], duration=0.5)
    time.sleep(0.6)
    robot.goto_target(antennas=_ANTENNAS_IDLE, duration=0.8)
    reset_head(robot)


def react_available(robot: ReachyMini) -> None:
    """Hand raise detected — signal available with a quick antenna perk, then reset head."""
    log.info("Reacting: available")
    robot.goto_target(antennas=_ANTENNAS_ALERT, duration=0.3)
    time.sleep(0.4)
    robot.goto_target(antennas=_ANTENNAS_INIT, duration=0.5)
    reset_head(robot)
