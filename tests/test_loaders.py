import pytest, torch
from psn_nodes import loaders as L

def fake_sd(diffusers, ch=128, mult=(1, 2, 4, 4), in_c=4, out_c=4, z=4, res=2):
    sd, pre, blk = {}, ("encoder.down_blocks." if diffusers else "encoder.down."), ("resnets" if diffusers else "block")
    sd["encoder.conv_in.weight"] = torch.zeros(ch, in_c, 3, 3); sd["decoder.conv_out.weight"] = torch.zeros(out_c, ch, 3, 3); sd["decoder.conv_in.weight"] = torch.zeros(512, z, 3, 3); sd["post_quant_conv.weight"] = torch.zeros(z, z, 1, 1)
    for i, m in enumerate(mult):
        for j in range(res): sd[f"{pre}{i}.{blk}.{j}.conv1.weight"] = torch.zeros(ch * m, ch, 3, 3); sd[f"{pre}{i}.{blk}.{j}.conv2.weight"] = torch.zeros(ch * m, ch * m, 3, 3)
    return sd

@pytest.mark.parametrize("diffusers", [True, False])
def test_vae_config_is_read_from_the_weights(diffusers):
    c = L.infer_vae_config(fake_sd(diffusers)); d = c["ddconfig"]
    assert (d["in_channels"], d["out_ch"], d["z_channels"], d["ch"], d["ch_mult"], d["num_res_blocks"], c["embed_dim"]) == (4, 4, 4, 128, [1, 2, 4, 4], 2, 4)
    d3 = L.infer_vae_config(fake_sd(diffusers, in_c=3, out_c=3, z=16, mult=(1, 2, 4), ch=64, res=3))["ddconfig"]; assert (d3["in_channels"], d3["out_ch"], d3["z_channels"], d3["ch_mult"], d3["ch"], d3["num_res_blocks"]) == (3, 3, 16, [1, 2, 4], 64, 3)

def test_not_a_vae_is_refused():
    with pytest.raises(ValueError, match="not a KL-VAE"): L.infer_vae_config({"x": torch.zeros(1)})

def test_rgbd_split_values_shapes_and_errors():
    img = torch.rand(2, 8, 8, 4); img[0, ..., 3] = torch.linspace(5, 9, 64).view(8, 8); img[1, ..., 3] = 0.3                              # image 1 has a flat depth map
    rgb, depth, mask = L.PSN_RGBDSplit().run(img)
    assert torch.equal(rgb, img[..., :3].clamp(0, 1)) and depth.shape == (2, 8, 8, 3) and mask.shape == (2, 8, 8)
    assert float(mask[0].min()) == 0.0 and float(mask[0].max()) == pytest.approx(1.0) and float(mask[1].abs().max()) == 0.0 and torch.isfinite(depth).all()    # per-image scaling, flat map -> zeros not NaN
    assert torch.equal(depth[..., 0], mask) and torch.equal(depth[..., 1], mask)
    with pytest.raises(ValueError, match="4-channel"): L.PSN_RGBDSplit().run(torch.rand(1, 8, 8, 3))
    assert L.PSN_RGBDSplit().run(torch.rand(1, 8, 8, 5).half())[1].dtype == torch.half
