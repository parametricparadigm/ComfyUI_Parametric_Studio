/* Pure logic of the 3D Pro page: what each ComfyUI node does, where it sits, when light reaches it, what a run looks like. No DOM and no three.js here; tested in tests/studio_lanes/test_graph3d.mjs. */
const I = (kind, short, say) => ({ kind, short, say });
const LOADV = "Loads the VAE, which translates between pixels and the small latent space where the model works.";
const SAVE = "Writes the finished file to the output folder. This is the file you see in the studio.";
const DEC = "Uses the VAE to turn the finished latent into real frames.";
const DECA = "Uses the audio VAE to turn the finished latent into a sound wave.";
const EMPTY = "Creates an empty latent at the output size. Its shape sets the width, height and length of the result.";
export const CLASS_INFO = {
  /* kijai's WanVideoWrapper nodes in the LongCat Avatar 1.5 talking-head template, from the pack's own descriptions and tooltips (commit 088128b) */
  WanVideoModelLoader: I("load", "Loads the video model", "kijai's WanVideoWrapper loader. Loads the Wan-family diffusion model (here LongCat Avatar 1.5) with its precision, attention mode, any LoRA and the block-swap settings."),
  WanVideoLoraSelect: I("load", "Picks a LoRA", "Chooses a LoRA from the loras folder and its strength, for WanVideoWrapper's model loader to apply. Here it is the distilled LoRA that lets the model run in a few steps."),
  WanVideoBlockSwap: I("plan", "Saves VRAM", "Settings for block swapping: this many transformer blocks wait in CPU memory and move to the GPU only when needed. Slower, but the model fits on a smaller card."),
  WanVideoVAELoader: I("load", "Loads the VAE", "Loads the Wan VAE, which turns pictures into the small latent space the model works in, and back."),
  WanVideoTextEncodeCached: I("text", "Reads the prompt", "Turns the positive and negative prompts into text embeddings with the UMT5 encoder, then unloads the encoder completely to free memory for the video model."),
  WanVideoEncode: I("latent", "Turns the picture into a latent", "Uses the Wan VAE to turn the starting picture into a latent the model can continue from."),
  WhisperModelLoader: I("load", "Loads Whisper", "Loads the Whisper audio encoder. It listens to the speech so the avatar's mouth and face can follow it."),
  LongCatAvatarWhisperEmbeds: I("text", "Reads the voice", "Runs the speech through Whisper at the video's frame rate (25 fps for LongCat Avatar 1.5), after levelling its loudness, so each frame knows which sound it goes with."),
  WanVideoLongCatAvatarExtendEmbeds: I("latent", "Lines up picture and voice", "Puts the starting latent, the reference frame and the audio embeddings together for the next stretch of frames, so a talking clip can be made in overlapping pieces."),
  WanVideoSchedulerv2: I("plan", "Sets the steps", "Chooses the noise schedule, the number of steps and the shift for WanVideoWrapper's sampler."),
  WanVideoSamplerv2: I("sample", "The sampler: makes the clip", "Where the clip actually forms: starts from noise and removes a little at every step, guided by the prompt, the picture and the voice."),
  WanVideoDecode: I("decode", "Turns the latent into frames", "Uses the Wan VAE to turn the finished latent into real video frames."),
  "EmptyAceStep1.5LatentAudio": I("latent", "Sets the song's length", "Makes the empty audio latent ACE-Step 1.5 fills, at the length you asked for."), EmptyLatentAudio: I("latent", "Sets the clip's length", "Makes the empty audio latent the sampler fills, at the length you asked for."), EmptyYuE2LatentAudio: I("latent", "Sets the song's length", "Makes the empty audio latent YuE2 fills. Its length comes from the plan YuE2 wrote."),
  "TextEncodeAceStepAudio1.5": I("text", "Reads the style and lyrics", "Turns style tags, lyrics, BPM and key into what ACE-Step 1.5 follows."), ACEStep15TaskTextEncode: I("text", "Reads the style for one task", "RyanOnTheInside's node. The same reading of words, told which task it's for: cover, repaint or extract."),
  CFGNorm: I("plan", "Keeps guidance from overshooting", "Normalises the guided prediction so a strong CFG doesn't wash out colour or detail. Used with Qwen-Image-Edit."), FluxKontextImageScale: I("media", "Resizes to a size the editor knows", "Scales the input picture to the nearest resolution these editing models were trained on, so edits stay sharp."), FluxKontextMultiReferenceLatentMethod: I("latent", "Chooses how reference pictures are joined", "Sets how the reference pictures' latents are attached to the prompt, so one edit can draw on more than one picture."),
  ImageBatch: I("media", "Joins two sets of frames", "Puts two pictures or frame sets into one batch, one after the other."), ImageCompositeMasked: I("media", "Places one picture over another", "Pastes the source over the destination wherever the mask is white, at the position you give."), ImageToMask: I("media", "Turns a channel into a mask", "Takes one colour channel of a picture and uses it as a mask."), RepeatImageBatch: I("media", "Repeats a picture", "Copies one picture several times to make a batch, for example a still background behind every frame of a clip."),
  LTXVAddGuide: I("latent", "Pins frames the video must hit", "Adds guide frames (a start, an end or a keyframe) into the LTX video latent so the clip passes through them."), LTXVAudioVAEEncode: I("latent", "Turns sound into latents", "Encodes an audio clip with LTX's audio VAE so the model can follow it or write new sound against it."), LTXVSetAudioRefTokens: I("text", "Marks the reference sound", "Tells LTX which part of the audio is the reference to keep, so a dub follows the source's timing and voice."),
  SamplerEulerAncestral: I("plan", "Picks Euler ancestral", "The Euler ancestral sampler: it adds a little fresh noise at each step, which can give looser, more varied results than plain Euler."), TextEncodeQwenImageEditPlus: I("text", "Reads the edit instruction", "Turns your instruction and up to three reference pictures into what Qwen-Image-Edit follows."),
  LoadControlFoleyModel: I("load", "Loads the sound-effects model", "Loads ControlFoley, Xiaomi Research's model that writes sound effects to match what happens in a video."), LoadControlFoleyVideo: I("media", "Loads the clip to score", "Reads the video ControlFoley will watch. The sound follows the clip's own length, up to 30 seconds."), ControlFoleyGenerate: I("sample", "Writes the sound effects", "ControlFoley watches the clip and generates sound that matches it. Your words steer which sounds it makes."),
  SaveControlFoleyAudio: I("save", "Saves the sound", "Writes the generated audio to the output folder as a WAV or FLAC file."), UnloadControlFoleyModel: I("value", "Frees the model's memory", "Runs once the sound is saved and drops ControlFoley from memory, so the next job gets that room back."),
  ImageColorSpace: I("media", "Converts the colour space", "Converts frames between colour spaces, such as ordinary sRGB, HDR video (HLG) and the ACEScct space LTX's HDR finish works in."), LTXVLoadConditioning: I("text", "Loads a ready-made prompt", "Loads a prompt that was already encoded and saved to a file, so no text encoder has to run. The HDR finish uses its scene file."), LTXVVAEForceFloat32: I("load", "Puts the VAE in full precision", "Switches the video VAE to 32-bit numbers for encoding and decoding. Native HDR needs this precision."),
  LTXVHDRDecodePostprocess: I("decode", "Recovers the HDR light", "Turns the decoded frames back into high-dynamic-range light and, when asked, writes them as an EXR image sequence. It also gives a tonemapped preview."), SaveImageAdvanced: I("save", "Saves the frames as images", "Saves pictures with more choices than Save Image: PNG at 8 or 16 bits, EXR or AVIF."),
  LTXVDrawTracks: I("media", "Draws the motion tracks", "Draws your tracks as moving dots with fading trails, one frame per point, as a guide video for LTX's motion-track LoRA to follow."), PSN_CameraPathEmbedding: I("plan", "Describes your drawn camera move", "This studio's own node: turns the camera path you drew into per-frame camera data that tells Wan how the view should move."),
  YuE2GenerateABC: I("plan", "Writes the tune as sheet music", "YuE2's first stage: it writes a melody plan in ABC notation from your style and lyrics."), YuE2GenerateMusic: I("plan", "Plans the song", "YuE2's second stage: it turns the words and the sheet music into what the audio model renders."), SheetSage2AudioToABC: I("plan", "Reads the tune from audio", "SheetSage listens to a song and writes its melody as ABC notation, so YuE2 can sing it again."),
  ACEStep15NativeCoverGuider: I("plan", "Keeps the song, changes the style", "RyanOnTheInside's guider. It holds the structure of the source audio while the words ask for a new style."), ACEStep15NativeEditGuider: I("plan", "Repaints or extends a part", "RyanOnTheInside's guider. It redoes a stretch of time, or adds more at either end, and leaves the rest alone."), ACEStep15NativeExtractGuider: I("plan", "Asks for one instrument", "RyanOnTheInside's guider. It has the model generate one part of a song, such as the vocals or drums."), ACEStepAudioPostProcessor: I("save", "Keeps the untouched parts exact", "RyanOnTheInside's node. It puts the original audio back wherever the edit wasn't asked to change anything."), ModelSamplingACEStep: I("plan", "Sets ACE-Step's timing", "Sets the shift, which decides how the sampling steps are spread out."), ModelSamplingAuraFlow: I("plan", "Sets the model's timing", "Sets the shift, which decides how the sampling steps are spread out."),
  LoadAudio: I("load", "Loads a song", "Reads an audio file you gave it."), AudioEncoderLoader: I("load", "Loads an audio reader", "Loads the model that listens to audio."), VAEEncodeAudio: I("latent", "Turns sound into latents", "Packs audio into the form the music model works on."), AudioTrim: I("value", "Cuts a stretch of audio", "RyanOnTheInside's node. It keeps the time between a start and an end."),
  AudioFeatureExtractor: I("value", "Measures the sound over time", "RyanOnTheInside's node. It gives one number per video frame: energy, attacks, brightness or the like."), FeatureToFloat: I("value", "Turns a feature into numbers", "RyanOnTheInside's node. It hands the measurement on as a plain list."), FlexAudioVisualizerCircular: I("value", "Draws sound in a ring", "RyanOnTheInside's node. It draws the audio's frequencies around a circle, frame by frame."), FlexImageBloom: I("value", "Glows with the music", "RyanOnTheInside's node. A glow whose strength follows a feature of the audio."), FlexImageChromaticAberration: I("value", "Splits colour on the beat", "RyanOnTheInside's node. A colour split whose size follows a feature of the audio."),
  PreviewAny: I("value", "Shows a value", "Shows what passes through, and hands it on as text."), PrimitiveString: I("value", "Holds some text", "A box that holds text for other nodes."), PrimitiveStringMultiline: I("value", "Holds some text", "A box that holds longer text for other nodes."),
  MiniMaxH3FunUnion2LoaderEXPT8: I("load", "Loads H3's control model", "Loads MiniMax H3's Fun Union control model, the part that makes a video follow a depth or pose guide."),
  MiniMaxH3FunUnion2ApplyEXPT8: I("plan", "Follows a depth or pose video", "Makes MiniMax H3 follow a guide video frame by frame, so the layout and the camera move hold while the picture is made new."),
  Wan22FunControlToVideo: I("plan", "Follows a guide video (Wan)", "Sets up Wan 2.2 to follow a depth or pose video, with a reference picture for the look."),
  TextEncodeQwenImage21: I("text", "Reads the words and the picture", "Turns your words and a reference picture into what Qwen-Image 2.1 edits from."),
  QwenImage21Cache: I("load", "Keeps Qwen-Image ready", "Holds Qwen-Image 2.1 in a form that runs faster over its steps."),
  EasyCache: I("value", "Skips repeated work", "Reuses earlier results when a step changes little, which saves time at a small cost in detail."),
  SolidMask: I("media", "A plain mask", "Makes a mask of one value across the whole frame. White here means make every pixel new."),
  ResizeImageMaskNode: I("media", "Resizes", "Resizes a picture or a video to the size the model works at."),
  UNETLoader: I("load", "Loads the diffusion model", "Loads the diffusion model: the network that learned to turn noise into a picture, step by step."),
  CheckpointLoaderSimple: I("load", "Loads a checkpoint", "Loads one file that holds the diffusion model, the text encoder and the VAE together."),
  CLIPLoader: I("load", "Loads the text encoder", "Loads the text encoder, the model that turns your words into numbers the diffusion model understands."),
  DualCLIPLoader: I("load", "Loads two text encoders", "Loads two text encoders that read your prompt together."),
  TripleCLIPLoader: I("load", "Loads three text encoders", "Loads three text encoders that read your prompt together."),
  VAELoader: I("load", "Loads the VAE", LOADV),
  LoraLoaderModelOnly: I("load", "Adds a LoRA to the model", "Patches the model with a LoRA, a small add-on trained for one style, one subject or a faster run."),
  LoraLoaderBypassModelOnly: I("load", "Adds a LoRA to the model", "Patches the model with a LoRA, a small add-on trained for one style, one subject or a faster run. This version applies it while the model runs, which saves memory."),
  LoraLoader: I("load", "Adds a LoRA", "Patches the model and text encoder with a LoRA, a small add-on trained for one style or subject."),
  LTXICLoRALoaderModelOnly: I("load", "Adds the effect LoRA", "Patches LTX with an image-conditioning LoRA trained for one edit, such as adding water or clearing a plate."),
  ModelSamplingSD3: I("plan", "Shifts the noise schedule", "Shifts the noise schedule, which gives more of the steps to the noisy start where structure forms."),
  MiniMaxH3SigmaShift: I("plan", "Shifts H3's schedule", "Shifts H3's noise schedule, separately for the video and the audio."),
  CLIPTextEncode: I("text", "Turns words into conditioning", "Runs a prompt through the text encoder. The result, called conditioning, tells the sampler what to make or avoid."),
  MiniMaxMusic3TextEncode: I("text", "Encodes style and lyrics", "Encodes the song description and the lyrics so the music model knows what to play and sing."),
  ConditioningZeroOut: I("text", "Blanks the conditioning", "Zeroes the conditioning so it can act as a neutral negative prompt."),
  LTXVConditioning: I("text", "Adds the frame rate", "Attaches the frame rate to both prompts so LTX times its motion correctly."),
  CFGGuider: I("text", "Balances the prompts", "Combines the model with the positive and negative prompts. CFG sets how hard the prompt steers each step."),
  BasicGuider: I("text", "Points the model at the prompt", "Pairs the model with one conditioning and no negative prompt, so each step simply follows the prompt."),
  MiniMaxH3ImageToVideo: I("text", "Sets up the H3 shot", "Encodes the prompt and any frames, and builds the empty H3 video and audio latent to fill."),
  MiniMaxH3ReferenceToVideo: I("text", "Feeds references to H3", "Encodes the prompt together with your reference pictures and clips, and builds the latent H3 will fill."),
  MiniMaxH3AddGuide: I("text", "Pins a keyframe", "Anchors a picture or a stretch of sound at one frame of the video, so H3 starts from it."),
  SetLatentNoiseMask: I("latent", "Marks what may change", "Tells the sampler which part of the latent to redraw. A mask of 0 keeps that part exactly as it came in."), TrimAudioDuration: I("media", "Cuts a stretch of sound", "Keeps the audio from a start time for a set number of seconds."),
  LTXAddVideoICLoRAGuide: I("text", "Feeds your clip as a guide", "Encodes the source clip and attaches it to the conditioning, so the edit follows its motion and framing."),
  WanCameraImageToVideo: I("text", "Combines frame and camera", "Combines the start frame, the prompts and the camera data into what the Wan sampler needs."),
  WanCameraEmbedding: I("plan", "Describes the camera move", "Turns a camera preset into per-frame data that tells Wan how the view should move."),
  KSamplerSelect: I("plan", "Picks the sampler", "Chooses the sampling method, the math that decides how each denoising step moves."),
  BasicScheduler: I("plan", "Plans the noise steps", "Builds the list of noise levels, the sigmas, that the sampler walks down from pure noise to a clean result."),
  Flux2Scheduler: I("plan", "Plans the noise steps", "Builds the list of noise levels for FLUX.2, adjusted for the image size."),
  ManualSigmas: I("plan", "Exact noise steps", "Sets the noise levels by hand, as tuned for this distilled model."),
  RandomNoise: I("plan", "Makes the starting noise", "Generates the starting noise from a seed. The same seed and settings give the same result."),
  LoadBackgroundRemovalModel: I("load", "Loads the cut-out model", "Loads a background removal model such as BiRefNet."), RemoveBackground: I("media", "Finds the foreground", "Makes a mask of the main subject in a picture."), InvertMask: I("media", "Flips a mask", "Swaps the masked and unmasked areas."), JoinImageWithAlpha: I("media", "Adds transparency", "Puts a mask on a picture as its alpha channel, giving a cut-out."),
  ApplyTextureToMesh: I("media", "Puts the texture on", "Wraps the baked colour picture around the mesh."), BakeAmbientOcclusion: I("media", "Bakes soft shadow", "Works out how much light reaches each part of the surface and stores it in a picture."), BakeNormalMapFromMesh: I("media", "Bakes fine detail", "Stores the detailed mesh's surface directions in a picture, so a lighter mesh still shows them."), BakeTextureFromVoxel: I("media", "Bakes the colour", "Turns the model's coloured 3D grid into pictures laid out on the mesh."), CFGOverride: I("value", "Sets the guidance", "Overrides how strongly the sampler follows its conditioning at this stage."), CLIPVisionLoader: I("load", "Loads the picture reader", "Loads the model that turns a picture into guidance."), DecimateMesh: I("media", "Lightens the mesh", "Reduces the mesh to a target number of faces."), EmptyTrellis2LatentStructure: I("value", "Starts the 3D shape", "An empty starting point for the coarse 3D structure."), GetMeshInfo: I("value", "Reports the mesh", "Passes the mesh along and reports its size."), ImageCropToMask: I("media", "Crops to the subject", "Trims the picture to the area the mask covers."), MaskPreview: I("media", "Shows the mask", "Shows the cut-out mask and passes it along."), MeshSmoothNormals: I("media", "Smooths the shading", "Evens out how light falls across the surface."), RemeshMesh: I("media", "Rebuilds the surface", "Makes a clean, even surface from the mesh."), RescaleCFG: I("value", "Steadies the guidance", "Rescales strong guidance so results keep their contrast."), Trellis2Conditioning: I("media", "Reads the picture", "Turns the picture into guidance for TRELLIS.2."), Trellis2ShapeStage: I("media", "Prepares the shape", "Sets up sampling of the detailed shape."), Trellis2TextureStage: I("media", "Prepares the colour", "Sets up sampling of the surface colour."), Trellis2UpsampleStage: I("media", "Prepares more detail", "Sets up sampling at a higher resolution."), UnwrapMesh: I("media", "Lays out the surface", "Unfolds the mesh so a flat picture can wrap around it."), VaeDecodeShapeTrellis: I("media", "Decodes the shape", "Turns the shape latent into a mesh."), VaeDecodeStructureTrellis2: I("media", "Decodes the structure", "Turns the coarse latent into a 3D grid."), VaeDecodeTextureTrellis: I("media", "Decodes the colour", "Turns the colour latent into a coloured 3D grid."),
  LoadMoGeModel: I("load", "Loads the depth model", "Loads MoGe, which estimates the shape of a scene from one picture."), MoGeInference: I("media", "Estimates geometry", "Runs MoGe on the picture."), MoGeGeometryToFOV: I("value", "Reads the lens", "Works out the camera's field of view from the estimated geometry."), SAM3_VideoTrack: I("media", "Finds the person", "SAM 3 finds and masks the subject named by the text."), SAM3DBody_Loader: I("load", "Loads SAM 3D Body", "Loads the model that turns a person in a picture into a 3D body."), SAM3DBody_Predict: I("media", "Builds the 3D body", "Estimates the body's shape and pose."), SAM3DBody_FaceExpression: I("media", "Adds the expression", "Estimates the face's expression for the 3D body."), SAM3DBody_Render: I("media", "Renders the body", "Draws the 3D body to a picture for checking."), BuildPoseFile: I("save", "Builds the rigged file", "Packs the body and pose into a file with a skeleton."), SaveGLB: I("save", "Saves a 3D file", "Writes a .glb file to the output folder."),
  EmptyLatentImage: I("latent", "Blank latent canvas", EMPTY), EmptySD3LatentImage: I("latent", "Blank latent canvas", EMPTY), EmptyFlux2LatentImage: I("latent", "Blank latent canvas", EMPTY), EmptyLTXVLatentVideo: I("latent", "Blank video latent", EMPTY),
  LTXVEmptyLatentAudio: I("latent", "Blank audio latent", "Creates an empty audio latent the same length as the video, so LTX generates sound with it."),
  EmptyMiniMaxMusic3LatentAudio: I("latent", "Blank song latent", "Creates an empty audio latent as long as the song."),
  Wan22ImageToVideoLatent: I("latent", "Starts from your image", "Encodes the start image and makes the empty video latent that grows from it."),
  LTXVConcatAVLatent: I("latent", "Joins video and audio", "Packs the video and audio latents together so both are denoised as one."),
  LTXVSeparateAVLatent: I("latent", "Splits video and audio", "Separates the finished latent back into its video and audio parts."),
  LTXVImgToVideoInplace: I("latent", "Places your image", "Writes the encoded start image into the first frame of the video latent."),
  LTXVCropGuides: I("latent", "Removes the guide frames", "Cuts the guide frames back out of the latent before decoding."),
  LTXVLatentUpsampler: I("latent", "Doubles the picture's size", "Upscales the latent two times before the short second pass of LTX."),
  LatentUpscaleModelLoader: I("loader", "Loads the upscaler", "Reads the model that doubles a latent's size."),
  SamplerCustomAdvanced: I("sample", "The sampler: makes the result", "Where the result actually forms. It starts from noise and removes a little at every step, guided by your prompt."),
  KSampler: I("sample", "The sampler: makes the result", "Where the result actually forms. It starts from noise and removes a little at every step, guided by your prompt."),
  KSamplerAdvanced: I("sample", "One stage of sampling", "Runs a chosen range of denoising steps, so one model can hand off to another partway through."),
  VAEDecode: I("decode", "Turns latents into pixels", DEC),
  VAEDecodeTiled: I("decode", "Turns latents into pixels", "Same as VAE decode, but in overlapping tiles and chunks so long video fits in memory."),
  VAEDecodeAudio: I("decode", "Turns latents into sound", DECA), VAEDecodeAudioTiled: I("decode", "Turns latents into sound", DECA), LTXVAudioVAEDecode: I("decode", "Turns latents into sound", DECA),
  VAEEncode: I("decode", "Turns pixels into a latent", "Uses the VAE to compress an image into the latent space the model works in."),
  LoadImage: I("media", "Loads your picture", "Loads a picture you uploaded from ComfyUI's input folder."),
  LoadVideo: I("media", "Loads your clip", "Loads a clip you uploaded from ComfyUI's input folder."),
  "Video Slice": I("media", "Cuts the clip to length", "Cuts the source clip down to the part this shot will use."),
  GetVideoComponents: I("media", "Splits frames and sound", "Splits a clip into its frames, its sound and its frame rate."),
  PSN_FPSResampler: I("media", "Converts to 24 fps", "This studio's own node: resamples the frames to the rate the model expects."),
  ImageFromBatch: I("media", "Picks a run of frames", "Takes the frames the shot needs from a longer batch."),
  ImageScale: I("media", "Resizes the frames", "Resizes and crops the frames to the size the model will work at."),
  LTXVPreprocess: I("media", "Prepares the start image", "Applies light compression to the start image so the model treats it like a video frame."),
  CreateVideo: I("media", "Joins frames and sound", "Combines the decoded frames, and sound if any, into one video at the set frame rate."),
  SaveImage: I("save", "Saves the result", SAVE), SaveVideo: I("save", "Saves the result", SAVE), SaveAudio: I("save", "Saves the result", SAVE), SaveAudioAdvanced: I("save", "Saves the result", SAVE), PreviewImage: I("save", "Shows a preview", "Shows the image in ComfyUI without keeping it in the output folder."),
  VRAM_Debug: I("value", "Frees GPU memory", "Unloads the text encoder and clears the GPU cache before sampling, so the big model fits."),
  ComfySwitchNode: I("value", "Chooses one of two inputs", "Passes on one input or the other. A setting in the studio flips it."),
  PrimitiveInt: I("value", "A whole number", "Holds one whole number that other nodes read."),
  PrimitiveFloat: I("value", "A number", "Holds one number that other nodes read."),
  PrimitiveBoolean: I("value", "On or off", "Holds one on or off value that other nodes read."),
  ComfyMathExpression: I("value", "Calculates a value", "Works out a value from its inputs with a small formula."),
  ResolutionSelector: I("value", "Picks width and height", "Works out the width and height from an aspect ratio and a megapixel budget."),
  LTXFloatToInt: I("value", "Converts a number", "Rounds a decimal number to a whole one for the next node."),
  SeedNode: I("value", "Holds the seed", "Holds the seed that the other nodes share, so the run can be repeated."),
  /* the graphs in workflows/ and studio/family_templates/ that had no note; each line was checked against the node's own source */
  SamplerCustom: I("sample", "Removes the noise", "Runs the sampler with a sampler, a list of noise levels and a guidance strength you wire in, instead of KSampler's fixed set."),
  SamplerLCM: I("plan", "Picks the LCM sampler", "Chooses the LCM sampler, made for models distilled to work in very few steps."),
  DualModelGuider: I("plan", "Guides with two models", "Classifier-free guidance where the positive pass and the negative pass can run on different models."),
  FluxGuidance: I("plan", "Sets FLUX's guidance", "Writes the guidance strength FLUX dev was distilled with into the prompt, in place of ordinary CFG."),
  SkipLayerGuidanceDiTSimple: I("plan", "Sharpens with skipped layers", "Skip-layer guidance: runs extra passes with some of the model's layers skipped, and steers away from them to firm up structure."),
  VideoLinearCFGGuidance: I("plan", "Ramps guidance across frames", "Raises guidance from a minimum on the first frame to the full value on the last, as Stable Video Diffusion expects."),
  ModelNoiseScale: I("plan", "Sets the model's noise scale", "Tells the model which noise scale it was trained with (HiDream-O1 base uses 8.0, dev 7.5)."),
  ContextWindowsManual: I("plan", "Splits a long video into windows", "Samples a long video in overlapping windows of frames and blends the overlaps, so it fits in memory."),
  HiDreamO1PatchSeamSmoothing: I("plan", "Smooths patch seams", "Late in sampling, averages the model's output over shifted patch grids so the grid seams cancel out."),
  Ideogram4Scheduler: I("plan", "Plans the noise steps", "Works out the noise level for each step from the step count and the picture size, the way Ideogram 4 was trained."),
  LTXVScheduler: I("plan", "Plans the noise steps", "Works out LTX's noise level for each step, shifted for the length and size of the video."),
  ImageOnlyCheckpointLoader: I("load", "Loads the video model", "Loads a checkpoint that holds the model, a CLIP vision encoder and the VAE, as Stable Video Diffusion ships."),
  UpscaleModelLoader: I("load", "Loads the upscaler", "Loads an upscale model such as Real-ESRGAN from the upscale_models folder."),
  ControlNetLoader: I("load", "Loads a ControlNet", "Loads a ControlNet, the extra network that makes the picture follow a pose, depth map or edges."),
  ModelPatchLoader: I("load", "Loads a model patch", "Loads extra weights that patch into the main model, here InfiniteTalk's audio layers."),
  FrameInterpolationModelLoader: I("load", "Loads the frame interpolator", "Loads a frame interpolation model such as RIFE, which invents the frames between the ones you have."),
  IPAdapterModelLoader: I("load", "Loads the IP-Adapter", "Loads an IP-Adapter, which lets a reference picture steer the result the way a prompt does."),
  IPAdapterSD3Loader: I("load", "Loads the SD3 IP-Adapter", "Loads InstantX's IP-Adapter for SD 3.5 Large, so a reference picture can steer the result."),
  ADE_AnimateDiffLoaderGen1: I("load", "Adds AnimateDiff motion", "AnimateDiff-Evolved. Puts a motion module into an SD 1.5 model so it makes short clips instead of single pictures."),
  ADE_StandardStaticContextOptions: I("plan", "Splits frames into windows", "AnimateDiff-Evolved. Sets how many frames the motion module sees at once and how much the windows overlap."),
  DownloadAndLoadKolorsModel: I("load", "Loads Kolors", "Kijai's Kolors wrapper. Loads the Kolors diffusion model, downloading it the first time."),
  DownloadAndLoadChatGLM3: I("load", "Loads Kolors' text model", "Kijai's Kolors wrapper. Loads ChatGLM3, the language model Kolors reads prompts with."),
  KolorsTextEncode: I("text", "Reads your prompt", "Kijai's Kolors wrapper. Turns the prompt and negative prompt into what Kolors follows, through ChatGLM3."),
  KolorsSampler: I("sample", "Makes the picture", "Kijai's Kolors wrapper. Removes the noise step by step to make the latent picture."),
  IrisModelLoader: I("load", "Loads Iris-3B", "Loads the Iris-3B image model, from the Iris-3B community nodes."),
  IrisTextEncoderLoader: I("load", "Loads Iris's text model", "Loads the text encoder Iris-3B reads prompts with."),
  IrisTextEncode: I("text", "Reads your prompt", "Turns the prompt into what Iris-3B follows."),
  IrisSamplerAdvanced: I("sample", "Makes the picture", "Iris-3B's sampler with exact size and solver settings. It removes the noise and hands back the finished picture."),
  HYMotionDiTLoader: I("load", "Loads HY-Motion", "Loads HY-Motion, a model that turns words into a 3D body movement."),
  HYMotionTextEncoderLoader: I("load", "Loads HY-Motion's text model", "Loads the text encoders HY-Motion reads the movement description with."),
  HYMotionTextEncode: I("text", "Reads the movement", "Turns your description of the movement into what HY-Motion follows."),
  HYMotionSampler: I("sample", "Makes the movement", "Removes the noise step by step to make the body motion: joint positions over time, not pixels."),
  HYMotionPreview2D: I("save", "Draws the movement", "Draws the motion as a stick figure so you can watch it without a 3D viewer."),
  LoadAndApplyICLightUnet: I("load", "Adds IC-Light", "Kijai's IC-Light nodes. Patches IC-Light's relighting weights into an SD 1.5 model."),
  ICLightConditioning: I("text", "Joins the picture to the prompt", "Kijai's IC-Light nodes. Attaches the foreground picture's latent to the prompt, so IC-Light relights that picture."),
  LightSource: I("media", "Draws the light", "Gaffer nodes. Draws a gradient from one side as a simple light source for IC-Light to follow."),
  LoadControlFoleyModel: I("load", "Loads ControlFoley", "Loads ControlFoley, a model that makes sound effects to match a video."),
  LoadControlFoleyVideo: I("media", "Loads the video", "Loads the clip ControlFoley will make sound for."),
  ControlFoleyGenerate: I("sample", "Makes the sound", "Makes sound that follows what happens in the video, steered by your prompt."),
  SaveControlFoleyAudio: I("save", "Saves the sound", "Writes the sound ControlFoley made to the output folder."),
  UnloadControlFoleyModel: I("other", "Frees the memory", "Unloads ControlFoley from the GPU when the sound is done."),
  LTXVDrawTracks: I("media", "Draws the motion tracks", "Lightricks' LTXVideo nodes. Draws the paths you set as dots on each frame, for LTX to follow as a motion guide."),
  LTXVLoadConditioning: I("text", "Loads a saved prompt", "Lightricks' LTXVideo nodes. Loads text conditioning computed ahead of time, here the one the HDR IC-LoRA expects."),
  LTXVVAEForceFloat32: I("load", "Keeps the VAE at full precision", "Lightricks' LTXVideo nodes. Makes the video VAE work in 32-bit floats, which HDR needs."),
  LTXVHDRDecodePostprocess: I("decode", "Recovers the HDR", "Lightricks' LTXVideo nodes. Expands the decoded frames back to high dynamic range and tone-maps a copy you can preview."),
  ImageColorSpace: I("media", "Converts the colour space", "Converts frames between sRGB, linear and HDR colour spaces such as Rec.2020 PQ, ACEScg and LogC3."),
  SaveImageAdvanced: I("save", "Saves the frames", "Saves pictures to the output folder, with more choices of file format than Save Image."),
  Save3DAdvanced: I("save", "Saves the 3D model", "Writes the 3D model to the output folder."),
  MeshToFile3D: I("media", "Makes a 3D file", "Packs the mesh into a GLB file that the save and preview nodes can read."),
  ReferenceLatent: I("text", "Attaches a reference picture", "Adds a picture's latent to the prompt, so the model edits or copies from that picture."),
  CLIPVisionEncode: I("text", "Reads a picture", "Uses a CLIP vision model to turn a picture into numbers the model can follow, the way a text encoder reads words."),
  unCLIPConditioning: I("text", "Adds a picture to the prompt", "Mixes a CLIP vision reading of a picture into the prompt, so the result takes after that picture."),
  InstructPixToPixConditioning: I("text", "Joins the picture to the edit", "Attaches the picture to the edit instruction, so InstructPix2Pix changes that picture as told."),
  ControlNetApplyAdvanced: I("text", "Applies the ControlNet", "Adds the control picture (pose, depth or edges) to both prompts, with a strength and the part of sampling it acts on."),
  IPAdapterAdvanced: I("plan", "Applies the IP-Adapter", "Cubiq's IPAdapter Plus. Patches the model so the reference picture steers the result, with a weight and a time range."),
  ApplyIPAdapterSD3: I("plan", "Applies the SD3 IP-Adapter", "Patches SD 3.5 Large so the reference picture steers the result."),
  TextEncodeBooguEdit: I("text", "Reads the edit", "Turns the edit instruction and the input pictures into the positive and negative prompts for Boogu's editor."),
  TextEncodeFibo2: I("text", "Reads your prompt", "Encodes a FIBO 2 prompt, plain words or a structured JSON caption. With pictures, the prompt is the edit."),
  Ideogram4PromptBuilderKJ: I("text", "Builds the layout prompt", "KJNodes. Builds Ideogram 4's JSON caption from regions you draw, each with its own text, description and colours."),
  StableCascade_StageB_Conditioning: I("text", "Passes stage C to stage B", "Hands the small latent Stable Cascade's stage C made to stage B as part of its prompt."),
  SVD_img2vid_Conditioning: I("text", "Sets up the clip", "Turns the start picture into Stable Video Diffusion's conditioning, with the size, length, motion amount and frame rate."),
  WanImageToVideo: I("latent", "Starts from your picture", "Makes Wan's empty video latent and ties its first frame to your picture."),
  WanInfiniteTalkToVideo: I("latent", "Ties the video to the voice", "Sets up Wan with InfiniteTalk so the person's lips and head follow the audio."),
  WanSCAILToVideo: I("latent", "Sets up the pose transfer", "Sets up Wan for SCAIL, which makes the character in your picture follow the poses of another video."),
  WanAnimate2ToVideo: I("latent", "Sets up the animation", "Sets up Wan Animate to move the character in your picture with the face, body and hands of a driving video."),
  WanAnimate2Cache: I("plan", "Caches the pose video", "Keeps the pose video's activations in RAM so they are worked out once instead of on every step. About twice as fast, at the cost of system memory."),
  WanDancerVideo: I("latent", "Sets up the dance", "Sets up WanDancer, which makes a person dance to the music from a start picture."),
  WanDancerEncodeAudio: I("text", "Reads the music", "Turns the song into features WanDancer dances to, and works out the frame rate from its length."),
  WanDancerPadKeyframesList: I("media", "Splits the song into segments", "Pads the key frames to whole segments and cuts the audio to match, one list entry per segment."),
  AudioEncoderEncode: I("text", "Reads the audio", "Runs the audio through an audio encoder, so a video model can follow the voice or the beat."),
  SCAIL2ColoredMask: I("media", "Colours each person", "Gives each tracked person their own colour mask, so SCAIL-2 knows who is who."),
  SAM3DBody_Smooth: I("other", "Smooths the captured pose", "Reduces frame-to-frame jitter in the 3D body pose captured from video."),
  EmptyHunyuanLatentVideo: I("latent", "Sets the clip's size", "Makes the empty video latent at your width, height and length. Wan uses the same shape."),
  EmptyHunyuanImageLatent: I("latent", "Sets the picture's size", "Makes the empty latent Hunyuan Image fills, at the width and height you asked for."),
  EmptyMochiLatentVideo: I("latent", "Sets the clip's size", "Makes the empty video latent Mochi fills, at your width, height and length."),
  EmptyHiDreamO1LatentImage: I("latent", "Sets the picture's size", "Makes the empty canvas HiDream-O1 fills. It works in pixels, and was trained at about 4 megapixels."),
  StableCascade_EmptyLatentImage: I("latent", "Sets the picture's size", "Makes the two small empty latents Stable Cascade's stage C and stage B fill."),
  TrimVideoLatent: I("latent", "Trims the start of the clip", "Cuts frames off the start of a video latent, such as the reference frames the model was given."),
  LatentCutToBatch: I("latent", "Cuts a latent into pieces", "Slices a latent along time, width or height and stacks the pieces as a batch."),
  ImageUpscaleWithModel: I("media", "Upscales the picture", "Runs the picture through the upscale model to make it larger and sharper."),
  ImageScaleToTotalPixels: I("media", "Resizes to a pixel budget", "Resizes the picture to about the number of megapixels you set, keeping its shape."),
  GetImageSize: I("value", "Reads the picture's size", "Hands on the picture's width, height and frame count for other nodes to use."),
  MaskToImage: I("media", "Shows the mask as a picture", "Turns a mask into a black and white picture you can save or preview."),
  BatchImagesNode: I("media", "Joins pictures into a batch", "Puts several pictures into one batch, one after the other."),
  RebatchImages: I("media", "Regroups the frames", "Splits or joins batches of pictures into batches of the size you set."),
  FrameInterpolate: I("media", "Adds in-between frames", "Invents the frames between each pair you have, for smoother or slower motion."),
  GFPGANRestorer: I("media", "Restores faces", "Runs GFPGAN over the picture to repair blurred or damaged faces."),
  CCSR_Model_Select: I("load", "Loads CCSR", "Kijai's CCSR nodes. Loads the CCSR upscaler, a diffusion model that adds detail as it enlarges."),
  CCSR_Upscale: I("sample", "Upscales with diffusion", "Kijai's CCSR nodes. Enlarges the picture and adds believable detail with CCSR's diffusion steps."),
  WanVideoUniAnimateDWPoseDetector: I("media", "Finds the pose", "Detects body, hand and face keypoints with DWPose and draws them as a stick figure."),
  LivePortraitLoadCropper: I("load", "Loads the face finder", "Kijai's LivePortrait nodes. Loads the face detector that crops the face to animate."),
  DownloadAndLoadLivePortraitModels: I("load", "Loads LivePortrait", "Kijai's LivePortrait nodes. Loads LivePortrait's models, downloading them the first time."),
  LivePortraitCropper: I("media", "Crops the face", "Kijai's LivePortrait nodes. Finds and crops the face in the portrait."),
  LivePortraitProcess: I("media", "Moves the face", "Kijai's LivePortrait nodes. Moves the portrait's face to follow the expressions of the driving video."),
  LivePortraitComposite: I("media", "Puts the face back", "Kijai's LivePortrait nodes. Pastes the animated face back into the full picture."),
  TextGenerate: I("text", "Writes text", "Runs a language model on your prompt, and on a picture, video or sound if given, and hands back the text it writes."),
  TrimAudioDuration: I("media", "Trims the audio", "Cuts the audio to a start time and length."),
  StringConcatenate: I("value", "Joins text", "Joins two pieces of text into one."),
  StringReplace: I("value", "Replaces text", "Replaces every match of a piece of text with another."),
  RegexExtract: I("value", "Pulls out text", "Finds text that matches a pattern and hands it on."),
  CustomCombo: I("value", "Picks from a list", "Offers a list of choices and hands on the one picked and its position."),
  PSN_CameraPathEmbedding: I("plan", "Turns your camera path into Wan's", "Our node. Turns the camera path drawn on the Camera Paths page into Wan 2.2 Fun Camera conditioning."),
  PSN_VAELoaderChannels: I("load", "Loads a VAE of any channel count", "Our node. Loads a VAE that isn't 3-channel colour, such as LDM3D's colour-plus-depth VAE, reading its layout from the weights."),
  PSN_RGBDSplit: I("media", "Splits colour from depth", "Our node. Splits a 4-channel result into a colour picture and a depth map."),
  ConditioningLoader: I("text", "Loads a saved prompt", "Loads conditioning saved ahead of time from the embeddings folder, in place of reading a prompt now."),
  DisableNoise: I("plan", "Starts with no added noise", "Hands the sampler zero noise, so it works from the input latent as it is."),
  WanVideoModelLoader: I("load", "Loads the video model", "Kijai's WanVideoWrapper. Loads a Wan-family video model, here LongCat-Avatar, with its LoRA and block-swap settings."),
  WanVideoLoraSelect: I("load", "Picks a LoRA", "Kijai's WanVideoWrapper. Picks a LoRA and its strength for the model loader, here the distilled LoRA that lets LongCat-Avatar work in few steps."),
  WanVideoBlockSwap: I("plan", "Saves GPU memory", "Kijai's WanVideoWrapper. Keeps some of the model's transformer blocks in system RAM and swaps them in as needed, so a big model fits a smaller card."),
  WanVideoVAELoader: I("load", "Loads the VAE", "Kijai's WanVideoWrapper. Loads the Wan VAE, which translates between frames and the latent space where the model works."),
  WanVideoTextEncodeCached: I("text", "Reads your prompt", "Kijai's WanVideoWrapper. Loads the T5 text encoder, turns the prompt and negative prompt into what the model follows, then unloads it."),
  WanVideoEncode: I("latent", "Encodes your picture", "Kijai's WanVideoWrapper. Uses the VAE to turn the portrait into latents the video starts from."),
  WhisperModelLoader: I("load", "Loads Whisper", "Kijai's WanVideoWrapper. Loads the Whisper audio encoder from the audio_encoders folder."),
  LongCatAvatarWhisperEmbeds: I("text", "Reads the voice", "Kijai's WanVideoWrapper. Runs the voice through Whisper, after levelling its loudness, so the avatar's lips follow it frame by frame."),
  WanVideoLongCatAvatarExtendEmbeds: I("latent", "Ties picture and voice together", "Kijai's WanVideoWrapper. Joins the portrait's latents and the voice features into what LongCat-Avatar samples, and can continue an earlier clip."),
  WanVideoSchedulerv2: I("plan", "Plans the noise steps", "Kijai's WanVideoWrapper. Sets the scheduler, the number of steps and the shift for the sampler."),
  WanVideoSamplerv2: I("sample", "Makes the video", "Kijai's WanVideoWrapper. Removes the noise step by step to make the talking video's latents."),
  WanVideoDecode: I("decode", "Turns latents into frames", "Kijai's WanVideoWrapper. Uses the Wan VAE to turn the finished latents into frames."),
  Krea2EditModelPatch: I("plan", "Shows the model your pictures", "lbouaraba's Krea2Edit nodes. Feeds the scene and the subject picture to Krea 2 as clean reference tokens beside the picture being made, as the identity-edit LoRA was trained, with a dial for how closely to follow each."),
  Krea2EditGroundedEncode: I("text", "Reads the edit while looking", "lbouaraba's Krea2Edit nodes. Shows the pictures to the Qwen3-VL text encoder along with the instruction, so it reads the edit knowing what is in them."),
  MarigoldV2PostProcess: I("media", "Turns the prediction into a picture", "Turns Marigold V2's decoded prediction into a picture: depth with near as bright, surface normals, or albedo colour."),
};
export const KIND_LABEL = { load: "Loader", text: "Prompt", latent: "Latent", plan: "Setting", sample: "Sampler", decode: "Decode", media: "Media", value: "Value", save: "Output", other: "Node" };
export const KIND_COLOR = { load: "#f5c518", text: "#ffe07a", latent: "#27e07f", plan: "#d8c25a", sample: "#ffc81f", decode: "#46e88f", media: "#7dffb8", value: "#a7ad8a", save: "#27e07f", other: "#c9cfb4" };
export function explain(cls) {
  const k = CLASS_INFO[cls]; if (k) return { ...k, known: true };
  const c = String(cls || ""), kind = /load/i.test(c) ? "load" : /sampler/i.test(c) ? "sample" : /save|preview/i.test(c) ? "save" : /decode/i.test(c) ? "decode" : /encode|condition|guider/i.test(c) ? "text" : /latent/i.test(c) ? "latent" : /primitive|switch|math/i.test(c) ? "value" : /image|video|audio/i.test(c) ? "media" : "other";
  return { kind, short: "", say: c, known: false };
}
/* ---------- wire types, gold for what steers the run, green for what it makes ---------- */
export const TYPE_COLOR = { MODEL: "#f5c518", CLIP: "#ffd866", VAE: "#e0a020", CONDITIONING: "#ffeca0", GUIDER: "#e9d850", NOISE: "#c7e24a", SAMPLER: "#cfc56a", SIGMAS: "#cfc56a", LATENT: "#27e07f", IMAGE: "#7dffb8", VIDEO: "#7dffb8", AUDIO: "#46e6c4", NUMBER: "#98a07c", BOOL: "#98a07c", ANY: "#98a07c" };
const OUT_TYPES = { UNETLoader: ["MODEL"], CheckpointLoaderSimple: ["MODEL", "CLIP", "VAE"], CLIPLoader: ["CLIP"], DualCLIPLoader: ["CLIP"], VAELoader: ["VAE"], LoraLoaderModelOnly: ["MODEL"], LTXICLoRALoaderModelOnly: ["MODEL", "NUMBER"], ModelSamplingSD3: ["MODEL"], MiniMaxH3SigmaShift: ["MODEL"], CLIPTextEncode: ["CONDITIONING"], ConditioningZeroOut: ["CONDITIONING"], LTXVConditioning: ["CONDITIONING", "CONDITIONING"], CFGGuider: ["GUIDER"], BasicGuider: ["GUIDER"], KSamplerSelect: ["SAMPLER"], BasicScheduler: ["SIGMAS"], Flux2Scheduler: ["SIGMAS"], ManualSigmas: ["SIGMAS"], RandomNoise: ["NOISE"], SamplerCustomAdvanced: ["LATENT", "LATENT"], KSampler: ["LATENT"], KSamplerAdvanced: ["LATENT"], VAEDecode: ["IMAGE"], VAEDecodeTiled: ["IMAGE"], VAEDecodeAudio: ["AUDIO"], VAEDecodeAudioTiled: ["AUDIO"], LTXVAudioVAEDecode: ["AUDIO"], LoadImage: ["IMAGE", "MASK"], LoadVideo: ["VIDEO"], "Video Slice": ["VIDEO"], GetVideoComponents: ["IMAGE", "AUDIO", "NUMBER"], ImageFromBatch: ["IMAGE"], ImageScale: ["IMAGE"], PSN_FPSResampler: ["IMAGE"], CreateVideo: ["VIDEO"], PrimitiveInt: ["NUMBER"], PrimitiveFloat: ["NUMBER"], PrimitiveBoolean: ["BOOL"], ComfyMathExpression: ["NUMBER", "NUMBER"], ResolutionSelector: ["NUMBER", "NUMBER"], LTXFloatToInt: ["NUMBER"], SeedNode: ["NUMBER"], MiniMaxH3ImageToVideo: ["CONDITIONING", "LATENT"], MiniMaxH3ReferenceToVideo: ["CONDITIONING", "LATENT"], LTXVConcatAVLatent: ["LATENT"], LTXVSeparateAVLatent: ["LATENT", "LATENT"], LTXVEmptyLatentAudio: ["LATENT"], EmptyLatentImage: ["LATENT"], EmptyFlux2LatentImage: ["LATENT"], EmptyLTXVLatentVideo: ["LATENT"], EmptyMiniMaxMusic3LatentAudio: ["LATENT"], Wan22ImageToVideoLatent: ["LATENT"], LTXVImgToVideoInplace: ["LATENT"], LTXAddVideoICLoRAGuide: ["CONDITIONING", "CONDITIONING", "LATENT"], LTXVCropGuides: ["CONDITIONING", "CONDITIONING", "LATENT"], LTXVPreprocess: ["IMAGE"], WanCameraEmbedding: ["CAMERA", "NUMBER", "NUMBER", "NUMBER"], WanCameraImageToVideo: ["CONDITIONING", "CONDITIONING", "LATENT"], MiniMaxMusic3TextEncode: ["CONDITIONING", "NUMBER"] };
const PASS_THROUGH = { ComfySwitchNode: ["on_true", "on_false"], VRAM_Debug: ["any_input"] };
export function keyType(key) {
  const k = String(key).toLowerCase();
  if (k === "model") return "MODEL"; if (k === "clip") return "CLIP"; if (/vae/.test(k)) return "VAE"; if (/^(positive|negative|conditioning)$/.test(k)) return "CONDITIONING"; if (k === "guider") return "GUIDER"; if (k === "noise") return "NOISE"; if (k === "sampler") return "SAMPLER"; if (k === "sigmas") return "SIGMAS";
  if (/latent|^samples$/.test(k)) return "LATENT"; if (/image|frame|pixels/.test(k)) return "IMAGE"; if (/video/.test(k)) return "VIDEO"; if (/audio/.test(k)) return "AUDIO"; if (/^switch$/.test(k)) return "BOOL"; if (/^(width|height|length|steps|fps|frame_rate|seed|value|seconds|source_fps|values\.)/.test(k)) return "NUMBER";
  return null;
}
const isLink = (v, graph) => Array.isArray(v) && v.length === 2 && typeof v[1] === "number" && graph[String(v[0])] != null;
const WIDGET_RANK = [/^(text|prompt|caption|lyrics)$/, /(unet|clip|vae|lora|ckpt)_name/, /^(file|image)$/, /seed/, /^steps$/, /^cfg$/, /sampler_name/, /^scheduler$/, /^(width|height|length|frames_number)$/, /^value$/, /aspect|megapixels|expression|camera_pose/, /strength|shift|sigmas|fps|frame_rate|denoise/];
const rank = (k) => { const i = WIDGET_RANK.findIndex((r) => r.test(k)); return i < 0 ? 99 : i; };
export const isLongText = (w) => /^(text|prompt|caption|lyrics|expression)$/.test(w.key);
export const fileBase = (s) => String(s).split(/[\\/]/).pop();
export function formatValue(v) { if (v === null || v === undefined) return ""; if (typeof v === "number") return Number.isInteger(v) ? String(v) : String(+v.toFixed(4)); if (typeof v === "boolean") return v ? "on" : "off"; if (typeof v === "object") return JSON.stringify(v); const s = String(v); return /\.(safetensors|ckpt|pt|pth|gguf|bin|onnx)$/.test(s) ? fileBase(s) : s; }
/** The graph as nodes and links: every link knows its source slot, target input and data type. Links to missing nodes are widgets, as ComfyUI would reject them anyway. */
export function buildModel(graph) {
  const g = graph || {}, ids = Object.keys(g), nodes = {}, links = [];
  ids.forEach((id) => { const n = g[id] || {}; nodes[id] = { id, cls: n.class_type || "Node", info: explain(n.class_type), inputs: [], widgets: [], outs: {}, depth: 0, col: 0, y: 0 }; });
  ids.forEach((id) => Object.entries((g[id] || {}).inputs || {}).forEach(([key, v]) => { if (isLink(v, g)) { const l = { id: links.length, from: String(v[0]), slot: v[1], to: id, key, type: "ANY" }; links.push(l); nodes[id].inputs.push(l); } else nodes[id].widgets.push({ key, value: v }); }));
  const seen = {}; const outType = (id, slot) => { const c = id + ":" + slot; if (seen[c]) return seen[c] === 1 ? "ANY" : seen[c]; seen[c] = 1; const n = nodes[id]; let t = (OUT_TYPES[n.cls] || [])[slot]; if (!t && PASS_THROUGH[n.cls]) { const k = n.inputs.find((l) => PASS_THROUGH[n.cls].includes(l.key)); if (k) t = outType(k.from, k.slot); } if (!t) { const l = links.find((x) => x.from === id && x.slot === slot && keyType(x.key)); t = l ? keyType(l.key) : "ANY"; } seen[c] = t; return t; };
  links.forEach((l) => { l.type = TYPE_COLOR[outType(l.from, l.slot)] ? outType(l.from, l.slot) : keyType(l.key) || "ANY"; const o = nodes[l.from].outs; (o[l.slot] ||= { type: l.type, to: [] }).to.push(l); });
  ids.forEach((id) => nodes[id].widgets.sort((a, b) => rank(a.key) - rank(b.key)));
  // longest path from any source; a cycle cannot loop forever (ComfyUI would reject it)
  const memo = {}; const dep = (id, st = new Set()) => { if (memo[id] != null) return memo[id]; if (st.has(id)) return 0; st.add(id); let d = 0; nodes[id].inputs.forEach((l) => { d = Math.max(d, dep(l.from, st) + 1); }); st.delete(id); return (memo[id] = d); };
  ids.forEach((id) => { nodes[id].depth = dep(id); });
  return { ids, nodes, links };
}
/* ---------- panel metrics, shared by the layout and the canvas that paints each panel ---------- */
export const PANEL = { rowH: 0.2, wrowH: 0.19, lineH: 0.165, foot: 0.12 };
export function panelSize(n) {
  const k = n.info.kind, w = k === "sample" ? 4.5 : k === "save" ? 3.9 : k === "value" ? 2.9 : 3.6, head = k === "value" ? 0.66 : k === "sample" ? 1.16 : 1.02;
  const rows = Math.min(8, Math.max(n.inputs.length, Object.keys(n.outs).length, 1)), shown = n.widgets.filter((x) => formatValue(x.value) !== "" && !/^(batch_size|weight_dtype|device|strict_duration|format|codec|start_time|bypass|multiple)$/.test(x.key)).slice(0, k === "value" ? 2 : 3);
  let wh = 0; shown.forEach((x) => { wh += isLongText(x) ? PANEL.lineH * 3 + 0.05 : PANEL.wrowH; });
  return { w, h: head + rows * PANEL.rowH + (wh ? 0.07 + wh : 0) + PANEL.foot, head, rows, shown, wh, rad: 0.11 };
}
/* ---------- columns: left to right by dependency, sources pulled up next to whatever first needs them, no column far taller than the rest ---------- */
function assignColumns(m) {
  const { ids, nodes, links } = m, consumers = {}; ids.forEach((i) => { consumers[i] = []; }); links.forEach((l) => consumers[l.from].push(l.to));
  const order = [...ids].sort((a, b) => nodes[b].depth - nodes[a].depth);
  order.forEach((id) => { const c = consumers[id]; nodes[id].col = c.length ? Math.min(...c.map((x) => nodes[x].col)) - 1 : nodes[id].depth; });
  const span = () => { const v = ids.map((i) => nodes[i].col); return [Math.min(...v, 0), Math.max(...v, 0)]; };
  const H = (id) => panelSize(nodes[id]).h + 0.5, total = ids.reduce((a, i) => a + H(i), 0), [lo0, hi0] = span(), cap = Math.max(7.5, (1.5 * total) / Math.max(1, hi0 - lo0 + 1));
  for (let c = hi0; c >= lo0; c--) { for (let guard = 0; guard < 30; guard++) { const here = ids.filter((i) => nodes[i].col === c), h = here.reduce((a, i) => a + H(i), 0); if (h <= cap || c <= lo0 && lo0 <= hi0 - 8) break; const mv = here.filter((i) => nodes[i].inputs.every((l) => nodes[l.from].col < c - 1)).sort((a, b) => H(a) - H(b) || a.localeCompare(b))[0]; if (!mv) break; nodes[mv].col = c - 1; } }
  const low = span()[0]; ids.forEach((i) => { nodes[i].col -= low; });
}
/* least-squares positions that keep the order and the gaps (pool adjacent violators) */
export function placeOrdered(want, heights, gap) {
  const n = want.length, off = [0]; for (let i = 1; i < n; i++) off[i] = off[i - 1] + (heights[i - 1] + heights[i]) / 2 + gap;
  const blocks = []; for (let i = 0; i < n; i++) { blocks.push({ s: want[i] - off[i], w: 1, n: 1 }); while (blocks.length > 1 && blocks[blocks.length - 2].s > blocks[blocks.length - 1].s) { const b = blocks.pop(), a = blocks.pop(); blocks.push({ s: (a.s * a.w + b.s * b.w) / (a.w + b.w), w: a.w + b.w, n: a.n + b.n }); } }
  const out = []; let i = 0; blocks.forEach((b) => { for (let k = 0; k < b.n; k++, i++) out.push(b.s + off[i]); }); return out;
}
function assignRows(m, gap) {
  const { ids, nodes, links } = m, maxCol = Math.max(0, ...ids.map((i) => nodes[i].col)), cols = Array.from({ length: maxCol + 1 }, () => []);
  ids.forEach((i) => cols[nodes[i].col].push(i)); const adj = {}; ids.forEach((i) => { adj[i] = []; }); links.forEach((l) => { const w = 1 / Math.max(1, nodes[l.to].col - nodes[l.from].col); adj[l.from].push([l.to, w]); adj[l.to].push([l.from, w]); });
  const sized = {}; ids.forEach((i) => { sized[i] = panelSize(nodes[i]); });
  cols.forEach((c) => { let y = 0; c.forEach((i) => { nodes[i].y = y; y += sized[i].h + gap; }); const mid = y / 2; c.forEach((i) => { nodes[i].y -= mid; }); });
  for (let it = 0; it < 14; it++) {
    const seq = it % 2 ? cols : [...cols].reverse();
    seq.forEach((c) => {
      if (!c.length) return; c.forEach((i) => { const a = adj[i], sw = a.reduce((s, x) => s + x[1], 0); nodes[i].want = sw ? a.reduce((s, [o, w]) => s + nodes[o].y * w, 0) / sw : nodes[i].y; });
      if (it < 10) c.sort((p, q) => nodes[p].want - nodes[q].want);
      const ys = placeOrdered(c.map((i) => nodes[i].want), c.map((i) => sized[i].h), gap); c.forEach((i, k) => { nodes[i].y = ys[k]; });
    });
  }
  const all = ids.map((i) => nodes[i]), top = Math.min(...all.map((n) => n.y - sized[n.id].h / 2)), bot = Math.max(...all.map((n) => n.y + sized[n.id].h / 2)), mid = (top + bot) / 2; all.forEach((n) => { n.y -= mid; n.size = sized[n.id]; });
  m.cols = cols; m.height = bot - top;
}
const add = (a, b, k = 1) => [a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k]; const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
export function bezierAt(c, t) { const u = 1 - t, a = u * u * u, b = 3 * u * u * t, d = 3 * u * t * t, e = t * t * t; return [0, 1, 2].map((i) => a * c[0][i] + b * c[1][i] + d * c[2][i] + e * c[3][i]); }
export function bezierLength(c, n = 24) { let L = 0, p = c[0]; for (let i = 1; i <= n; i++) { const q = bezierAt(c, i / n); L += dist(p, q); p = q; } return L; }
/** World layout of the whole graph on a gentle arc that faces the viewer, ending in the result plate. In: API-format graph. Out: nodes with pos/yaw/size, links with Bezier control points, length, arrival clock. */
export function layoutGraph(graph, opts = {}) {
  const m = buildModel(graph); if (!m.ids.length) return { ...m, cols: [], bounds: [], arrive: {}, maxArrive: 0, period: 20, floor: -6 };
  assignColumns(m); assignRows(m, opts.gap ?? (Math.max(...m.ids.map((i) => m.nodes[i].col), 0) > 7 ? 1.05 : 0.8));
  const { ids, nodes, links } = m, plate = opts.plate === false ? null : { w: opts.plateW ?? 7.6, h: opts.plateH ?? 6.2 }, colW = m.cols.map((c) => Math.max(...c.map((i) => nodes[i].size.w), 1)), pitchGap = opts.colGap ?? 1.25, colX = []; let x = 0;
  const deep = m.cols.length > 7, weave = 1; colW.forEach((w, c) => { colX[c] = x + w / 2; x += deep ? w * weave + 0.45 : w + pitchGap; }); const last = colW.length - 1, S = (deep ? x - 0.45 + colW[last] * (1 - weave) : x - pitchGap) + (plate ? plate.w + pitchGap * 1.25 : 0), R = Math.max(14, S / 1.75), shift = plate ? 0.06 : 0;
  const place = (s, y, st = 0) => { const th = (s - S / 2) / R + shift; return { pos: [R * Math.sin(th), y, R * (1 - Math.cos(th)) + st], yaw: -th * 0.9, th }; };
  m.cols.forEach((c, ci) => c.forEach((id, row) => { const n = nodes[id]; const p = place(colX[ci], n.y, (c.length > 1 ? (row % 2 ? -0.55 : 0.55) : 0) + 0); n.pos = p.pos; n.yaw = p.yaw; n.th = p.th; n.axisX = [Math.cos(p.yaw), 0, -Math.sin(p.yaw)]; n.out = [Math.sin(p.th), 0, -Math.cos(p.th)]; }));
  const rowY = (n, i) => n.size.h / 2 - n.size.head - PANEL.rowH * (i + 0.5);
  ids.forEach((id) => { const n = nodes[id]; n.inputs.sort((a, b) => nodes[b.from].y - nodes[a.from].y); n.inputs.forEach((l, i) => { l.y1 = rowY(n, Math.min(i, n.size.rows - 1)); }); Object.keys(n.outs).map(Number).sort((a, b) => a - b).forEach((s, i) => { n.outs[s].y = rowY(n, Math.min(i, n.size.rows - 1)); n.outs[s].row = i; }); });
  links.forEach((l, i) => {
    const A = nodes[l.from], B = nodes[l.to], yA = A.outs[l.slot].y, p0 = add(add(A.pos, A.axisX, A.size.w / 2 + 0.03), [0, yA, 0]), p3 = add(add(B.pos, B.axisX, -B.size.w / 2 - 0.03), [0, l.y1, 0]), span = B.col - A.col, L = Math.max(0.8, dist(p0, p3) * 0.42), bulge = span > 1 ? Math.min(5, 0.95 * span) : 0, wob = ((i % 3) - 1) * 0.14;
    const p1 = add(add(p0, A.axisX, L), A.out, bulge + wob), p2 = add(add(p3, B.axisX, -L), B.out, bulge - wob); l.curve = [p0, p1, p2, p3]; l.len = bezierLength(l.curve); l.span = span;
  });
  /* the clock: a pulse arrives at a node when its longest input chain would, every input reaching it together, so light travels the graph as one wave */
  const arrive = {}, dep = (id, st = new Set()) => { if (arrive[id] != null) return arrive[id]; if (st.has(id)) return 0; st.add(id); let a = 0; nodes[id].inputs.forEach((l) => { a = Math.max(a, dep(l.from, st) + l.len); }); st.delete(id); return (arrive[id] = a); };
  ids.forEach((id) => dep(id)); links.forEach((l) => { l.start = arrive[l.to] - l.len; }); const maxArrive = Math.max(1, ...ids.map((i) => arrive[i]));
  m.arrive = arrive; m.maxArrive = maxArrive; m.period = Math.max(16, Math.min(34, maxArrive * 0.6));
  const bottom = Math.min(...ids.map((i) => nodes[i].y - nodes[i].size.h / 2)), top = Math.max(...ids.map((i) => nodes[i].y + nodes[i].size.h / 2)); m.floor = bottom - 1.5;
  if (plate) { const sinks = ids.filter((i) => !links.some((l) => l.from === i)), save = sinks.find((i) => nodes[i].info.kind === "save") || sinks[0] || ids[ids.length - 1], sn = nodes[save], py = Math.max(m.floor + plate.h / 2 + 0.35, sn.y); const p = place(S - plate.w / 2, py); m.plate = { ...plate, pos: p.pos, yaw: p.yaw * 1.05, th: p.th, save, axisX: [Math.cos(p.yaw * 1.05), 0, -Math.sin(p.yaw * 1.05)] }; }
  m.bounds = []; ids.forEach((id) => { const n = nodes[id], w = n.size.w / 2, h = n.size.h / 2; [-1, 1].forEach((sx) => [-1, 1].forEach((sy) => m.bounds.push(add(add(n.pos, n.axisX, sx * w), [0, sy * h, 0])))); });
  if (m.plate) { const q = m.plate; [-1, 1].forEach((sx) => [-1, 1].forEach((sy) => m.bounds.push(add(add(q.pos, q.axisX, (sx * q.w) / 2), [0, (sy * q.h) / 2, 0])))); }
  m.top = top; return m;
}
/** Camera for a view direction that fits every point, centred. Yaw and pitch in radians, fov vertical in degrees. */
export function fitView(points, yaw, pitch, fov, aspect, margin = 1.08) {
  const d = [Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch)], r = [Math.cos(yaw), 0, -Math.sin(yaw)], u = [d[1] * r[2] - d[2] * r[1], d[2] * r[0] - d[0] * r[2], d[0] * r[1] - d[1] * r[0]];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2], tanV = Math.tan((fov * Math.PI) / 360), tanH = tanV * aspect;
  let c = [0, 0, 0]; points.forEach((p) => { c = add(c, p, 1 / Math.max(1, points.length)); });
  for (let it = 0; it < 4; it++) {
    let lox = 1e9, hix = -1e9, loy = 1e9, hiy = -1e9, dist0 = 0;
    points.forEach((p) => { const q = add(p, c, -1), x = dot(q, r), y = dot(q, u), z = dot(q, d); dist0 = Math.max(dist0, z + Math.abs(x) / tanH, z + Math.abs(y) / tanV); });
    points.forEach((p) => { const q = add(p, c, -1), z = dot(q, d), s = dist0 / (dist0 - z), x = dot(q, r) * s, y = dot(q, u) * s; lox = Math.min(lox, x); hix = Math.max(hix, x); loy = Math.min(loy, y); hiy = Math.max(hiy, y); });
    c = add(add(c, r, (lox + hix) / 2), u, (loy + hiy) / 2); if (it === 3) { const dd = dist0 * margin; return { target: c, position: add(c, d, dd), distance: dd }; }
  }
}
/* ---------- the wave ---------- */
/** Where comets are on a link at this clock, as fractions along it, source to target. */
export function cometsOn(l, clock, period) { const out = [], lo = Math.ceil((clock - (l.start + l.len)) / period), hi = Math.floor((clock - l.start) / period); for (let k = lo; k <= hi; k++) { const u = (clock - k * period - l.start) / l.len; if (u >= 0 && u <= 1) out.push(u); } return out; }
export const pulseAge = (at, clock, period) => { const d = (clock - at) % period; return d < 0 ? d + period : d; };
/* ---------- what lights up ---------- */
/** Direct neighbourhood (hover) or the whole chain feeding and leaving a node (click). */
export function focusSets(m, id, chain = false) {
  const nodes = new Set(id != null ? [id] : []), links = new Set(); if (id == null || !m.nodes[id]) return { nodes, links };
  if (!chain) { m.links.forEach((l) => { if (l.from === id || l.to === id) { links.add(l.id); nodes.add(l.from); nodes.add(l.to); } }); return { nodes, links }; }
  const walk = (start, fwd) => { const st = [start], seen = new Set([start]); while (st.length) { const c = st.pop(); m.links.forEach((l) => { const a = fwd ? l.from : l.to, b = fwd ? l.to : l.from; if (a === c) { links.add(l.id); nodes.add(b); if (!seen.has(b)) { seen.add(b); st.push(b); } } }); } }; walk(id, true); walk(id, false); return { nodes, links };
}
/** The state of each node in a run, from what ComfyUI reported. run = {running:{id:[value,max]}, done:[...], cached:[...], error}. */
export function nodeStates(m, run) { const out = {}; if (!run) return out; m.ids.forEach((id) => { out[id] = "pending"; }); (run.cached || []).forEach((i) => { if (out[i]) out[i] = "cached"; }); (run.done || []).forEach((i) => { if (out[i]) out[i] = "done"; }); Object.keys(run.running || {}).forEach((i) => { if (out[i]) out[i] = "running"; }); if (run.error && out[run.error]) out[run.error] = "error"; return out; }
export function linkState(l, st) { const a = st[l.from], b = st[l.to]; if (b === "running" && (a === "done" || a === "cached" || a === "running")) return "flow"; if (a === "running") return "next"; if ((a === "done" || a === "cached") && b === "pending") return "ready"; if ((b === "done" || b === "cached") && (a === "done" || a === "cached")) return "spent"; if (b === "error") return "ready"; return "idle"; }
/* ---------- replay of a run: a simulation that follows the real order of the graph, its share of the measured total comes from a small table of typical weights, and the page says so ---------- */
const WEIGHT = { sample: 60, decode: 7, load: 3, text: 3, media: 1.2, save: 1.5, latent: 0.5, plan: 0.25, value: 0.12, other: 1 };
export function executionOrder(m) { const left = new Set(m.ids), out = [], done = new Set(); while (left.size) { const ready = [...left].filter((i) => m.nodes[i].inputs.every((l) => done.has(l.from) || !left.has(l.from))).sort((a, b) => m.nodes[a].col - m.nodes[b].col || m.nodes[a].y - m.nodes[b].y || a.localeCompare(b)); const nx = ready[0] ?? [...left][0]; out.push(nx); done.add(nx); left.delete(nx); } return out; }
export function replayPlan(m, totalSeconds = 20) { const order = executionOrder(m), w = order.map((i) => WEIGHT[m.nodes[i].info.kind] ?? 1), sum = w.reduce((a, b) => a + b, 0) || 1; let t = 0; return order.map((id, i) => { const s = (w[i] / sum) * totalSeconds, e = { id, start: t, seconds: s, kind: m.nodes[id].info.kind, steps: m.nodes[id].info.kind === "sample" ? 20 : 0 }; t += s; return e; }); }
/** Run state at a moment of a plan: the same shape the live feed uses. */
export function replayAt(plan, at) { const run = { running: {}, done: [], cached: [], times: {} }; for (const e of plan) { if (at >= e.start + e.seconds) { run.done.push(e.id); run.times[e.id] = e.seconds; } else if (at >= e.start) { run.running[e.id] = e.steps ? [Math.min(e.steps, Math.floor(((at - e.start) / e.seconds) * e.steps) + 1), e.steps] : [0, 0]; break; } else break; } return run; }
/** What the Pro page should ask /api/graph for: always a graph. An empty prompt gets a sample; a missing upload gets a named placeholder the page points out. */
export const PREVIEW_SEED = 11;
export const PLACEHOLDER = { video: "your_clip.mp4", image: "your_picture.png", last_image: "your_last_frame.png" };
export function graphRequest(draft, goal, ideas = {}) {
  if (!draft || !draft.goal) return null; const g = goal || {}, { job, ...body } = draft, typed = String(draft.prompt || "").trim(), sampled = !typed && !g.prompt_optional, fills = [];
  if (sampled) body.prompt = (ideas[draft.goal] || ideas.image || ["a lighthouse on a cliff at dawn"])[0];
  [["needs_video", "video"], ["needs_image", "image"], ["needs_last_image", "last_image"]].forEach(([need, k]) => { if (g[need] && !body[k]) { body[k] = PLACEHOLDER[k]; fills.push(k); } });
  const fixed = body.seed !== "" && body.seed != null; if (!fixed) body.seed = PREVIEW_SEED; return { body, sampled, fills, previewSeed: !fixed };
}
/** First stop for the walk-through: nodes in the order data reaches them, skipping small value nodes. */
export function walkOrder(m) { return Object.values(m.nodes).filter((n) => n.info.kind !== "value").sort((a, b) => (m.arrive[a.id] ?? 0) - (m.arrive[b.id] ?? 0) || b.y - a.y).map((n) => n.id); }
/* ---------- labels: which node names float over the scene when the panels are too small to read ---------- */
const LABEL_RANK = { sample: 0, save: 1, load: 2, text: 3, decode: 4, latent: 5, media: 6, plan: 7, other: 8, value: 9 };
/** Lower is more important: the sampler first, then the output, the loaders and the prompts; the small value nodes last. */
export const labelPriority = (kind) => LABEL_RANK[kind] ?? 8;
/** Screen pixels per world unit at a distance, for a vertical field of view in degrees and a viewport height in pixels. */
export const pxPerUnit = (dist, fov, height) => height / (2 * Math.tan((fov * Math.PI) / 360) * Math.max(1e-3, dist));
/** Greedy declutter. Each candidate is {id, x, y, w, h, pri, z}: a label anchored by its bottom centre at (x, y), w by h pixels. The most important labels win (lower pri, then nearer z); a label is kept only if it sits inside the view and clears every kept label by pad pixels. Returns the kept ids, best first. */
export function declutterLabels(cands, { width, height, max = 12, pad = 4 } = {}) {
  const order = [...cands].sort((a, b) => a.pri - b.pri || a.z - b.z || String(a.id).localeCompare(String(b.id))), kept = [], boxes = [];
  for (const c of order) {
    if (kept.length >= max) break;
    const x0 = c.x - c.w / 2, x1 = c.x + c.w / 2, y0 = c.y - c.h, y1 = c.y;
    if (!(x0 >= 0 && y0 >= 0 && x1 <= width && y1 <= height)) continue;
    if (boxes.some((b) => x0 < b[2] + pad && x1 + pad > b[0] && y0 < b[3] + pad && y1 + pad > b[1])) continue;
    boxes.push([x0, y0, x1, y1]); kept.push(c.id);
  }
  return kept;
}
/** Zoom limits that suit the graph: close enough to read one panel, far enough to see the whole graph with room around it. */
export const zoomLimits = (fitDistance) => ({ min: Math.max(2, fitDistance * 0.12), max: Math.max(30, fitDistance * 2.4) });
/** The next node for the arrow keys: steps through order (the walk order) and wraps; from nothing, forward starts at the first node and back at the last. */
export function stepNode(order, current, dir) {
  if (!order.length) return null; const i = order.indexOf(current);
  if (i < 0) return dir < 0 ? order[order.length - 1] : order[0];
  return order[(i + (dir < 0 ? -1 : 1) + order.length) % order.length];
}
/* ---------- the overview: what the camera shows first, and which titles a nearer panel hides from it ---------- */
/** The opening camera for a viewport: a gentle three-quarter view on a phone (taller than wide; any steeper and the near columns cover the far ones' titles), almost straight on elsewhere, fitted to every panel and the result plate. */
export function overviewView(m, W, H, fov = 30) {
  const narrow = W / H < 1, pts = m.bounds && m.bounds.length ? m.bounds : [[0, 0, 0]];
  return fitView(pts, narrow ? 0.5 : 0.16, narrow ? 0.24 : 0.1, fov * (narrow ? 1 : 0.86), (W / H) / (narrow ? 1 : 0.86), narrow ? 1.06 : 1.045);
}
/** Screen boxes [x0, y0, x1, y1] of each panel and of its title strip, seen from view {position, target} with a vertical fov in degrees on a W x H viewport; z is the depth of the panel's centre. */
export function panelBoxes(m, view, fov, W, H) {
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2], unit = (a) => { const l = Math.hypot(...a) || 1; return a.map((x) => x / l); };
  const f = unit(sub(view.target, view.position)), r = unit([-f[2], 0, f[0]]), u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]], t = Math.tan((fov * Math.PI) / 360);
  const proj = (p) => { const q = sub(p, view.position), z = Math.max(1e-3, dot(q, f)); return [W / 2 + (dot(q, r) / (z * t * (W / H))) * (W / 2), H / 2 - (dot(q, u) / (z * t)) * (H / 2), z]; };
  const box = (cs) => [Math.min(...cs.map((c) => c[0])), Math.min(...cs.map((c) => c[1])), Math.max(...cs.map((c) => c[0])), Math.max(...cs.map((c) => c[1]))];
  return m.ids.map((id) => { const n = m.nodes[id], hw = n.size.w / 2, hh = n.size.h / 2, at = (sx, sy) => proj(add(add(n.pos, n.axisX, sx * hw), [0, sy * hh, 0])), ty = 1 - (2 * n.size.head) / n.size.h;
    return { id, all: box([at(-1, 1), at(1, 1), at(1, -1), at(-1, -1)]), title: box([at(-1, 1), at(1, 1), at(1, ty), at(-1, ty)]), z: proj(n.pos)[2] }; });
}
/** Ids whose title strip is more than `limit` covered by one nearer panel. */
export function hiddenTitles(boxes, limit = 0.25) {
  const out = [];
  for (const a of boxes) { const T = a.title, area = Math.max(1e-6, (T[2] - T[0]) * (T[3] - T[1]));
    if (boxes.some((b) => b !== a && b.z < a.z && (Math.max(0, Math.min(T[2], b.all[2]) - Math.max(T[0], b.all[0])) * Math.max(0, Math.min(T[3], b.all[3]) - Math.max(T[1], b.all[1]))) / area > limit)) out.push(a.id); }
  return out;
}
