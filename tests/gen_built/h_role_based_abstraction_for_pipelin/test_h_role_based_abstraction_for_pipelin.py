import json

import torch

from h_role_based_abstraction_for_pipelin import (
    PSN_RoleCatalogue,
    PSN_RoleResolve,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _parse_catalogue_text,
    _resolve_role,
)

CATALOGUE_JSON = json.dumps({
    "entries": [
        {"id": "photo_a", "roles": ["img:best_photo", "img:portrait"],
         "settings": {"model": "sd_xl", "steps": 30}},
        {"id": "photo_b", "roles": ["img:best_photo"],
         "settings": {"model": "sd_15", "steps": 20}},
        {"id": "video_x", "roles": ["vid:best_clip"],
         "settings": {"fps": 24}},
    ]
})


def test_module_mappings():
    assert "PSN_RoleCatalogue" in NODE_CLASS_MAPPINGS
    assert "PSN_RoleResolve" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_RoleCatalogue"]
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_RoleResolve"]
    # INPUT_TYPES classmethod exists and returns a dict with 'required'
    it = PSN_RoleCatalogue.INPUT_TYPES()
    assert "required" in it
    it2 = PSN_RoleResolve.INPUT_TYPES()
    assert "required" in it2 and "optional" in it2


def test_build_catalogue_and_summary():
    node = PSN_RoleCatalogue()
    cat, summary = node.run(CATALOGUE_JSON)
    assert isinstance(cat, dict)
    assert len(cat["entries"]) == 3
    assert cat["roles"]["img:best_photo"] == ["photo_a", "photo_b"]
    assert cat["roles"]["vid:best_clip"] == ["video_x"]
    assert "3 entries" in summary and "3 roles" in summary


def test_resolve_first_candidate():
    cat, _ = PSN_RoleCatalogue().run(CATALOGUE_JSON)
    node = PSN_RoleResolve()
    entry_id, settings_json, ok = node.run(cat, "img:best_photo")
    assert ok is True
    assert entry_id == "photo_a"  # first candidate wins
    settings = json.loads(settings_json)
    assert settings == {"model": "sd_xl", "steps": 30}


def test_resolve_with_overrides():
    cat, _ = PSN_RoleCatalogue().run(CATALOGUE_JSON)
    node = PSN_RoleResolve()
    entry_id, settings_json, ok = node.run(
        cat, "img:best_photo", overrides_json='{"steps": 50, "cfg": 7}'
    )
    assert ok is True
    settings = json.loads(settings_json)
    assert settings["steps"] == 50
    assert settings["cfg"] == 7
    assert settings["model"] == "sd_xl"  # untouched key preserved


def test_resolve_unknown_role():
    cat, _ = PSN_RoleCatalogue().run(CATALOGUE_JSON)
    node = PSN_RoleResolve()
    entry_id, settings_json, ok = node.run(cat, "img:nope")
    assert ok is False
    assert entry_id == ""
    assert json.loads(settings_json) == {}


def test_bad_inputs():
    node = PSN_RoleCatalogue()
    # non-string catalogue
    try:
        node.run(123)
        assert False, "expected ValueError"
    except ValueError:
        pass
    # malformed JSON
    try:
        node.run("not json")
        assert False, "expected ValueError"
    except ValueError:
        pass
    # missing 'entries'
    try:
        node.run(json.dumps({"foo": 1}))
        assert False, "expected ValueError"
    except ValueError:
        pass
    # duplicate entry id
    try:
        _parse_catalogue_text(json.dumps({"entries": [
            {"id": "a", "roles": []}, {"id": "a", "roles": []}
        ]}))
        assert False, "expected ValueError"
    except ValueError:
        pass
    # bad role id on resolve
    cat, _ = node.run(CATALOGUE_JSON)
    try:
        PSN_RoleResolve().run(cat, "")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_latent_validation():
    cat, _ = PSN_RoleCatalogue().run(CATALOGUE_JSON)
    node = PSN_RoleResolve()
    good_latent = {"samples": torch.zeros(1, 4, 8, 8)}
    entry_id, settings_json, ok = node.run(cat, "img:best_photo", latent=good_latent)
    assert ok is True and entry_id == "photo_a"
    # bad latent: wrong rank
    try:
        node.run(cat, "img:best_photo", latent={"samples": torch.zeros(1, 4, 8)})
        assert False, "expected ValueError"
    except ValueError:
        pass
    # bad latent: not a dict
    try:
        node.run(cat, "img:best_photo", latent=[1, 2, 3])
        assert False, "expected ValueError"
    except ValueError:
        pass
    # input not mutated
    assert good_latent["samples"].shape == (1, 4, 8, 8)


if __name__ == "__main__":
    test_module_mappings()
    test_build_catalogue_and_summary()
    test_resolve_first_candidate()
    test_resolve_with_overrides()
    test_resolve_unknown_role()
    test_bad_inputs()
    test_latent_validation()
    print("ok")
