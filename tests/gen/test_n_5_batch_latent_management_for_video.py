"""Tests for psn_nodes.gen.n_5_batch_latent_management_for_video."""

import pytest

from psn_nodes.gen.n_5_batch_latent_management_for_video import (
    PSN_Latent_Batch_Repeat,
    PSN_Latent_Batch_Split,
    PSN_Latent_Batch_Merge,
    _validate_latent,
)


def _latent(shape, frames=None):
    d = {"shape": list(shape)}
    if frames is not None:
        d["frames"] = frames
    return d


class TestRepeat:
    def test_repeat_basic(self):
        node = PSN_Latent_Batch_Repeat()
        latent = _latent((2, 16, 32, 32))
        (out,) = node.run(latent, 3)
        assert out["shape"] == [6, 16, 32, 32]

    def test_repeat_one_is_identity(self):
        node = PSN_Latent_Batch_Repeat()
        latent = _latent((4, 8, 8))
        (out,) = node.run(latent, 1)
        assert out["shape"] == [4, 8, 8]

    def test_repeat_preserves_frames(self):
        node = PSN_Latent_Batch_Repeat()
        latent = _latent((2, 16, 32, 32), frames=10)
        (out,) = node.run(latent, 2)
        assert out["frames"] == 10
        assert out["shape"] == [4, 16, 32, 32]

    def test_repeat_zero_raises(self):
        node = PSN_Latent_Batch_Repeat()
        latent = _latent((2, 16, 32, 32))
        with pytest.raises(ValueError, match="repeat_count must be >= 1"):
            node.run(latent, 0)

    def test_repeat_non_int_raises(self):
        node = PSN_Latent_Batch_Repeat()
        latent = _latent((2, 16, 32, 32))
        with pytest.raises(ValueError, match="repeat_count must be an int"):
            node.run(latent, 2.5)

    def test_repeat_bad_latent_raises(self):
        node = PSN_Latent_Batch_Repeat()
        with pytest.raises(ValueError, match="must be a dict"):
            node.run("not a dict", 2)


class TestSplit:
    def test_split_basic(self):
        node = PSN_Latent_Batch_Split()
        latent = _latent((5, 16, 32, 32))
        first, second = node.run(latent, 2)
        assert first["shape"] == [2, 16, 32, 32]
        assert second["shape"] == [3, 16, 32, 32]

    def test_split_at_zero(self):
        node = PSN_Latent_Batch_Split()
        latent = _latent((4, 8, 8))
        first, second = node.run(latent, 0)
        assert first["shape"] == [0, 8, 8]
        assert second["shape"] == [4, 8, 8]

    def test_split_at_full_batch(self):
        node = PSN_Latent_Batch_Split()
        latent = _latent((4, 8, 8))
        first, second = node.run(latent, 4)
        assert first["shape"] == [4, 8, 8]
        assert second["shape"] == [0, 8, 8]

    def test_split_out_of_range_raises(self):
        node = PSN_Latent_Batch_Split()
        latent = _latent((3, 8, 8))
        with pytest.raises(ValueError, match="out of range"):
            node.run(latent, 5)

    def test_split_negative_raises(self):
        node = PSN_Latent_Batch_Split()
        latent = _latent((3, 8, 8))
        with pytest.raises(ValueError, match="out of range"):
            node.run(latent, -1)

    def test_split_preserves_frames(self):
        node = PSN_Latent_Batch_Split()
        latent = _latent((4, 16, 32, 32), frames=20)
        first, second = node.run(latent, 2)
        assert first["frames"] == 20
        assert second["frames"] == 20


class TestMerge:
    def test_merge_basic(self):
        node = PSN_Latent_Batch_Merge()
        a = _latent((2, 16, 32, 32))
        b = _latent((3, 16, 32, 32))
        (out,) = node.run(a, b)
        assert out["shape"] == [5, 16, 32, 32]

    def test_merge_mismatched_dims_raises(self):
        node = PSN_Latent_Batch_Merge()
        a = _latent((2, 16, 32, 32))
        b = _latent((3, 16, 64, 64))
        with pytest.raises(ValueError, match="Non-batch dimensions must match"):
            node.run(a, b)

    def test_merge_zero_batch(self):
        node = PSN_Latent_Batch_Merge()
        a = _latent((0, 16, 32, 32))
        b = _latent((4, 16, 32, 32))
        (out,) = node.run(a, b)
        assert out["shape"] == [4, 16, 32, 32]

    def test_merge_preserves_frames_from_a(self):
        node = PSN_Latent_Batch_Merge()
        a = _latent((2, 16, 32, 32), frames=10)
        b = _latent((3, 16, 32, 32), frames=20)
        (out,) = node.run(a, b)
        assert out["frames"] == 10

    def test_merge_frames_falls_back_to_b(self):
        node = PSN_Latent_Batch_Merge()
        a = _latent((2, 16, 32, 32))
        b = _latent((3, 16, 32, 32), frames=20)
        (out,) = node.run(a, b)
        assert out["frames"] == 20


class TestSmoke:
    def test_merge_then_split_roundtrip(self):
        """Merge two 1-frame latents, split back, verify original shapes."""
        merge_node = PSN_Latent_Batch_Merge()
        split_node = PSN_Latent_Batch_Split()
        a = _latent((1, 16, 32, 32), frames=1)
        b = _latent((1, 16, 32, 32), frames=1)
        (merged,) = merge_node.run(a, b)
        assert merged["shape"] == [2, 16, 32, 32]
        first, second = split_node.run(merged, 1)
        assert first["shape"] == [1, 16, 32, 32]
        assert second["shape"] == [1, 16, 32, 32]
        assert first["frames"] == 1
        assert second["frames"] == 1

    def test_repeat_then_split_roundtrip(self):
        """Repeat a latent 3x, then split back into 3 equal parts."""
        repeat_node = PSN_Latent_Batch_Repeat()
        split_node = PSN_Latent_Batch_Split()
        original = _latent((2, 16, 32, 32))
        (repeated,) = repeat_node.run(original, 3)
        assert repeated["shape"] == [6, 16, 32, 32]
        first, rest = split_node.run(repeated, 2)
        assert first["shape"] == [2, 16, 32, 32]
        second, third = split_node.run(rest, 2)
        assert second["shape"] == [2, 16, 32, 32]
        assert third["shape"] == [2, 16, 32, 32]


class TestValidation:
    def test_validate_latent_missing_shape(self):
        _, err = _validate_latent({"frames": 10})
        assert err is not None
        assert "shape" in err

    def test_validate_latent_non_int_dim(self):
        _, err = _validate_latent({"shape": [2, "16", 32]})
        assert err is not None
        assert "int" in err

    def test_validate_latent_negative_dim(self):
        _, err = _validate_latent({"shape": [2, -1, 32]})
        assert err is not None
        assert ">= 0" in err

    def test_validate_latent_empty_shape(self):
        _, err = _validate_latent({"shape": []})
        assert err is not None
        assert "empty" in err

    def test_validate_latent_bool_dim_rejected(self):
        _, err = _validate_latent({"shape": [True, 16, 32]})
        assert err is not None
        assert "int" in err
