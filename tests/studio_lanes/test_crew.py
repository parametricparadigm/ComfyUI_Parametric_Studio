import os
import sys
import tempfile
import shutil
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crew import roster, retrieve, ask, route, NAMES

def setup_kb():
    tmp = tempfile.mkdtemp()
    kb_root = os.path.join(tmp, "kb")
    
    # Family 1: 01-Stable
    fam1 = os.path.join(kb_root, "model_families", "01-Stable")
    os.makedirs(os.path.join(fam1, "dossier"))
    with open(os.path.join(fam1, "dossier", "SKILL.md"), "w") as f:
        f.write("Stable Diffusion skill notes.\n\nGreat for photorealism.")
    with open(os.path.join(fam1, "dossier", "TOOLS.md"), "w") as f:
        f.write("Tools for Stable: ComfyUI, A1111.")
    
    # Family 2: 02-Anime
    fam2 = os.path.join(kb_root, "model_families", "02-Anime")
    os.makedirs(os.path.join(fam2, "dossier"))
    with open(os.path.join(fam2, "dossier", "SKILL.md"), "w") as f:
        f.write("Anime style generation.\n\nBest for cel-shading.")
    with open(os.path.join(fam2, "dossier", "PROMPTING.md"), "w") as f:
        f.write("Use keywords like 'anime', 'cel-shaded'.")
    
    # Family 3: 03-Realistic (no dossier)
    fam3 = os.path.join(kb_root, "model_families", "03-Realistic")
    os.makedirs(fam3)
    
    return tmp, kb_root

def main():
    tmp, kb_root = setup_kb()
    
    try:
        # Test roster
        members = roster(kb_root)
        
        # Should have 3 families + 3 secondary + 3 tertiary + 1 master = 10
        assert len(members) == 10, f"Expected 10 members, got {len(members)}"
        
        # Check names are unique
        names = [m["name"] for m in members]
        assert len(names) == len(set(names)), "Names are not unique"
        
        # Check determinism
        members2 = roster(kb_root)
        assert members == members2, "Roster is not deterministic"
        
        # Check master files
        master = [m for m in members if m["id"] == "master"][0]
        # Family 1 has 2 files, Family 2 has 2 files, Family 3 has 0
        assert len(master["files"]) == 4, f"Master should have 4 files, got {len(master['files'])}"
        
        # Test retrieve
        stable_member = [m for m in members if m["id"] == "stable"][0]
        chunks = retrieve(stable_member["files"], "photorealism", k=2)
        assert len(chunks) > 0, "Should find chunks"
        assert chunks[0]["file"].endswith("SKILL.md"), "SKILL.md should be top result"
        
        # Test ask with supported quote
        def fake_chat_supported(messages):
            return json.dumps({
                "answer": "Stable Diffusion is great for photorealism.",
                "quotes": [{"file": stable_member["files"][0], "quote": "Great for photorealism."}]
            })
        
        result = ask(stable_member, "photorealism", fake_chat_supported)
        assert result["supported"] == True, f"Expected supported=True, got {result['supported']}"
        assert len(result["quotes"]) == 1, f"Expected 1 quote, got {len(result['quotes'])}"
        
        # Test ask with fabricated quote
        def fake_chat_fabricated(messages):
            return json.dumps({
                "answer": "Something else.",
                "quotes": [{"file": stable_member["files"][0], "quote": "This quote does not exist in the file."}]
            })
        
        result2 = ask(stable_member, "photorealism", fake_chat_fabricated)
        assert result2["supported"] == False, f"Expected supported=False, got {result2['supported']}"
        assert result2["answer"] == "I can't back that up from my notes.", f"Wrong answer: {result2['answer']}"
        
        # Test ask with invalid JSON
        def fake_chat_invalid(messages):
            return "This is not JSON at all"
        
        result3 = ask(stable_member, "photorealism", fake_chat_invalid)
        assert result3["supported"] == False, f"Expected supported=False, got {result3['supported']}"
        assert len(result3["problems"]) > 0, "Should have problems"
        
        # Test route
        assert route("How do I use Stable Diffusion?", members) == "stable"
        assert route("Tell me about anime styles", members) == "anime"
        assert route("What is a lora?", members) == "master"
        
        print("ok")
    finally:
        shutil.rmtree(tmp)

if __name__ == "__main__":
    main()
