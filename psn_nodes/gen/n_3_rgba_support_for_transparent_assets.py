"""PSN RGBA support for transparent assets (pure-logic core).

This module implements the *pure-logic, secure-by-design* part of the
"RGBA Support for Transparent Assets" spec. The real VAE encode/decode
requires torch + ComfyUI + an AlphaVAE model, which are intentionally NOT
used here. Instead we operate on plain values:

  * RGBA images are represented as JSON text (a list of rows, each row a
    list of [r, g, b, a] pixel lists) OR as a flat list of pixel lists.
  * Latents are represented as JSON text (a list of rows, each row a list
    of [r, g, b, a] latent values) OR as a flat list of value lists.

The encode/decode logic is a deterministic, lossless channel-preserving
transform (a stand-in for the VAE) that guarantees the alpha channel is
carried through the latent representation and restored on decode. This
lets us unit-test the *data-flow contract* (alpha preserved, 4 channels
in/out, transparent center stays transparent) without any GPU or model.

No network, no file/OS access, no torch, no comfy imports.
"""

import json

CAT = "ParametricStudio/AlphaVAE"

# Channel count for RGBA.
_CHANNELS = 4
# Allowed value range for each channel (0..1 float or 0..255 int).
_MIN_V = 0.0
_MAX_V = 255.0


