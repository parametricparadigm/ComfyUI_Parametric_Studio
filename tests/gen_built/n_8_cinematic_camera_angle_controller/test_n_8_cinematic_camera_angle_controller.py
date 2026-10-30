import json
import n_8_cinematic_camera_angle_controller as m


def test_table_size():
    assert len(m.ANGLE_TABLE) == 96


def test_angle_0_prompt():
    node = m.PSN_Camera_Angle_Controller()
    prompt, params_json = node.run(0, 5.0, 0.0, 0.0)
    assert isinstance(prompt, str)
    assert m.ANGLE_TABLE[0] in prompt
    p = json.loads(params_json)
    assert p["angle_index"] == 0
    assert p["description"] == m.ANGLE_TABLE[0]


def test_angle_95_prompt():
    node = m.PSN_Camera_Angle_Controller()
    prompt, params_json = node.run(95, 10.0, 15.0, -30.0)
    assert m.ANGLE_TABLE[95] in prompt
    p = json.loads(params_json)
    assert p["angle_index"] == 95
    assert p["distance"] == 10.0
    assert p["tilt"] == 15.0
    assert p["pan"] == -30.0


def test_bad_index_low():
    node = m.PSN_Camera_Angle_Controller()
    try:
        node.run(-1, 5.0, 0.0, 0.0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_bad_index_high():
    node = m.PSN_Camera_Angle_Controller()
    try:
        node.run(96, 5.0, 0.0, 0.0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_clamping():
    node = m.PSN_Camera_Angle_Controller()
    prompt, params_json = node.run(0, 999.0, 500.0, -999.0)
    p = json.loads(params_json)
    assert p["distance"] == 100.0
    assert p["tilt"] == 90.0
    assert p["pan"] == -180.0


def test_input_types():
    it = m.PSN_Camera_Angle_Controller.INPUT_TYPES()
    assert "angle_index" in it["required"]
    assert "distance" in it["required"]
    assert "tilt" in it["required"]
    assert "pan" in it["required"]


def test_return_types():
    assert m.PSN_Camera_Angle_Controller.RETURN_TYPES == ("STRING", "STRING")
    assert m.PSN_Camera_Angle_Controller.RETURN_NAMES == ("camera_prompt", "camera_params")
    assert m.PSN_Camera_Angle_Controller.FUNCTION == "run"


def test_node_mappings():
    assert "PSN_Camera_Angle_Controller" in m.NODE_CLASS_MAPPINGS
    assert "PSN_Camera_Angle_Controller" in m.NODE_DISPLAY_NAME_MAPPINGS


def test_all_indices_unique():
    assert len(set(m.ANGLE_TABLE)) == 96


if __name__ == "__main__":
    test_table_size()
    test_angle_0_prompt()
    test_angle_95_prompt()
    test_bad_index_low()
    test_bad_index_high()
    test_clamping()
    test_input_types()
    test_return_types()
    test_node_mappings()
    test_all_indices_unique()
    print("ok")
