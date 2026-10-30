# Fusion paste

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


Fusion takes ONE image on which the object has already been roughly pasted, and blends it in: lighting, reflections, a contact
shadow. It keeps the pasted shape and size exactly, so you place and scale the object yourself. This tool makes that
pasted picture in the browser.

## In the studio
1. Edit tab, generator "Qwen-Image 2.1 · Blend a pasted object in (Fusion)" (or the Fusion card, Choose).
2. Click **📋 Paste an object into a photo**.
3. Fill the two slots: **photo** (the scene) and **object** (the thing to add). Each takes a dropped file, an image dragged from
   a card, the **📋 Paste** button (clipboard), or Ctrl+V after clicking the slot (the highlighted slot gets the paste).
4. No transparency in the object? Pick one of the three offered:
   - **Automatic cut-out**: the studio's BiRefNet background remover (`img:bgremove`, a GPU job of about a second; its card also
     appears in the feed). Glass and liquids come out solid.
   - **Remove plain background**: flood-fills the colour at the four corners with a tolerance slider (browser only, no model).
     It warns when the corners are not one colour.
   - **Keep the rectangle**: pastes the picture as it is.
5. Drag the object to move it, a corner to resize, or use size, rotate, flip, opacity. **Reset** puts it back in the middle.
6. Type **What is the object?** and **Where does it go?**. **Use this composite** uploads a PNG at the photo's size (long side
   capped at 2048) into the `image` slot and writes the prompt `Blend the <object> into the <place> seamlessly.` (editable).
   The enhancer is switched off for it, because the words are an instruction. Press Generate.

## Tips
- **Place it at the right size.** Fusion keeps the pasted size; a mug pasted sofa-sized stays sofa-sized.
- A cut-out with soft edges works best; hard halo edges survive the blend.
- Leave a little room for the shadow to fall on the surface below the object.
- Fusion vs the plain Qwen edit (no LoRA): Fusion keeps the object pixel-faithful and adds shading, reflections and contact.
  A plain turbo edit tends to re-render the object at a plausible smaller size, which can be better for a badly scaled paste.
- Klein 9B `fusion2250` / `fusion4b` LoRAs are registered in the LoRA library but greyed "no studio engine yet"; Klein Fusion
  does not remove the pasted product and there is no Klein studio engine, so this tool does not use them.

## Not verified
The composite and the prompt are CPU-tested only; no Fusion render was run through this tool.
