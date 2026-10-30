"""Tests for PSN_Lora_Dataset_Loader."""

import json
import pytest

from psn_nodes.gen.psn_lora_dataset_loader import (
    PSN_Lora_Dataset_Loader,
    _validate_extension,
    _parse_manifest,
    _matches_extension,
    _sort_entries,
)


def _make_manifest(entries):
    return json.dumps(entries)


class TestPSN_Lora_Dataset_Loader:

    def test_basic_load_and_sort_by_name(self):
        manifest = _make_manifest([
            {"name": "zeta.safetensors", "path": "/data/zeta.safetensors", "size": 100, "date": "2024-01-01"},
            {"name": "alpha.safetensors", "path": "/data/alpha.safetensors", "size": 200, "date": "2024-01-02"},
            {"name": "mid.safetensors", "path": "/data/mid.safetensors", "size": 150, "date": "2024-01-03"},
        ])
        node = PSN_Lora_Dataset_Loader()
        lora_list, names = node.run(manifest, ".safetensors", "name")
        assert len(lora_list) == 3
        assert lora_list[0]["name"] == "alpha.safetensors"
        assert lora_list[1]["name"] == "mid.safetensors"
        assert lora_list[2]["name"] == "zeta.safetensors"
        assert names == "alpha.safetensors, mid.safetensors, zeta.safetensors"

    def test_filter_by_extension_excludes_non_matching(self):
        manifest = _make_manifest([
            {"name": "good.safetensors", "path": "/data/good.safetensors", "size": 10, "date": ""},
            {"name": "bad.ckpt", "path": "/data/bad.ckpt", "size": 20, "date": ""},
            {"name": "also_good.safetensors", "path": "/data/also_good.safetensors", "size": 30, "date": ""},
        ])
        node = PSN_Lora_Dataset_Loader()
        lora_list, names = node.run(manifest, ".safetensors", "name")
        assert len(lora_list) == 2
        assert "bad.ckpt" not in names
        assert "good.safetensors" in names
        assert "also_good.safetensors" in names

    def test_sort_by_size(self):
        manifest = _make_manifest([
            {"name": "big.safetensors", "path": "/data/big.safetensors", "size": 300, "date": ""},
            {"name": "small.safetensors", "path": "/data/small.safetensors", "size": 100, "date": ""},
            {"name": "medium.safetensors", "path": "/data/medium.safetensors", "size": 200, "date": ""},
        ])
        node = PSN_Lora_Dataset_Loader()
        lora_list, names = node.run(manifest, ".safetensors", "size")
        assert lora_list[0]["size"] == 100
        assert lora_list[1]["size"] == 200
        assert lora_list[2]["size"] == 300

    def test_sort_by_date(self):
        manifest = _make_manifest([
            {"name": "c.safetensors", "path": "/data/c.safetensors", "size": 1, "date": "2024-03-01"},
            {"name": "a.safetensors", "path": "/data/a.safetensors", "size": 1, "date": "2024-01-01"},
            {"name": "b.safetensors", "path": "/data/b.safetensors", "size": 1, "date": "2024-02-01"},
        ])
        node = PSN_Lora_Dataset_Loader()
        lora_list, names = node.run(manifest, ".safetensors", "date")
        assert lora_list[0]["name"] == "a.safetensors"
        assert lora_list[1]["name"] == "b.safetensors"
        assert lora_list[2]["name"] == "c.safetensors"

    def test_empty_manifest(self):
        node = PSN_Lora_Dataset_Loader()
        lora_list, names = node.run("[]", ".safetensors", "name")
        assert lora_list == []
        assert names == ""

    def test_invalid_json_returns_error(self):
        node = PSN_Lora_Dataset_Loader()
        lora_list, names = node.run("not valid json", ".safetensors", "name")
        assert lora_list == []
        assert "Error" in names

    def test_manifest_not_array_returns_error(self):
        node = PSN_Lora_Dataset_Loader()
        lora_list, names = node.run('{"name": "x"}', ".safetensors", "name")
        assert lora_list == []
        assert "Error" in names

    def test_entry_missing_name_returns_error(self):
        manifest = _make_manifest([{"path": "/data/x.safetensors", "size": 10}])
        node = PSN_Lora_Dataset_Loader()
        lora_list, names = node.run(manifest, ".safetensors", "name")
        assert lora_list == []
        assert "Error" in names

    def test_invalid_extension_returns_error(self):
        node = PSN_Lora_Dataset_Loader()
        lora_list, names = node.run("[]", ".exe", "name")
        assert lora_list == []
        assert "Error" in names

    def test_invalid_sort_key_returns_error(self):
        node = PSN_Lora_Dataset_Loader()
        lora_list, names = node.run("[]", ".safetensors", "invalid_key")
        assert lora_list == []
        assert "Error" in names

    def test_metadata_preserved(self):
        manifest = _make_manifest([
            {"name": "test.safetensors", "path": "/data/test.safetensors", "size": 50, "date": "", "metadata": {"author": "alice", "version": 2}},
        ])
        node = PSN_Lora_Dataset_Loader()
        lora_list, names = node.run(manifest, ".safetensors", "name")
        assert len(lora_list) == 1
        assert lora_list[0]["metadata"] == {"author": "alice", "version": 2}

    def test_validate_extension_helper(self):
        assert _validate_extension(".safetensors") == ".safetensors"
        assert _validate_extension("safetensors") == ".safetensors"
        assert _validate_extension(".CKPT") == ".ckpt"
        assert _validate_extension(".exe") is None
        assert _validate_extension("") is None
        assert _validate_extension(None) is None

    def test_parse_manifest_bad_size(self):
        manifest = _make_manifest([{"name": "x.safetensors", "path": "/x", "size": -1, "date": ""}])
        entries, err = _parse_manifest(manifest)
        assert entries is None
        assert err is not None

    def test_parse_manifest_bad_metadata(self):
        manifest = _make_manifest([{"name": "x.safetensors", "path": "/x", "size": 1, "date": "", "metadata": "notadict"}])
        entries, err = _parse_manifest(manifest)
        assert entries is None
        assert err is not None

    def test_matches_extension_case_insensitive(self):
        entry = {"name": "MyFile.SAFETENSORS", "path": "/data/MyFile.SAFETENSORS"}
        assert _matches_extension(entry, ".safetensors") is True
        assert _matches_extension(entry, ".ckpt") is False
