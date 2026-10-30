"""Tests for h_define_a_standard_interface_for_re.

Run:  python3 -B test_h_define_a_standard_interface_for_re.py
Must print 'ok' and exit 0.
"""

import json
import posixpath

from h_define_a_standard_interface_for_re import (
    InterpreterSpec,
    InterpreterRegistry,
    PSN_InterpreterRegistryBuild,
    PSN_InterpreterResolve,
    PSN_InterpreterSpecInfo,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


# ---------------------------------------------------------------------------
# 1. InterpreterSpec path computation (linux)
# ---------------------------------------------------------------------------
spec = InterpreterSpec("scrape", "/opt/psn/tools", "linux", "venv")
assert spec.venv_dir == "/opt/psn/tools/scrape/venv", spec.venv_dir
assert spec.bin_dir == "/opt/psn/tools/scrape/venv/bin", spec.bin_dir
assert spec.interpreter == "/opt/psn/tools/scrape/venv/bin/python", spec.interpreter

# ---------------------------------------------------------------------------
# 2. InterpreterSpec path computation (windows)
# ---------------------------------------------------------------------------
win_spec = InterpreterSpec("train", "C:/tools", "win32", "venv")
assert win_spec.bin_dir == "C:/tools/train/venv/Scripts", win_spec.bin_dir
assert win_spec.interpreter == "C:/tools/train/venv/Scripts/python.exe", win_spec.interpreter

# ---------------------------------------------------------------------------
# 3. Bad input: empty family raises ValueError
# ---------------------------------------------------------------------------
try:
    InterpreterSpec("", "/opt")
    raise AssertionError("expected ValueError for empty family")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 4. Bad input: unknown platform raises ValueError
# ---------------------------------------------------------------------------
try:
    InterpreterSpec("scrape", "/opt", "freebsd")
    raise AssertionError("expected ValueError for bad platform")
except ValueError:
    pass

# ---------------------------------------------------------------------------
# 5. Registry resolve: explicit family
# ---------------------------------------------------------------------------
reg = InterpreterRegistry()
reg.register(InterpreterSpec("scrape", "/opt/psn/tools"))
reg.register(InterpreterSpec("train", "/opt/psn/tools"))
assert reg.resolve("scrape") == "/opt/psn/tools/scrape/venv/bin/python"
assert reg.resolve("train") == "/opt/psn/tools/train/venv/bin/python"

# ---------------------------------------------------------------------------
# 6. Registry resolve: default fallback
# ---------------------------------------------------------------------------
reg.set_default("scrape")
assert reg.resolve("unknown_family") == "/opt/psn/tools/scrape/venv/bin/python"

# ---------------------------------------------------------------------------
# 7. Registry resolve: no match and no default -> KeyError
# ---------------------------------------------------------------------------
reg2 = InterpreterRegistry()
reg2.register(InterpreterSpec("scrape", "/opt"))
try:
    reg2.resolve("nope")
    raise AssertionError("expected KeyError")
except KeyError:
    pass

# ---------------------------------------------------------------------------
# 8. Registry with probe that rejects -> LookupError
# ---------------------------------------------------------------------------
reg3 = InterpreterRegistry(probe=lambda p: False)
reg3.register(InterpreterSpec("scrape", "/opt"))
try:
    reg3.resolve("scrape")
    raise AssertionError("expected LookupError")
except LookupError:
    pass

# ---------------------------------------------------------------------------
# 9. Registry with probe that accepts -> ok
# ---------------------------------------------------------------------------
reg4 = InterpreterRegistry(probe=lambda p: True)
reg4.register(InterpreterSpec("scrape", "/opt"))
assert reg4.resolve("scrape") == "/opt/scrape/venv/bin/python"

# ---------------------------------------------------------------------------
# 10. families() excludes 'default' alias
# ---------------------------------------------------------------------------
assert reg.families() == ["scrape", "train"], reg.families()
assert len(reg) == 2

# ---------------------------------------------------------------------------
# 11. Node: PSN_InterpreterRegistryBuild
# ---------------------------------------------------------------------------
node = PSN_InterpreterRegistryBuild()
(reg_obj,) = node.run(
    root="/opt/psn/tools",
    platform="linux",
    families="scrape, train, eval",
    venv_name="venv",
    default_family="scrape",
)
assert isinstance(reg_obj, InterpreterRegistry)
assert reg_obj.families() == ["eval", "scrape", "train"]
assert reg_obj.resolve("train") == "/opt/psn/tools/train/venv/bin/python"
assert reg_obj.resolve("anything") == "/opt/psn/tools/scrape/venv/bin/python"  # default

# ---------------------------------------------------------------------------
# 12. Node: PSN_InterpreterResolve (found + not found)
# ---------------------------------------------------------------------------
res_node = PSN_InterpreterResolve()
path, found = res_node.run(reg_obj, "train")
assert found is True
assert path == "/opt/psn/tools/train/venv/bin/python"

path2, found2 = res_node.run(reg_obj, "nonexistent")
# 'nonexistent' falls back to default 'scrape', so found should be True
assert found2 is True
assert path2 == "/opt/psn/tools/scrape/venv/bin/python"

# registry with no default: unknown family -> found=False
reg_nod = InterpreterRegistry()
reg_nod.register(InterpreterSpec("scrape", "/opt"))
path3, found3 = res_node.run(reg_nod, "ghost")
assert found3 is False
assert path3 == ""

# ---------------------------------------------------------------------------
# 13. Node: PSN_InterpreterResolve bad registry type
# ---------------------------------------------------------------------------
try:
    res_node.run("not a registry", "scrape")
    raise AssertionError("expected TypeError")
except TypeError:
    pass

# ---------------------------------------------------------------------------
# 14. Node: PSN_InterpreterSpecInfo
# ---------------------------------------------------------------------------
info_node = PSN_InterpreterSpecInfo()
(spec_json,) = info_node.run(reg_obj, "scrape")
d = json.loads(spec_json)
assert d["family"] == "scrape"
assert d["interpreter"] == "/opt/psn/tools/scrape/venv/bin/python"
assert d["platform"] == "linux"

# unknown family -> empty dict
(spec_json2,) = info_node.run(reg_nod, "ghost")
assert json.loads(spec_json2) == {}

# ---------------------------------------------------------------------------
# 15. NODE_CLASS_MAPPINGS / NODE_DISPLAY_NAME_MAPPINGS sanity
# ---------------------------------------------------------------------------
assert set(NODE_CLASS_MAPPINGS) == {
    "PSN_InterpreterRegistryBuild",
    "PSN_InterpreterResolve",
    "PSN_InterpreterSpecInfo",
}
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_InterpreterResolve"] == "Interpreter Resolve"
for cls_name, cls in NODE_CLASS_MAPPINGS.items():
    assert hasattr(cls, "INPUT_TYPES"), cls_name
    assert hasattr(cls, "RETURN_TYPES"), cls_name
    assert cls.FUNCTION == "run", cls_name
    assert cls.CATEGORY.startswith("ParametricStudio/"), cls_name

# ---------------------------------------------------------------------------
# 16. Edge: root with trailing slash is normalised
# ---------------------------------------------------------------------------
spec_slash = InterpreterSpec("scrape", "/opt/psn/tools/")
assert spec_slash.root == "/opt/psn/tools", spec_slash.root
assert spec_slash.venv_dir == "/opt/psn/tools/scrape/venv"

# ---------------------------------------------------------------------------
# 17. Edge: families string with extra whitespace
# ---------------------------------------------------------------------------
(reg_ws,) = PSN_InterpreterRegistryBuild().run(
    root="/opt", platform="linux", families="  scrape ,  train  ",
    venv_name="venv", default_family="scrape",
)
assert reg_ws.families() == ["scrape", "train"]

# ---------------------------------------------------------------------------
# 18. Edge: empty families string raises ValueError
# ---------------------------------------------------------------------------
try:
    PSN_InterpreterRegistryBuild().run(
        root="/opt", platform="linux", families="  ",
        venv_name="venv", default_family="scrape",
    )
    raise AssertionError("expected ValueError for empty families")
except ValueError:
    pass

print("ok")
