"""Parametric Studio node: UTCDateTime TypeDecorator behaviour.

The original studio idea is a SQLAlchemy ``TypeDecorator`` that forces every
database timestamp to round-trip as a timezone-aware UTC ``datetime``.  A
ComfyUI node cannot open a database, so this module implements the *core*
behaviour of that decorator in pure Python (stdlib ``datetime`` only) and
exposes it as a ComfyUI custom node:

* ``PSN_UTCDateTimeRoundTrip`` - takes a timestamp (ISO string or epoch
  seconds) plus an optional source timezone offset and returns the
  normalised tz-aware UTC ISO-8601 string, exactly what the decorator's
  ``process_bind_param`` / ``process_result_value`` pair would produce.
* ``PSN_UTCDateTimeBatch`` - applies the same normalisation to a small batch
  of timestamps and reports how many were naive (needed conversion) vs
  already aware, mirroring how the decorator silently fixes naive values.

No tensors are involved; the node works on plain strings/numbers, which is
the honest core of the idea (timezone normalisation logic).
"""

from datetime import datetime, timedelta, timezone

CAT = "ParametricStudio/Time"


def _parse_input(value):
    """Parse a timestamp given as ISO-8601 string or epoch seconds.

    Returns a ``datetime`` (possibly naive).  Raises ``ValueError`` for
    unparseable input.
    """
    if isinstance(value, (int, float)):
        # epoch seconds (UTC by definition)
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string or epoch seconds")
    text = value.strip()
    if not text:
        raise ValueError("empty timestamp string")
    # Python 3.11+ fromisoformat handles 'Z'; normalise for older versions.
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _normalise_utc(value, source_offset_minutes=0):
    """Core of the UTCDateTime TypeDecorator.

    ``process_bind_param`` equivalent: whatever comes in is converted to a
    tz-aware UTC datetime before it is "stored".

    * aware datetime  -> converted to UTC
    * naive datetime  -> assumed to be in ``source_offset_minutes`` (default
      UTC, i.e. 0) and tagged accordingly, then converted to UTC

    Returns the aware UTC datetime.  Never mutates the input.
    """
    dt = _parse_input(value)
    if dt.tzinfo is None:
        offset = timedelta(minutes=int(source_offset_minutes))
        dt = dt.replace(tzinfo=timezone(offset))
    return dt.astimezone(timezone.utc)


def _format_utc(dt):
    """``process_result_value`` equivalent: serialise aware UTC to ISO-8601
    with an explicit ``+00:00`` offset (what a DB row would hand back)."""
    if dt.tzinfo is None:
        raise ValueError("refusing to serialise a naive datetime")
    return dt.astimezone(timezone.utc).isoformat()


class PSN_UTCDateTimeRoundTrip:
    """Normalise one timestamp to tz-aware UTC (UTCDateTime TypeDecorator core)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "timestamp": ("STRING", {"default": "2024-01-01T12:00:00"}),
                "source_offset_minutes": ("INT", {"default": 0, "min": -720, "max": 720}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("utc_iso", "epoch_seconds")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, timestamp, source_offset_minutes):
        dt = _normalise_utc(timestamp, source_offset_minutes)
        iso = _format_utc(dt)
        epoch = int(dt.timestamp())
        return (iso, epoch)


class PSN_UTCDateTimeBatch:
    """Normalise a batch of timestamps (one per line) to tz-aware UTC."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "timestamps": ("STRING", {"multiline": 4, "default": "2024-01-01T12:00:00\n2024-01-01T14:30:00+02:00"}),
                "source_offset_minutes": ("INT", {"default": 0, "min": -720, "max": 720}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT")
    RETURN_NAMES = ("utc_iso_lines", "naive_count", "total_count")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, timestamps, source_offset_minutes):
        lines = [ln for ln in str(timestamps).splitlines() if ln.strip()]
        out_lines = []
        naive_count = 0
        for ln in lines:
            dt = _parse_input(ln)
            if dt.tzinfo is None:
                naive_count += 1
            out_lines.append(_format_utc(_normalise_utc(ln, source_offset_minutes)))
        return ("\n".join(out_lines), naive_count, len(lines))


NODE_CLASS_MAPPINGS = {
    "PSN_UTCDateTimeRoundTrip": PSN_UTCDateTimeRoundTrip,
    "PSN_UTCDateTimeBatch": PSN_UTCDateTimeBatch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_UTCDateTimeRoundTrip": "UTCDateTime Round-Trip (TypeDecorator core)",
    "PSN_UTCDateTimeBatch": "UTCDateTime Batch Normalise",
}
