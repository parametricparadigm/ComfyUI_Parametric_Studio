"""Parametric Studio - VRAM tracking class.

Implements a VRAM tracking class that monitors real GPU memory usage and
reservations to prevent out-of-memory errors during pipeline execution.

The tracker keeps an in-memory ledger of:
  * the total VRAM reported by the device (or a configured fallback),
  * the currently *reserved* bytes (explicit reservations made by pipeline
    steps before heavy work),
  * the *observed* bytes (peak usage sampled from torch when a CUDA device
    is available, otherwise a simulated counter for CPU-only testing).

A ComfyUI node (PSN_VramGate) exposes the tracker: it reserves a budget
for the upcoming step, checks whether the reservation fits, and reports the
result as a boolean plus a human-readable status string.  When the budget
would exceed available VRAM the node raises a clear error so the pipeline
can pause or fall back instead of crashing with a CUDA OOM.

Only torch (CPU) and the Python standard library are used.  No network,
no subprocess, no file I/O.
"""

import math

import torch

CAT = "ParametricStudio/Resources"


class VramTracker:
    """Tracks real VRAM usage and reservations for a single device.

    Parameters
    ----------
    device : str, optional
        Torch device string, e.g. ``"cuda:0"`` or ``"cpu"``.  When the
        device is not available (e.g. no GPU on this machine) the tracker
        falls back to a *simulated* memory model so the logic can still be
        exercised and tested on CPU.
    total_bytes : int, optional
        Override the total VRAM in bytes.  When omitted the tracker queries
        ``torch.cuda.get_device_properties`` for CUDA devices, or uses a
        default of 8 GiB for the simulated fallback.
    """

    DEFAULT_TOTAL_BYTES = 8 * 1024 ** 3  # 8 GiB fallback

    def __init__(self, device="cuda:0", total_bytes=None):
        self.device = device
        self._cuda = False
        try:
            self._cuda = torch.cuda.is_available() and device.startswith("cuda")
        except Exception:
            self._cuda = False

        if total_bytes is not None:
            if not isinstance(total_bytes, int) or isinstance(total_bytes, bool):
                raise TypeError("total_bytes must be an int")
            if total_bytes <= 0:
                raise ValueError("total_bytes must be positive")
            self.total_bytes = total_bytes
        elif self._cuda:
            idx = 0
            if ":" in device:
                try:
                    idx = int(device.split(":", 1)[1])
                except ValueError:
                    idx = 0
            props = torch.cuda.get_device_properties(idx)
            self.total_bytes = int(props.total_memory)
        else:
            self.total_bytes = self.DEFAULT_TOTAL_BYTES

        self._reserved = 0
        self._observed = 0
        self._peak = 0
        self._reservations = []  # list of (label, bytes)

    # ------------------------------------------------------------------ #
    # sampling
    # ------------------------------------------------------------------ #
    def sample(self):
        """Sample the current memory usage and return observed bytes.

        On a real CUDA device this reads ``torch.cuda.memory_allocated``;
        otherwise it returns the simulated observed counter (which is
        advanced by :meth:`simulate_usage`).
        """
        if self._cuda:
            try:
                self._observed = int(torch.cuda.memory_allocated())
            except Exception:
                self._observed = 0
        else:
            self._observed = self._sim_observed
        self._peak = max(self._peak, self._observed)
        return self._observed

    # ------------------------------------------------------------------ #
    # simulated usage (CPU-only testing path)
    # ------------------------------------------------------------------ #
    _sim_observed = 0

    def simulate_usage(self, bytes_used):
        """Advance the simulated observed usage (CPU-only testing)."""
        if not isinstance(bytes_used, int) or isinstance(bytes_used, bool):
            raise TypeError("bytes_used must be an int")
        if bytes_used < 0:
            raise ValueError("bytes_used must be >= 0")
        self._sim_observed = bytes_used
        return self.sample()

    # ------------------------------------------------------------------ #
    # reservations
    # ------------------------------------------------------------------ #
    def reserve(self, label, bytes_needed):
        """Reserve ``bytes_needed`` bytes for a pipeline step.

        Returns the number of bytes actually reserved.  Raises
        :class:`VramError` when the reservation would exceed the available
        VRAM (total minus already reserved minus observed usage).
        """
        if not isinstance(bytes_needed, int) or isinstance(bytes_needed, bool):
            raise TypeError("bytes_needed must be an int")
        if bytes_needed < 0:
            raise ValueError("bytes_needed must be >= 0")
        if not isinstance(label, str) or not label:
            raise ValueError("label must be a non-empty string")

        self.sample()
        available = self.available_bytes()
        if bytes_needed > available:
            raise VramError(
                f"cannot reserve {bytes_needed} bytes for '{label}': "
                f"only {available} bytes available "
                f"(total={self.total_bytes}, reserved={self._reserved}, "
                f"observed={self._observed})"
            )
        self._reserved += bytes_needed
        self._reservations.append((label, bytes_needed))
        return bytes_needed

    def release(self, label):
        """Release the most recent reservation with ``label``.

        Returns the number of bytes released.  Raises ``KeyError`` if no
        such reservation exists.
        """
        for i in range(len(self._reservations) - 1, -1, -1):
            if self._reservations[i][0] == label:
                _, b = self._reservations.pop(i)
                self._reserved -= b
                return b
        raise KeyError(f"no active reservation named '{label}'")

    def release_all(self):
        """Release every active reservation.  Returns total bytes freed."""
        freed = self._reserved
        self._reserved = 0
        self._reservations = []
        return freed

    # ------------------------------------------------------------------ #
    # queries
    # ------------------------------------------------------------------ #
    def available_bytes(self):
        """Bytes that can still be reserved (total - reserved - observed)."""
        self.sample()
        return max(0, self.total_bytes - self._reserved - self._observed)

    def utilization(self):
        """Fraction of total VRAM currently in use (reserved + observed)."""
        self.sample()
        used = self._reserved + self._observed
        if self.total_bytes <= 0:
            return 1.0
        return min(1.0, used / self.total_bytes)

    def status(self):
        """Human-readable one-line status string."""
        self.sample()
        return (
            f"vram total={_gb(self.total_bytes)}GiB "
            f"reserved={_gb(self._reserved)}GiB "
            f"observed={_gb(self._observed)}GiB "
            f"available={_gb(self.available_bytes())}GiB "
            f"util={self.utilization():.1%}"
        )

    def report(self):
        """Dict snapshot of the tracker state (safe to serialize)."""
        self.sample()
        return {
            "device": self.device,
            "total_bytes": self.total_bytes,
            "reserved_bytes": self._reserved,
            "observed_bytes": self._observed,
            "peak_bytes": self._peak,
            "available_bytes": self.available_bytes(),
            "utilization": self.utilization(),
            "reservations": list(self._reservations),
        }


