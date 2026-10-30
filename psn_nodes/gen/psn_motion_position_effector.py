"""
PSN_Motion_Position_Effector

Pure-logic implementation of a position animation effector for video frames.

Because the original spec requires torch/numpy for actual pixel translation,
this module implements ONLY the secure, pure-Python logic:
  - Config validation (positions, duration, easing)
  - Easing curve evaluation (linear, ease_in, ease_out, ease_in_out)
  - Per-frame offset computation (dx, dy for each frame index)
  - Trajectory generation (list of (x, y) offsets for all frames)

The node accepts plain values (ints, strings) and returns:
  - animated_offsets: A list of (dx, dy) tuples representing the translation
    offset for each frame in the animation.
  - trajectory: A list of (x, y) absolute positions for each frame.
  - status: A string indicating success or error.

No GPU, no torch, no numpy, no file I/O, no network.
"""

import math

# Easing functions: t in [0, 1] -> eased value in [0, 1]
def _ease_linear(t):
    return t

def _ease_in(t):
    return t * t

def _ease_out(t):
    return 1.0 - (1.0 - t) * (1.0 - t)

def _ease_in_out(t):
    if t < 0.5:
        return 2.0 * t * t
    else:
        f = (1.0 - t) * 2.0
        return 1.0 - (f * f) / 2.0

_EASING_FUNCS = {
    "linear": _ease_linear,
    "ease_in": _ease_in,
    "ease_out": _ease_out,
    "ease_in_out": _ease_in_out,
}

_EASING_MODES = list(_EASING_FUNCS.keys())


def validate_motion_config(start_pos, end_pos, duration, easing):
    """
    Validate motion configuration parameters.
    
    Args:
        start_pos: tuple/list of two ints (x, y)
        end_pos: tuple/list of two ints (x, y)
        duration: int, number of frames
        easing: str, one of the easing modes
    
    Returns:
        (bool, str): (is_valid, error_message)
    """
    # Validate start_pos
    if not isinstance(start_pos, (tuple, list)) or len(start_pos) != 2:
        return False, "start_pos must be a tuple/list of two integers"
    for i, v in enumerate(start_pos):
        if not isinstance(v, int):
            return False, f"start_pos[{i}] must be an integer, got {type(v).__name__}"
    
    # Validate end_pos
    if not isinstance(end_pos, (tuple, list)) or len(end_pos) != 2:
        return False, "end_pos must be a tuple/list of two integers"
    for i, v in enumerate(end_pos):
        if not isinstance(v, int):
            return False, f"end_pos[{i}] must be an integer, got {type(v).__name__}"
    
    # Validate duration
    if not isinstance(duration, int):
        return False, f"duration must be an integer, got {type(duration).__name__}"
    if duration < 1:
        return False, "duration must be at least 1"
    if duration > 10000:
        return False, "duration must be at most 10000"
    
    # Validate easing
    if not isinstance(easing, str):
        return False, f"easing must be a string, got {type(easing).__name__}"
    if easing not in _EASING_FUNCS:
        return False, f"easing must be one of {_EASING_MODES}, got '{easing}'"
    
    return True, ""


def compute_frame_offsets(start_pos, end_pos, duration, easing):
    """
    Compute the translation offset (dx, dy) for each frame in the animation.
    
    Args:
        start_pos: (x, y) starting position
        end_pos: (x, y) ending position
        duration: number of frames
        easing: easing function name
    
    Returns:
        list of (dx, dy) tuples, one per frame
    """
    ease_func = _EASING_FUNCS[easing]
    dx_total = end_pos[0] - start_pos[0]
    dy_total = end_pos[1] - start_pos[1]
    
    offsets = []
    for i in range(duration):
        if duration == 1:
            t = 1.0
        else:
            t = i / (duration - 1)
        eased_t = ease_func(t)
        dx = int(round(dx_total * eased_t))
        dy = int(round(dy_total * eased_t))
        offsets.append((dx, dy))
    
    return offsets


def compute_trajectory(start_pos, end_pos, duration, easing):
    """
    Compute the absolute position (x, y) for each frame in the animation.
    
    Args:
        start_pos: (x, y) starting position
        end_pos: (x, y) ending position
        duration: number of frames
        easing: easing function name
    
    Returns:
        list of (x, y) tuples, one per frame
    """
    offsets = compute_frame_offsets(start_pos, end_pos, duration, easing)
    trajectory = []
    for i, (dx, dy) in enumerate(offsets):
        x = start_pos[0] + dx
        y = start_pos[1] + dy
        trajectory.append((x, y))
    return trajectory


class PSN_Motion_Position_Effector:
    """
    Applies position animation trajectory computation to video frames.
    
    This node computes the per-frame translation offsets and absolute positions
    for a motion animation from start_pos to end_pos over a given duration
    with a specified easing curve.
    
    Inputs:
        start_pos_x, start_pos_y: Starting x, y position (int)
        end_pos_x, end_pos_y: Ending x, y position (int)
        duration: Number of frames for the animation (int)
        easing: Easing mode (combo)
    
    Outputs:
        animated_offsets: List of (dx, dy) tuples for each frame
        trajectory: List of (x, y) absolute positions for each frame
        status: String indicating success or error
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "start_pos_x": ("INT", {"default": 0, "min": -100000, "max": 100000}),
                "start_pos_y": ("INT", {"default": 0, "min": -100000, "max": 100000}),
                "end_pos_x": ("INT", {"default": 100, "min": -100000, "max": 100000}),
                "end_pos_y": ("INT", {"default": 50, "min": -100000, "max": 100000}),
                "duration": ("INT", {"default": 30, "min": 1, "max": 10000}),
                "easing": (_EASING_MODES,),
            },
            "optional": {},
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("animated_offsets", "trajectory", "status")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Motion"
    
    def run(self, start_pos_x, start_pos_y, end_pos_x, end_pos_y, duration, easing):
        start_pos = (start_pos_x, start_pos_y)
        end_pos = (end_pos_x, end_pos_y)
        
        is_valid, error_msg = validate_motion_config(start_pos, end_pos, duration, easing)
        if not is_valid:
            return ("", "", f"Error: {error_msg}")
        
        offsets = compute_frame_offsets(start_pos, end_pos, duration, easing)
        trajectory = compute_trajectory(start_pos, end_pos, duration, easing)
        
        # Serialize offsets and trajectory as JSON-like strings
        offsets_str = str(offsets)
        trajectory_str = str(trajectory)
        
        return (offsets_str, trajectory_str, "success")


NODE_CLASS_MAPPINGS = {
    "PSN_Motion_Position_Effector": PSN_Motion_Position_Effector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Motion_Position_Effector": "PSN Motion Position Effector",
}
