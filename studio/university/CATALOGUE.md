# ComfyUniversity course catalogue

Every lesson has a CPU lab with stored output, a quiz, and linked primary sources. Rebuild with `python studio/university/build.py --labs`.

## Level 100: Foundations: what happens when you press Queue

- **CU-101** [What generative AI actually is](100/CU-101-what-is-generative-ai/lesson.md). Learn a distribution, then sample from it. Three models on one dataset show the difference between learning and memorising.
- **CU-102** [Anatomy of a ComfyUI graph](100/CU-102-anatomy-of-a-graph/lesson.md). Nodes, typed wires, execution order and caching.
- **CU-103** [Pixels, tensors and shapes](100/CU-103-pixels-tensors-shapes/lesson.md). Why [B,H,W,C] and [B,C,H,W] both exist and what breaks when you mix them.
- **CU-104** [Prompts become numbers: tokens and embeddings](100/CU-104-prompts-to-embeddings/lesson.md). Tokenization, embedding tables and what a text encoder hands the model.
- **CU-105** [Seeds, noise and determinism](100/CU-105-seeds-and-noise/lesson.md). Why the same seed gives the same picture and what changes it.
- **CU-106** [Your first image: checkpoint, sampler, VAE](100/CU-106-first-image-walkthrough/lesson.md). Follow one prompt through the whole text-to-image pipeline. Needs CU-102.
- **CU-107** [Models on disk: safetensors and families](100/CU-107-models-on-disk/lesson.md). What is inside a model file and why families matter.
- **CU-109** [Resolution, aspect ratio and the pixel budget](100/CU-109-resolution-aspect-ratio-pixel-budget/lesson.md). Master the art of balancing image dimensions to maximize detail without blowing up your VRAM usage.
- **CU-110** [Reading a workflow JSON like a map](100/CU-110-reading-workflow-json-like-a-map/lesson.md). Stop staring at the spaghetti code and start seeing the logical flow of your image generation pipeline. Needs CU-102.
- **CU-111** [Files and formats: PNG metadata, MP4, WAV, safetensors](100/CU-111-files-formats/lesson.md). Discover how ComfyUI reads and writes the invisible data that makes your images and models work.

## Level 200: Mechanics: how the pieces really work

