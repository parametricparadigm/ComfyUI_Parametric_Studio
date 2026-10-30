#!/usr/bin/env python3
"""Adds one new ComfyUniversity class with your local language model. A class only lands if its lab runs twice with identical output in under 60 s on the CPU and its quiz parses. New classes carry status "draft", shown as a banner, until a person audits them against sources. Topics come from studio/university/topics_next.txt.
Usage: weekly_class.py [--dry-run]. Weekly on Linux or macOS: 0 6 * * 1  cd /path/to/repo && python scripts/weekly_class.py"""
import argparse, json, os, re, shutil, subprocess, sys, urllib.request
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); UNI = os.path.join(ROOT, "studio", "university"); sys.path.insert(0, ROOT)
from studio import llm_tiers
PROMPT = """Write one ComfyUniversity class for people learning generative AI and ComfyUI. Topic: {title}. Level: {level} of 100-400.
Be accurate and specific. Do not invent numbers, papers or dates; if unsure, say what is uncertain. Teach with a small worked example. No brand or real person references.
Reply with exactly these three fenced blocks and nothing else:
```markdown
the lesson: objective first, then the explanation, the maths where it helps, then a short summary
```
```python
a lab using only the standard library and numpy or torch on the CPU, fixed seeds, finishing in under 30 seconds, printing real numbers that demonstrate the lesson
```
```json
{{"questions": [{{"q": "...", "options": ["...", "...", "...", "..."], "answer": "the exact text of the right option", "why": "..."}}]}}
```
Write 4 questions whose answers follow from the lesson."""
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args(); tf = os.path.join(UNI, "topics_next.txt"); topics = [l.strip() for l in open(tf) if l.strip()]
    if not topics: print("no topics left in topics_next.txt"); return 0
    level, title = topics[0].split("|", 1); ep = llm_tiers.endpoint()
    if not ep: print("no local language model is running"); return 1
    body = {"model": ep["model"], "messages": [{"role": "user", "content": PROMPT.format(title=title, level=level)}], "temperature": 0.3, "max_tokens": 6000, "chat_template_kwargs": {"enable_thinking": False}}
    with urllib.request.urlopen(urllib.request.Request(ep["url"] + "/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=900) as r: text = json.load(r)["choices"][0]["message"]["content"]
    blocks = dict(re.findall(r"```(markdown|python|json)\n(.*?)```", text, re.S))
    if len(blocks) != 3: print("the model did not return all three parts"); return 1
    quiz = json.loads(blocks["json"]); nums = [int(m) for d in os.listdir(os.path.join(UNI, level)) for m in re.findall(r"^CU-(\d+)", d)]; code = f"CU-{max(nums, default=int(level)) + 1}"; slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:44]; d = os.path.join(UNI, level, f"{code}-{slug}"); os.makedirs(d)
    json.dump({"title": title, "level": level, "char": "tune", "hook": blocks["markdown"].strip().split("\n")[0].lstrip("# ")[:160], "code": code, "prereq": [], "status": "draft", "code_refs": []}, open(d + "/course.json", "w"), indent=1); open(d + "/lesson.md", "w").write(blocks["markdown"]); open(d + "/lab.py", "w").write(blocks["python"]); json.dump({"code": code, "title": title, "level": level, **quiz}, open(d + "/quiz.json", "w"), indent=1)
    ok = subprocess.run([sys.executable, os.path.join(UNI, "build.py"), "--labs", "--only", code], capture_output=True, text=True, timeout=300).returncode == 0
    if not ok or a.dry_run:
        shutil.rmtree(d); subprocess.run([sys.executable, os.path.join(UNI, "build.py")], capture_output=True); print(f"{code} {title}: " + ("dry run, lab passed" if ok else "lab failed, not added")); return 0 if ok else 1
    open(tf, "w").write("\n".join(topics[1:]) + "\n"); subprocess.run([sys.executable, os.path.join(UNI, "build.py")], capture_output=True); print(f"added {code} {title} as a draft"); return 0
sys.exit(main())
