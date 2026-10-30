import json

import numpy as np
import pandas as pd
import torch

from n_5_statistical_analysis_dashboard import (
    PSN_DataFrameStats,
    PSN_StatPlotGenerator,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_df():
    return pd.DataFrame({
        "a": [1.0, 2.0, 3.0, 4.0, 5.0],
        "b": [2.0, 4.0, 6.0, 8.0, 10.0],
        "c": ["x", "y", "x", "y", "x"],
    })


# 1. module-level mappings exist and are consistent
assert set(NODE_CLASS_MAPPINGS) == {"PSN_DataFrameStats", "PSN_StatPlotGenerator"}
assert set(NODE_DISPLAY_NAME_MAPPINGS) == set(NODE_CLASS_MAPPINGS)
for cls in NODE_CLASS_MAPPINGS.values():
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")
    it = cls.INPUT_TYPES()
    assert "required" in it

# 2. DataFrameStats: describe + corr on numeric columns
stats = PSN_DataFrameStats()
summary, corr = stats.run(make_df(), json.dumps(["a", "b"]))
assert isinstance(summary, pd.DataFrame)
assert isinstance(corr, pd.DataFrame)
assert list(summary.index) == ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]
assert abs(summary.loc["mean", "a"] - 3.0) < 1e-9
assert abs(summary.loc["mean", "b"] - 6.0) < 1e-9
assert corr.shape == (2, 2)
assert abs(corr.loc["a", "b"] - 1.0) < 1e-9  # perfectly correlated
assert abs(corr.loc["a", "a"] - 1.0) < 1e-9

# 3. DataFrameStats: input not mutated
src = make_df()
before = src.copy(deep=True)
stats.run(src, json.dumps(["a"]))
assert src.equals(before)

# 4. DataFrameStats: bad inputs raise
try:
    stats.run("not a df", json.dumps(["a"]))
    raise AssertionError("expected ValueError for non-DataFrame input")
except ValueError:
    pass
try:
    stats.run(make_df(), "not json")
    raise AssertionError("expected ValueError for invalid JSON")
except ValueError:
    pass
try:
    stats.run(make_df(), json.dumps(["nope"]))
    raise AssertionError("expected ValueError for missing column")
except ValueError:
    pass
try:
    stats.run(make_df(), json.dumps([]))
    raise AssertionError("expected ValueError for empty column list")
except ValueError:
    pass

# 5. Plot generator: bar chart produces a valid IMAGE tensor
plot = PSN_StatPlotGenerator()
img = plot.run(make_df(), "bar", "c", "a", width=256, height=256)[0]
assert isinstance(img, torch.Tensor)
assert img.shape == (1, 256, 256, 3)
assert img.dtype == torch.float32
assert img.min() >= 0.0 and img.max() <= 1.0
# image should not be a single flat color (some variation)
assert img.std() > 0.01

# 6. Plot generator: all four plot types run and return correct shape
for ptype, x, y in [("line", "a", "b"), ("scatter", "a", "b"), ("histogram", "a", "")]:
    out = plot.run(make_df(), ptype, x, y, width=128, height=128)[0]
    assert out.shape == (1, 128, 128, 3), f"{ptype} wrong shape {out.shape}"
    assert out.min() >= 0.0 and out.max() <= 1.0

# 7. Plot generator: bad inputs raise
try:
    plot.run(make_df(), "pie", "a", "b")
    raise AssertionError("expected ValueError for unknown plot type")
except ValueError:
    pass
try:
    plot.run(make_df(), "bar", "missing", "a")
    raise AssertionError("expected ValueError for missing x_col")
except ValueError:
    pass
try:
    plot.run(make_df(), "bar", "a", "")
    raise AssertionError("expected ValueError for empty y_col")
except ValueError:
    pass

# 8. sample_size actually subsamples (deterministic, smaller frame used)
big = pd.DataFrame({"a": np.arange(100, dtype=float), "b": np.arange(100, dtype=float) * 2.0})
img_full = plot.run(big, "scatter", "a", "b", sample_size=0, width=128, height=128)[0]
img_sub = plot.run(big, "scatter", "a", "b", sample_size=10, width=128, height=128)[0]
assert img_full.shape == img_sub.shape == (1, 128, 128, 3)
# the two renders should differ (different number of points)
assert not torch.equal(img_full, img_sub)

# 9. histogram with all-NaN numeric column still renders (edge case)
nan_df = pd.DataFrame({"a": [float("nan")] * 5, "b": [1.0] * 5})
out = plot.run(nan_df, "histogram", "a", "", width=128, height=128)[0]
assert out.shape == (1, 128, 128, 3)

# 10. empty dataframe rejected
try:
    plot.run(pd.DataFrame({"a": []}), "bar", "a", "a")
    raise AssertionError("expected ValueError for empty dataframe")
except ValueError:
    pass

print("ok")
