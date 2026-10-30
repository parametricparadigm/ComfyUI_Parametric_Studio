"""Pure-logic batch latent management for video.

This module implements the *shape metadata* operations for batch latent
management (repeat, split, merge) without touching any tensor data.
Because the spec depends on torch (GPU tensors), only the secure,
pure-logic part is implemented here: validating latent shape metadata
and computing the resulting batch dimensions.

A "latent" in this module is represented as a plain dict with a "shape"
key (a tuple/list of ints) and an optional "frames" key. The batch
dimension is assumed to be the first element of the shape.

No torch, no ComfyUI imports, no I/O, no network.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/VideoLatent"

# Sentinel type name used in INPUT_TYPES for the latent metadata dict.
LATENT = "LATENT"


def _validate_latent(latent, name="latent"):
    """Validate a latent metadata dict and return its shape tuple.

    Returns (shape_tuple, error_string). error_string is None on success.
    """
    if not isinstance(latent, dict):
        return None, "%s must be a dict with a 'shape' key" % name
    if "shape" not in latent:
        return None, "%s dict must contain a 'shape' key" % name
    shape = latent["shape"]
    if not isinstance(shape, (list, tuple)):
        return None, "%s 'shape' must be a list or tuple of ints" % name
    if len(shape) == 0:
        return None, "%s 'shape' must not be empty" % name
    for i, dim in enumerate(shape):
        if not isinstance(dim, int) or isinstance(dim, bool):
            return None, "%s shape dimension %d must be an int, got %r" % (name, i, dim)
        if dim < 0:
            return None, "%s shape dimension %d must be >= 0, got %d" % (name, i, dim)
    return tuple(shape), None


def _batch_size(shape):
    """Return the batch dimension (first element) of a shape tuple."""
    return shape[0]


def _make_latent(shape, frames=None):
    """Build a latent metadata dict from a shape tuple."""
    d = {"shape": list(shape)}
    if frames is not None:
        d["frames"] = frames
    return d


class PSN_Latent_Batch_Repeat:
    """Repeat (tile) the batch dimension of a latent N times.

    Pure-logic: computes the new batch size and returns updated latent
    metadata. No tensor data is touched.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": (LATENT,),
                "repeat_count": ("INT", {"default": 1, "min": 1, "max": 1024}),
            }
        }

    RETURN_TYPES = (LATENT,)
    RETURN_NAMES = ("latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, repeat_count):
        shape, err = _validate_latent(latent, "latent")
        if err:
            raise ValueError(err)
        if not isinstance(repeat_count, int) or isinstance(repeat_count, bool):
            raise ValueError("repeat_count must be an int")
        if repeat_count < 1:
            raise ValueError("repeat_count must be >= 1")
        new_batch = _batch_size(shape) * repeat_count
        new_shape = (new_batch,) + shape[1:]
        frames = latent.get("frames")
        return (_make_latent(new_shape, frames),)


class PSN_Latent_Batch_Split:
    """Split the batch dimension of a latent at split_index.

    Pure-logic: computes the two resulting batch sizes and returns two
    latent metadata dicts. No tensor data is touched.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": (LATENT,),
                "split_index": ("INT", {"default": 1, "min": 0, "max": 1024}),
            }
        }

    RETURN_TYPES = (LATENT, LATENT)
    RETURN_NAMES = ("latent_first", "latent_second")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, split_index):
        shape, err = _validate_latent(latent, "latent")
        if err:
            raise ValueError(err)
        if not isinstance(split_index, int) or isinstance(split_index, bool):
            raise ValueError("split_index must be an int")
        batch = _batch_size(shape)
        if split_index < 0 or split_index > batch:
            raise ValueError(
                "split_index %d out of range for batch size %d" % (split_index, batch)
            )
        first_batch = split_index
        second_batch = batch - split_index
        frames = latent.get("frames")
        first_shape = (first_batch,) + shape[1:]
        second_shape = (second_batch,) + shape[1:]
        return (_make_latent(first_shape, frames), _make_latent(second_shape, frames))


class PSN_Latent_Batch_Merge:
    """Concatenate two latents along the batch axis.

    Pure-logic: validates that both latents have compatible non-batch
    dimensions, computes the merged batch size, and returns updated
    latent metadata. No tensor data is touched.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent_a": (LATENT,),
                "latent_b": (LATENT,),
            }
        }

    RETURN_TYPES = (LATENT,)
    RETURN_NAMES = ("latent",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent_a, latent_b):
        shape_a, err_a = _validate_latent(latent_a, "latent_a")
        if err_a:
            raise ValueError(err_a)
        shape_b, err_b = _validate_latent(latent_b, "latent_b")
        if err_b:
            raise ValueError(err_b)
        if shape_a[1:] != shape_b[1:]:
            raise ValueError(
                "Non-batch dimensions must match: %r vs %r" % (shape_a[1:], shape_b[1:])
            )
        merged_batch = _batch_size(shape_a) + _batch_size(shape_b)
        merged_shape = (merged_batch,) + shape_a[1:]
        frames_a = latent_a.get("frames")
        frames_b = latent_b.get("frames")
        frames = frames_a if frames_a is not None else frames_b
        return (_make_latent(merged_shape, frames),)


NODE_CLASS_MAPPINGS = {
    "PSN_Latent_Batch_Repeat": PSN_Latent_Batch_Repeat,
    "PSN_Latent_Batch_Split": PSN_Latent_Batch_Split,
    "PSN_Latent_Batch_Merge": PSN_Latent_Batch_Merge,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Latent_Batch_Repeat": "Latent Batch Repeat",
    "PSN_Latent_Batch_Split": "Latent Batch Split",
    "PSN_Latent_Batch_Merge": "Latent Batch Merge",
}
