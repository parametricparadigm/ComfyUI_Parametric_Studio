"""Idempotent project structure setup node.

Checks a (virtual) project file tree for missing standard boilerplate files
and reports/injects the missing ones. Running the node twice with the same
inputs yields the same result (idempotent): the second run reports that
nothing is missing.

The node works on plain Python data (dicts of relative path -> content) so it
can be used as a readiness check before any build stage. No files are ever
written to disk; the "project" is a mapping passed through ComfyUI as a
STRING (JSON) so it can be chained with other nodes.
"""

import json

CAT = "ParametricStudio/Project"

# Standard boilerplate files that a minimal project is expected to contain.
# Each entry: relative path -> default content (may be empty string).
DEFAULT_BOILERPLATE = {
    "README.md": "# Project\n\nGenerated project.\n",
    "project.json": '{"name": "project", "version": "0.1.0"}\n',
    "src/main.py": "# entry point\nprint('hello')\n",
    "tests/test_main.py": "def test_main():\n    assert True\n",
    ".gitignore": "__pycache__/\n*.pyc\nbuild/\ndist/\n",
}


def _parse_project(raw):
    """Parse the project mapping from a JSON string.

    Returns (project_dict, error_string). project_dict maps relative path ->
    content string. On error, project_dict is None.
    """
    if raw is None:
        return {}, None
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return None, "project is not valid JSON"
    if not isinstance(data, dict):
        return None, "project must be a JSON object mapping path -> content"
    # Validate keys/values are strings.
    for k, v in data.items():
        if not isinstance(k, str):
            return None, "project keys must be strings"
        if not isinstance(v, str):
            return None, "project values must be strings"
    return data, None


def _check(project, boilerplate):
    """Compute which boilerplate files are missing and which are present.

    Returns (missing, present) as sorted lists of relative paths.
    """
    missing = []
    present = []
    for path in sorted(boilerplate):
        if path in project:
            present.append(path)
        else:
            missing.append(path)
    return missing, present


def _inject(project, boilerplate):
    """Return a NEW project dict with missing boilerplate files injected.

    Never modifies the input dict. Existing files are left untouched.
    """
    new_project = dict(project)
    for path, content in boilerplate.items():
        if path not in new_project:
            new_project[path] = content
    return new_project


def _boilerplate_from_string(raw):
    """Parse an optional custom boilerplate JSON string.

    Returns (boilerplate_dict, error_string). If raw is empty/None, returns
    the default boilerplate.
    """
    if raw is None or raw == "":
        return dict(DEFAULT_BOILERPLATE), None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None, "boilerplate is not valid JSON"
    if not isinstance(data, dict):
        return None, "boilerplate must be a JSON object mapping path -> content"
    for k, v in data.items():
        if not isinstance(k, str):
            return None, "boilerplate keys must be strings"
        if not isinstance(v, str):
            return None, "boilerplate values must be strings"
    return data, None


class PSN_IdempotentProjectStructureSetup:
    """Check a project file tree for missing boilerplate and inject it.

    Idempotent: running twice with the same project yields the same output
    (second run reports zero missing files).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "project": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "{}",
                        "tooltip": "JSON object mapping relative file path -> content.",
                    },
                ),
            },
            "optional": {
                "boilerplate": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Optional JSON object of required files. Empty = defaults.",
                    },
                ),
                "inject": (
                    "BOOLEAN",
                    {"default": True, "tooltip": "If true, add missing files to the output project."},
                ),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("project_out", "report", "missing_count", "present_count")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, project, boilerplate="", inject=True):
        proj, err = _parse_project(project)
        if err is not None:
            raise ValueError(err)

        boiler, berr = _boilerplate_from_string(boilerplate)
        if berr is not None:
            raise ValueError(berr)

        missing, present = _check(proj, boiler)

        if inject:
            out_proj = _inject(proj, boiler)
        else:
            out_proj = dict(proj)

        report = {
            "missing": missing,
            "present": present,
            "total_files": len(out_proj),
            "injected": bool(inject),
            "idempotent": True,
        }
        report_str = json.dumps(report, indent=2, sort_keys=True)
        project_out_str = json.dumps(out_proj, indent=2, sort_keys=True)

        return (project_out_str, report_str, len(missing), len(present))


NODE_CLASS_MAPPINGS = {
    "PSN_IdempotentProjectStructureSetup": PSN_IdempotentProjectStructureSetup,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_IdempotentProjectStructureSetup": "Idempotent Project Structure Setup",
}
