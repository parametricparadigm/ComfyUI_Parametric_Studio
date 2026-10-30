"""ParametricStudio - Statistical Analysis Dashboard.

Two ComfyUI custom nodes for structured (tabular) data:

* PSN_DataFrameStats      - describe()/corr() over selected columns.
* PSN_StatPlotGenerator   - bar / line / scatter / histogram rendered to a
                            ComfyUI IMAGE tensor [B,H,W,C] in 0..1.

The DATAFRAME type is the pandas DataFrame object passed around by other
ParametricStudio data nodes.  Plots are rendered with matplotlib (Agg
backend, no display) and converted to a float32 torch tensor on CPU.
"""

import json
import math

import numpy as np
import torch

try: from ._lazy import LazyModule
except ImportError: from _lazy import LazyModule     # imported on its own by the module's plain test

def _use_agg():
    import matplotlib
    matplotlib.use("Agg")

pd = LazyModule("pandas")     # pandas and matplotlib cost 280 ms of pack load, and only this module wants them
plt = LazyModule("matplotlib.pyplot", setup=_use_agg)

CAT = "ParametricStudio/StatisticalAnalysis"

DATAFRAME = "DATAFRAME"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _require_dataframe(df, name="dataframe"):
    if not isinstance(df, pd.DataFrame):
        raise ValueError(f"{name} must be a pandas DataFrame, got {type(df).__name__}")
    if df.empty:
        raise ValueError(f"{name} is empty (no rows)")
    return df


def _parse_columns(columns, df):
    """Parse the JSON list of column names; validate against the frame."""
    if not isinstance(columns, str):
        raise ValueError("columns must be a JSON list string, e.g. '[\"a\", \"b\"]'")
    try:
        cols = json.loads(columns)
    except json.JSONDecodeError as e:
        raise ValueError(f"columns is not valid JSON: {e}") from e
    if not isinstance(cols, list) or not cols:
        raise ValueError("columns must be a non-empty JSON list of column names")
    for c in cols:
        if not isinstance(c, str):
            raise ValueError(f"column names must be strings, got {type(c).__name__}")
        if c not in df.columns:
            raise ValueError(f"column {c!r} not found in dataframe (have {list(df.columns)})")
    return cols


def _fig_to_image(fig, width, height):
    """Render a matplotlib figure to a ComfyUI IMAGE tensor [1,H,W,C] float32 0..1."""
    fig.set_size_inches(width / 100.0, height / 100.0, forward=True)
    fig.canvas.draw()
    # canvas buffer is RGBA; take RGB
    rgba = np.asarray(fig.canvas.buffer_rgba())
    rgb = rgba[:height, :width, :3].copy()
    arr = torch.from_numpy(rgb.astype(np.float32) / 255.0)
    return arr.unsqueeze(0)  # [1,H,W,C]


def _close(fig):
    try:
        plt.close(fig)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# node 1: statistics
# ---------------------------------------------------------------------------

