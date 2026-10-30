"""PSN_Seed_Generator: deterministic / pseudo-random / hashed seed generation.

Pure-logic node only. No torch, no ComfyUI imports, no network, no file/OS access.
The 'Pseudo-Random' mode uses a pure-Python Mersenne Twister (random.Random)
seeded from base_seed, then mixes in param_a and param_b deterministically,
so it is reproducible without numpy.
"""
import hashlib
import random

CAT = "ParametricStudio/Seeds"
MODES = ["Deterministic", "Pseudo-Random", "Hashed"]
MAX_SEED = 2**63 - 1


def _clamp_int(value, lo, hi):
    try:
        v = int(value)
    except (TypeError, ValueError):
        v = 0
    if v < lo:
        v = lo
    elif v > hi:
        v = hi
    return v


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_str(value):
    if value is None:
        return ""
    return str(value)


def _deterministic_seed(base_seed, param_a, param_b):
    return _clamp_int(base_seed + int(param_a * 1000) + int(param_b * 1000), 0, MAX_SEED)


def _pseudo_random_seed(base_seed, param_a, param_b):
    rng = random.Random(base_seed)
    a_int = int(param_a * 1000)
    b_int = int(param_b * 1000)
    r1 = rng.randint(0, 2**32 - 1)
    r2 = rng.randint(0, 2**32 - 1)
    mixed = (r1 ^ (a_int & 0xFFFFFFFF)) + (r2 ^ (b_int & 0xFFFFFFFF))
    return _clamp_int(mixed, 0, MAX_SEED)


def _hashed_seed(base_seed, param_a, param_b, salt):
    payload = f"{base_seed}:{param_a}:{param_b}:{salt}"
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & MAX_SEED


class PSN_Seed_Generator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_seed": ("INT", {"default": 0, "min": 0, "max": MAX_SEED, "step": 1}),
                "param_a": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "param_b": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "mode": (MODES,),
            },
            "optional": {
                "salt": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("seed", "seed_hex")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, base_seed, param_a, param_b, mode, salt=""):
        base_seed = _clamp_int(base_seed, 0, MAX_SEED)
        param_a = _to_float(param_a)
        param_b = _to_float(param_b)
        salt = _to_str(salt)

        if mode == "Deterministic":
            seed = _deterministic_seed(base_seed, param_a, param_b)
        elif mode == "Pseudo-Random":
            seed = _pseudo_random_seed(base_seed, param_a, param_b)
        elif mode == "Hashed":
            seed = _hashed_seed(base_seed, param_a, param_b, salt)
        else:
            seed = _hashed_seed(base_seed, param_a, param_b, salt)

        seed_hex = format(seed, "016x")
        return (seed, seed_hex)


NODE_CLASS_MAPPINGS = {"PSN_Seed_Generator": PSN_Seed_Generator}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Seed_Generator": "PSN Seed Generator"}
