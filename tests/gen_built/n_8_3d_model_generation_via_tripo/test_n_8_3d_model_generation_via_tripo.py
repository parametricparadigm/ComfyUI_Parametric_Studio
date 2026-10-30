import torch
import base64

from n_8_3d_model_generation_via_tripo import (
    PSN_Tripo_Text_To_3D,
    PSN_Tripo_Image_To_3D,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _validate_image,
    _image_to_base64_png,
    _make_job_id,
    _make_model_url,
)

# 1. Module-level mappings exist and are correct
assert "PSN_Tripo_Text_To_3D" in NODE_CLASS_MAPPINGS
assert "PSN_Tripo_Image_To_3D" in NODE_CLASS_MAPPINGS
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Tripo_Text_To_3D"] == "Tripo Text to 3D"
assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Tripo_Image_To_3D"] == "Tripo Image to 3D"

# 2. INPUT_TYPES classmethod works
it = PSN_Tripo_Text_To_3D.INPUT_TYPES()
assert "api_key" in it["required"]
assert "prompt" in it["required"]
assert "texture" in it["required"]
assert "pbr" in it["required"]

it2 = PSN_Tripo_Image_To_3D.INPUT_TYPES()
assert "image" in it2["required"]

# 3. Text-to-3D: valid input returns URL and job_id
node = PSN_Tripo_Text_To_3D()
url, jid = node.run(api_key="test_key", prompt="a red cube", texture=True, pbr=True)
assert isinstance(url, str) and url.startswith("https://")
assert isinstance(jid, str) and jid.startswith("tripo_")
assert len(jid) == len("tripo_") + 24

# 4. Text-to-3D: deterministic - same prompt gives same job id
url2, jid2 = node.run(api_key="test_key", prompt="a red cube", texture=True, pbr=True)
assert jid == jid2
assert url == url2

# 5. Text-to-3D: different prompt gives different job id
_, jid3 = node.run(api_key="test_key", prompt="a blue sphere", texture=True, pbr=True)
assert jid3 != jid

# 6. Text-to-3D: empty prompt raises ValueError
try:
    node.run(api_key="k", prompt="   ", texture=True, pbr=True)
    assert False, "should have raised"
except ValueError:
    pass

# 7. Text-to-3D: non-string prompt raises TypeError
try:
    node.run(api_key="k", prompt=123, texture=True, pbr=True)
    assert False, "should have raised"
except TypeError:
    pass

# 8. Image-to-3D: valid image returns URL and job_id
img = torch.rand(1, 8, 8, 3)  # [B,H,W,C] in 0..1
node2 = PSN_Tripo_Image_To_3D()
url_i, jid_i = node2.run(api_key="test_key", image=img, texture=True)
assert isinstance(url_i, str) and url_i.startswith("https://")
assert isinstance(jid_i, str) and jid_i.startswith("tripo_")

# 9. Image-to-3D: deterministic
url_i2, jid_i2 = node2.run(api_key="test_key", image=img, texture=True)
assert jid_i == jid_i2
assert url_i == url_i2

# 10. Image-to-3D: different image gives different job id
img_diff = torch.rand(1, 8, 8, 3)
_, jid_diff = node2.run(api_key="test_key", image=img_diff, texture=True)
assert jid_diff != jid_i

# 11. Image validation: wrong dims raises ValueError
try:
    _validate_image(torch.rand(4, 4, 3))  # 3-D, not 4-D
    assert False, "should have raised"
except ValueError:
    pass

# 12. Image validation: bad channel count raises ValueError
try:
    _validate_image(torch.rand(1, 4, 4, 5))  # 5 channels
    assert False, "should have raised"
except ValueError:
    pass

# 13. Image validation: out-of-range values raise ValueError
try:
    _validate_image(torch.rand(1, 4, 4, 3) * 2.0)  # values up to ~2
    assert False, "should have raised"
except ValueError:
    pass

# 14. Image validation: non-tensor raises TypeError
try:
    _validate_image("not a tensor")
    assert False, "should have raised"
except TypeError:
    pass

# 15. Image-to-3D: non-tensor image raises TypeError
try:
    node2.run(api_key="k", image="bad", texture=True)
    assert False, "should have raised"
except TypeError:
    pass

# 16. Image-to-3D: non-bool texture raises TypeError
try:
    node2.run(api_key="k", image=img, texture="yes")
    assert False, "should have raised"
except TypeError:
    pass

# 17. _image_to_base64_png produces valid base64
b64 = _image_to_base64_png(img)
decoded = base64.b64decode(b64)
assert len(decoded) == 8 * 8 * 3  # H*W*C bytes

# 18. _make_job_id is deterministic
assert _make_job_id("abc") == _make_job_id("abc")
assert _make_job_id("abc") != _make_job_id("abd")

# 19. _make_model_url format
u = _make_model_url("tripo_abc123")
assert u == "https://models.tripo3d.ai/tripo_abc123/tripo_abc123.glb"

# 20. RETURN_TYPES and RETURN_NAMES
assert PSN_Tripo_Text_To_3D.RETURN_TYPES == ("STRING", "STRING")
assert PSN_Tripo_Text_To_3D.RETURN_NAMES == ("model_url", "job_id")
assert PSN_Tripo_Image_To_3D.RETURN_TYPES == ("STRING", "STRING")
assert PSN_Tripo_Image_To_3D.RETURN_NAMES == ("model_url", "job_id")

# 21. FUNCTION and CATEGORY
assert PSN_Tripo_Text_To_3D.FUNCTION == "run"
assert PSN_Tripo_Text_To_3D.CATEGORY == "ParametricStudio/3D"
assert PSN_Tripo_Image_To_3D.FUNCTION == "run"
assert PSN_Tripo_Image_To_3D.CATEGORY == "ParametricStudio/3D"

# 22. Single-channel image works
img1 = torch.rand(1, 4, 4, 1)
b64_1 = _image_to_base64_png(img1)
assert len(base64.b64decode(b64_1)) == 4 * 4 * 3  # expanded to 3 channels

# 23. 4-channel image works (alpha stripped)
img4 = torch.rand(1, 4, 4, 4)
b64_4 = _image_to_base64_png(img4)
assert len(base64.b64decode(b64_4)) == 4 * 4 * 3

# 24. Batch > 1 works (uses first image)
img_batch = torch.rand(3, 4, 4, 3)
url_b, jid_b = node2.run(api_key="k", image=img_batch, texture=True)
assert jid_b.startswith("tripo_")

print('ok')
