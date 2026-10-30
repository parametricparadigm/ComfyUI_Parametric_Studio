import torch

from n_10_workflow_group_control import (
    PSN_Group_Bypass,
    PSN_Node_Gate,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


# --- module-level wiring ----------------------------------------------------
assert "PSN_Group_Bypass" in NODE_CLASS_MAPPINGS
assert "PSN_Node_Gate" in NODE_CLASS_MAPPINGS
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Group_Bypass"]
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Node_Gate"]

# --- INPUT_TYPES / metadata -------------------------------------------------
bt = PSN_Group_Bypass.INPUT_TYPES()
assert "group_id" in bt["required"] and "enabled" in bt["required"]
assert PSN_Group_Bypass.RETURN_TYPES == ("BOOLEAN",)
assert PSN_Group_Bypass.FUNCTION == "run"
assert PSN_Group_Bypass.CATEGORY.startswith("ParametricStudio/")

gt = PSN_Node_Gate.INPUT_TYPES()
assert "input" in gt["required"] and "bypass_signal" in gt["required"]
assert PSN_Node_Gate.RETURN_TYPES == ("*",)

# --- group bypass signal ----------------------------------------------------
gb = PSN_Group_Bypass()
# enabled=True  -> group runs -> bypass False
assert gb.run("audio", True) == (False,)
# enabled=False -> group skipped -> bypass True
assert gb.run("audio", False) == (True,)
# 0/1 coercion
assert gb.run("audio", 0) == (True,)
assert gb.run("audio", 1) == (False,)

# bad group_id
try:
    gb.run("", True)
    raise AssertionError("empty group_id should raise")
except ValueError:
    pass
try:
    gb.run(123, True)
    raise AssertionError("non-string group_id should raise")
except TypeError:
    pass

# --- node gate: bypass passes through unchanged -----------------------------
gate = PSN_Node_Gate()
img = torch.full((1, 4, 4, 3), 0.7)
# bypass=True: identity, same object (no copy, no mutation)
out = gate.run(img, True)[0]
assert out is img

# bypass=False: processing clamps floats to [0,1] and clones (no in-place)
big = torch.full((1, 2, 2, 3), 1.5)
processed = gate.run(big, False)[0]
assert processed is not big
assert torch.all(processed <= 1.0)
assert torch.all(big == 1.5)  # input untouched

# --- node gate: scalar / string / container processing ----------------------
assert gate.run(3.14159, False)[0] == 3.1416
assert gate.run("  hi  ", False)[0] == "hi"
assert gate.run("  hi  ", True)[0] == "  hi  "  # bypass keeps original
assert gate.run([1, 2.5], False)[0] == [1, 2.5]
assert gate.run(None, False)[0] is None

# --- end-to-end: disabled group skips processing ----------------------------
signal = gb.run("audio", False)[0]          # group disabled -> True
result = gate.run(9.99999, signal)[0]
assert result == 9.99999                    # passed through, not rounded

signal_on = gb.run("audio", True)[0]        # group enabled -> False
result_on2 = gate.run(2.56789, signal_on)[0]
assert result_on2 == 2.5679

# --- bad bypass_signal -------------------------------------------------------
try:
    gate.run(1, 0.5)
    raise AssertionError("0.5 bypass should raise")
except ValueError:
    pass
try:
    gate.run(1, "yes")
    raise AssertionError("string bypass should raise")
except TypeError:
    pass

print("ok")
