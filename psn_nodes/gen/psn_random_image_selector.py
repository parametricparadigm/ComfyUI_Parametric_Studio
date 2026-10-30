"""
PSN_Random_Image_Selector

Pure-logic, secure-by-design implementation of a random image selector.

This module does NOT perform any file system access, image loading, or GPU
operations. Instead, it implements the core selection logic:
- Validates that a folder path is a non-empty string
- Validates that num_images is a positive integer
- Validates that seed (if provided) is an integer
- Given a list of file names (simulating a directory listing), shuffles them
  using the provided seed (or a random seed if none is given), and selects
  the first num_images entries

The node is designed to be used in conjunction with a separate file-scanning
node that provides the list of available image file names. This module
handles only the deterministic selection logic.

Inputs:
    folder_path (STRING): The path to the folder (validated for format only)
    num_images (INT): Number of images to select (must be >= 1)
    seed (INT, optional): Random seed for reproducibility
    file_names (LIST[STRING], optional): List of available image file names
        (simulates the result of scanning the folder)

Outputs:
    selected_indices (LIST[INT]): Indices into the original file_names list
    selected_file_names (LIST[STRING]): The selected file names
    file_paths (LIST[STRING]): Full paths constructed from folder_path + file name
    reason (STRING): Human-readable explanation of the selection or error
"""

import random
import string

# Allowed characters for file names (basic validation)
_ALLOWED_FILE_CHARS = set(string.ascii_letters + string.digits + "._-")

# Allowed characters for folder path segments
_ALLOWED_PATH_CHARS = set(string.ascii_letters + string.digits + "._-/\\")


def _validate_folder_path(folder_path):
    """
    Validate that folder_path is a non-empty string with reasonable characters.
    Returns (is_valid, error_message).
    """
    if not isinstance(folder_path, str):
        return False, "folder_path must be a string"
    if not folder_path.strip():
        return False, "folder_path must not be empty"
    # Check for null bytes or control characters
    for ch in folder_path:
        if ord(ch) < 32 or ord(ch) == 127:
            return False, "folder_path contains invalid control characters"
    return True, ""


def _validate_num_images(num_images):
    """
    Validate that num_images is a positive integer.
    Returns (is_valid, error_message).
    """
    if not isinstance(num_images, int) or isinstance(num_images, bool):
        return False, "num_images must be an integer"
    if num_images < 1:
        return False, "num_images must be at least 1"
    return True, ""


def _validate_seed(seed):
    """
    Validate that seed is an integer or None.
    Returns (is_valid, error_message).
    """
    if seed is None:
        return True, ""
    if not isinstance(seed, int) or isinstance(seed, bool):
        return False, "seed must be an integer or None"
    return True, ""


def _validate_file_names(file_names):
    """
    Validate that file_names is a list of strings.
    Returns (is_valid, error_message).
    """
    if file_names is None:
        return True, ""  # No file names provided; selection will be empty
    if not isinstance(file_names, (list, tuple)):
        return False, "file_names must be a list of strings"
    for i, name in enumerate(file_names):
        if not isinstance(name, str):
            return False, f"file_names[{i}] must be a string"
        if not name.strip():
            return False, f"file_names[{i}] must not be empty"
    return True, ""


def select_random_images(folder_path, num_images, seed, file_names=None):
    """
    Core selection logic: given a list of file names, shuffle and select
    the first num_images entries.

    Args:
        folder_path: Validated folder path string
        num_images: Validated positive integer
        seed: Optional integer seed for reproducibility
        file_names: Optional list of file name strings

    Returns:
        (selected_indices, selected_file_names, file_paths, reason)
    """
    if file_names is None:
        file_names = []

    if not file_names:
        return [], [], [], "No files available in folder"

    # Clamp num_images to available count
    actual_count = min(num_images, len(file_names))

    # Create a list of indices and shuffle
    indices = list(range(len(file_names)))

    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    rng.shuffle(indices)

    selected_indices = indices[:actual_count]
    selected_file_names = [file_names[i] for i in selected_indices]

    # Construct full paths
    normalized_folder = folder_path.rstrip("/\\")
    file_paths = [f"{normalized_folder}/{name}" for name in selected_file_names]

    reason = f"Selected {actual_count} of {len(file_names)} available files"
    if seed is not None:
        reason += f" (seed={seed})"

    return selected_indices, selected_file_names, file_paths, reason


class PSN_Random_Image_Selector:
    """
    Select random images from a directory for testing.

    This node implements the pure-logic selection portion: it validates inputs,
    shuffles a provided list of file names using an optional seed, and returns
    the selected indices, file names, and constructed file paths.

    It does NOT scan the file system or load images. Use a separate file-listing
    node to provide the file_names input.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "", "multiline": False}),
                "num_images": ("INT", {"default": 3, "min": 1, "max": 10000, "step": 1}),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": -2147483648, "max": 2147483647, "step": 1}),
                "file_names": ("LIST[STRING]", {"default": []}),
            },
        }

    RETURN_TYPES = ("LIST[INT]", "LIST[STRING]", "LIST[STRING]", "STRING")
    RETURN_NAMES = ("selected_indices", "selected_file_names", "file_paths", "reason")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Selection"

    def run(self, folder_path, num_images, seed=0, file_names=None):
        # Validate inputs
        valid, err = _validate_folder_path(folder_path)
        if not valid:
            return ([], [], [], f"Validation error: {err}")

        valid, err = _validate_num_images(num_images)
        if not valid:
            return ([], [], [], f"Validation error: {err}")

        # Treat seed=0 as "no seed" for backward compatibility, or use as-is
        # We'll use the seed value directly; if user wants no seed, they can
        # pass a large random value. For reproducibility, seed=0 is valid.
        valid, err = _validate_seed(seed)
        if not valid:
            return ([], [], [], f"Validation error: {err}")

        valid, err = _validate_file_names(file_names)
        if not valid:
            return ([], [], [], f"Validation error: {err}")

        # Perform selection
        selected_indices, selected_file_names, file_paths, reason = select_random_images(
            folder_path, num_images, seed, file_names
        )

        return (selected_indices, selected_file_names, file_paths, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Random_Image_Selector": PSN_Random_Image_Selector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Random_Image_Selector": "PSN Random Image Selector",
}
