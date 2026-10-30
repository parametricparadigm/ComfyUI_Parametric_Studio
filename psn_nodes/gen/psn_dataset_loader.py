"""PSN_Dataset_Loader: load a dataset (csv/json/folder) and emit metadata.

ComfyUI custom node. The DATASET output is a plain Python dict (custom type)
holding the parsed records plus a small summary, so downstream nodes can
iterate over it without any heavy dependencies.
"""

import json
import csv

CAT = "ParametricStudio/Dataset"

DATASET = "PSN_DATASET"


def _parse_csv(text):
    """Parse CSV text into a list of dict records (first row = header)."""
    rows = list(csv.reader(text.splitlines()))
    rows = [r for r in rows if r and any(cell.strip() for cell in r)]
    if not rows:
        return []
    header = [h.strip() for h in rows[0]]
    records = []
    for row in rows[1:]:
        rec = {}
        for i, key in enumerate(header):
            rec[key] = row[i] if i < len(row) else ""
        records.append(rec)
    return records


def _parse_json(text):
    """Parse JSON text; accept a list of objects or a single object."""
    data = json.loads(text)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError("JSON dataset must be a list or an object")


def _parse_folder(text):
    """'Folder' format: the path string is treated as a newline-separated
    list of file paths (no filesystem access is performed here)."""
    paths = [p.strip() for p in text.splitlines() if p.strip()]
    return [{"path": p} for p in paths]


_PARSERS = {
    "csv": _parse_csv,
    "json": _parse_json,
    "folder": _parse_folder,
}


class PSN_Dataset_Loader:
    """Load a dataset (csv / json / folder) and return records + metadata."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dataset_path": ("STRING", {"default": ""}),
                "format": (["csv", "json", "folder"], {"default": "csv"}),
            }
        }

    RETURN_TYPES = (DATASET, "STRING")
    RETURN_NAMES = ("DATASET", "metadata")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, dataset_path, format):
        fmt = (format or "").strip().lower()
        if fmt not in _PARSERS:
            raise ValueError("unsupported dataset format: %r" % (format,))
        if not isinstance(dataset_path, str):
            raise TypeError("dataset_path must be a string")
        text = dataset_path
        if not text.strip():
            raise ValueError("dataset_path is empty")

        records = _PARSERS[fmt](text)
        if not isinstance(records, list):
            raise ValueError("parser did not return a list of records")

        n = len(records)
        keys = []
        for rec in records:
            if isinstance(rec, dict):
                for k in rec:
                    if k not in keys:
                        keys.append(k)

        metadata = json.dumps(
            {
                "format": fmt,
                "num_records": n,
                "keys": keys,
                "source": dataset_path[:200],
            },
            sort_keys=True,
        )

        dataset = {
            "records": records,
            "format": fmt,
            "num_records": n,
            "keys": keys,
        }
        return (dataset, metadata)


NODE_CLASS_MAPPINGS = {"PSN_Dataset_Loader": PSN_Dataset_Loader}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Dataset_Loader": "PSN Dataset Loader"}