def _is_number(x):
    """Return True if x is an int/float (not bool)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _normalize_pixel(px):
    """Validate a single pixel is a list of 4 numbers in [0, 255].

    Returns a normalized list of floats, or raises ValueError.
    """
    if not isinstance(px, (list, tuple)):
        raise ValueError("pixel must be a list/tuple of 4 numbers")
    if len(px) != _CHANNELS:
        raise ValueError("pixel must have exactly 4 channels (RGBA), got %d" % len(px))
    out = []
    for i, v in enumerate(px):
        if not _is_number(v):
            raise ValueError("pixel channel %d must be a number, got %r" % (i, v))
        if v < _MIN_V or v > _MAX_V:
            raise ValueError("pixel channel %d out of range [0,255]: %r" % (i, v))
        out.append(float(v))
    return out


def _parse_image(text):
    """Parse an RGBA image from JSON text or a nested list.

    Accepts:
      * a JSON string: list of rows, each row a list of [r,g,b,a]
      * a Python list: same shape
    Returns (height, width, rows) where rows is a list of lists of
    normalized pixel lists.
    """
    if isinstance(text, str):
        try:
            data = json.loads(text)
        except (ValueError, TypeError) as e:
            raise ValueError("invalid JSON image: %s" % e)
    elif isinstance(text, (list, tuple)):
        data = list(text)
    else:
        raise ValueError("image must be JSON text or a list of rows")

    if not isinstance(data, (list, tuple)):
        raise ValueError("image must be a list of rows")
    if len(data) == 0:
        raise ValueError("image must have at least one row")

    rows = []
    for r, row in enumerate(data):
        if not isinstance(row, (list, tuple)):
            raise ValueError("row %d must be a list of pixels" % r)
        if len(row) == 0:
            raise ValueError("row %d must have at least one pixel" % r)
        norm_row = [_normalize_pixel(px) for px in row]
        rows.append(norm_row)

    # All rows must have the same width.
    width = len(rows[0])
    for r, row in enumerate(rows):
        if len(row) != width:
            raise ValueError("row %d has width %d, expected %d" % (r, len(row), width))
    return len(rows), width, rows


def _encode_rows(rows):
    """Encode image rows into latent rows (lossless channel-preserving).

    The stand-in VAE maps each pixel to a latent value list of the same
    length, preserving every channel (including alpha) exactly. This
    models an AlphaVAE that keeps the alpha channel in latent space.
    """
    latent_rows = []
    for row in rows:
        latent_row = []
        for px in row:
            # Identity mapping: latent value == pixel value, 4 channels.
            latent_row.append(list(px))
        latent_rows.append(latent_row)
    return latent_rows


def _decode_rows(latent_rows):
    """Decode latent rows back into image rows (lossless)."""
    image_rows = []
    for row in latent_rows:
        image_row = []
        for lv in row:
            image_row.append(list(lv))
        image_rows.append(image_row)
    return image_rows


def _rows_to_json(rows):
    """Serialize rows (list of lists of value lists) to JSON text."""
    return json.dumps(rows)


def _validate_latent(text):
    """Parse and validate a latent (JSON text or nested list).

    Returns (height, width, rows) where each value is a list of 4 numbers.
    """
    if isinstance(text, str):
        try:
            data = json.loads(text)
        except (ValueError, TypeError) as e:
            raise ValueError("invalid JSON latent: %s" % e)
    elif isinstance(text, (list, tuple)):
        data = list(text)
    else:
        raise ValueError("latent must be JSON text or a list of rows")

    if not isinstance(data, (list, tuple)):
        raise ValueError("latent must be a list of rows")
    if len(data) == 0:
        raise ValueError("latent must have at least one row")

    rows = []
    for r, row in enumerate(data):
        if not isinstance(row, (list, tuple)):
            raise ValueError("latent row %d must be a list of values" % r)
        if len(row) == 0:
            raise ValueError("latent row %d must have at least one value" % r)
        norm_row = []
        for c, lv in enumerate(row):
            if not isinstance(lv, (list, tuple)):
                raise ValueError("latent value at (%d,%d) must be a list" % (r, c))
            if len(lv) != _CHANNELS:
                raise ValueError("latent value at (%d,%d) must have 4 channels" % (r, c))
            vals = []
            for i, v in enumerate(lv):
                if not _is_number(v):
                    raise ValueError("latent channel %d at (%d,%d) must be a number" % (i, r, c))
                if v < _MIN_V or v > _MAX_V:
                    raise ValueError("latent channel %d at (%d,%d) out of range [0,255]" % (i, r, c))
                vals.append(float(v))
            norm_row.append(vals)
        rows.append(norm_row)

    width = len(rows[0])
    for r, row in enumerate(rows):
        if len(row) != width:
            raise ValueError("latent row %d has width %d, expected %d" % (r, len(row), width))
    return len(rows), width, rows


class PSN_Alpha_VAE_Encode:
    """Encode an RGBA image into a latent that preserves the alpha channel.

    Pure-logic stand-in for the AlphaVAE encoder: the alpha channel is
    carried through the latent representation exactly.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("STRING", {"multiline": 4, "default": "[]"}),
                "vae": ("STRING", {"default": "alpha_vae.safetensors"}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("latent", "meta")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, vae):
        height, width, rows = _parse_image(image)
        latent_rows = _encode_rows(rows)
        latent_json = _rows_to_json(latent_rows)
        meta = json.dumps({
            "vae": vae,
            "height": height,
            "width": width,
            "channels": _CHANNELS,
            "alpha_preserved": True,
        })
        return (latent_json, meta)


class PSN_Alpha_VAE_Decode:
    """Decode a latent back into an RGBA image, restoring the alpha channel.

    Pure-logic stand-in for the AlphaVAE decoder: the alpha channel is
    restored exactly from the latent representation.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("STRING", {"multiline": 4, "default": "[]"}),
                "vae": ("STRING", {"default": "alpha_vae.safetensors"}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("image", "meta")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, vae):
        height, width, latent_rows = _validate_latent(latent)
        image_rows = _decode_rows(latent_rows)
        image_json = _rows_to_json(image_rows)
        meta = json.dumps({
            "vae": vae,
            "height": height,
            "width": width,
            "channels": _CHANNELS,
            "alpha_restored": True,
        })
        return (image_json, meta)


NODE_CLASS_MAPPINGS = {
    "PSN_Alpha_VAE_Encode": PSN_Alpha_VAE_Encode,
    "PSN_Alpha_VAE_Decode": PSN_Alpha_VAE_Decode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Alpha_VAE_Encode": "PSN Alpha VAE Encode",
    "PSN_Alpha_VAE_Decode": "PSN Alpha VAE Decode",
}