- **CU-201** [Latent space and the VAE](200/CU-201-latent-space-and-the-vae/lesson.md). Train a tiny VAE on a CPU, and see why the midpoint of two latents is a picture while the midpoint of two images is a ghost. Needs CU-101, CU-103.
- **CU-202** [Diffusion from first principles](200/CU-202-diffusion-from-first-principles/lesson.md). Destroy data with noise on purpose, learn to undo one step, and train a real model on a CPU. Needs CU-101, CU-105.
- **CU-203** [Score matching, Tweedie and the SDE view](200/CU-203-score-matching-and-sdes/lesson.md). Why predicting noise is the same as learning the gradient of the data density, proved numerically. Needs CU-202.
- **CU-204** [Flow matching and rectified flow](200/CU-204-flow-matching-and-rectified-flow/lesson.md). Each training pair flies straight. The field you actually integrate does not, and that is the whole subject. Needs CU-202, CU-203.
- **CU-205** [Samplers are ODE solvers](200/CU-205-samplers-as-ode-solvers/lesson.md). Euler, Heun and DPM++ 2M written in five lines each, then measured against the exact answer. Needs CU-203.
- **CU-206** [Sigma schedules: where the steps go](200/CU-206-sigma-schedules/lesson.md). The scheduler chooses which noise levels the solver visits. Same model, same steps, different error. Needs CU-205.
- **CU-207** [Ancestral and SDE samplers: adding noise back](200/CU-207-ancestral-and-sde-samplers/lesson.md). Why a sampler that keeps injecting noise never settles on one image, and when that helps. Needs CU-205.
- **CU-208** [Guidance: CFG and what it really does](200/CU-208-guidance-cfg/lesson.md). One line of arithmetic, and it does not sample the distribution people usually say it does. Needs CU-205.
- **CU-209** [Negative prompts and cfg 1.0](200/CU-209-negative-prompts/lesson.md). A negative prompt is not a subtraction of concepts. It replaces the unconditional branch, and at cfg 1 it does nothing at all. Needs CU-208.
- **CU-210** [Precision: fp32, fp16, bf16, fp8](200/CU-210-precision/lesson.md). Where rounding bites: small LoRA deltas vanish, sums stall, and fp16 overflows at 65,504. Needs CU-103.
- **CU-211** [Quantization: int8, FP8, 4-bit and GGUF](200/CU-211-quantization/lesson.md). Trading bits for memory, and measuring what you lose. Needs CU-210.
- **CU-212** [LoRA: low-rank adaptation](200/CU-212-lora-low-rank/lesson.md). Why two skinny matrices can change a giant one. Needs CU-210.
- **CU-213** [Inpainting masks and edge blending](200/CU-213-inpainting-masks-edge-blending/lesson.md). Master the art of seamless image editing by learning how to mathematically feather mask edges for natural transitions. Needs CU-214.
- **CU-214** [Conditioning: img2img, inpaint, ControlNet, IP-Adapter](200/CU-214-conditioning-controlnet-ip/lesson.md). Every way of telling the model more than a prompt. Needs CU-106.
- **CU-215** [Video basics: frames, fps and temporal latents](200/CU-215-video-basics/lesson.md). Time as another axis, and why video models compress it. Needs CU-201.
- **CU-216** [Audio and music basics: waveforms to spectrograms](200/CU-216-audio-basics/lesson.md). Sample rate, Nyquist, STFT and why audio models work on spectrograms or latents.
- **CU-217** [Upscaling and tiling math](200/CU-217-upscaling-tiling-math/lesson.md). Master the geometry of high-resolution generation by calculating exact tile overlaps and upscaling factors without relying on GPU acceleration. Needs CU-201.
- **CU-218** [Seeds, batches and variations in video](200/CU-218-seeds-batches-variations-video/lesson.md). Discover how a single integer seed transforms random noise into reproducible video variations across your entire batch. Needs CU-105, CU-215.
- **CU-219** [Depth and edge preprocessors: Sobel by hand](200/CU-219-depth-edge-preprocessors-sobel-by/lesson.md). Stop treating depth maps as black boxes and learn to manually extract sharp edges using classic Sobel operators in pure PyTorch. Needs CU-103.
- **CU-220** [The execution model: what runs, and in what order](200/CU-220-execution-model/lesson.md). ComfyUI starts from the output nodes and works backwards. Build its scheduler in 60 lines and watch a lazy input change the order. Needs CU-102.
- **CU-221** [Caching: why changing the seed does not reload the model](200/CU-221-caching/lesson.md). Each node gets a key built from its whole ancestry. Change one input and only what lies downstream runs again. Needs CU-220.
- **CU-222** [Sub-graphs and node expansion](200/CU-222-subgraphs-and-expansion/lesson.md). A sub-graph is a front-end idea that the server never sees. Node expansion is a server idea that the front-end never sees. Needs CU-220.
- **CU-223** [App Mode: a graph with a form on top](200/CU-223-app-mode/lesson.md). App Mode shows chosen inputs and outputs of a workflow as a simple form. The graph underneath does not change. Needs CU-109, CU-220.
- **CU-224** [The API: queue, watch, fetch](200/CU-224-the-api/lesson.md). Everything the page does, a script can do: POST a prompt, read events from a websocket, fetch the files. Needs CU-109, CU-220.
- **CU-229** [Color spaces, gamma and image math](200/CU-229-color-and-image-math/lesson.md). sRGB vs linear light and why blending in the wrong space looks muddy. Needs CU-103.
- **CU-501** [History 1: GANs, the adversarial game (2014)](200/CU-501-history-1-gans-adversarial-game-2/lesson.md). Discover how the adversarial game between generator and discriminator laid the foundation for modern generative AI.
- **CU-502** [History 2: Variational autoencoders and the latent idea (2013)](200/CU-502-history-2-variational-autoencoder/lesson.md). Discover how the 'latent space' concept revolutionized generative AI by teaching machines to compress data into meaningful, continuous representations.
- **CU-503** [History 3: Pixel by pixel, autoregressive image models](200/CU-503-history-3-autoregressive-image-mo/lesson.md). Discover how early AI painted images one pixel at a time, laying the groundwork for modern generative techniques.
- **CU-505** [History 5: CLIP and contrastive learning](200/CU-505-history-5-clip-and-contrastive-le/lesson.md). Discover how CLIP learns to match images and text by maximizing the similarity of correct pairs while pushing incorrect ones apart.
- **CU-506** [History 6: Denoising diffusion arrives (DDPM, 2020)](200/CU-506-history-6-denoising-diffusion-arr/lesson.md). Discover how DDPM revolutionized image generation by teaching models to reverse noise step-by-step.
- **CU-507** [History 7: Latent diffusion and Stable Diffusion (2022)](200/CU-507-latent-diffusion-stable-diffusion/lesson.md). Discover how Stable Diffusion revolutionized image generation by operating in a compressed latent space rather than raw pixels. Needs CU-201.
- **CU-508** [History 8: Adapters era: LoRA and ControlNet](200/CU-508-history-8-adapters-era-lora-contr/lesson.md). Discover how low-rank adaptations and spatial controls revolutionized efficient fine-tuning in the ComfyUI ecosystem. Needs CU-212.

## Level 300: Architecture: the machinery inside the models

