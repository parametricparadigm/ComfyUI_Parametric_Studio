import torch

from h_implement_a_non_destructive_post_p import (
    PSN_NonDestructiveMasterHook,
    PSN_MasterSongCopy,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _audio(scale=0.05):
    return torch.randn(2, 16) * scale


def test_module_mappings():
    assert "PSN_NonDestructiveMasterHook" in NODE_CLASS_MAPPINGS
    assert "PSN_MasterSongCopy" in NODE_CLASS_MAPPINGS
    assert set(NODE_CLASS_MAPPINGS) == set(NODE_DISPLAY_NAME_MAPPINGS)
    for cls in NODE_CLASS_MAPPINGS.values():
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        assert "required" in cls.INPUT_TYPES()


def test_hook_appends_without_mutating():
    a = {"name": "song", "audio": _audio(), "meta": {"k": 1}}
    original_list = [a]
    snapshot_audio = a["audio"].clone()
    snapshot_meta = dict(a["meta"])
    out_list, new_art = PSN_NonDestructiveMasterHook().run(original_list, -14, "_mastered")
    # original list object untouched, still length 1
    assert original_list is not out_list
    assert len(original_list) == 1
    assert len(out_list) == 2
    # original artifact audio and meta unchanged
    assert torch.equal(original_list[0]["audio"], snapshot_audio)
    assert original_list[0]["meta"] == snapshot_meta
    # new artifact appended with new name and meta
    assert out_list[-1]["name"] == "song_mastered"
    assert out_list[-1]["meta"]["source"] == "song"
    assert out_list[-1]["meta"]["mastered"] is True
    assert new_art is out_list[-1]


def test_normalization_changes_gain_and_clips():
    # quiet input should be amplified toward target
    quiet = torch.full((1, 8), 0.01)
    _, art = PSN_NonDestructiveMasterHook().run([{"name": "q", "audio": quiet}], -14, "_m")
    assert art["audio"].abs().max().item() > 0.01
    # loud input should be limited (ceiling) and clipped to <= 1
    loud = torch.full((1, 8), 0.9)
    _, art2 = PSN_NonDestructiveMasterHook().run([{"name": "l", "audio": loud}], -14, "_m")
    assert art2["audio"].abs().max().item() <= 1.0 + 1e-6
    # input tensors not modified
    assert torch.equal(quiet, torch.full((1, 8), 0.01))
    assert torch.equal(loud, torch.full((1, 8), 0.9))


def test_silent_input_is_safe():
    silent = torch.zeros(1, 8)
    _, art = PSN_NonDestructiveMasterHook().run([{"name": "s", "audio": silent}], -14, "_m")
    assert art["audio"].abs().max().item() == 0.0


def test_bad_inputs_raise():
    # non-list artifacts
    try:
        PSN_NonDestructiveMasterHook().run("nope", -14, "_m")
        assert False, "expected TypeError"
    except TypeError:
        pass
    # empty list
    try:
        PSN_NonDestructiveMasterHook().run([], -14, "_m")
        assert False, "expected ValueError"
    except ValueError:
        pass
    # artifact without audio
    try:
        PSN_NonDestructiveMasterHook().run([{"name": "x"}], -14, "_m")
        assert False, "expected ValueError"
    except ValueError:
        pass
    # bad audio type
    try:
        PSN_NonDestructiveMasterHook().run([{"name": "x", "audio": 42}], -14, "_m")
        assert False, "expected TypeError"
    except TypeError:
        pass


def test_master_song_copy_node():
    x = _audio(0.03)
    before = x.clone()
    (art,) = PSN_MasterSongCopy().run(x, "track", -16)
    assert art["name"] == "track_mastered"
    assert art["meta"]["source"] == "track"
    assert art["meta"]["target_lufs"] == -16
    assert art["audio"].shape == x.shape
    assert torch.equal(x, before)  # input untouched
    assert art["audio"].abs().max().item() > 0.03  # gain applied


def test_multichannel_audio():
    x = torch.randn(2, 16, 3) * 0.05
    (art,) = PSN_MasterSongCopy().run(x, "mc", -14)
    assert art["audio"].shape == (2, 16, 3)
    assert art["audio"].abs().max().item() <= 1.0 + 1e-6


if __name__ == "__main__":
    test_module_mappings()
    test_hook_appends_without_mutating()
    test_normalization_changes_gain_and_clips()
    test_silent_input_is_safe()
    test_bad_inputs_raise()
    test_master_song_copy_node()
    test_multichannel_audio()
    print("ok")
