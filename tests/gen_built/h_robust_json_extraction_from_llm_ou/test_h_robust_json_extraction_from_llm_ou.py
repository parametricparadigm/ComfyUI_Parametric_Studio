"""Tests for h_robust_json_extraction_from_llm_ou."""

import json
import sys

from h_robust_json_extraction_from_llm_ou import (
    extract_first_json,
    PSN_ExtractJsonFromLLM,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

# 1. Simple JSON object
val, err = extract_first_json('{"a": 1, "b": 2}')
assert val == {"a": 1, "b": 2}, f"Test 1 failed: {val}"
assert err == "", f"Test 1 error: {err}"

# 2. JSON with surrounding prose
val, err = extract_first_json('Here is the result: {"name": "test", "count": 42} hope that helps')
assert val == {"name": "test", "count": 42}, f"Test 2 failed: {val}"
assert err == "", f"Test 2 error: {err}"

# 3. JSON in markdown code fence
fenced = '\n{"key": "value", "nested": {"x": 1}}\n'
val, err = extract_first_json(fenced)
assert val == {"key": "value", "nested": {"x": 1}}, f"Test 3 failed: {val}"
assert err == "", f"Test 3 error: {err}"

# 4. Nested braces and escaped quotes
complex_json = '{"msg": "He said \\"hello\\"", "data": {"list": [1, 2, {"deep": true}]}}'
val, err = extract_first_json(complex_json)
assert val == {"msg": 'He said "hello"', "data": {"list": [1, 2, {"deep": True}]}}, f"Test 4 failed: {val}"
assert err == "", f"Test 4 error: {err}"

# 5. Empty input (edge case)
val, err = extract_first_json("")
assert val is None, f"Test 5 failed: expected None, got {val}"
assert err != "", f"Test 5: expected error message"

# 6. No JSON at all (bad input)
val, err = extract_first_json("This is just plain text with no JSON anywhere.")
assert val is None, f"Test 6 failed: expected None, got {val}"
assert err != "", f"Test 6: expected error message"

# 7. Non-string input (bad input)
val, err = extract_first_json(12345)
assert val is None, f"Test 7 failed: expected None, got {val}"
assert err == "Input is not a string", f"Test 7 error: {err}"

# 8. JSON array
val, err = extract_first_json('Result: [1, 2, 3] done')
assert val == [1, 2, 3], f"Test 8 failed: {val}"
assert err == "", f"Test 8 error: {err}"

# 9. Multiple JSON objects - should return the first valid one
val, err = extract_first_json('First: {"a": 1} Second: {"b": 2}')
assert val == {"a": 1}, f"Test 9 failed: {val}"
assert err == "", f"Test 9 error: {err}"

# 10. Node class structure
assert "PSN_ExtractJsonFromLLM" in NODE_CLASS_MAPPINGS, "Test 10: node not in mappings"
assert "PSN_ExtractJsonFromLLM" in NODE_DISPLAY_NAME_MAPPINGS, "Test 10: display name missing"
node_cls = NODE_CLASS_MAPPINGS["PSN_ExtractJsonFromLLM"]
assert node_cls.FUNCTION == "run", "Test 10: FUNCTION should be 'run'"
assert node_cls.CATEGORY == "ParametricStudio/Text", "Test 10: wrong category"
assert node_cls.RETURN_TYPES == ("STRING", "STRING"), "Test 10: wrong return types"
assert node_cls.RETURN_NAMES == ("json_string", "error"), "Test 10: wrong return names"

# 11. Node run method - success
node = PSN_ExtractJsonFromLLM()
json_str, err = node.run('{"hello": "world"}')
assert json_str == '{"hello": "world"}', f"Test 11 failed: {json_str}"
assert err == "", f"Test 11 error: {err}"

# 12. Node run method - failure
json_str, err = node.run("no json here")
assert json_str == "", f"Test 12 failed: {json_str}"
assert err != "", f"Test 12: expected error"

# 13. INPUT_TYPES has required field
it = PSN_ExtractJsonFromLLM.INPUT_TYPES()
assert "required" in it, "Test 13: no required in INPUT_TYPES"
assert "llm_output" in it["required"], "Test 13: llm_output not in required"

# 14. JSON with whitespace and newlines
val, err = extract_first_json('  \n  {"a": 1,\n  "b": 2}  \n  ')
assert val == {"a": 1, "b": 2}, f"Test 14 failed: {val}"
assert err == "", f"Test 14 error: {err}"

print('ok')