class VramError(RuntimeError):
    """Raised when a VRAM reservation cannot be satisfied."""


def _gb(n):
    return round(n / 1024 ** 3, 3)


# ---------------------------------------------------------------------- #
# ComfyUI node
# ---------------------------------------------------------------------- #
class PSN_VramGate:
    """Reserve a VRAM budget for the next pipeline step and report status.

    Inputs
    ------
    image : IMAGE
        The tensor about to be processed (its byte size is used as a
        sanity check and reported, but the tensor itself is passed through
        unchanged).
    budget_mb : INT
        VRAM budget to reserve for the upcoming step, in MiB.
    total_mb : INT
        Total VRAM to assume (MiB).  Use 0 to auto-detect (falls back to
        8192 MiB when no CUDA device is present).

    Outputs
    -------
    image : IMAGE
        The input tensor, unchanged.
    ok : BOOLEAN
        True when the reservation fits.
    status : STRING
        Human-readable tracker status line.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "budget_mb": ("INT", {"default": 512, "min": 0, "max": 1048576}),
                "total_mb": ("INT", {"default": 0, "min": 0, "max": 1048576}),
            }
        }

    RETURN_TYPES = ("IMAGE", "BOOLEAN", "STRING")
    RETURN_NAMES = ("image", "ok", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, budget_mb, total_mb):
        if not isinstance(image, torch.Tensor):
            raise TypeError("image must be a torch.Tensor")
        if image.dim() != 4:
            raise ValueError("image must be [B,H,W,C]")
        if image.shape[0] < 1 or image.shape[1] < 1 or image.shape[2] < 1 or image.shape[3] < 1:
            raise ValueError("image dimensions must be >= 1")
        if not (0.0 <= float(image.min()) and float(image.max()) <= 1.0):
            raise ValueError("image values must be in 0..1")
        if not isinstance(budget_mb, int) or isinstance(budget_mb, bool) or budget_mb < 0:
            raise ValueError("budget_mb must be a non-negative int")
        if not isinstance(total_mb, int) or isinstance(total_mb, bool) or total_mb < 0:
            raise ValueError("total_mb must be a non-negative int")

        total_bytes = total_mb * 1024 ** 2 if total_mb > 0 else None
        tracker = VramTracker(device="cuda:0", total_bytes=total_bytes)

        # Account for the input tensor's own footprint as observed usage.
        observed = int(image.numel() * image.element_size())
        tracker.simulate_usage(observed)

        budget_bytes = budget_mb * 1024 ** 2
        try:
            tracker.reserve("step", budget_bytes)
            ok = True
        except VramError:
            ok = False

        # Never modify the input in place; return a clone.
        return (image.clone(), ok, tracker.status())


NODE_CLASS_MAPPINGS = {
    "PSN_VramGate": PSN_VramGate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VramGate": "VRAM Gate (ParametricStudio)",
}
