"""ComfyUniversity: served from the repo with no env var, finished lessons only on the catalogue, audited lessons pass every content check, their labs reproduce their stored output."""
import concurrent.futures as cf, importlib, json, os, re, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.university import build as B
from psn import paths
SRC = Path(paths.setting("COMFYUI_SRC", default=paths.home("ComfyUI")))

def audited(): return [c for c in B.courses() if c.get("status") != "draft" and B.complete(c)]

def test_default_path_is_in_the_repo_and_env_var_is_optional(monkeypatch):
    monkeypatch.delenv("STUDIO_UNIVERSITY", raising=False); import studio.server as s; s = importlib.reload(s)
    assert s.UNI == Path(s.__file__).resolve().parent / "university" and (s.UNI / "catalogue.json").exists()
    monkeypatch.setenv("STUDIO_UNIVERSITY", ""); s = importlib.reload(s); assert s.UNI.name == "university" and (s.UNI / "catalogue.json").exists()

def test_api_serves_courses_from_a_clean_tree(monkeypatch):
    monkeypatch.delenv("STUDIO_UNIVERSITY", raising=False); import studio.server as s; s = importlib.reload(s)
    from fastapi.testclient import TestClient
    c = TestClient(s.app); cat = c.get("/api/university").json(); assert len(cat["courses"]) >= 40 and set(cat["levels"]) == {"100", "200", "300", "400"}
    for row in cat["courses"]:
        d = c.get("/api/university/" + row["code"]).json(); assert d["lesson"].startswith("# " + row["code"]) and d["lab"] and d["lab_output"] and d["quiz"], row["code"]
    assert c.get("/api/university/CU-999").status_code == 404 and c.get("/api/university/nope").status_code == 400

def test_catalogue_is_current_and_lists_only_finished_lessons():
    cat = json.loads((B.HERE / "catalogue.json").read_text()); codes = [c["code"] for c in cat["courses"]]; assert len(codes) == len(set(codes))
    for row in cat["courses"]:
        d = B.HERE / row["path"]; assert all((d / n).exists() for n in ("lesson.md", "lab.py", "lab_output.txt", "quiz.json")), row["code"]; assert re.fullmatch(r"CU-\d{3}", row["code"]) and row["level"] in cat["levels"] and row["char"] in cat["characters"]
    finished = {c["code"] for c in B.courses() if B.complete(c)}; assert finished == set(codes)

def test_every_audited_lesson_passes_the_content_checks():
    rows = B.courses(); codes = {c["code"] for c in rows}; src = {k.rstrip("/"): v for k, v in B.SOURCES().items()}; bad = {c["code"]: p for c in audited() for p in [B.check_course(c, codes, src)] if p}; assert not bad, bad; assert len(audited()) >= 8

def test_quiz_answers_mark_exactly_one_option_for_every_lesson():
    for c in audited():
        for q in json.loads((c["dir"] / "quiz.json").read_text())["questions"]:
            if q.get("options"): assert sum(B.quiz_right(q, o, i) for i, o in enumerate(q["options"])) == 1, (c["code"], q["q"])

def test_arxiv_sources_match_the_title_arxiv_gives():
    src = B.SOURCES()
    for c in audited():
        md = (c["dir"] / "lesson.md").read_text()
        for text, url in B.lesson_links(md[md.find("## Sources"):]):
            e = src[url.rstrip("/")]; assert e.get("checked"), url
            if "arxiv.org" in url: assert e["title"].lower() in text.lower(), (c["code"], url, e["title"])

@pytest.mark.skipif(not (SRC / "execution.py").exists(), reason="no ComfyUI checkout here to compare with")
def test_named_comfyui_symbols_exist_in_the_source():
    for c in audited():
        for r in c.get("code_refs", []):
            f, _, sym = r.partition(":"); assert (SRC / f).exists() and sym in (SRC / f).read_text(errors="replace"), (c["code"], r)

def test_audited_labs_run_on_cpu_under_a_minute_and_reproduce():
    import torch
    rows = audited(); same = torch.__version__ == json.loads((B.HERE / "meta.json").read_text()).get("lab_torch")
    with cf.ThreadPoolExecutor(6) as ex: res = list(ex.map(lambda c: (c, B.run_lab(c["dir"] / "lab.py")), rows))
    for c, (ok, out, sec, err) in res:
        assert ok, (c["code"], err); assert sec < B.LIMIT, c["code"]
        if same: assert out == (c["dir"] / "lab_output.txt").read_text(), c["code"] + " output changed"

def test_university_stays_small_and_text_only():
    files = [p for p in B.HERE.rglob("*") if p.is_file() and "__pycache__" not in p.parts]; assert sum(p.stat().st_size for p in files) < 8 << 20; assert {p.suffix for p in files} <= {".md", ".py", ".txt", ".json"}
