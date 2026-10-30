import importlib
import sys
from datetime import datetime, timezone

mod = importlib.import_module("h_use_a_custom_utcdatetime_typedecor")

# 1. Module-level mappings exist and are consistent.
assert hasattr(mod, "NODE_CLASS_MAPPINGS"), "missing NODE_CLASS_MAPPINGS"
assert hasattr(mod, "NODE_DISPLAY_NAME_MAPPINGS"), "missing NODE_DISPLAY_NAME_MAPPINGS"
assert set(mod.NODE_CLASS_MAPPINGS) == set(mod.NODE_DISPLAY_NAME_MAPPINGS)
assert "PSN_UTCDateTimeRoundTrip" in mod.NODE_CLASS_MAPPINGS
assert "PSN_UTCDateTimeBatch" in mod.NODE_CLASS_MAPPINGS

# 2. Node class contract: INPUT_TYPES classmethod, RETURN_TYPES, FUNCTION, CATEGORY.
for name in ("PSN_UTCDateTimeRoundTrip", "PSN_UTCDateTimeBatch"):
    cls = mod.NODE_CLASS_MAPPINGS[name]
    assert callable(cls.INPUT_TYPES)
    spec = cls.INPUT_TYPES()
    assert "required" in spec
    assert cls.RETURN_TYPES
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")
    assert hasattr(cls, "run")

node = mod.PSN_UTCDateTimeRoundTrip()

# 3. Naive timestamp assumed UTC (offset 0) -> aware UTC ISO with +00:00.
iso, epoch = node.run("2024-01-01T12:00:00", 0)
assert iso == "2024-01-01T12:00:00+00:00", iso
assert epoch == int(datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp())

# 4. Aware non-UTC timestamp is converted to UTC (offset +02:00 -> -2h).
iso, epoch = node.run("2024-01-01T14:30:00+02:00", 0)
assert iso == "2024-01-01T12:30:00+00:00", iso

# 5. Naive timestamp with a source offset (e.g. +03:00 = 180 min) is shifted.
iso, epoch = node.run("2024-06-15T08:00:00", 180)
assert iso == "2024-06-15T05:00:00+00:00", iso

# 6. Epoch seconds input round-trips.
iso, epoch = node.run(1704110400, 0)  # 2024-01-01T12:00:00Z
assert iso == "2024-01-01T12:00:00+00:00", iso
assert epoch == 1704110400

# 7. 'Z' suffix is accepted and normalised.
iso, _ = node.run("2024-01-01T12:00:00Z", 0)
assert iso == "2024-01-01T12:00:00+00:00", iso

# 8. Bad input raises ValueError (unparseable string).
try:
    node.run("not-a-date", 0)
    raise AssertionError("expected ValueError for bad input")
except ValueError:
    pass

# 9. Empty string raises ValueError.
try:
    node.run("   ", 0)
    raise AssertionError("expected ValueError for empty input")
except ValueError:
    pass

# 10. Non-string non-number input raises ValueError.
try:
    node.run([1, 2, 3], 0)
    raise AssertionError("expected ValueError for list input")
except ValueError:
    pass

# 11. Batch node: counts naive vs aware and normalises each line.
batch = mod.PSN_UTCDateTimeBatch()
out, naive, total = batch.run("2024-01-01T12:00:00\n2024-01-01T14:30:00+02:00\n\n2024-01-01T00:00:00Z", 0)
assert total == 3, total
assert naive == 1, naive
lines = out.splitlines()
assert lines[0] == "2024-01-01T12:00:00+00:00"
assert lines[1] == "2024-01-01T12:30:00+00:00"
assert lines[2] == "2024-01-01T00:00:00+00:00"

# 12. Batch with source offset applied to naive lines only.
out, naive, total = batch.run("2024-06-15T08:00:00\n2024-06-15T08:00:00+03:00", 180)
assert naive == 1
assert out.splitlines()[0] == "2024-06-15T05:00:00+00:00"
assert out.splitlines()[1] == "2024-06-15T05:00:00+00:00"

# 13. Negative offset (e.g. -05:00 = -300 min) shifts forward.
iso, _ = node.run("2024-01-01T12:00:00", -300)
assert iso == "2024-01-01T17:00:00+00:00", iso

# 14. Display names are non-empty strings.
for k, v in mod.NODE_DISPLAY_NAME_MAPPINGS.items():
    assert isinstance(v, str) and v.strip(), k

print("ok")
