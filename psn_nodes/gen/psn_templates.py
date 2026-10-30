"""PSN Templates: pure-logic, secure-by-design template orchestration for ComfyUI.

This module implements the *logic* of a Loader-Controller-Sampler template
framework. It does NOT load models, run samplers, or touch the GPU. Instead it
validates template names, builds a deterministic, allow-listed "plan" (a plain
dict of sampler parameters) and a redacted, JSON-serializable "payload" that a
real ComfyUI node could later hand to the sampler.

The real ComfyUI nodes (PSN_Template_Loader / PSN_Template_Controller) would
wire these helpers to actual MODEL/CONDITIONING/LATENT/SAMPLER tensors. Here we
only produce and validate plain values (strings, numbers, dicts, JSON text) so
the module is safe to import and test with the standard library alone.
"""

import json

# Allow-list of known templates. Anything outside this set is rejected.
TEMPLATE_NAMES = ("basic_img2img", "video_gen", "inpaint")

# Per-template default sampler configuration (pure data, no tensors).
_TEMPLATE_DEFAULTS = {
    "basic_img2img": {
        "sampler_name": "euler",
        "scheduler": "normal",
        "steps": 20,
        "cfg": 7.0,
        "denoise": 0.75,
    },
    "video_gen": {
        "sampler_name": "euler_ancestral",
        "scheduler": "karras",
        "steps": 30,
        "cfg": 6.0,
        "denoise": 1.0,
    },
    "inpaint": {
        "sampler_name": "dpmpp_2m",
        "scheduler": "sgm_uniform",
        "steps": 25,
        "cfg": 5.0,
        "denoise": 0.9,
    },
}

# Bounds used to validate user-supplied numeric overrides.
_STEPS_MIN, _STEPS_MAX = 1, 1000
_CFG_MIN, _CFG_MAX = 0.0, 100.0
_DENOISE_MIN, _DENOISE_MAX = 0.0, 1.0


