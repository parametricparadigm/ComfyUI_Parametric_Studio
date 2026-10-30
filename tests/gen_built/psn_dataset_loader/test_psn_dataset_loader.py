import json

from psn_dataset_loader import (
    PSN_Dataset_Loader,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    DATASET,
)

node = PSN_Dataset_Loader()

# 1. CSV happy path
out, meta = node.run("name,age\nAlice,30\nBob,25", "csv")
assert out["num_records"] == 2
assert out["records"][0] == {"name": "Alice", "age": "30"}
assert out["keys"] == ["name", "age"]
m = json.loads(meta)
assert m["num_records"] == 2 and m["format"] == "csv"

# 2. JSON happy path (list of objects)
out, meta = node.run('[{"a": 1}, {"a": 2, "b": 3}]', "json")
assert out["num_records"] == 2
assert out["keys"] == ["a", "b"]
assert json.loads(meta)["num_records"] == 2

# 3. JSON single object -> wrapped in list
out, _ = node.run('{"x": 5}', "json")
assert out["num_records"] == 1
assert out["records"] == [{"x": 5}]

# 4. Folder format: newline-separated paths
out, meta = node.run("/data/a.png\n/data/b.png", "folder")
assert out["num_records"] == 2
assert out["records"][1] == {"path": "/data/b.png"}

# 5. Edge: empty CSV (only header) -> zero records
out, meta = node.run("name,age", "csv")
assert out["num_records"] == 0
assert out["records"] == []
assert json.loads(meta)["num_records"] == 0

# 6. Bad input: unsupported format raises
try:
    node.run("x", "yaml")
    raise AssertionError("expected ValueError for bad format")
except ValueError:
    pass

# 7. Bad input: empty path raises
try:
    node.run("   ", "csv")
    raise AssertionError("expected ValueError for empty path")
except ValueError:
    pass

# 8. Bad input: non-string path raises TypeError
try:
    node.run(123, "csv")
    raise AssertionError("expected TypeError for non-string path")
except TypeError:
    pass

# 9. Bad input: invalid JSON raises
try:
    node.run("{not json", "json")
    raise AssertionError("expected error for invalid JSON")
except Exception:
    pass

# 10. Module-level mappings exist and are consistent
assert "PSN_Dataset_Loader" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_Dataset_Loader"] is PSN_Dataset_Loader
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Dataset_Loader"] == "PSN Dataset Loader"

# 11. Node contract: INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
it = PSN_Dataset_Loader.INPUT_TYPES()
assert "dataset_path" in it["required"]
assert "format" in it["required"]
assert PSN_Dataset_Loader.RETURN_TYPES == (DATASET, "STRING")
assert PSN_Dataset_Loader.FUNCTION == "run"
assert PSN_Dataset_Loader.CATEGORY.startswith("ParametricStudio/")

# 12. CSV with ragged rows: missing cells become empty strings
out, _ = node.run("a,b,c\n1,2", "csv")
assert out["records"][0] == {"a": "1", "b": "2", "c": ""}

print("ok")
