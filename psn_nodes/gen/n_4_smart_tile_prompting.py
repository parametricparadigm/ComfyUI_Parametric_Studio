"""PSN_Smart_Tile_Prompter (pure-logic, secure-by-design).

This node implements ONLY the deterministic, offline part of "Smart Tile
Prompting": it computes the tile grid for an image (from its width/height,
tile size and overlap) and builds a deterministic, non-empty prompt string
for every tile.

The real VLM / LLaVA inference (torch, transformers, pillow, network, GPU)
is intentionally NOT performed here. Instead, the node takes plain values
(width, height, tile_size, overlap, model name) and returns:

  * TILE_PROMPTS : list[str]  - one deterministic prompt per tile
  * TILE_COORDS  : list[list[int]] - [x, y, w, h] for each tile

The prompt text is a stable, content-free placeholder that downstream
tooling can later replace with real VLM output. This keeps the node
pure-Python (standard library only), with no torch/comfy imports, no
network, no file/OS access, no eval/exec and no dunder tricks.
"""

import math

try:
    from psn import expr, orchestration
except Exception:  # pragma: no cover - optional helpers
    expr = None
    orchestration = None

CAT = "ParametricStudio/SmartTile"

# Allowed vision-language model identifiers (allow-list, secure-by-design).
ALLOWED_MODELS = (
    "llava-1.5-7b",
    "llava-1.5-13b",
    "llava-1.6-7b",
    "llava-1.6-13b",
    "llava-1.6-34b",
    "llava-1.6-34b-hf",
    "llava-1.6-mistral-7b",
    "llava-1.6-mistral-7b-hf",
    "llava-1.6-vicuna-7b",
    "llava-1.6-vicuna-7b-hf",
    "llava-1.6-vicuna-13b",
    "llava-1.6-vicuna-13b-hf",
    "llava-1.6-yi-34b",
    "llava-1.6-yi-34b-hf",
    "llava-1.6-llama-3-8b",
    "llava-1.6-llama-3-8b-hf",
    "llava-1.6-llama-3-70b",
    "llava-1.6-llama-3-70b-hf",
    "llava-1.6-llama-3-405b",
    "llava-1.6-llama-3-405b-hf",
)

# Hard bounds for tile geometry (defensive, secure-by-design).
_MIN_TILE = 16
_MAX_TILE = 4096
_MAX_DIM = 16384
_MAX_TILES = 4096


def _clamp_int(value, low, high):
    """Coerce a value to an int clamped into [low, high].

    Raises ValueError for non-numeric / non-finite input.
    """
    if isinstance(value, bool):
        raise ValueError("tile/overlap values must be numbers, not bool")
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError("tile/overlap values must be numeric")
    if not math.isfinite(num):
        raise ValueError("tile/overlap values must be finite")
    as_int = int(num)
    if as_int < low:
        return low
    if as_int > high:
        return high
    return as_int


def compute_tile_grid(width, height, tile_size, overlap):
    """Compute the tile grid for an image.

    Returns a list of (x, y, w, h) tuples. The grid is deterministic:
    tiles are laid out left-to-right, top-to-bottom. The last tile in each
    axis is clamped so it never exceeds the image bounds.

    Raises ValueError for invalid geometry.
    """
    width = _clamp_int(width, 1, _MAX_DIM)
    height = _clamp_int(height, 1, _MAX_DIM)
    tile_size = _clamp_int(tile_size, _MIN_TILE, _MAX_TILE)
    overlap = _clamp_int(overlap, 0, tile_size - 1)

    if width <= 0 or height <= 0:
        raise ValueError("image width and height must be positive")

    step = tile_size - overlap
    if step <= 0:
        raise ValueError("overlap must be smaller than tile_size")

    def _positions(dim):
        if dim <= tile_size:
            return [0]
        positions = []
        pos = 0
        while True:
            positions.append(pos)
            if pos + tile_size >= dim:
                break
            pos += step
        # Ensure the final tile covers the right/bottom edge.
        last = dim - tile_size
        if last > positions[-1]:
            positions.append(last)
        return positions

    xs = _positions(width)
    ys = _positions(height)

    tiles = []
    for y in ys:
        for x in xs:
            w = min(tile_size, width - x)
            h = min(tile_size, height - y)
            tiles.append((x, y, w, h))

    if len(tiles) > _MAX_TILES:
        raise ValueError("tile grid exceeds maximum tile count")

    return tiles


def build_tile_prompt(tile_index, x, y, w, h, model):
    """Build a deterministic, non-empty prompt string for a tile.

    The prompt is a stable placeholder describing the tile's position and
    size, tagged with the model name. It is safe to log and cache.
    """
    return (
        "tile {idx}: region x={x} y={y} w={w} h={h} "
        "model={model} (placeholder: replace with VLM output)"
    ).format(idx=tile_index, x=x, y=y, w=w, h=h, model=model)


class PSN_Smart_Tile_Prompter:
    """Compute a tile grid and a deterministic prompt per tile.

    Pure-logic node: no VLM inference, no torch, no network.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 1024, "min": 1, "max": _MAX_DIM, "step": 1}),
                "height": ("INT", {"default": 1024, "min": 1, "max": _MAX_DIM, "step": 1}),
                "tile_size": ("INT", {"default": 512, "min": _MIN_TILE, "max": _MAX_TILE, "step": 1}),
                "overlap": ("INT", {"default": 64, "min": 0, "max": _MAX_TILE - 1, "step": 1}),
                "llm_model": (list(ALLOWED_MODELS),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("TILE_PROMPTS", "TILE_COORDS")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, width, height, tile_size, overlap, llm_model):
        if llm_model not in ALLOWED_MODELS:
            raise ValueError("llm_model must be one of the allowed models")

        tiles = compute_tile_grid(width, height, tile_size, overlap)

        prompts = []
        coords = []
        for i, (x, y, w, h) in enumerate(tiles):
            prompts.append(build_tile_prompt(i, x, y, w, h, llm_model))
            coords.append([x, y, w, h])

        # Serialize to JSON-ish text so the node returns plain strings.
        prompts_text = "\n".join(prompts)
        coords_text = "\n".join(
            "[{x}, {y}, {w}, {h}]".format(x=c[0], y=c[1], w=c[2], h=c[3])
            for c in coords
        )
        return (prompts_text, coords_text)


NODE_CLASS_MAPPINGS = {
    "PSN_Smart_Tile_Prompter": PSN_Smart_Tile_Prompter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Smart_Tile_Prompter": "Smart Tile Prompter (PSN)",
}
