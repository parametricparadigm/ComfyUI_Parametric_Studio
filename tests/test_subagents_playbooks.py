import os
from psn.subagents.playbooks import playbook_for, MAP, DIR

def test_every_mapped_playbook_exists_and_is_capped():
    for names in MAP.values():
        for n in names: assert os.path.exists(os.path.join(DIR, n + ".md")), n
    assert os.path.exists(os.path.join(DIR, "LICENSE-awesome-claude-agents.txt"))
    t = playbook_for("builder"); assert t.startswith("\n\nWORKING GUIDANCE") and len(t) < 6000 and "---\nname:" not in t

def test_unmapped_role_and_switch_off(monkeypatch):
    assert playbook_for("captioner") == ""
    monkeypatch.setenv("PSN_PLAYBOOKS", "0"); assert playbook_for("builder") == ""
