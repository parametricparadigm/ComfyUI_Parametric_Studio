"""ParametricStudio status aggregation nodes.

Builds a status aggregation system that polls individual ComfyUI instances
to report health and resource usage.  Because a ComfyUI custom node cannot
open sockets, the *polling* side is modelled as a pure function over a
structured snapshot (the same shape ``_poll_instance`` would return from a
live instance), and the *aggregation* side combines many snapshots into a
fleet-wide health report.  Tensors are used where the spec calls for real
ComfyUI types: a per-instance health score is emitted as a small IMAGE
tensor so the report can be visualised in the UI.
"""

import torch

CAT = "ParametricStudio/Status"

# ---------------------------------------------------------------------------
# snapshot helpers
# ---------------------------------------------------------------------------


def _as_float(value, default=0.0):
    """Coerce a scalar to float, tolerating None / bad strings."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalise_snapshot(name, snap):
    """Validate one instance snapshot dict and return a clean copy.

    Expected keys (all optional, defaults applied):
        name, alive (bool), queue (int), vram_used (float GB), vram_total
        (float GB), cpu (float 0..100), uptime (float s), error (str).
    """
    if not isinstance(snap, dict):
        raise ValueError("each snapshot must be a dict")
    out = {
        "name": str(snap.get("name") or name or "instance"),
        "alive": bool(snap.get("alive", True)),
        "queue": max(0, _as_int(snap.get("queue"), 0)),
        "vram_used": max(0.0, _as_float(snap.get("vram_used"), 0.0)),
        "vram_total": max(0.0, _as_float(snap.get("vram_total"), 0.0)),
        "cpu": min(100.0, max(0.0, _as_float(snap.get("cpu"), 0.0))),
        "uptime": max(0.0, _as_float(snap.get("uptime"), 0.0)),
        "error": str(snap.get("error") or ""),
    }
    return out


def _score_instance(snap):
    """Score one instance 0..1: alive, VRAM headroom, queue pressure."""
    if not snap["alive"]:
        return 0.0
    score = 1.0
    if snap["vram_total"] > 0:
        headroom = 1.0 - (snap["vram_used"] / snap["vram_total"])
        score *= max(0.0, min(1.0, headroom * 2.0))  # full below 50% used
    if snap["queue"] > 0:
        score *= max(0.0, 1.0 - snap["queue"] / 32.0)
    return max(0.0, min(1.0, score))


def _fleet_state(scores, alive_count, total):
    if total == 0:
        return "empty"
    if alive_count == 0:
        return "down"
    avg = sum(scores) / total
    if alive_count < total:
        return "degraded"
    if avg >= 0.75:
        return "healthy"
    if avg >= 0.4:
        return "busy"
    return "degraded"


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------


class PSN_StatusPollInstance:
    """Poll one ComfyUI instance snapshot and score its health (0..1)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "name": ("STRING", {"default": "instance-0"}),
                "alive": ("BOOLEAN", {"default": True}),
                "queue": ("INT", {"default": 0, "min": 0, "max": 100000}),
                "vram_used": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 10000.0}),
                "vram_total": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 10000.0}),
                "cpu": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 100.0}),
                "uptime": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9}),
                "error": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "FLOAT", "IMAGE")
    RETURN_NAMES = ("report", "score", "score_image")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, name, alive, queue, vram_used, vram_total, cpu, uptime, error):
        snap = _normalise_snapshot(
            name,
            {
                "alive": alive,
                "queue": queue,
                "vram_used": vram_used,
                "vram_total": vram_total,
                "cpu": cpu,
                "uptime": uptime,
                "error": error,
            },
        )
        score = _score_instance(snap)
        lines = [
            "instance: %s" % snap["name"],
            "alive: %s" % ("yes" if snap["alive"] else "no"),
            "queue: %d" % snap["queue"],
            "vram: %.2f/%.2f GB" % (snap["vram_used"], snap["vram_total"]),
            "cpu: %.1f%%" % snap["cpu"],
            "uptime: %.1f s" % snap["uptime"],
            "score: %.3f" % score,
        ]
        if snap["error"]:
            lines.append("error: %s" % snap["error"])
        report = "\n".join(lines)
        # 1x1 image encoding the score (red channel = score).
        img = torch.zeros((1, 1, 1, 3), dtype=torch.float32)
        img[0, 0, 0, 0] = score
        img[0, 0, 0, 1] = 1.0 - score
        return (report, score, img)


class PSN_StatusAggregateFleet:
    """Aggregate per-instance snapshots into a fleet health report."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "snapshots": ("STRING", {"default": ""}),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("STRING", "FLOAT", "IMAGE")
    RETURN_NAMES = ("report", "fleet_score", "score_image")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, snapshots, threshold):
        # snapshots: one JSON object per line (or a single JSON array).
        import json

        snaps = []
        text = (snapshots or "").strip()
        if text:
            if text.startswith("["):
                parsed = json.loads(text)
                if not isinstance(parsed, list):
                    raise ValueError("snapshot array must be a JSON list")
                for i, item in enumerate(parsed):
                    snaps.append(_normalise_snapshot("instance-%d" % i, item))
            else:
                for i, line in enumerate(text.splitlines()):
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    snaps.append(_normalise_snapshot("instance-%d" % i, item))

        if not snaps:
            report = "fleet: empty (no snapshots)"
            fleet = 0.0
            img = torch.zeros((1, 1, 1, 3), dtype=torch.float32)
            return (report, fleet, img)

        scores = [_score_instance(s) for s in snaps]
        alive = sum(1 for s in snaps if s["alive"])
        state = _fleet_state(scores, alive, len(snaps))
        fleet = sum(scores) / len(scores)
        worst = min(zip(snaps, scores), key=lambda p: p[1])
        lines = [
            "fleet: %s" % state,
            "instances: %d (%d alive)" % (len(snaps), alive),
            "fleet score: %.3f (threshold %.2f)" % (fleet, threshold),
            "worst: %s (%.3f)" % (worst[0]["name"], worst[1]),
        ]
        for s, sc in zip(snaps, scores):
            flag = "ok" if sc >= threshold else "WARN"
            lines.append("  [%s] %s score=%.3f queue=%d" % (flag, s["name"], sc, s["queue"]))
        report = "\n".join(lines)
        img = torch.zeros((1, 1, 1, 3), dtype=torch.float32)
        img[0, 0, 0, 0] = fleet
        img[0, 0, 0, 1] = 1.0 - fleet
        return (report, fleet, img)


NODE_CLASS_MAPPINGS = {
    "PSN_StatusPollInstance": PSN_StatusPollInstance,
    "PSN_StatusAggregateFleet": PSN_StatusAggregateFleet,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_StatusPollInstance": "Status: Poll Instance",
    "PSN_StatusAggregateFleet": "Status: Aggregate Fleet",
}
