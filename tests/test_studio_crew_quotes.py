from studio import crew

CH = [{"file": "/box/notes/01-Fam/dossier/PLAYBOOK.md", "text": "SAM 3D Objects uses torch 2.14.1+cu132 on this stack. It needs about 12 GB of VRAM.\nRun it with the mesh template."}]
def reply(*quotes): return lambda m: '{"answer": "It uses torch 2.14.", "quotes": [' + ",".join('{"file": "x", "quote": "%s"}' % q for q in quotes) + "]}"
def run(chat, monkeypatch):
    monkeypatch.setattr(crew, "retrieve", lambda *a, **k: CH); return crew.ask({"id": "m", "name": "M", "family": "F", "files": ["x"]}, "which torch?", chat)

def test_quote_with_citation_marks_counts_and_hides_paths(monkeypatch):
    r = run(reply("SAM 3D Objects uses torch 2.14.1+cu132 [3D_INSTALLS_2026-10-11.md]."), monkeypatch)
    assert r["supported"] and r["answer"].startswith("It uses") and r["quotes"][0]["file"] == "dossier/PLAYBOOK.md" and "/box" not in str(r)

def test_close_paraphrase_shows_the_notes_own_words(monkeypatch):
    r = run(reply("SAM 3D Objects uses torch 2.14.1+cu132 on the stack."), monkeypatch)
    assert r["supported"] and r["quotes"][0]["quote"] == "SAM 3D Objects uses torch 2.14.1+cu132 on this stack."

def test_one_bad_quote_does_not_sink_a_good_one(monkeypatch):
    r = run(reply("It needs about 12 GB of VRAM.", "Completely invented claim about something else entirely."), monkeypatch)
    assert r["supported"] and len(r["quotes"]) == 1

def test_invented_quote_is_still_refused(monkeypatch):
    r = run(reply("This model requires 400 GB of VRAM and a quantum computer."), monkeypatch)
    assert not r["supported"] and r["quotes"] == [] and "can't back" in r["answer"] and "/box" not in str(r)
