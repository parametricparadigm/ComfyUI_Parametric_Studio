# CU-301 lab: scaled dot-product attention, measured.
# Run: python lab.py  (CPU only, a few seconds).
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
def attention(q, k, v):
    s = q @ k.transpose(-1, -2) / math.sqrt(k.shape[-1])      # who matches whom
    w = s.softmax(-1)                                         # each query's weights sum to 1
    return w @ v, w
# 1. A hand example: three keys, one query. The output is a weighted average of the values.
k = torch.tensor([[1., 0.], [0., 1.], [1., 1.]]); v = torch.tensor([[10.], [20.], [30.]]); q = torch.tensor([[2., 0.]])
out, w = attention(q, k, v); print("weights:", [round(x, 4) for x in w[0].tolist()], " output:", round(out.item(), 4))
assert abs(w.sum().item() - 1) < 1e-6 and abs(out.item() - (w @ v).item()) < 1e-6
# 2. Why divide by sqrt(d). Dot products of random unit-variance vectors have variance d.
print("\nd       var(q.k)  var after /sqrt(d)  largest weight, no scale  largest weight, scaled")
for d in (4, 64, 512, 4096):
    q_ = torch.randn(2000, 1, d); k_ = torch.randn(2000, 32, d); s = (q_ * k_).sum(-1)
    print(f"{d:<7d} {s.var():<9.1f} {(s / math.sqrt(d)).var():<19.3f} {s.softmax(-1).max(-1).values.mean():<25.3f} {(s / math.sqrt(d)).softmax(-1).max(-1).values.mean():.3f}")
    if d == 4096: assert s.softmax(-1).max(-1).values.mean() > .9 and (s / math.sqrt(d)).softmax(-1).max(-1).values.mean() < .3
# 3. Attention alone has no idea of order: permute the inputs and the outputs just permute with them.
x = torch.randn(1, 6, 16); W = [torch.randn(16, 16) for _ in range(3)]
def self_attn(x): return attention(x @ W[0], x @ W[1], x @ W[2])[0]
p = torch.randperm(6); gap = (self_attn(x)[:, p] - self_attn(x[:, p])).abs().max().item(); print(f"\nself-attention, permute then attend against attend then permute: max difference {gap:.1e}"); assert gap < 1e-4
# 4. Cross-attention: queries from the image, keys and values from the text. This is how a word reaches a pixel.
words = ["a", "red", "fox", "<pad>"]; dim = 32; txt = torch.randn(1, 4, dim); img = torch.randn(1, 64, dim)    # 64 latent patches
img[0, 20:28] = txt[0, 2] * 1.5 + .2 * torch.randn(8, dim)                                                      # eight patches that look like "fox"
out, w = attention(img, txt, txt); print(f"\ncross-attention shapes: image {tuple(img.shape)}, text {tuple(txt.shape)}, weights {tuple(w.shape)}, output {tuple(out.shape)}")
print("mean weight on each word, fox patches:  ", {a: round(b, 3) for a, b in zip(words, w[0, 20:28].mean(0).tolist())}); print("mean weight on each word, other patches:", {a: round(b, 3) for a, b in zip(words, w[0, :20].mean(0).tolist())})
assert w[0, 20:28].mean(0).argmax().item() == 2
# 5. Masking: padding must get no weight, or it changes the result.
s = img @ txt.transpose(-1, -2) / math.sqrt(dim); masked = s.clone(); masked[..., 3] = -float("inf"); wm = masked.softmax(-1); print("weight on <pad> without a mask:", round(w[0, ..., 3].mean().item(), 3), " with a mask:", wm[0, ..., 3].max().item()); assert wm[..., 3].max() == 0
# 6. Cost. Every token looks at every token.
print("\nimage side  latent side  tokens (patch 2)  pairs in self-attention  attention matrix for one head at fp16")
for side in (512, 768, 1024, 1536, 2048):
    n = (side // 16) ** 2; print(f"{side:<11d} {side // 8:<12d} {n:<17,d} {n * n:<24,d} {n * n * 2 / 2 ** 30:.2f} GiB")
print("doubling the side quadruples the tokens and multiplies the pairs by 16")
