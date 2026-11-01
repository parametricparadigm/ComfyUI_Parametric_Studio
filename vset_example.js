// The Virtual Set hero: one scene, same camera and seed, rendered by two engines and copied small into vset_art. The numbers are each shot's own record (hievlnxxoasa and oqfxxmiordxs: shot.json, state.json). Recorded examples, not live results.
const PROMPT = "Slow push-in along an empty wet night street toward the sculpture standing in the road, rain falling, streetlight reflections on the asphalt, no people, no cars, plain unbranded buildings";
const pass = (engine, key, label, what) => ({ key, label, what, clip: `vset_art/${engine}_${key}.mp4`, still: `vset_art/${engine}_${key}.webp` });
const SHADED = "How the set looks, lit in Blender.", DEPTH = "How far away everything is.", EDGES = "The lines of the set.";
export const EXAMPLES = [
  { id: "h3", engine: "MiniMax H3", name: "Night street push-in", mode: "A", size: "1344 x 768", fps: 24, frames: 124, seed: 4242, flicker: 3.2, layout: 0.13, prompt: PROMPT,
    how: "Our own render, MiniMax H3 steered by the depth pass.",
    held: "The camera and the layout. The street, the kerbs and the push-in line up with the passes all the way through, and it looks like a photograph.",
    lost: "The exact set. H3 invented taller buildings, shop fronts and a yellow road line that are not in the scene, and the knot came back as a lumpy carved shape.",
    result: { clip: "vset_art/h3_result.mp4", still: "vset_art/h3_result.webp" },
    passes: [pass("h3", "shaded", "Shaded", SHADED), pass("h3", "depth", "Depth", DEPTH), pass("h3", "edges", "Edges", EDGES)] },
  { id: "ltx", engine: "LTX-2.5", name: "Night street push-in", mode: "A", size: "1920 x 1088", fps: 24, frames: 121, seed: 4242, flicker: 2.0, layout: 0.33, prompt: PROMPT,
    how: "Our own render, LTX-2.5 from the raw shaded keyframes and the clay pass.",
    held: "The set itself. The buildings, the lamp posts and the knot sculpture stay where the passes put them, all the way through the push-in.",
    lost: "Realism. It still looks like a CG render, and the rain in the prompt never appeared. Started from the raw keyframes, LTX-2.5 keeps the set exact and does not make it photoreal.",
    result: { clip: "vset_art/ltx_result.mp4", still: "vset_art/ltx_result.webp" },
    passes: [pass("ltx", "shaded", "Shaded", SHADED), pass("ltx", "depth", "Depth", DEPTH), pass("ltx", "edges", "Edges", EDGES), pass("ltx", "clay", "Clay", "The shapes alone, with no materials.")] },
];
