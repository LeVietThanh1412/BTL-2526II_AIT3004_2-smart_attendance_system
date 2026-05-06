import os
import tempfile
from typing import List

import cv2
import numpy as np
from fastapi import HTTPException, status


def extract_frames_from_video(video_bytes: bytes, frame_interval: int = 1) -> List[np.ndarray]:
    """
    Extract frames from video at specified interval (in seconds).
    Trich xuat khung hinh tu video voi khoang thoi gian cu the (tinh bang giay).

    Args:
        video_bytes: Raw video file bytes
        frame_interval: Time interval between frames in seconds (default: 1 second)

    Returns:
        List of numpy arrays representing video frames

    Raises:
        HTTPException: If video cannot be read or no frames can be extracted
    """
    tmp_file = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    try:
        tmp_file.write(video_bytes)
        tmp_file.flush()
        tmp_file.close()

        cap = cv2.VideoCapture(tmp_file.name)
        if not cap.isOpened():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot read video file. Ensure it's a valid video format.",
            )

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0
        frame_skip = max(1, int(fps * frame_interval))
        frames = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_skip == 0:
                frames.append(frame)

            frame_count += 1

        cap.release()
    finally:
        try:
            os.unlink(tmp_file.name)
        except OSError:
            pass

    if not frames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No frames could be extracted from video.",
        )

    return frames
