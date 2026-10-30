import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from psn.expr import evaluate, ExprError

@pytest.mark.parametrize("src,vars,want", [
    ("1+2*3", {}, 7), ("(a+b)/2", {"a": 4, "b": 8}, 6.0), ("a if a>b else b", {"a": 3, "b": 9}, 9), ("sqrt(16)+floor(2.7)", {}, 6.0),
    ("clamp(a,0,1)", {"a": 5}, 1), ("lerp(10,20,0.25)", {}, 12.5), ("lower('AbC')+upper('x')", {}, "abcX"), ("len(split('a,b,c', ','))", {}, 3),
    ("at([1,2,3], 9, -1)", {}, -1), ("[1,2,3][1:]", {}, [2, 3]), ("'x'*3", {}, "xxx"), ("a and b", {"a": 0, "b": 5}, 0), ("1 < a <= 3", {"a": 3}, True),
    ("sum(seq(5))", {}, 10), ("join('-', ['a','b'])", {}, "a-b"), ("{'k': a}['k']", {"a": 7}, 7), ("pi > 3 and e < 3", {}, True), ("replace('aXb','X','-')", {}, "a-b"),
    ("round(2.567, ndigits=1)", {}, 2.6), ("not False", {}, True), ("-a", {"a": 2}, -2), ("2**10", {}, 1024), ("7//2 + 7%2", {}, 4),
])
def test_valid(src, vars, want): assert evaluate(src, vars) == want

BAD = ["__import__('os').system('id')", "().__class__", "a.__class__", "open('/etc/passwd')", "eval('1')", "exec('1')", "[x for x in range(3)]", "(lambda: 1)()", "{x: 1 for x in 'ab'}", "a.real",
       "'{0.__class__}'.format(1)", "f'{1}'", "getattr(a,'x')", "globals()", "x", "1 if", "1+", "a[0]", "2**100000", "10**10**10", "'a'*10**9", "[0]*10**9", "seq(10**9)", "1/0", "(1,)*10**7", "not_a_func(1)", "a is b",
       "[1,2][::0]", "abs(*[1])", "dict(a=1)", "type(1)", "'x'.join(['a'])", "sorted(seq(5), key=len)", "print(1)", "await x", "(yield)", "1;2", "x:=1", "b'abc'", "...", "1j"]
@pytest.mark.parametrize("src", BAD)
def test_blocked(src):
    with pytest.raises(ExprError): evaluate(src, {"a": 1, "b": 2})

def test_limits():
    with pytest.raises(ExprError): evaluate("1+" * 300 + "1")           # node count
    with pytest.raises(ExprError): evaluate("-" * 50 + "1")   # depth
    with pytest.raises(ExprError): evaluate("1" * 3000)                  # length
    with pytest.raises(ExprError): evaluate("a", {"a": object()})        # variable type
    assert evaluate("a", {"a": [1, 2]}) == [1, 2]

def test_source_never_calls_eval_exec_compile():
    import ast
    tree = ast.parse(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "psn", "expr.py")).read())
    bad = [n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("eval", "exec", "compile", "__import__", "open")]
    assert not bad