- **CU-301** [Attention from scratch](300/CU-301-attention-from-scratch/lesson.md). Scaled dot-product attention in six lines, why the square root of d is there, and how a prompt reaches a pixel. Needs CU-103, CU-104.
- **CU-302** [Multi-head, GQA and RoPE](300/CU-302-heads-gqa-rope/lesson.md). Splitting attention, sharing keys, and rotating positions. Needs CU-301.
- **CU-303** [DiT and MM-DiT blocks](300/CU-303-dit-and-mmdit/lesson.md). How a transformer replaces the U-Net: patches, adaLN, joint text-image attention. Needs CU-301.
- **CU-304** [Why attention is O(n^2) and how Flash/Sage fix the memory](300/CU-304-flash-attention-memory/lesson.md). Tiling, online softmax and the memory wall. Needs CU-301.
- **CU-305** [VRAM budget math: weights, activations, caches](300/CU-305-vram-budget-math/lesson.md). Predicting whether it fits before you press Queue. Needs CU-210.
- **CU-306** [Text encoders: CLIP, T5 and LLM encoders](300/CU-306-text-encoders-deep/lesson.md). What each encoder gives the model and what it costs. Needs CU-104.
- **CU-307** [3D generation: meshes, SDFs, voxels and Gaussian splats](300/CU-307-three-d-representations/lesson.md). The shapes a model can output and how they convert. Needs CU-201.
- **CU-308** [Speed: distillation, caching, compile, fewer steps](300/CU-308-speed-tricks/lesson.md). Where the seconds go and how to get them back.
- **CU-309** [Positional encodings in 2D and 3D](300/CU-309-positional-encodings-2d-3d/lesson.md). Discover how we inject spatial awareness into neural networks by transforming grid coordinates into rich frequency signals. Needs CU-302.
- **CU-310** [Cross-attention versus joint attention](300/CU-310-cross-attention-versus-joint-attention/lesson.md). Discover how ComfyUI's attention mechanisms differ by exploring the mathematical distinction between conditioning on external prompts and self-attending within  Needs CU-301.
- **CU-311** [Mixed precision: where accumulation hides](300/CU-311-mixed-precision-accumulation/lesson.md). Discover why your gradients vanish or explode when mixing float16 and float32, and how ComfyUI's scheduler hides the accumulation trap. Needs CU-210.
- **CU-312** [KV cache and autoregressive decoding](300/CU-312-kv-cache-autoregressive-decoding/lesson.md). Discover how ComfyUI's text encoders and diffusion schedulers leverage caching to speed up sequential generation without sacrificing quality. Needs CU-301.
- **CU-313** [Mixture of experts routing](300/CU-313-mixture-of-experts-routing/lesson.md). Discover how ComfyUI's advanced diffusion models intelligently select the right expert for each token to boost efficiency and quality. Needs CU-301.
- **CU-314** [Flow-matching losses and velocity targets](300/CU-314-flow-matching-losses-and-velocity-target/lesson.md). Learn how to compute the exact velocity field that guides your diffusion model from noise to data.
- **CU-315** [Temporal consistency and optical flow basics](300/CU-315-temporal-consistency-optical-flow-basics/lesson.md). Learn how to keep your AI videos from jittering by mastering the math behind motion estimation. Needs CU-215.
- **CU-316** [Video VAEs and receptive fields](300/CU-316-video-vaes-and-receptive-fields/lesson.md). Discover how Video VAEs compress temporal dimensions and why understanding receptive fields is key to controlling motion artifacts. Needs CU-215, CU-201.
- **CU-317** [Sparse and windowed attention](300/CU-317-sparse-windowed-attention/lesson.md). Discover how limiting attention to local windows and sparse patterns drastically reduces computational cost while preserving spatial context. Needs CU-304.
- **CU-504** [History 4: StyleGAN and style modulation](300/CU-504-history-4-stylegan-style-modulati/lesson.md). Discover how StyleGAN decouples content from style to achieve fine-grained control over generated images. Needs CU-501.
- **CU-509** [History 9: Transformers replace U-Nets: DiT and rectified flow](300/CU-509-transformers-replace-unets-dit-re/lesson.md). Discover how Diffusion Transformers (DiT) and rectified flow are reshaping the landscape of generative AI by moving away from traditional U-Net architectures. Needs CU-303.
- **CU-510** [History 10: From frames to space-time: the road to modern video models](300/CU-510-history-10-frames-to-space-time/lesson.md). Discover how video generation evolved from static image sequences to coherent space-time volumes. Needs CU-215.
- **CU-511** [History 11: Audio models: WaveNet to autoregressive music to diffusion music](300/CU-511-history-11-audio-models/lesson.md). Trace the evolution of AI audio from sample-by-sample prediction to holistic diffusion synthesis. Needs CU-216.
- **CU-513** [History 13: Seeing in 3D: NeRF, Gaussian splats and structured latents](300/CU-513-seeing-in-3d-nerf-gaussian-splats/lesson.md). Explore how modern 3D generation moves from implicit fields to explicit particles and structured latent spaces to render photorealistic scenes. Needs CU-307.
- **CU-514** [History 14: The speed era: LCM, turbo and distillation](300/CU-514-history-14-speed-era-lcm-turbo-di/lesson.md). Discover how we tricked diffusion models into thinking they were already finished, slashing generation time from minutes to seconds. Needs CU-308.
- **CU-515** [History 15: The size era: FP8, GGUF and 4-bit formats arrive](300/CU-515-history-15-size-era-fp8-gguf-4bit/lesson.md). Discover how quantization formats like FP8 and GGUF revolutionized local AI by shrinking model sizes without sacrificing too much quality. Needs CU-211.

