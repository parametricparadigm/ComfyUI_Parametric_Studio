import os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAID = ["api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com", "api.x.ai", "api.deepseek.com", "api.groq.com", "openrouter.ai", "api.mistral.ai", "api.cohere", "api.klingai.com", "klingai.com", "api.runwayml.com", "runwayml.com",
        "higgsfield", "api.lumalabs.ai", "api.bfl.ai", "fal.run", "api.replicate.com", "api.stability.ai", "api.ideogram.ai", "api.recraft.ai", "api.heygen.com", "api.elevenlabs.io", "api.together.xyz", "api.fireworks.ai", "bedrock", "azure.com/openai"]
PAID_IMPORTS = re.compile(r"^\s*(?:import|from)\s+(openai|anthropic|google\.generativeai|replicate|fal_client|elevenlabs|runwayml|cohere|groq)\b", re.M)
def test_no_paid_api_hosts_or_sdks_in_source():
    hits = []
    for base in ("psn", "psn_nodes"):
        for dp, _, fs in os.walk(os.path.join(ROOT, base)):
            for f in fs:
                if not f.endswith(".py"): continue
                t = open(os.path.join(dp, f), errors="replace").read(); p = os.path.relpath(os.path.join(dp, f), ROOT)
                hits += [f"{p}: host {h}" for h in PAID if h in t.lower()]; hits += [f"{p}: import {m.group(1)}" for m in PAID_IMPORTS.finditer(t)]
    assert not hits, hits
