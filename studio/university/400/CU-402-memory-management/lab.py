# CU-402 lab: the budgeting arithmetic of load_models_gpu and free_memory, on a simulated card. No GPU needed.
# Constants and the order of eviction are read from comfy/model_management.py. Sizes are examples, not measurements of real models.
# Run: python lab.py  (standard library only, under a second).
MB = 1024 ** 2; GB = 1024 ** 3
EXTRA_RESERVED = 400 * MB                                      # EXTRA_RESERVED_VRAM on Linux, unless --reserve-vram is set
def minimum_inference_memory(): return 0.8 * GB + EXTRA_RESERVED
class Card:
    def __init__(self, total): self.total = total; self.loaded = []     # [name, bytes, offloaded_bytes, in_use]
    def free(self): return self.total - sum(m[1] for m in self.loaded)
    def show(self, what): print(f"{what:44s} free {self.free() / GB:6.2f} GB   loaded: " + (", ".join(f"{m[0]} {m[1] / GB:.1f}" for m in self.loaded) or "nothing"))
def free_memory(card, required, keep=()):
    """Sort candidates, then unload only as much as is needed. Already partly offloaded models come first, as in free_memory's sort key."""
    cand = sorted([m for m in card.loaded if m[0] not in keep], key=lambda m: (-m[2], m[1]))
    for m in cand:
        need = required - card.free()
        if need <= 0: break
        print(f"    evict {m[0]} ({m[1] / GB:.1f} GB)"); card.loaded.remove(m)
def load(card, models, activation=0):
    """load_models_gpu: reserve room for the models plus 10 percent, plus working memory for the run itself."""
    extra = max(minimum_inference_memory(), activation + EXTRA_RESERVED); names = [n for n, _ in models]
    need = sum(s for n, s in models if n not in [m[0] for m in card.loaded])
    free_memory(card, need * 1.1 + extra, keep=names)
    for n, s in models:
        if n not in [m[0] for m in card.loaded]:
            room = card.free() - extra
            if room >= s: card.loaded.append([n, s, 0, True])
            else:
                part = max(0, room); print(f"    {n} does not fit: {part / GB:.2f} of {s / GB:.2f} GB on the GPU, the rest is streamed from RAM per layer"); card.loaded.append([n + "(partial)", part, s - part, True])
print(f"minimum_inference_memory: {minimum_inference_memory() / GB:.3f} GB")
c = Card(24 * GB); c.show("start, a 24 GB card")
load(c, [("text_encoder", int(5 * GB))]); c.show("encode the prompt")
load(c, [("unet", int(12 * GB))], activation=int(6 * GB)); c.show("sample")
load(c, [("vae", int(.3 * GB))], activation=int(4 * GB)); c.show("decode")
print("nothing evicted yet: models stay until room is needed, that is why a second run is fast")
load(c, [("video_model", int(14 * GB))], activation=int(8 * GB)); c.show("now load a big video model")
assert any(m[0] == "video_model" for m in c.loaded) and not any(m[0] == "text_encoder" for m in c.loaded)
print()
c = Card(8 * GB); c.show("start, an 8 GB card")
load(c, [("unet", int(12 * GB))], activation=int(3 * GB)); c.show("a 12 GB model on 8 GB")
m = c.loaded[0]; assert m[0] == "unet(partial)" and m[2] > 0
print(f"\nmodel share on the GPU: {m[1] / (m[1] + m[2]):.0%}. It runs, and each step copies the rest across PCIe.")
# Size of a model from its parameter count, and activation memory that grows with resolution.
print("\nweights: parameters x bytes per parameter")
for name, p in (("SD 1.x U-Net", 860e6), ("SDXL U-Net", 2.6e9)):                # parameter counts from Table 1 of the SDXL paper
    print(f"  {name:20s} " + "  ".join(f"{d}: {p * b / GB:5.1f} GB" for d, b in (("fp32", 4), ("fp16", 2), ("fp8", 1))))
print("\nlatent memory alone, one fp32 16-channel latent")
for side in (512, 1024, 2048): print(f"  {side}px: {(side // 8) ** 2 * 16 * 4 / MB:7.2f} MB")
assert abs((1024 // 8) ** 2 * 16 * 4 / MB - 1.0) < 1e-9
