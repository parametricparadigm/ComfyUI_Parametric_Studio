"""
PSN_RayParallelSampler

Pure-logic, secure-by-design configuration and planning node for a multi-GPU
Ray-based parallel sampler. This module does NOT import torch, Ray, or any
ComfyUI internals, and it performs no network, file, or OS access. It only
validates user-supplied configuration, computes a deterministic work plan
(sharding of a batch across worker slots), and formats a JSON payload that a
downstream (out-of-scope) Ray executor would consume.

All public functions and the node wrapper take plain values (numbers, strings,
JSON text) and return plain values (tuples of numbers, strings, booleans, and
JSON text).
"""

import json
import math

CAT = "ParametricStudio/Ray"

# Allow-list of supported scheduling strategies.
SCHEDULING_MODES = ("round_robin", "static", "dynamic")

# Allow-list of supported payload formats.
PAYLOAD_FORMATS = ("json", "csv")

# Hard safety caps to prevent absurd or malicious configurations.
MAX_WORKERS = 1024
MAX_BATCH_SIZE = 1_000_000
MAX_ITEMS_PER_TASK = 10_000


def psn_validate_config(num_workers, batch_size, items_per_task, scheduling, payload_format):
    """
    Validate a Ray parallel sampler configuration.

    Returns (ok, errors) where errors is a list of human-readable strings.
    """
    errors = []

    # num_workers
    if not isinstance(num_workers, int) or isinstance(num_workers, bool):
        errors.append("num_workers must be an integer")
    elif num_workers < 1:
        errors.append("num_workers must be >= 1")
    elif num_workers > MAX_WORKERS:
        errors.append("num_workers must be <= %d" % MAX_WORKERS)

    # batch_size
    if not isinstance(batch_size, int) or isinstance(batch_size, bool):
        errors.append("batch_size must be an integer")
    elif batch_size < 1:
        errors.append("batch_size must be >= 1")
    elif batch_size > MAX_BATCH_SIZE:
        errors.append("batch_size must be <= %d" % MAX_BATCH_SIZE)

    # items_per_task
    if not isinstance(items_per_task, int) or isinstance(items_per_task, bool):
        errors.append("items_per_task must be an integer")
    elif items_per_task < 1:
        errors.append("items_per_task must be >= 1")
    elif items_per_task > MAX_ITEMS_PER_TASK:
        errors.append("items_per_task must be <= %d" % MAX_ITEMS_PER_TASK)

    # scheduling
    if not isinstance(scheduling, str) or scheduling not in SCHEDULING_MODES:
        errors.append("scheduling must be one of: %s" % ", ".join(SCHEDULING_MODES))

    # payload_format
    if not isinstance(payload_format, str) or payload_format not in PAYLOAD_FORMATS:
        errors.append("payload_format must be one of: %s" % ", ".join(PAYLOAD_FORMATS))

    return (len(errors) == 0, errors)


def psn_compute_shard_sizes(num_workers, batch_size):
    """
    Compute how many items each worker receives for a static/round_robin plan.

    Returns a list of length num_workers where each entry is the number of
    items assigned to that worker. The sum equals batch_size.
    """
    if num_workers <= 0 or batch_size <= 0:
        return []
    base = batch_size // num_workers
    remainder = batch_size % num_workers
    sizes = [base] * num_workers
    for i in range(remainder):
        sizes[i] += 1
    return sizes


def psn_build_work_plan(num_workers, batch_size, items_per_task, scheduling):
    """
    Build a deterministic work plan: a list of tasks, each with a worker id,
    a start index, and a count of items.

    For 'static' and 'round_robin', items are chunked by items_per_task and
    assigned to workers in order (round_robin cycles through workers).
    For 'dynamic', a single task per worker is emitted with the full shard
    size (the executor is expected to subdivide at runtime).

    Returns a list of dicts: {"worker": int, "start": int, "count": int}
    """
    if num_workers <= 0 or batch_size <= 0:
        return []

    tasks = []

    if scheduling == "dynamic":
        sizes = psn_compute_shard_sizes(num_workers, batch_size)
        start = 0
        for w in range(num_workers):
            count = sizes[w]
            if count > 0:
                tasks.append({"worker": w, "start": start, "count": count})
                start += count
        return tasks

    # static or round_robin: chunk by items_per_task
    chunk = max(1, items_per_task)
    start = 0
    worker_idx = 0
    while start < batch_size:
        count = min(chunk, batch_size - start)
        if scheduling == "round_robin":
            w = worker_idx % num_workers
        else:  # static: fill worker 0 first, then 1, etc.
            w = min(worker_idx, num_workers - 1)
        tasks.append({"worker": w, "start": start, "count": count})
        start += count
        worker_idx += 1
    return tasks


def psn_format_payload(config, plan, payload_format):
    """
    Format the final payload as a string.

    config: dict with validated configuration values.
    plan: list of task dicts from psn_build_work_plan.
    payload_format: 'json' or 'csv'.

    Returns the formatted string.
    """
    if payload_format == "csv":
        lines = ["worker,start,count"]
        for t in plan:
            lines.append("%d,%d,%d" % (t["worker"], t["start"], t["count"]))
        return "\n".join(lines)

    # default: json
    return json.dumps({"config": config, "plan": plan}, sort_keys=True)


class PSN_RayParallelSampler:
    """
    Manages multi-GPU sampler setups via Ray (pure-logic planning only).

    Validates configuration, computes a deterministic work plan for sharding
    a batch across worker slots, and emits a formatted payload (JSON or CSV)
    that a downstream Ray executor would consume. No actual Ray, GPU, or
    network access is performed here.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "num_workers": ("INT", {"default": 4, "min": 1, "max": MAX_WORKERS, "step": 1}),
                "batch_size": ("INT", {"default": 64, "min": 1, "max": MAX_BATCH_SIZE, "step": 1}),
                "items_per_task": ("INT", {"default": 8, "min": 1, "max": MAX_ITEMS_PER_TASK, "step": 1}),
                "scheduling": (list(SCHEDULING_MODES),),
                "payload_format": (list(PAYLOAD_FORMATS),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING", "INT")
    RETURN_NAMES = ("valid", "payload", "reason", "task_count")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, num_workers, batch_size, items_per_task, scheduling, payload_format):
        ok, errors = psn_validate_config(
            num_workers, batch_size, items_per_task, scheduling, payload_format
        )
        if not ok:
            return (False, "", "; ".join(errors), 0)

        plan = psn_build_work_plan(num_workers, batch_size, items_per_task, scheduling)
        config = {
            "num_workers": num_workers,
            "batch_size": batch_size,
            "items_per_task": items_per_task,
            "scheduling": scheduling,
            "payload_format": payload_format,
        }
        payload = psn_format_payload(config, plan, payload_format)
        return (True, payload, "ok", len(plan))


NODE_CLASS_MAPPINGS = {
    "PSN_RayParallelSampler": PSN_RayParallelSampler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_RayParallelSampler": "PSN Ray Parallel Sampler",
}
