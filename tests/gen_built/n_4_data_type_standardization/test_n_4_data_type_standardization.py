"""Tests for n_4_data_type_standardization.py"""

from n_4_data_type_standardization import (
    PSN_StringToList,
    PSN_ListToString,
    PSN_IntToFloatList,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

# --- PSN_StringToList ---

# 1. Basic split
node = PSN_StringToList()
result = node.run("a,b,c", ",")
assert result[0] == ["a", "b", "c"], f"Expected ['a','b','c'], got {result[0]}"

# 2. Delimiter not found → single-element list
result = node.run("hello", ",")
assert result[0] == ["hello"], f"Expected ['hello'], got {result[0]}"

# 3. Empty string → empty list
result = node.run("", ",")
assert result[0] == [], f"Expected [], got {result[0]}"

# 4. Custom delimiter
result = node.run("a|b|c", "|")
assert result[0] == ["a", "b", "c"], f"Expected ['a','b','c'], got {result[0]}"

# --- PSN_ListToString ---

# 5. Basic join
node2 = PSN_ListToString()
result = node2.run(["a", "b", "c"], ",")
assert result[0] == "a,b,c", f"Expected 'a,b,c', got {result[0]}"

# 6. Empty list → empty string
result = node2.run([], ",")
assert result[0] == "", f"Expected '', got {result[0]}"

# 7. Custom delimiter
result = node2.run(["x", "y"], "-")
assert result[0] == "x-y", f"Expected 'x-y', got {result[0]}"

# --- PSN_IntToFloatList ---

# 8. Basic conversion
node3 = PSN_IntToFloatList()
result = node3.run([1, 2, 3])
assert result[0] == [1.0, 2.0, 3.0], f"Expected [1.0,2.0,3.0], got {result[0]}"
assert all(isinstance(v, float) for v in result[0]), "All elements must be float"

# 9. Empty list
result = node3.run([])
assert result[0] == [], f"Expected [], got {result[0]}"

# 10. Bad input: non-numeric element raises ValueError
try:
    node3.run([1, "abc", 3])
    assert False, "Expected ValueError for non-numeric element"
except ValueError:
    pass

# --- Module-level mappings ---

# 11. NODE_CLASS_MAPPINGS has all three nodes
assert "PSN_StringToList" in NODE_CLASS_MAPPINGS
assert "PSN_ListToString" in NODE_CLASS_MAPPINGS
assert "PSN_IntToFloatList" in NODE_CLASS_MAPPINGS

# 12. NODE_DISPLAY_NAME_MAPPINGS has all three nodes
assert "PSN_StringToList" in NODE_DISPLAY_NAME_MAPPINGS
assert "PSN_ListToString" in NODE_DISPLAY_NAME_MAPPINGS
assert "PSN_IntToFloatList" in NODE_DISPLAY_NAME_MAPPINGS

# 13. Each node class has required attributes
for cls in (PSN_StringToList, PSN_ListToString, PSN_IntToFloatList):
    assert hasattr(cls, "INPUT_TYPES"), f"{cls.__name__} missing INPUT_TYPES"
    assert hasattr(cls, "RETURN_TYPES"), f"{cls.__name__} missing RETURN_TYPES"
    assert hasattr(cls, "FUNCTION"), f"{cls.__name__} missing FUNCTION"
    assert cls.FUNCTION == "run", f"{cls.__name__} FUNCTION must be 'run'"
    assert hasattr(cls, "CATEGORY"), f"{cls.__name__} missing CATEGORY"
    assert cls.CATEGORY.startswith("ParametricStudio/"), f"{cls.__name__} bad CATEGORY"

print("ok")