## Level 400: Engineering and research: build, train, measure, scale

- **CU-401** [Writing a custom node with the V3 API](400/CU-401-custom-nodes-v3/lesson.md). A class with a schema and an execute method. The engine calls your node without making an instance, and that changes how you write it. Needs CU-220, CU-221.
- **CU-402** [Memory management: who gets the GPU](400/CU-402-memory-management/lesson.md). Before each sampler run, ComfyUI budgets VRAM and evicts what it must. Replay the arithmetic and read your own logs. Needs CU-220.
- **CU-403** [Model merging: weighted, SLERP, task arithmetic](400/CU-403-model-merging-math/lesson.md). Why averaging weights can work and when it fails. Needs CU-212.
- **CU-404** [Evaluating outputs: metrics, checks and their limits](400/CU-404-evaluating-outputs/lesson.md). What PSNR, SSIM-style and embedding scores tell you, and what they cannot. Needs CU-106.
- **CU-405** [Agents on ComfyUI: tools, verification, side-effect safety](400/CU-405-agents-on-comfyui/lesson.md). Letting a model drive the graph without letting it break things. Needs CU-102, CU-401.
- **CU-406** [Scaling: sharding, batching and serving](400/CU-406-scaling-and-serving/lesson.md). From one GPU to many, and what throughput really means. Needs CU-305.
- **CU-407** [Reading a generative-AI paper in 20 minutes](400/CU-407-reading-papers/lesson.md). A method for extracting claims, assumptions and what to check.
- **CU-409** [Distillation math: teacher, student, consistency](400/CU-409-distillation-math-teacher-student/lesson.md). Learn how to compress a complex diffusion model into a fast, few-step generator by mastering the mathematical bridge between teacher guidance and student consis Needs CU-308.
- **CU-410** [Quantization error propagation through layers](400/CU-410-quantization-error-propagation/lesson.md). Discover how tiny rounding errors in low-bit weights can snowball into significant output drift as they pass through deep neural networks. Needs CU-211.
- **CU-411** [Evaluating video: a flicker metric](400/CU-411-evaluating-video-flicker-metric/lesson.md). Learn to quantify visual stability by calculating the temporal variance of pixel intensities to detect flicker in generated video sequences. Needs CU-404.
- **CU-412** [Dataset curation and captioning for training](400/CU-412-dataset-curation-and-captioning-for-trai/lesson.md). Learn how to transform raw images into high-quality training data by mastering precise captioning and dataset balancing techniques. Needs CU-402.
- **CU-413** [Prompt adherence evaluation](400/CU-413-prompt-adherence-evaluation/lesson.md). Learn to quantify how well your generated images actually match the text prompts using deterministic CPU-based metrics. Needs CU-404.
- **CU-415** [Reproducibility and provenance: hashing graphs and seeds](400/CU-415-reproducibility-and-provenance/lesson.md). Learn how to cryptographically fingerprint your ComfyUI workflows and seeds to ensure bit-perfect reproducibility across different machines and sessions. Needs CU-105, CU-405.
- **CU-416** [Profiling memory and time on a GPU (with a CPU model of it)](400/CU-416-profiling-memory-and-time-on-a-gpu-with-/lesson.md). Learn to predict GPU memory bottlenecks by simulating tensor lifecycles and operation costs on your CPU. Needs CU-305.
- **CU-516** [History 16: What open means: weights, licences and the ecosystem](400/CU-516-what-open-means-weights-licences-/lesson.md). Explore the legal and technical boundaries of open-source AI by dissecting how model weights, licenses, and community contributions shape the ComfyUI ecosystem.
- **CU-517** [History 17: Studios and agents: when models became pipelines](400/CU-517-studios-and-agents/lesson.md). Discover how ComfyUI transforms static model calls into dynamic, agent-driven pipelines that orchestrate complex creative workflows. Needs CU-405.
