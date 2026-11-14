"""The frame-rate check used by the US-14 test (DESIGN_f351eee.md OQ-40).

The average over the run must be above 30 frames per second; a single slow
frame does not fail it on its own.
"""

MIN_FPS = 30.0


def average_fps(timestamps):
    """Frames per second over the run: frame intervals / elapsed time."""
    return (len(timestamps) - 1) / (timestamps[-1] - timestamps[0])


def frame_rate_failure(timestamps):
    """None if the average is above 30 fps, otherwise a message with the average."""
    average = average_fps(timestamps)
    if average > MIN_FPS:
        return None
    return f"average frame rate {average:.1f} fps is not above {MIN_FPS:.0f} fps"
