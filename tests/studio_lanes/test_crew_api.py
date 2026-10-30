import sys
import types
from unittest.mock import MagicMock

# Import the router after ensuring the module exists
import crew_api

# Monkeypatch crew functions
fake_roster = [
    {"id": "m1", "name": "Alice", "tier": "senior", "family": "tech", "has_dossier": True},
    {"id": "m2", "name": "Bob", "tier": "junior", "family": "design", "has_dossier": False},
]

def fake_roster_func(kb_root):
    return fake_roster

def fake_ask(member, question, chat, k=4):
    return {"answer": f"Answer from {member['name']} to: {question}"}

def fake_route(question, members):
    return members[0]

crew_api.crew.roster = fake_roster_func
crew_api.crew.ask = fake_ask
crew_api.crew.route = fake_route
crew_api.crew.default_chat = "default"

from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
app.include_router(crew_api.router)
client = TestClient(app)

# Test GET /api/crew
resp = client.get("/api/crew")
assert resp.status_code == 200
data = resp.json()
assert "members" in data
assert len(data["members"]) == 2
assert data["members"][0]["id"] == "m1"

# Test POST /api/crew/ask with specific member
resp = client.post("/api/crew/ask", json={"who": "m1", "question": "Hello there"})
assert resp.status_code == 200
data = resp.json()
assert "result" in data
assert "member" in data
assert data["member"]["id"] == "m1"
assert data["member"]["name"] == "Alice"
assert data["result"]["answer"] == "Answer from Alice to: Hello there"

# Test POST /api/crew/ask with auto routing
resp = client.post("/api/crew/ask", json={"who": "auto", "question": "Auto question"})
assert resp.status_code == 200
data = resp.json()
assert data["member"]["id"] == "m1"

# Test validation: question too short
resp = client.post("/api/crew/ask", json={"who": "m1", "question": "Hi"})
assert resp.status_code == 400

# Test validation: question too long
resp = client.post("/api/crew/ask", json={"who": "m1", "question": "x" * 601})
assert resp.status_code == 400

# Test unknown member
resp = client.post("/api/crew/ask", json={"who": "unknown", "question": "Hello there"})
assert resp.status_code == 404

print("ok")
