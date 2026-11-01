// The Virtual Set hero: one real shot of ours, copied small into vset_art. The numbers are that shot's own record (oqfxxmiordxs: shot.json, state.json). It is a recorded example, not a live result.
export const EXAMPLE = {
  name: "Night street push-in", mode: "A", size: "1920 x 1088", fps: 24, frames: 121, seed: 4242, flicker: 2.0, layout: 0.33,
  prompt: "Slow push-in along an empty wet night street toward the sculpture standing in the road, rain falling, streetlight reflections on the asphalt, no people, no cars, plain unbranded buildings",
  result: { clip: "vset_art/result.mp4", still: "vset_art/result.webp" },
  passes: [
    { key: "shaded", label: "Shaded", what: "How the set looks, lit in Blender.", clip: "vset_art/shaded.mp4", still: "vset_art/shaded.webp" },
    { key: "depth", label: "Depth", what: "How far away everything is.", clip: "vset_art/depth.mp4", still: "vset_art/depth.webp" },
    { key: "edges", label: "Edges", what: "The lines of the set.", clip: "vset_art/edges.mp4", still: "vset_art/edges.webp" },
    { key: "clay", label: "Clay", what: "The shapes alone, with no materials.", clip: "vset_art/clay.mp4", still: "vset_art/clay.webp" },
  ],
};
