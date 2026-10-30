"""PSN_Tiled_Renderer: pure-logic tiling planner and stitcher for large image jobs.

This module implements ONLY the secure, pure-Python logic of a tiled renderer:
- validating tile_size / overlap / image dimensions,
- computing the tile grid (start offsets and tile sizes) for a given image,
- stitching a list of rendered tiles back into a single image using linear
  cross-fade blending in the overlap regions to avoid seams.

It does NOT touch torch, ComfyUI, Pillow, files, sockets, or the network.
The `image` input is represented as a plain nested list of floats (rows of
pixels, each pixel a list of channel values). The `model` input is accepted
but only validated as a non-empty string identifier; no model is loaded or
called. The actual per-tile generation is out of scope for this pure-logic
node; the stitcher accepts pre-rendered tiles.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Rendering"

# Placeholder for ComfyUI's ANY type (not available in pure-logic context).
ANY = "ANY"

# Allowed blend modes for stitching.
BLEND_MODES = ("linear", "none")


def _validate_positive_int(value, name):
    """Return (ok, reason, coerced_value)."""
    if isinstance(value, bool):
        return (False, "%s must be an integer, got bool" % name, None)
    if not isinstance(value, int):
        return (False, "%s must be an integer, got %s" % (name, type(value).__name__), None)
    if value <= 0:
        return (False, "%s must be > 0, got %d" % (name, value), None)
    return (True, "ok", value)


def _validate_non_negative_int(value, name):
    """Return (ok, reason, coerced_value) for non-negative integers."""
    if isinstance(value, bool):
        return (False, "%s must be an integer, got bool" % name, None)
    if not isinstance(value, int):
        return (False, "%s must be an integer, got %s" % (name, type(value).__name__), None)
    if value < 0:
        return (False, "%s must be >= 0, got %d" % (name, value), None)
    return (True, "ok", value)


def _validate_image(image):
    """Validate a nested-list image. Returns (ok, reason, height, width, channels)."""
    if not isinstance(image, list) or len(image) == 0:
        return (False, "image must be a non-empty list of rows", 0, 0, 0)
    height = len(image)
    first_row = image[0]
    if not isinstance(first_row, list) or len(first_row) == 0:
        return (False, "image rows must be non-empty lists of pixels", 0, 0, 0)
    width = len(first_row)
    first_pixel = first_row[0]
    if not isinstance(first_pixel, list) or len(first_pixel) == 0:
        return (False, "image pixels must be non-empty lists of channel values", 0, 0, 0)
    channels = len(first_pixel)
    for r, row in enumerate(image):
        if not isinstance(row, list) or len(row) != width:
            return (False, "image row %d has inconsistent width" % r, 0, 0, 0)
        for c, pixel in enumerate(row):
            if not isinstance(pixel, list) or len(pixel) != channels:
                return (False, "image pixel (%d,%d) has inconsistent channels" % (r, c), 0, 0, 0)
            for v in pixel:
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    return (False, "image channel values must be numbers", 0, 0, 0)
    return (True, "ok", height, width, channels)


def compute_tile_grid(height, width, tile_size, overlap):
    """Compute tile start offsets and sizes.

    Returns a list of (row_start, col_start, tile_h, tile_w) tuples.
    Tiles are laid out so that consecutive tiles overlap by `overlap` pixels.
    The last tile in each dimension is clamped so it does not exceed the image.
    """
    if tile_size <= 0:
        raise ValueError("tile_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= tile_size:
        raise ValueError("overlap must be < tile_size")

    step = tile_size - overlap
    tiles = []
    row_starts = []
    r = 0
    while r < height:
        row_starts.append(r)
        if r + tile_size >= height:
            break
        r += step
    col_starts = []
    c = 0
    while c < width:
        col_starts.append(c)
        if c + tile_size >= width:
            break
        c += step

    for rs in row_starts:
        for cs in col_starts:
            th = min(tile_size, height - rs)
            tw = min(tile_size, width - cs)
            tiles.append((rs, cs, th, tw))
    return tiles


def _extract_tile(image, rs, cs, th, tw):
    """Extract a tile (list of rows) from the image."""
    tile = []
    for r in range(rs, rs + th):
        row = []
        for c in range(cs, cs + tw):
            row.append(list(image[r][c]))
        tile.append(row)
    return tile


def _blend_pixel(a, b, weight):
    """Linear blend of two channel lists: a*(1-weight) + b*weight."""
    return [a[i] * (1.0 - weight) + b[i] * weight for i in range(len(a))]


def stitch_tiles(image, tiles, tile_images, blend_mode="linear"):
    """Stitch rendered tiles back into a full image.

    `tiles` is the list of (rs, cs, th, tw) from compute_tile_grid.
    `tile_images` is a list of rendered tiles (same order), each a nested list
    of the same size as the corresponding tile.
    Overlap regions are blended using a linear cross-fade based on the
    position within the overlap.
    """
    if len(tiles) != len(tile_images):
        raise ValueError("tiles and tile_images length mismatch")
    height = len(image)
    width = len(image[0])
    channels = len(image[0][0])

    # Initialize output with zeros.
    out = [[[0.0] * channels for _ in range(width)] for _ in range(height)]
    # Accumulate weights for blending.
    weight = [[0.0 for _ in range(width)] for _ in range(height)]

    for (rs, cs, th, tw), tile_img in zip(tiles, tile_images):
        if len(tile_img) != th or len(tile_img[0]) != tw:
            raise ValueError("tile image size mismatch")
        for r in range(th):
            for c in range(tw):
                gr = rs + r
                gc = cs + c
                pixel = tile_img[r][c]
                if len(pixel) != channels:
                    raise ValueError("tile pixel channel mismatch")
                if blend_mode == "none":
                    # Last write wins; just overwrite.
                    out[gr][gc] = list(pixel)
                    weight[gr][gc] = 1.0
                else:
                    # Linear cross-fade: weight increases from 0 at the top-left
                    # edge of the tile to 1 at the bottom-right edge.
                    wr = (r + 1) / float(th)
                    wc = (c + 1) / float(tw)
                    w = (wr + wc) / 2.0
                    # Accumulate weighted sum.
                    for i in range(channels):
                        out[gr][gc][i] += pixel[i] * w
                    weight[gr][gc] += w

    # Normalize by accumulated weight.
    for r in range(height):
        for c in range(width):
            w = weight[r][c]
            if w > 0:
                for i in range(len(out[r][c])):
                    out[r][c][i] /= w
            else:
                # Should not happen if tiles cover the image, but keep safe.
                out[r][c] = list(image[r][c])

    return out


class PSN_Tiled_Renderer:
    """Plan tiles for a large image and stitch rendered tiles with blending.

    Pure-logic node: validates inputs, computes the tile grid, and stitches
    pre-rendered tiles. No GPU, no model loading, no file/network I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": (ANY,),
                "tile_size": ("INT", {"default": 512, "min": 1, "max": 100000, "step": 1}),
                "overlap": ("INT", {"default": 64, "min": 0, "max": 100000, "step": 1}),
                "model": ("STRING", {"default": "default_model", "multiline": False}),
                "blend_mode": (list(BLEND_MODES),),
            },
            "optional": {
                "tile_images": (ANY,),
            },
        }

    RETURN_TYPES = (ANY, "STRING", "STRING")
    RETURN_NAMES = ("rendered_image", "tile_grid", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, tile_size, overlap, model, blend_mode, tile_images=None):
        # Validate model.
        if not isinstance(model, str) or len(model.strip()) == 0:
            return (None, "[]", "model must be a non-empty string")

        # Validate tile_size and overlap.
        ok, why, ts = _validate_positive_int(tile_size, "tile_size")
        if not ok:
            return (None, "[]", why)
        ok, why, ov = _validate_non_negative_int(overlap, "overlap")
        if not ok:
            return (None, "[]", why)
        if ov >= ts:
            return (None, "[]", "overlap must be < tile_size")

        # Validate image.
        ok, why, height, width, channels = _validate_image(image)
        if not ok:
            return (None, "[]", why)

        # Compute tile grid.
        try:
            tiles = compute_tile_grid(height, width, ts, ov)
        except ValueError as e:
            return (None, "[]", str(e))

        tile_grid_str = str(tiles)

        # If tile_images provided, stitch them.
        if tile_images is not None:
            if not isinstance(tile_images, list) or len(tile_images) != len(tiles):
                return (None, tile_grid_str, "tile_images must be a list matching tile count")
            try:
                rendered = stitch_tiles(image, tiles, tile_images, blend_mode)
            except ValueError as e:
                return (None, tile_grid_str, str(e))
            return (rendered, tile_grid_str, "ok")

        # If no tile_images, return the original image as a placeholder
        # (pure-logic node does not perform generation).
        return (image, tile_grid_str, "ok (no tile_images provided; returned input)")


NODE_CLASS_MAPPINGS = {
    "PSN_Tiled_Renderer": PSN_Tiled_Renderer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Tiled_Renderer": "PSN Tiled Renderer",
}
