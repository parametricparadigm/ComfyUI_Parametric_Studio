"""Tests for h_idempotent_project_structure_setup."""

import json
import sys

sys.path.insert(0, ".")

from h_idempotent_project_structure_setup import (
    PSN_IdempotentProjectStructureSetup,
    DEFAULT_BOILERPLATE,
    _parse_project,
    _check,
    _inject,
    _boilerplate_from_string,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_module_level_mappings():
    """NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS exist and are consistent."""
    assert "PSN_IdempotentProjectStructureSetup" in NODE_CLASS_MAPPINGS
    assert "PSN_IdempotentProjectStructureSetup" in NODE_DISPLAY_NAME_MAPPINGS
    cls = NODE_CLASS_MAPPINGS["PSN_IdempotentProjectStructureSetup"]
    assert cls is PSN_IdempotentProjectStructureSetup
    assert isinstance(NODE_DISPLAY_NAME_MAPPINGS["PSN_IdempotentProjectStructureSetup"], str)


def test_input_types_structure():
    """INPUT_TYPES has required 'project' and optional 'boilerplate'/'inject'."""
    it = PSN_IdempotentProjectStructureSetup.INPUT_TYPES()
    assert "project" in it["required"]
    assert "boilerplate" in it["optional"]
    assert "inject" in it["optional"]
    # RETURN_TYPES / RETURN_NAMES / FUNCTION / CATEGORY
    assert PSN_IdempotentProjectStructureSetup.RETURN_TYPES == ("STRING", "STRING", "INT", "INT")
    assert PSN_IdempotentProjectStructureSetup.RETURN_NAMES == ("project_out", "report", "missing_count", "present_count")
    assert PSN_IdempotentProjectStructureSetup.FUNCTION == "run"
    assert PSN_IdempotentProjectStructureSetup.CATEGORY.startswith("ParametricStudio/")


def test_empty_project_all_missing():
    """Empty project -> all default boilerplate files are missing."""
    node = PSN_IdempotentProjectStructureSetup()
    proj_out, report, missing_count, present_count = node.run(project="{}", inject=True)
    assert missing_count == len(DEFAULT_BOILERPLATE)
    assert present_count == 0
    rep = json.loads(report)
    assert len(rep["missing"]) == len(DEFAULT_BOILERPLATE)
    assert rep["present"] == []
    # Output project should now contain all boilerplate files
    out = json.loads(proj_out)
    for path in DEFAULT_BOILERPLATE:
        assert path in out, f"expected {path} in output project"


def test_idempotent_second_run():
    """Running the node twice with the same input yields the same output (idempotent)."""
    node = PSN_IdempotentProjectStructureSetup()
    proj1, rep1, mc1, pc1 = node.run(project="{}", inject=True)
    # Second run: feed the output of the first run back in.
    proj2, rep2, mc2, pc2 = node.run(project=proj1, inject=True)
    assert mc2 == 0, "second run should find no missing files"
    assert pc2 == len(DEFAULT_BOILERPLATE)
    # Output should be identical
    assert json.loads(proj1) == json.loads(proj2)


def test_partial_project():
    """Project with some files present -> only missing ones are injected."""
    existing = {"README.md": "# My Project\n", "project.json": '{"name": "test"}\n'}
    node = PSN_IdempotentProjectStructureSetup()
    proj_out, report, mc, pc = node.run(project=json.dumps(existing), inject=True)
    # 5 default files, 2 present -> 3 missing
    assert pc == 2
    assert mc == len(DEFAULT_BOILERPLATE) - 2
    out = json.loads(proj_out)
    # Existing content is preserved (not overwritten)
    assert out["README.md"] == "# My Project\n"
    assert out["project.json"] == '{"name": "test"}\n'
    # Missing files are injected with default content
    assert "src/main.py" in out
    assert out["src/main.py"] == DEFAULT_BOILERPLATE["src/main.py"]


def test_inject_false_does_not_add():
    """With inject=False, missing files are reported but not added."""
    node = PSN_IdempotentProjectStructureSetup()
    proj_out, report, mc, pc = node.run(project="{}", inject=False)
    out = json.loads(proj_out)
    assert len(out) == 0, "no files should be added when inject=False"
    assert mc == len(DEFAULT_BOILERPLATE)


def test_custom_boilerplate():
    """Custom boilerplate overrides the defaults."""
    custom = {"a.txt": "A", "b.txt": "B"}
    node = PSN_IdempotentProjectStructureSetup()
    proj_out, report, mc, pc = node.run(project="{}", boilerplate=json.dumps(custom), inject=True)
    assert mc == 2
    out = json.loads(proj_out)
    assert out == {"a.txt": "A", "b.txt": "B"}


def test_bad_input_invalid_json():
    """Invalid JSON project string raises ValueError."""
    node = PSN_IdempotentProjectStructureSetup()
    try:
        node.run(project="not valid json {{{", inject=True)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "not valid JSON" in str(e)


def test_bad_input_non_dict_json():
    """JSON array (not object) raises ValueError."""
    node = PSN_IdempotentProjectStructureSetup()
    try:
        node.run(project="[1,2,3]", inject=True)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "must be a JSON object" in str(e)


def test_bad_input_non_string_value():
    """Project with non-string value raises ValueError."""
    node = PSN_IdempotentProjectStructureSetup()
    try:
        node.run(project='{"a": 123}', inject=True)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "values must be strings" in str(e)


def test_input_not_modified():
    """The input project dict is never modified in place."""
    original = {"README.md": "# Original"}
    snapshot = dict(original)
    node = PSN_IdempotentProjectStructureSetup()
    node.run(project=json.dumps(original), inject=True)
    assert original == snapshot, "input dict must not be mutated"


def test_parse_project_none():
    """_parse_project(None) returns empty dict, no error."""
    proj, err = _parse_project(None)
    assert err is None
    assert proj == {}


def test_check_sorted():
    """_check returns sorted lists."""
    proj = {"b.txt": "x"}
    boiler = {"a.txt": "1", "b.txt": "2", "c.txt": "3"}
    missing, present = _check(proj, boiler)
    assert missing == ["a.txt", "c.txt"]
    assert present == ["b.txt"]


def test_inject_does_not_mutate():
    """_inject returns a new dict; original is unchanged."""
    proj = {"a.txt": "orig"}
    boiler = {"a.txt": "default", "b.txt": "new"}
    result = _inject(proj, boiler)
    assert proj == {"a.txt": "orig"}, "original must not be mutated"
    assert result == {"a.txt": "orig", "b.txt": "new"}


def test_boilerplate_from_string_empty():
    """Empty boilerplate string returns defaults."""
    bp, err = _boilerplate_from_string("")
    assert err is None
    assert bp == DEFAULT_BOILERPLATE


def test_boilerplate_bad_json():
    """Invalid boilerplate JSON raises via _boilerplate_from_string."""
    bp, err = _boilerplate_from_string("not json")
    assert bp is None
    assert err is not None
    assert "not valid JSON" in err


if __name__ == "__main__":
    test_module_level_mappings()
    test_input_types_structure()
    test_empty_project_all_missing()
    test_idempotent_second_run()
    test_partial_project()
    test_inject_false_does_not_add()
    test_custom_boilerplate()
    test_bad_input_invalid_json()
    test_bad_input_non_dict_json()
    test_bad_input_non_string_value()
    test_input_not_modified()
    test_parse_project_none()
    test_check_sorted()
    test_inject_does_not_mutate()
    test_boilerplate_from_string_empty()
    test_boilerplate_bad_json()
    print("ok")
