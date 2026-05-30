"""Shared knock logic — used by both the Discord and HTTP rails."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from reachy_mini.media.media_manager import MediaManager

from vision.face_detection import capture_and_detect, DetectionResult
from vision.gesture import detect_hand_raise
from robot.movements import search_for_face, hold_gaze, react_busy, react_available, reset_head

log = logging.getLogger(__name__)

GESTURE_WINDOW_SECONDS = 8


@dataclass
class KnockResult:
    found: bool
    busy: bool
    message: str


def _largest_face_center(result: DetectionResult) -> Optional[Tuple[int, int]]:
    if not result.boxes or result.frame is None:
        return None
    h_img, w_img = result.frame.shape[:2]
    x, y, w, h = max(result.boxes, key=lambda b: b[2] * b[3])
    u = max(1, min(int(x + w / 2), w_img - 1))
    v = max(1, min(int(y + h / 2), h_img - 1))
    return (u, v)


def _face_y_norm(result: DetectionResult) -> float:
    """Normalised Y-centre of the largest detected face (0=top, 1=bottom)."""
    if not result.boxes or result.frame is None:
        return 0.5
    h_img = result.frame.shape[0]
    x, y, w, h = max(result.boxes, key=lambda b: b[2] * b[3])
    return (y + h / 2) / h_img


async def run_knock(robot, media: MediaManager, lock: asyncio.Lock) -> KnockResult:
    """Core knock sequence. Shared by Discord and HTTP rails.

    Uses a lock so concurrent triggers queue rather than clash.
    """
    async with lock:
        loop = asyncio.get_event_loop()

        # ── 1. Search for face ────────────────────────────────────────────────
        if robot is not None:
            face_result = await loop.run_in_executor(
                None, search_for_face, robot, media
            )
        else:
            try:
                r = await loop.run_in_executor(None, capture_and_detect, media)
                face_result = r if r.face_detected else None
            except RuntimeError:
                face_result = None

        if face_result is None:
            if robot is not None:
                await loop.run_in_executor(None, reset_head, robot)
            return KnockResult(
                found=False,
                busy=False,
                message="Couldn't find the user. They may be away from their desk.",
            )

        # ── 2. Lock gaze and wait for hand raise ─────────────────────────────
        face_center = _largest_face_center(face_result)
        face_y = _face_y_norm(face_result)
        if robot is not None and face_center is not None:
            await loop.run_in_executor(None, hold_gaze, robot, face_center)

        # Hand raise = come in (active yes). No gesture = busy (passive default).
        # Threshold is the face Y so detection works at any camera angle.
        raised = await loop.run_in_executor(
            None, detect_hand_raise, media, face_y, float(GESTURE_WINDOW_SECONDS)
        )
        available = raised

        # ── 3. Robot reacts and resets head ──────────────────────────────────
        if robot is not None:
            await loop.run_in_executor(
                None, react_available if available else react_busy, robot
            )

        if available:
            return KnockResult(
                found=True,
                busy=False,
                message="🟢 Come On In — they're free, go ahead!",
            )
        return KnockResult(
            found=True,
            busy=True,
            message="🔴 Not yet — give them a moment.",
        )
