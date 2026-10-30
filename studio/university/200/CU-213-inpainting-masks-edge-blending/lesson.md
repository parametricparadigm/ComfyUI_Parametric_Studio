# CU-213 - Inpainting masks and edge blending

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the bridge, cadets. In CU-208, we learned how to steer the ship using conditioning. Today, we are dealing with the hull integrity of our images. When you inpaint, you are not just painting over a hole; you are splicing new fabric into an existing sail. If the seam is rough, the whole image looks patched and amateurish.

The goal of this lesson is to master the "seam." We will look at how ComfyUI handles the boundary between the original image and the generated content. A hard edge creates a visual artifact—a harsh line where the AI's guess meets the original pixels. We need to smooth that transition. This is not just aesthetic; it is mechanical. If you do not understand how the alpha channel interpolates, you will never get a seamless result.

## The intuition

Imagine you have two photos: Image A (the original) and Image B (the generated patch). You want to replace a specific region of Image A with Image B.

If you use a "hard" mask, it is like a switch. Pixel is either fully A or fully B. There is no in-between. At the boundary, you jump from value 10 to value 100 instantly. To the human eye, this looks like a sharp, artificial cut.

Now, imagine a "feathered" mask. This is like a fade. At the boundary, the pixel is a mix. It is 50% A and 50% B. As you move away from the boundary, it becomes 90% A and 10% B, then 99% A and 1% B. This gradual change tricks the eye into seeing a continuous surface rather than a splice.

In nautical terms: A hard mask is a welded joint with no grinding. A feathered mask is a blended weld, ground smooth so the metal flows from one piece to the next.

## Under the hood (the mechanism; math in plain text, define every symbol)

The core mechanism is linear interpolation of the alpha channel. We define a blend equation that combines two source images based on a mask value.

Let `img_a` be the tensor of the original image pixels.
Let `img_b` be the tensor of the generated image pixels.
Let `mask` be the tensor of alpha values, where each value `alpha` is between 0.0 and 1.0.

The blended output `result` is calculated as:

`result = alpha * img_a + (1 - alpha) * img_b`

Here is what each symbol does:
*   `alpha`: The weight given to the original image. If `alpha` is 1.0, the result is purely `img_a`. If `alpha` is 0.0, the result is purely `img_b`.
*   `1 - alpha`: The weight given to the generated image. This ensures the weights always sum to 1.0, preserving the brightness and color balance.
*   `img_a`: The source pixels from the original image.
*   `img_b`: The source pixels from the inpainted region.

When `alpha` is binary (0.0 or 1.0), the operation is a hard switch. When `alpha` is a gradient (e.g., 0.0, 0.5, 1.0), the operation is a smooth blend. The "feathering" is simply the creation of this gradient in the mask tensor before the multiplication occurs.

## In ComfyUI

In the ComfyUI ecosystem, this logic is implemented in various compositor and blend nodes. The evidence points to the `comfy_extras` module, which houses specialized functionality for image compositing. Specifically, the test suite `tests-unit/comfy_extras_test` validates the behavior of these nodes.

The file `tests-unit/comfy_extras_test/image_blend_alpha_test.py` contains a test case `test_rgba_keeps_image1_alpha`. This verifies that when blending RGBA images, the alpha channel of the first image is preserved correctly, which is critical for maintaining transparency and correct blending order.

Additionally, `tests-unit/comfy_extras_test/pad_image_test.py` includes `test_feathering_is_smooth_for_large_fp16_images`. This test ensures that the feathering process (the creation of the soft mask edges) works correctly even with half-precision floating-point numbers (fp16), which are common in VRAM-constrained environments. This is vital because fp16 has lower precision, and naive feathering can introduce banding or artifacts if not handled carefully.

The specific node names for the blend operation are not explicitly listed in the provided evidence beyond the test file names, so we refer to them generally as the image blend nodes within `comfy_extras`.

## Lab

In this lab, we simulate the blend operation using PyTorch tensors. We define a binary mask and a feathered mask, then apply the linear interpolation formula to two source images.

The lab code defines:
*   `mask`: A binary tensor `[0.0, 0.0, 1.0, 1.0]`.
*   `feather`: A soft tensor `[0.0, 0.5, 0.5, 1.0]`.
*   `img_a`: Values `[10.0, 20.0, 30.0, 40.0]`.
*   `img_b`: Values `[100.0, 200.0, 300.0, 400.0]`.

We calculate `hard_blend` using the binary mask and `feathered_blend` using the soft mask.

Here are the results from the lab run:

`RESULT hard_blend = [100.0, 200.0, 30.0, 40.0]`
This proves that with a binary mask, the output is a hard switch. At index 0 and 1, where the mask is 0.0, the output is exactly `img_b` (100.0 and 200.0). At index 2 and 3, where the mask is 1.0, the output is exactly `img_a` (30.0 and 40.0). There is no mixing.

`RESULT feathered_blend = [100.0, 110.0, 165.0, 40.0]`
This proves that with a feathered mask, the output is a smooth interpolation.
*   At index 0, `alpha` is 0.0, so the result is `img_b` (100.0).
*   At index 1, `alpha` is 0.5. The calculation is `0.5 * 20.0 + 0.5 * 200.0 = 10.0 + 100.0 = 110.0`. This is a perfect 50/50 mix, demonstrating the smooth transition.
*   At index 2, `alpha` is 0.5. The calculation is `0.5 * 30.0 + 0.5 * 300.0 = 15.0 + 150.0 = 165.0`. Again, a 50/50 mix.
*   At index 3, `alpha` is 1.0, so the result is `img_a` (40.0).

The key takeaway is the value `110.0` at index 1. In the hard blend, this pixel was `200.0`. In the feathered blend, it is `110.0`. This intermediate value is what prevents the harsh visual artifact.

## Common mistakes

1.  **Ignoring the mask gradient:** Using a binary mask for inpainting. This creates a hard edge that is immediately visible. Always apply a feather or blur to the mask before blending.
2.  **Feathering too wide:** If the feather is too large, the generated content bleeds into the original image, causing a "ghosting" effect. The feather width should be proportional to the scale of the detail in the image.
3.  **Precision errors in fp16:** As noted in the `pad_image_test.py` evidence, feathering in fp16 can be tricky. If you see banding in your blends, try upcasting the mask to fp32 for the calculation, then downcasting the result.
4.  **Forgetting the alpha channel:** If you are working with RGBA images, ensure your blend node respects the alpha channel. The `test_rgba_keeps_image1_alpha` test reminds us that alpha preservation is a specific behavior that must be validated.

## Go deeper

The mathematical foundation for these blending operations is standard in computer graphics, but the specific implementation in ComfyUI is validated by the unit tests in the `comfy_extras` module. For a deeper understanding of the underlying segmentation models that generate these masks, look into the SAM3 architecture.

The evidence references `comfy/ldm/sam3`, which contains the core implementation of the Segment Anything Model 3. The file `comfy/ldm/sam3/tracker.py` includes functions like `_compute_mask_overlap` and `fill_holes_in_mask_scores`. These functions are critical for generating clean, binary masks before they are feathered. If your base mask has holes or noise, feathering will not fix it; it will just blur the noise.

For the specific papers behind SAM3, the evidence does not provide arXiv IDs directly, but the module name `sam3` refers to the Segment Anything Model 3. You should look up the official arXiv paper for "Segment Anything Model 3" to understand the transformer-based architecture and memory mechanisms that produce the initial segmentation masks.

> UNVERIFIED: name not in evidence: result = alpha * img_a + (1 - alpha) * img_b