class PSN_DataFrameStats:
    """Compute describe() and corr() over the selected numeric columns."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dataframe": (DATAFRAME,),
                "columns": ("STRING", {"default": "[]", "multiline": True}),
            }
        }

    RETURN_TYPES = (DATAFRAME, DATAFRAME)
    RETURN_NAMES = ("summary_df", "correlation_matrix")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, dataframe, columns):
        df = _require_dataframe(dataframe)
        cols = _parse_columns(columns, df)
        sub = df[cols]

        # describe() on numeric data (pandas describe handles mixed types)
        summary = sub.describe().copy()

        # corr() needs numeric columns only
        numeric = sub.select_dtypes(include=["number"])
        if numeric.shape[1] >= 2:
            corr = numeric.corr().copy()
        elif numeric.shape[1] == 1:
            corr = numeric.corr().copy()  # 1x1 matrix of 1.0
        else:
            corr = pd.DataFrame(index=cols, columns=cols, dtype=float)

        return (summary, corr)


# ---------------------------------------------------------------------------
# node 2: plot generator
# ---------------------------------------------------------------------------

PLOT_TYPES = ("bar", "line", "scatter", "histogram")


class PSN_StatPlotGenerator:
    """Render a bar / line / scatter / histogram plot of a DataFrame to an IMAGE."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dataframe": (DATAFRAME,),
                "plot_type": (list(PLOT_TYPES),),
                "x_col": ("STRING", {"default": ""}),
                "y_col": ("STRING", {"default": ""}),
                "sample_size": ("INT", {"default": 0, "min": 0, "max": 1000000}),
                "width": ("INT", {"default": 512, "min": 64, "max": 4096}),
                "height": ("INT", {"default": 512, "min": 64, "max": 4096}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("plot_image",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, dataframe, plot_type, x_col, y_col, sample_size=0, width=512, height=512):
        df = _require_dataframe(dataframe)
        if plot_type not in PLOT_TYPES:
            raise ValueError(f"plot_type must be one of {PLOT_TYPES}, got {plot_type!r}")
        if not isinstance(x_col, str) or not x_col:
            raise ValueError("x_col must be a non-empty column name")
        if x_col not in df.columns:
            raise ValueError(f"x_col {x_col!r} not found in dataframe (have {list(df.columns)})")
        if plot_type != "histogram" and (not isinstance(y_col, str) or not y_col):
            raise ValueError("y_col must be a non-empty column name for this plot type")
        if plot_type != "histogram" and y_col not in df.columns:
            raise ValueError(f"y_col {y_col!r} not found in dataframe (have {list(df.columns)})")

        # optional sampling to keep plotting fast on large frames
        if sample_size and sample_size > 0 and sample_size < len(df):
            df = df.sample(n=sample_size, random_state=0).reset_index(drop=True)

        fig, ax = plt.subplots(figsize=(width / 100.0, height / 100.0))
        try:
            if plot_type == "bar":
                self._bar(ax, df, x_col, y_col)
            elif plot_type == "line":
                self._line(ax, df, x_col, y_col)
            elif plot_type == "scatter":
                self._scatter(ax, df, x_col, y_col)
            else:
                self._histogram(ax, df, x_col)
            ax.set_title(f"{plot_type}: {x_col} vs {y_col}" if plot_type != "histogram"
                         else f"histogram: {x_col}")
            fig.tight_layout()
            img = _fig_to_image(fig, width, height)
        finally:
            _close(fig)
        return (img,)

    # -- individual plot styles -------------------------------------------

    @staticmethod
    def _bar(ax, df, x_col, y_col):
        x = df[x_col].astype(str)
        y = pd.to_numeric(df[y_col], errors="coerce").fillna(0.0)
        ax.bar(range(len(x)), y.values, tick_label=x.values)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)

    @staticmethod
    def _line(ax, df, x_col, y_col):
        x = pd.to_numeric(df[x_col], errors="coerce")
        y = pd.to_numeric(df[y_col], errors="coerce")
        mask = x.notna() & y.notna()
        ax.plot(x[mask].values, y[mask].values, marker="o", linewidth=1.0)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)

    @staticmethod
    def _scatter(ax, df, x_col, y_col):
        x = pd.to_numeric(df[x_col], errors="coerce")
        y = pd.to_numeric(df[y_col], errors="coerce")
        mask = x.notna() & y.notna()
        ax.scatter(x[mask].values, y[mask].values, s=12, alpha=0.7)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)

    @staticmethod
    def _histogram(ax, df, x_col):
        x = pd.to_numeric(df[x_col], errors="coerce").dropna()
        if x.empty:
            ax.text(0.5, 0.5, "no numeric data", ha="center", va="center")
            return
        ax.hist(x.values, bins=min(30, max(1, int(math.sqrt(len(x))))), color="steelblue", edgecolor="black")
        ax.set_xlabel(x_col)
        ax.set_ylabel("count")


NODE_CLASS_MAPPINGS = {
    "PSN_DataFrameStats": PSN_DataFrameStats,
    "PSN_StatPlotGenerator": PSN_StatPlotGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_DataFrameStats": "PSN DataFrame Stats",
    "PSN_StatPlotGenerator": "PSN Stat Plot Generator",
}
