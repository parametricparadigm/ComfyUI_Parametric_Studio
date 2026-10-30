import pytest, sys, os, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from psn import sandbox

def test_result_variable_and_run_function():
    assert sandbox.run("result = sum(inputs['x'])", {"x": [1, 2, 3]})["result"] == 6
    r = sandbox.run("import math\ndef run(inputs):\n    return {'r': math.sqrt(inputs['v'])}", {"v": 16}); assert r["ok"] and r["result"] == {"r": 4.0}

def test_stdout_captured_not_leaked():
    r = sandbox.run("print('hi')\nresult = 1"); assert r["ok"] and "hi" in r["stdout"]

@pytest.mark.parametrize("code", [
    "import os", "import subprocess", "import socket", "import sys", "from os import path", "import numpy", "import json.tool", "__import__('os')", "open('/etc/passwd')", "eval('1')", "exec('x=1')", "compile('1','a','eval')",
    "().__class__", "x = [].__class__.__base__", "getattr(1,'real')", "type(1)", "'{0.__class__}'.format(1)", "globals()", "vars()", "result = __builtins__", "import string\nstring.Formatter()", "import re\nre.os",
    "def f():\n    yield 1\nresult = f().gi_frame", "result = (lambda: 1).__globals__", "class A(object): pass", "from math import _foo", "global x", "import math\nmath.__loader__", "breakpoint()", "input()", "while True:\n    pass",
])
def test_blocked_or_contained(code):
    r = sandbox.run(code, timeout=2); assert not r["ok"]

def test_timeout_kills_process():
    t = time.time(); r = sandbox.run("while True:\n    pass", timeout=1.5); assert r["timed_out"] and time.time() - t < 6
    out = subprocess.run(["pgrep", "-f", r" -I -S \S*sandbox_runner\.py$"], capture_output=True, text=True).stdout.strip(); assert out == ""

def test_memory_limit():
    r = sandbox.run("x = [0] * (10**9)\nresult = len(x)", mem_mb=256, timeout=5); assert not r["ok"]

def test_big_result_and_output_limits():
    assert not sandbox.run("result = 'x' * 2_000_000")["ok"]
    r = sandbox.run("for i in range(100000):\n    print('line', i)\nresult = 1"); assert r["ok"] and len(r["stdout"]) <= 10000

def test_recursion_and_errors_are_reported():
    assert not sandbox.run("def f(n):\n    return f(n+1)\nresult = f(0)")["ok"]
    r = sandbox.run("result = 1/0"); assert not r["ok"] and "ZeroDivisionError" in r["error"]
    r = sandbox.run("x = 1"); assert not r["ok"] and "result" in r["error"]
    assert not sandbox.run("def (:")["ok"]

def test_non_json_result_rejected():
    assert not sandbox.run("result = {1, 2}")["ok"]

def test_allow_list_can_be_narrowed():
    assert sandbox.run("import math\nresult = 1", allow=["math"])["ok"]
    assert not sandbox.run("import json\nresult = 1", allow=["math"])["ok"]
    assert not sandbox.run("import socket\nresult = 1", allow=["socket"])["ok"]       # allow can only narrow the default list

def test_no_file_writes_outside_tmp():
    assert not sandbox.run("open('/tmp/psn_probe', 'w')")["ok"]
    assert not os.path.exists("/tmp/psn_probe")