def _is_number(value):
    """True for int/float but not bool (bool is a subclass of int)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _clamp(value, lo, hi):
    """Clamp a numeric value into [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _redact(text):
    """Redact anything that looks like a secret (token/key/password) in a string.

    Returns a new string where the value portion of `key=value` or `key: value`
    pairs whose key matches a sensitive name is replaced with '***'.
    """
    if not isinstance(text, str):
        return text
    sensitive = ("token", "key", "secret", "password", "api")
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        replaced = False
        for sep in ("=", ":"):
            if sep in stripped:
                key, _, val = stripped.partition(sep)
                if any(s in key.lower() for s in sensitive) and val.strip():
                    # Preserve the original spacing around the separator
                    if sep == "=":
                        replacement = key + "=" + "***"
                    else:
                        replacement = key + ": " + "***"
                    out.append(line.replace(stripped, replacement, 1))
                    replaced = True
                    break
        if not replaced:
            out.append(line)
    return "\n".join(out)


def build_plan(template_name, steps=None, cfg=None, denoise=None):
    """Build a validated, deterministic sampler plan for a template.

    Returns a dict with keys: template, sampler_name, scheduler, steps, cfg,
    denoise. Raises ValueError for unknown templates or out-of-range numbers.
    """
    if not isinstance(template_name, str) or template_name not in TEMPLATE_NAMES:
        raise ValueError("unknown template: %r" % (template_name,))

    base = dict(_TEMPLATE_DEFAULTS[template_name])

    if steps is not None:
        if not _is_number(steps):
            raise ValueError("steps must be a number")
        base["steps"] = int(_clamp(steps, _STEPS_MIN, _STEPS_MAX))
    if cfg is not None:
        if not _is_number(cfg):
            raise ValueError("cfg must be a number")
        base["cfg"] = float(_clamp(cfg, _CFG_MIN, _CFG_MAX))
    if denoise is not None:
        if not _is_number(denoise):
            raise ValueError("denoise must be a number")
        base["denoise"] = float(_clamp(denoise, _DENOISE_MIN, _DENOISE_MAX))

    base["template"] = template_name
    return base


def build_payload(template_name, steps=None, cfg=None, denoise=None, notes=""):
    """Build a JSON-serializable, redacted payload describing a generation run.

    The payload is plain data (no tensors) and is safe to log or transmit.
    """
    plan = build_plan(template_name, steps=steps, cfg=cfg, denoise=denoise)
    payload = {
        "template": plan["template"],
        "sampler": {
            "name": plan["sampler_name"],
            "scheduler": plan["scheduler"],
            "steps": plan["steps"],
            "cfg": plan["cfg"],
            "denoise": plan["denoise"],
        },
        "notes": _redact(notes),
    }
    return payload


def payload_to_json(payload):
    """Serialize a payload dict to a stable JSON string."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def parse_payload(json_text):
    """Parse a JSON payload string back into a dict, validating its shape."""
    if not isinstance(json_text, str):
        raise ValueError("payload must be a JSON string")
    data = json.loads(json_text)
    if not isinstance(data, dict) or "sampler" not in data:
        raise ValueError("payload missing 'sampler'")
    sampler = data["sampler"]
    if not isinstance(sampler, dict):
        raise ValueError("payload 'sampler' must be an object")
    for key in ("name", "scheduler", "steps", "cfg", "denoise"):
        if key not in sampler:
            raise ValueError("payload sampler missing %r" % (key,))
    return data


# ---------------------------------------------------------------------------
# ComfyUI node wrappers (pure-logic; real tensor wiring would live elsewhere)
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/Templates"


class PSN_Template_Loader:
    """Selects a pre-configured template and emits its sampler plan + payload.

    In a full ComfyUI build this node would also emit MODEL/CONDITIONING/LATENT/
    SAMPLER tensors. Here it emits the validated plan (as a dict) and a redacted
    JSON payload string, which is the secure, testable core of the loader.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "template_name": (list(TEMPLATE_NAMES),),
            },
            "optional": {
                "steps": ("INT", {"default": 0, "min": 0, "max": 1000}),
                "cfg": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 100.0, "step": 0.1}),
                "denoise": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "notes": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("DICT", "STRING")
    RETURN_NAMES = ("plan", "payload_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, template_name, steps=0, cfg=0.0, denoise=0.0, notes=""):
        # 0 means "use template default" for the optional numeric overrides.
        plan = build_plan(
            template_name,
            steps=steps if steps else None,
            cfg=cfg if cfg else None,
            denoise=denoise if denoise else None,
        )
        payload = build_payload(
            template_name,
            steps=steps if steps else None,
            cfg=cfg if cfg else None,
            denoise=denoise if denoise else None,
            notes=notes,
        )
        return (plan, payload_to_json(payload))


class PSN_Template_Controller:
    """Validates a loader payload and reports the resolved sampler configuration.

    This is the pure-logic half of the "simplified sampler": it checks the
    payload is well-formed and in-range, then returns the resolved plan plus a
    human-readable status. The actual sampling (GPU/torch) is intentionally out
    of scope for this module.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "payload_json": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("DICT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("plan", "status", "ok")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, payload_json):
        try:
            data = parse_payload(payload_json)
        except (ValueError, json.JSONDecodeError) as exc:
            return ({}, "invalid payload: %s" % (exc,), False)

        sampler = data["sampler"]
        plan = {
            "template": data.get("template", ""),
            "sampler_name": sampler["name"],
            "scheduler": sampler["scheduler"],
            "steps": int(sampler["steps"]),
            "cfg": float(sampler["cfg"]),
            "denoise": float(sampler["denoise"]),
        }
        # Re-validate ranges as a final guard.
        try:
            build_plan(
                plan["template"],
                steps=plan["steps"],
                cfg=plan["cfg"],
                denoise=plan["denoise"],
            )
        except ValueError as exc:
            return (plan, "out of range: %s" % (exc,), False)

        return (plan, "ready: %s/%s steps=%d cfg=%.2f" % (
            plan["sampler_name"], plan["scheduler"], plan["steps"], plan["cfg"]), True)


NODE_CLASS_MAPPINGS = {
    "PSN_Template_Loader": PSN_Template_Loader,
    "PSN_Template_Controller": PSN_Template_Controller,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Template_Loader": "PSN Template Loader",
    "PSN_Template_Controller": "PSN Template Controller",
}
