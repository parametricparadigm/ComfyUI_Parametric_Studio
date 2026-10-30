import torch
from n_5_folder_based_batch_queueing_for_image_ import (
    PSN_Folder_Batch_Queue,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _matches_pattern,
)

node = PSN_Folder_Batch_Queue()

# 1. Basic: 3 files, sorted by name
manifest = [
    {"name": "c.png", "mtime": 3.0, "data": b"ccc"},
    {"name": "a.png", "mtime": 1.0, "data": b"aaa"},
    {"name": "b.png", "mtime": 2.0, "data": b"bbb"},
]
images, paths, count = node.run(manifest, "name")
assert count == 3, f"expected 3, got {count}"
assert paths == ["a.png", "b.png", "c.png"], f"bad order: {paths}"
assert len(images) == 3
for img in images:
    assert isinstance(img, torch.Tensor)
    assert img.dim() == 4 and img.shape[0] == 1 and img.shape[3] == 3
    assert img.min() >= 0.0 and img.max() <= 1.0

# 2. Sort by date
images2, paths2, _ = node.run(manifest, "date")
assert paths2 == ["a.png", "b.png", "c.png"], f"date sort: {paths2}"

# 3. Pattern filter: only .jpg
manifest_mixed = [
    {"name": "x.png", "mtime": 1.0, "data": b"1"},
    {"name": "y.jpg", "mtime": 2.0, "data": b"2"},
    {"name": "z.jpeg", "mtime": 3.0, "data": b"3"},
]
_, paths3, c3 = node.run(manifest_mixed, "name", file_pattern="*.jpg")
assert c3 == 1 and paths3 == ["y.jpg"], f"pattern filter: {paths3}"

# 4. max_files limit
_, paths4, c4 = node.run(manifest, "name", max_files=2)
assert c4 == 2 and paths4 == ["a.png", "b.png"], f"max_files: {paths4}"

# 5. Empty manifest
images5, paths5, c5 = node.run([], "name")
assert c5 == 0 and images5 == [] and paths5 == []

# 6. Bad input: manifest not a list
try:
    node.run("not a list", "name")
    assert False, "should have raised TypeError"
except TypeError:
    pass

# 7. Bad sort_order
try:
    node.run(manifest, "bogus")
    assert False, "should have raised ValueError"
except ValueError:
    pass

# 8. Bad manifest entry (missing name)
try:
    node.run([{"data": b"x"}], "name")
    assert False, "should have raised ValueError"
except ValueError:
    pass

# 9. Deterministic: same data -> same tensor
i_a, _, _ = node.run([{"name": "a.png", "mtime": 1.0, "data": b"aaa"}], "name")
i_b, _, _ = node.run([{"name": "a.png", "mtime": 1.0, "data": b"aaa"}], "name")
assert torch.equal(i_a[0], i_b[0]), "same data must give same tensor"

# 10. Different data -> different tensor
i_c, _, _ = node.run([{"name": "a.png", "mtime": 1.0, "data": b"bbb"}], "name")
assert not torch.equal(i_a[0], i_c[0]), "different data should differ"

# 11. Module-level mappings exist
assert "PSN_Folder_Batch_Queue" in NODE_CLASS_MAPPINGS
assert "PSN_Folder_Batch_Queue" in NODE_DISPLAY_NAME_MAPPINGS

# 12. INPUT_TYPES / RETURN_TYPES sanity
it = PSN_Folder_Batch_Queue.INPUT_TYPES()
assert "required" in it and "manifest" in it["required"]
assert PSN_Folder_Batch_Queue.RETURN_TYPES == ("LIST[IMAGE]", "LIST[STRING]", "INT")
assert PSN_Folder_Batch_Queue.FUNCTION == "run"
assert PSN_Folder_Batch_Queue.CATEGORY.startswith("ParametricStudio/")

# 13. Input not mutated
manifest_copy = [dict(m) for m in manifest]
node.run(manifest, "name")
assert manifest == manifest_copy, "input manifest was mutated"

# 14. _matches_pattern edge cases
assert _matches_pattern("a.png", "*.png")
assert not _matches_pattern("a.jpg", "*.png")
assert _matches_pattern("a.png", "*")
assert _matches_pattern("a1.png", "a?.png")
assert not _matches_pattern("a12.png", "a?.png")

print("ok")
