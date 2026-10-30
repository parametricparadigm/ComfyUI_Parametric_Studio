"""Parametric Studio: Camera moves and looks preset library."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Union
from psn.camera import camera_moves, one_move_problems

router = APIRouter()

# 8 Camera Presets
# Each phrase must classify as exactly [key] via camera_moves()
CAMERA = {
    "push_in": {
        "label": "Push In",
        "phrase": "slow dolly push in toward the subject",
        "blurb": "Gradually move closer to the subject for emphasis."
    },
    "pull_out": {
        "label": "Pull Out",
        "phrase": "smooth dolly pull out from the subject",
        "blurb": "Gradually move away from the subject to reveal context."
    },
    "pan": {
        "label": "Pan",
        "phrase": "steady horizontal pan across the scene",
        "blurb": "Rotate the camera horizontally to show a wider area."
    },
    "tilt": {
        "label": "Tilt",
        "phrase": "gentle vertical tilt up from the base",
        "blurb": "Rotate the camera vertically to reveal height or detail."
    },
    "orbit": {
        "label": "Orbit",
        "phrase": "smooth orbit around the central figure",
        "blurb": "Circle the subject to create a dynamic 360-degree view."
    },
    "track": {
        "label": "Track",
        "phrase": "tracking shot following the moving subject",
        "blurb": "Move the camera alongside the subject to maintain relative position."
    },
    "crane": {
        "label": "Crane",
        "phrase": "crane shot rising above the crowd",
        "blurb": "Vertical movement using a crane or jib for a sweeping view."
    },
    "handheld": {
        "label": "Handheld",
        "phrase": "handheld camera with natural subtle shake",
        "blurb": "Simulate the organic, slightly shaky feel of a hand-held camera."
    }
}

# 24 Look Presets
# Phrases must NOT contain camera move words (camera_moves(phrase) == [])
LOOKS = [
    {"id": "cinematic-4k", "label": "Cinematic 4K", "group": "cinematic", "phrase": "cinematic 4k, shallow depth of field, film grain", "blurb": "High-quality film look with realistic grain and focus."},
    {"id": "anamorphic", "label": "Anamorphic", "group": "cinematic", "phrase": "anamorphic lens flare, widescreen aspect ratio, teal and orange", "blurb": "Classic movie look with horizontal flares and color grading."},
    {"id": "noir", "label": "Film Noir", "group": "moody", "phrase": "black and white, high contrast, dramatic shadows", "blurb": "Moody, high-contrast monochrome style reminiscent of classic noir."},
    {"id": "neon-noir", "label": "Neon Noir", "group": "moody", "phrase": "neon lights, rain-slicked streets, cyberpunk atmosphere", "blurb": "Dark, futuristic city vibe with vibrant neon accents."},
    {"id": "watercolor", "label": "Watercolor", "group": "illustration", "phrase": "soft watercolor painting, pastel colors, textured paper", "blurb": "Gentle, artistic style with soft edges and paper texture."},
    {"id": "oil-painting", "label": "Oil Painting", "group": "illustration", "phrase": "thick oil paint strokes, canvas texture, classical style", "blurb": "Rich, textured look mimicking traditional oil paintings."},
    {"id": "pencil-sketch", "label": "Pencil Sketch", "group": "illustration", "phrase": "black and white pencil sketch, cross-hatching, rough lines", "blurb": "Monochrome drawing style with visible pencil strokes."},
    {"id": "comic-book", "label": "Comic Book", "group": "illustration", "phrase": "bold comic book style, halftone dots, vibrant colors", "blurb": "Punchy, graphic style with strong outlines and colors."},
    {"id": "pixel-art", "label": "Pixel Art", "group": "retro", "phrase": "8-bit pixel art, retro video game style, limited palette", "blurb": "Nostalgic, blocky aesthetic from early video games."},
    {"id": "vhs", "label": "VHS", "group": "retro", "phrase": "vhs tape aesthetic, tracking lines, 1990s color cast", "blurb": "Grainy, distorted look of old VHS recordings."},
    {"id": "polaroid", "label": "Polaroid", "group": "retro", "phrase": "instant photo, white border, faded colors, nostalgic", "blurb": "Casual, snapshot feel with a white frame and soft colors."},
    {"id": "sepia", "label": "Sepia", "group": "retro", "phrase": "sepia tone, vintage photograph, aged paper texture", "blurb": "Warm, brownish tint evoking old photographs."},
    {"id": "portrait", "label": "Portrait", "group": "photo", "phrase": "professional portrait, soft studio lighting, sharp focus", "blurb": "Clean, well-lit photography style ideal for people."},
    {"id": "landscape", "label": "Landscape", "group": "photo", "phrase": "wide angle landscape, natural lighting, high dynamic range", "blurb": "Vivid, detailed outdoor photography with balanced exposure."},
    {"id": "macro", "label": "Macro", "group": "photo", "phrase": "extreme close-up macro, intricate details, shallow focus", "blurb": "Very close photography highlighting fine textures and details."},
    {"id": "street", "label": "Street", "group": "photo", "phrase": "candid street photography, urban environment, natural light", "blurb": "Spontaneous, real-life urban moments captured naturally."},
    {"id": "documentary", "label": "Documentary", "group": "photo", "phrase": "documentary style, realistic, unposed, natural colors", "blurb": "Authentic, unglamorous look focusing on reality."},
    {"id": "fantasy", "label": "Fantasy", "group": "bright", "phrase": "fantasy art, magical lighting, ethereal glow, vibrant", "blurb": "Whimsical, otherworldly style with magical elements."},
    {"id": "scifi", "label": "Sci-Fi", "group": "bright", "phrase": "futuristic sci-fi, sleek technology, blue and white light", "blurb": "Clean, advanced technological aesthetic with cool tones."},
    {"id": "pastel", "label": "Pastel", "group": "bright", "phrase": "soft pastel colors, dreamy atmosphere, gentle lighting", "blurb": "Light, airy, and colorful with a soft focus."},
    {"id": "golden-hour", "label": "Golden Hour", "group": "bright", "phrase": "warm golden hour light, long shadows, soft glow", "blurb": "Warm, natural lighting typical of sunset or sunrise."},
    {"id": "high-key", "label": "High Key", "group": "bright", "phrase": "high key lighting, bright and airy, minimal shadows", "blurb": "Bright, evenly lit style with very few shadows."},
    {"id": "low-key", "label": "Low Key", "group": "moody", "phrase": "low key lighting, deep shadows, dramatic mood", "blurb": "Dark, moody style with strong contrast and shadows."},
    {"id": "vintage-film", "label": "Vintage Film", "group": "retro", "phrase": "vintage film look, light leaks, faded colors, grain", "blurb": "Aesthetic of old film cameras with light leaks and grain."}
]

def apply(prompt, camera=None, look=None, kind='video'):
    """
    Appends look phrase and (video only) camera phrase to the prompt.
    Returns str if no notes, or tuple (str, list[str]) if notes exist.
    """
    notes = []
    parts = [prompt.strip()] if prompt and prompt.strip() else []
    
    # Add look
    if look:
        look_obj = next((l for l in LOOKS if l['id'] == look), None)
        if look_obj:
            phrase = look_obj['phrase']
            # Check if already in prompt (simple substring check for phrase or key parts)
            # Spec says "avoiding duplicates". We check if the phrase is already present.
            if phrase.lower() not in prompt.lower():
                parts.append(phrase)
        else:
            notes.append(f"Unknown look: {look}")

    # Add camera (video only)
    if kind == 'video' and camera:
        cam_obj = CAMERA.get(camera)
        if cam_obj:
            phrase = cam_obj['phrase']
            # Check if user's prompt already names a camera move
            existing_moves = camera_moves(prompt)
            if existing_moves:
                notes.append(f"Camera move already present in prompt ({', '.join(existing_moves)}); skipping preset '{camera}'")
            else:
                # Check if this specific phrase is already there
                if phrase.lower() not in prompt.lower():
                    parts.append(phrase)
        else:
            notes.append(f"Unknown camera: {camera}")

    # Collapse spaces
    final_text = " ".join(parts)
    final_text = " ".join(final_text.split())
    
    if notes:
        return final_text, notes
    return final_text

class ApplyRequest(BaseModel):
    prompt: str
    camera: Optional[str] = None
    look: Optional[str] = None
    kind: Optional[str] = 'video'

@router.get("/api/presets")
def get_presets():
    return {"camera": CAMERA, "looks": LOOKS}

@router.post("/api/presets/apply")
def apply_presets(req: ApplyRequest):
    result = apply(req.prompt, req.camera, req.look, req.kind or 'video')
    if isinstance(result, tuple):
        text, notes = result
    else:
        text, notes = result, []
    return {"prompt": text, "notes": notes}
