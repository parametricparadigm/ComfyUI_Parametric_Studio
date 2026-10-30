import h_provide_a_dedicated_tool_for_exact as m


def test_basic_multiplication():
    v, err = m.exact_eval("1024 * 768")
    assert err is None
    assert v == 786432


def test_float_and_precedence():
    v, err = m.exact_eval("2 + 3 * 4")
    assert err is None
    assert v == 14
    v2, err2 = m.exact_eval("(2 + 3) * 4")
    assert err2 is None
    assert v2 == 20


def test_division_and_floor():
    v, err = m.exact_eval("10 / 4")
    assert err is None
    assert v == 2.5
    v2, err2 = m.exact_eval("10 // 4")
    assert err2 is None
    assert v2 == 2
    v3, err3 = m.exact_eval("10 % 3")
    assert err3 is None
    assert v3 == 1


def test_power_and_unary():
    v, err = m.exact_eval("2 ** 10")
    assert err is None
    assert v == 1024
    v2, err2 = m.exact_eval("-5 + 3")
    assert err2 is None
    assert v2 == -2


def test_constants():
    v, err = m.exact_eval("pi * 2")
    assert err is None
    assert abs(v - 6.283185307179586) < 1e-9


def test_division_by_zero():
    v, err = m.exact_eval("1 / 0")
    assert v is None
    assert "division by zero" in err


def test_bad_input_non_string():
    v, err = m.exact_eval(123)
    assert v is None
    assert err is not None


def test_empty_expression():
    v, err = m.exact_eval("   ")
    assert v is None
    assert err is not None


def test_forbidden_name():
    v, err = m.exact_eval("__import__('os')")
    assert v is None
    assert err is not None


def test_node_run_ok():
    node = m.PSN_ExactArithmetic()
    value, status = node.run("1024 * 768")
    assert status == "ok"
    assert value == 786432.0


def test_node_run_error_fallback():
    node = m.PSN_ExactArithmetic()
    value, status = node.run("1 / 0", fallback=42.0)
    assert status.startswith("error:")
    assert value == 42.0


def test_node_interface():
    assert m.PSN_ExactArithmetic.FUNCTION == "run"
    assert m.PSN_ExactArithmetic.RETURN_TYPES == ("FLOAT", "STRING")
    assert m.PSN_ExactArithmetic.CATEGORY.startswith("ParametricStudio/")
    it = m.PSN_ExactArithmetic.INPUT_TYPES()
    assert "expression" in it["required"]
    assert "PSN_ExactArithmetic" in m.NODE_CLASS_MAPPINGS
    assert "PSN_ExactArithmetic" in m.NODE_DISPLAY_NAME_MAPPINGS


if __name__ == "__main__":
    test_basic_multiplication()
    test_float_and_precedence()
    test_division_and_floor()
    test_power_and_unary()
    test_constants()
    test_division_by_zero()
    test_bad_input_non_string()
    test_empty_expression()
    test_forbidden_name()
    test_node_run_ok()
    test_node_run_error_fallback()
    test_node_interface()
    print("ok")
