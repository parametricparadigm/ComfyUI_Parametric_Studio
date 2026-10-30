import torch

from n_4_latent_inpainting_for_local_edits import (
    PSN_Latent_Inpaint_Encode,
    PSN_Latent_Inpaint_Decode,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


class FakeVAE:
    """A tiny deterministic VAE stand-in: encode = 2x downsample, decode = 2x upsample."""

    def encode(self, image):
        # image [B,H,W,C] -> latent [B,C,H/2,W/2]
        x = image.permute(0, 3, 1, 2)
        x = torch.nn.functional.avg_pool2d(x, kernel_size=2, stride=2)
        return {"samples": x}

    def decode(self, latent):
        x = latent["samples"]
        x = torch.nn.functional.interpolate(x, scale_factor=2, mode="nearest")
        return x.permute(0, 2, 3, 1)


def make_image(b=1, h=8, w=8, c=3, val=0.5):
    return torch.full((b, h, w, c), val, dtype=torch.float32)


def make_mask(b=1, h=8, w=8):
    m = torch.zeros((b, h, w), dtype=torch.float32)
    m[:, 2:6, 2:6] = 1.0  # center square is the inpaint region
    return m


def test_module_mappings():
    assert "PSN_Latent_Inpaint_Encode" in NODE_CLASS_MAPPINGS
    assert "PSN_Latent_Inpaint_Decode" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Latent_Inpaint_Encode"] == "PSN Latent Inpaint Encode"
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Latent_Inpaint_Decode"] == "PSN Latent Inpaint Decode"


def test_input_types_schema():
    enc = PSN_Latent_Inpaint_Encode.INPUT_TYPES()
    assert "image" in enc["required"]
    assert "mask" in enc["required"]
    assert "vae" in enc["required"]
    assert "mask_blur" in enc["required"]
    assert enc["required"]["mask_blur"][1]["default"] == 4

    dec = PSN_Latent_Inpaint_Decode.INPUT_TYPES()
    assert "latent" in dec["required"]
    assert "mask_latent" in dec["required"]
    assert "vae" in dec["required"]
    assert "original_image" in dec["required"]


def test_encode_shapes_and_mask_alignment():
    vae = FakeVAE()
    img = make_image(h=8, w=8)
    msk = make_mask(h=8, w=8)
    node = PSN_Latent_Inpaint_Encode()
    latent, mask_latent = node.run(img, msk, vae, mask_blur=2)

    # latent samples [B,C,H/2,W/2]
    assert latent["samples"].shape == (1, 3, 4, 4)
    # mask latent must match latent grid
    assert mask_latent.shape == (1, 4, 4)
    # mask latent values in 0..1
    assert mask_latent.min() >= 0.0
    assert mask_latent.max() <= 1.0
    # with blur=2 the mask latent center is partial, so the latent center is
    # attenuated but not fully zero; corners (mask ~0) keep ~the original value.
    s = latent["samples"]
    assert torch.all(s[:, :, 1:3, 1:3] < 0.5)
    # corner latent value = 0.5 * (1 - corner_mask) ~ 0.5 * (1 - 0.0312) ~ 0.484
    assert torch.allclose(s[:, :, 0:1, 0:1], torch.full((1, 3, 1, 1), 0.4844), atol=1e-3)
    # mask latent center should be the strongest region
    assert mask_latent[0, 1:3, 1:3].min() > 0.5
    # mask latent corners should be weak
    assert mask_latent[0, 0, 0] < 0.1


def test_decode_blends_only_masked_region():
    vae = FakeVAE()
    img = make_image(h=8, w=8, val=0.5)
    msk = make_mask(h=8, w=8)
    enc = PSN_Latent_Inpaint_Encode()
    latent, mask_latent = enc.run(img, msk, vae, mask_blur=0)

    # Simulate the sampler filling the masked region with a different value.
    filled = latent["samples"].clone()
    filled[:, :, 1:3, 1:3] = 0.9  # edited region
    edited_latent = {"samples": filled}

    dec = PSN_Latent_Inpaint_Decode()
    out = dec.run(edited_latent, mask_latent, vae, img)[0]

    assert out.shape == img.shape
    # Outside the mask, output must equal the original image.
    outside = torch.ones((1, 8, 8, 1), dtype=torch.float32)
    outside[:, 2:6, 2:6, :] = 0.0
    assert torch.allclose(out * outside, img * outside)
    # Inside the mask, output should reflect the edited value (0.9).
    inside = out[:, 3:5, 3:5, :]
    assert torch.allclose(inside, torch.full_like(inside, 0.9), atol=1e-5)


def test_no_inplace_mutation():
    vae = FakeVAE()
    img = make_image(h=8, w=8)
    msk = make_mask(h=8, w=8)
    img_before = img.clone()
    msk_before = msk.clone()
    enc = PSN_Latent_Inpaint_Encode()
    latent, mask_latent = enc.run(img, msk, vae, mask_blur=2)
    assert torch.equal(img, img_before)
    assert torch.equal(msk, msk_before)

    # decode must not mutate the latent or original image
    filled = latent["samples"].clone()
    filled[:, :, 1:3, 1:3] = 0.9
    edited = {"samples": filled}
    edited_before = edited["samples"].clone()
    dec = PSN_Latent_Inpaint_Decode()
    dec.run(edited, mask_latent, vae, img)
    assert torch.equal(edited["samples"], edited_before)
    assert torch.equal(img, img_before)


def test_bad_inputs_raise():
    vae = FakeVAE()
    enc = PSN_Latent_Inpaint_Encode()
    dec = PSN_Latent_Inpaint_Decode()

    # wrong image dims
    try:
        enc.run(torch.zeros(1, 8, 8), make_mask(), vae, 0)
        assert False, "expected ValueError for 3D image"
    except ValueError:
        pass

    # image values out of range
    try:
        enc.run(torch.full((1, 8, 8, 3), 2.0), make_mask(), vae, 0)
        assert False, "expected ValueError for out-of-range image"
    except ValueError:
        pass

    # batch mismatch
    try:
        enc.run(make_image(b=2), make_mask(b=1), vae, 0)
        assert False, "expected ValueError for batch mismatch"
    except ValueError:
        pass

    # mask size mismatch
    try:
        enc.run(make_image(h=8, w=8), make_mask(h=8, w=4), vae, 0)
        assert False, "expected ValueError for size mismatch"
    except ValueError:
        pass

    # latent missing samples key
    try:
        dec.run({}, make_mask(h=4, w=4), vae, make_image())
        assert False, "expected ValueError for missing samples"
    except ValueError:
        pass

    # mask_latent wrong dims
    try:
        dec.run({"samples": torch.zeros(1, 3, 4, 4)}, torch.zeros(1, 4, 4, 1), vae, make_image())
        assert False, "expected ValueError for 4D mask_latent"
    except ValueError:
        pass


def test_blur_zero_radius_is_identity():
    vae = FakeVAE()
    img = make_image(h=8, w=8)
    msk = make_mask(h=8, w=8)
    enc = PSN_Latent_Inpaint_Encode()
    _, m0 = enc.run(img, msk, vae, mask_blur=0)
    # with no blur the downsampled mask should still have a clear center
    assert m0.shape == (1, 4, 4)
    assert m0[0, 2, 2] > 0.5


def main():
    test_module_mappings()
    test_input_types_schema()
    test_encode_shapes_and_mask_alignment()
    test_decode_blends_only_masked_region()
    test_no_inplace_mutation()
    test_bad_inputs_raise()
    test_blur_zero_radius_is_identity()
    print("ok")


if __name__ == "__main__":
    main()
