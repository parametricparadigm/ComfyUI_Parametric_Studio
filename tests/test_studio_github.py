import json, io, pytest
from studio import github_link as G

class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()

def opener_for(routes, log=None):
    def op(req, timeout=0):
        if log is not None: log.append((req.get_method(), req.full_url, dict(req.header_items())))
        for k, v in routes.items():
            if k in req.full_url:
                if isinstance(v, Exception): raise v
                return Resp(json.dumps(v).encode() if not isinstance(v, bytes) else v)
        raise AssertionError("unexpected " + req.full_url)
    return op

def test_search_drops_flagged_and_shapes_results():
    d = {"items": [{"full_name": "a/good", "stargazers_count": 9, "license": {"spdx_id": "MIT"}, "pushed_at": "2026-10-01T00:00:00Z", "description": "nice workflows", "html_url": "u"}, {"full_name": "b/nsfw-pack", "stargazers_count": 99, "description": "x", "html_url": "u2"}]}
    r = G.search("flux", opener=opener_for({"search/repositories": d})); assert [x["repo"] for x in r] == ["a/good"] and r[0]["license"] == "MIT"

def test_list_and_import_with_sfw_scan(tmp_path):
    files = [{"type": "file", "name": "a.json", "path": "wf/a.json", "size": 10}, {"type": "file", "name": "b.txt", "path": "wf/b.txt", "size": 5}, {"type": "dir", "name": "d", "path": "wf/d"}]
    assert G.list_json("o/r", "wf", opener=opener_for({"/contents/": files})) == [{"path": "wf/a.json", "size": 10}]
    with pytest.raises(G.GitHubError): G.list_json("bad repo", "")
    with pytest.raises(G.GitHubError): G.import_file("o/r", "wf/a.json", tmp_path)                       # needs confirm
    with pytest.raises(G.GitHubError): G.import_file("o/r", "../x.json", tmp_path, confirm=True)
    ok = G.import_file("o/r", "wf/a.json", tmp_path, confirm=True, opener=opener_for({"raw.githubusercontent": b'{"nodes": []}'})); assert json.load(open(ok)) == {"nodes": []}
    with pytest.raises(G.GitHubError, match="safe-for-work"): G.import_file("o/r", "wf/b.json", tmp_path, confirm=True, opener=opener_for({"raw.githubusercontent": b'{"text": "explicit nude art"}'}))
    with pytest.raises(G.GitHubError, match="not valid JSON"): G.import_file("o/r", "wf/c.json", tmp_path, confirm=True, opener=opener_for({"raw.githubusercontent": b"nope"}))

def test_publish_needs_confirm_token_and_safe_paths():
    log = []; op = opener_for({"/contents/": {"sha": "abc"}}, log)
    with pytest.raises(G.GitHubError, match="confirm"): G.publish("o/r", {"a.json": "{}"}, "m", token="t", opener=op)
    with pytest.raises(G.GitHubError, match="GITHUB_TOKEN"): G.publish("o/r", {"a.json": "{}"}, "m", confirm=True, token="", opener=op)
    for bad in (".github/workflows/x.yml", "../x", "/abs.json"):
        with pytest.raises(G.GitHubError, match="refusing"): G.publish("o/r", {bad: "{}"}, "m", confirm=True, token="t", opener=op)
    assert G.publish("o/r", {"apps/a.json": "{}"}, "hello", confirm=True, token="t", opener=op) == ["apps/a.json"]
    put = [x for x in log if x[0] == "PUT"][0]; assert put[2].get("Authorization") == "Bearer t"                     # token travels in the header only
