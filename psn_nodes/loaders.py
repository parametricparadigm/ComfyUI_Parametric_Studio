"""Loader wrappers for models core ComfyUI cannot read as-is. PSN_VAELoaderChannels reads the layout (colour channels in/out, latent size, block widths) from the weights themselves, so a VAE that is not 3-channel RGB
(for example LDM3D's 4-channel RGB-D VAE) loads and decodes. PSN_RGBDSplit turns the 4-channel result into a colour image and a depth image. Original code."""
import torch

def infer_vae_config(sd):
    """KL-VAE layout from a state dict in diffusers ('down_blocks') or original ('down') key naming -> dict(ddconfig, embed_dim)."""
    diff = any(k.startswith("encoder.down_blocks.") for k in sd)
    pre = "encoder.down_blocks." if diff else "encoder.down."; blk = "resnets" if diff else "block"
    n = len({k[len(pre):].split(".")[0] for k in sd if k.startswith(pre)})
    if not n: raise ValueError("not a KL-VAE state dict (no encoder down blocks)")
    ch = sd["encoder.conv_in.weight"].shape[0]; mult = [sd[f"{pre}{i}.{blk}.0.conv2.weight"].shape[0] // ch for i in range(n)]
    res = len({k.split(".")[4] for k in sd if k.startswith(f"{pre}0.{blk}.") and k.endswith("conv1.weight")})
    z = sd["decoder.conv_in.weight"].shape[1]; emb = sd["post_quant_conv.weight"].shape[0] if "post_quant_conv.weight" in sd else z
    dd = {"double_z": True, "z_channels": z, "resolution": 256, "in_channels": sd["encoder.conv_in.weight"].shape[1], "out_ch": sd["decoder.conv_out.weight"].shape[0], "ch": ch, "ch_mult": mult,
          "num_res_blocks": res or 2, "attn_resolutions": [], "dropout": 0.0}
    return {"ddconfig": dd, "embed_dim": emb}

class PSN_VAELoaderChannels:
    """Load a KL-VAE whose colour channel count is not 3 (e.g. LDM3D-4C RGB-D). The layout is read from the weights; nothing is guessed."""
    @classmethod
    def INPUT_TYPES(cls):
        try: import folder_paths; names = folder_paths.get_filename_list("vae")
        except ImportError: names = []                      # not running inside ComfyUI (tests, docs): no files to list
        return {"required": {"vae_name": (names,)}}
    RETURN_TYPES = ("VAE",); RETURN_NAMES = ("vae",); FUNCTION = "run"; CATEGORY = "ParametricStudio/Loaders"
    def run(self, vae_name):
        import folder_paths, comfy.sd, comfy.utils
        sd = comfy.utils.load_torch_file(folder_paths.get_full_path_or_raise("vae", vae_name)); cfg = infer_vae_config(sd)
        return (comfy.sd.VAE(sd=sd, config={"target": "comfy.ldm.models.autoencoder.AutoencoderKL", "params": cfg}),)

class PSN_RGBDSplit:
    """Split a 4-channel image into colour (first 3 channels) and depth (4th channel, scaled to 0..1 per image; a flat depth map becomes zeros). Also returns the depth as a MASK."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"image": ("IMAGE",)}}
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK"); RETURN_NAMES = ("rgb", "depth", "depth_mask"); FUNCTION = "run"; CATEGORY = "ParametricStudio/Loaders"
    def run(self, image):
        if image.dim() != 4 or image.shape[-1] < 4: raise ValueError(f"needs a 4-channel (RGB-D) image, got shape {tuple(image.shape)}")
        rgb, d = image[..., :3].clamp(0, 1), image[..., 3].float()
        lo, hi = d.amin((1, 2), keepdim=True), d.amax((1, 2), keepdim=True); d = ((d - lo) / (hi - lo).clamp_min(1e-6)).to(image.dtype)
        return (rgb, d.unsqueeze(-1).expand(-1, -1, -1, 3).contiguous(), d)

NODE_CLASS_MAPPINGS = {"PSN_VAELoaderChannels": PSN_VAELoaderChannels, "PSN_RGBDSplit": PSN_RGBDSplit}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_VAELoaderChannels": "PSN VAE Loader (any colour channels)", "PSN_RGBDSplit": "PSN RGB-D Split"}
