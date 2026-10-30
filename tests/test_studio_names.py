from studio.names import resolve_names
OI = {"UNETLoader": {"input": {"required": {"unet_name": [["a/flux3_image_klein_bf16.safetensors", "minimax_h3/minimax_h3_fl2va_pruned_int8_convrot.safetensors", "x.safetensors"], {}]}}},
      "VAELoader": {"input": {"required": {"vae_name": [["minimax_h3_video_vae_fp16.safetensors"], {}]}}}}
def test_close_names_are_remapped_and_far_ones_reported():
    g = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux3-klein/flux3_image_klein_bf16.safetensors"}},
         "2": {"class_type": "UNETLoader", "inputs": {"unet_name": "totally_different_model.safetensors"}},
         "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"}},
         "4": {"class_type": "UNETLoader", "inputs": {"unet_name": "x.safetensors"}}}
    g, rep = resolve_names(g, OI)
    assert g["1"]["inputs"]["unet_name"] == "a/flux3_image_klein_bf16.safetensors" and g["3"]["inputs"]["vae_name"] == "minimax_h3_video_vae_fp16.safetensors"
    assert g["2"]["inputs"]["unet_name"] == "totally_different_model.safetensors" and any(r["node"] == "2" and r["now"] is None for r in rep) and g["4"]["inputs"]["unet_name"] == "x.safetensors"
