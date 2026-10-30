# CU-210 lab: what each float format can hold, and three places where the difference shows up.
# Run: python lab.py  (CPU only, a few seconds).
import torch
torch.manual_seed(0); torch.set_num_threads(1)
T = {"fp32": torch.float32, "fp16": torch.float16, "bf16": torch.bfloat16}
print("format  bits  mantissa  epsilon      largest      smallest normal")
for n, d in T.items():
    f = torch.finfo(d); print(f"{n:7s} {f.bits:<5d} {dict(fp32=23, fp16=10, bf16=7)[n]:<9d} {f.eps:<12.4e} {f.max:<12.4e} {f.tiny:.4e}")
print(f"{'fp8':7s} {8:<5d} {3:<9d} {2.0 ** -3:<12.4e} {448.0:<12.4e} {2.0 ** -14:.4e}   (e4m3fn, from its definition; torch has no compute type for it here)")
# Rounding fp8 by hand: 3 mantissa bits, 4 exponent bits, finite maximum 448.
def to_fp8(x):
    s = x.sign(); a = x.abs().clamp(max=448.); e = torch.floor(torch.log2(a.clamp(min=2.0 ** -17))).clamp(min=-14.); q = 2.0 ** (e - 3); return s * (a / q).round() * q
# 1. A small update added to a weight: this is what a LoRA or a merge does.
w = torch.randn(1_000_000) * .05; d = torch.randn(1_000_000) * 1e-4
print("\nweight std 0.05, update std 1e-4: how much of the update survives when the sum is stored in each format")
kept = {}
for n, f in (("fp32", lambda t: t.to(torch.float32)), ("fp16", lambda t: t.to(torch.float16).to(torch.float32)), ("bf16", lambda t: t.to(torch.bfloat16).to(torch.float32)), ("fp8", to_fp8)):
    base = f(w); new = f(w + d); got = new - base; kept[n] = (got * d).sum().item() / (d * d).sum().item(); print(f"{n:6s} captured share of the update {kept[n]:.4f}   RMS error of the update {((got - d) ** 2).mean().sqrt():.2e}")
assert kept["fp32"] > .99
# 2. Accumulation: add a small number many times.
print("\nstart at 1.0 and add 0.0001 ten thousand times; the exact answer is 2.0")
res = {}
for n, dt in T.items():
    x = torch.tensor(1.0, dtype=dt); s = torch.tensor(1e-4, dtype=dt)
    for _ in range(10000): x = x + s
    res[n] = x.item(); print(f"{n:6s} {x.item():.5f}")
assert res["bf16"] == 1.0 and abs(res["fp32"] - 2) < .01
# Sum the small terms first and the same formats do far better.
small = torch.full((10000,), 1e-4, dtype=torch.float32); print(f"bf16 with the sum done in fp32 first: {(torch.tensor(1.0, dtype=torch.float32) + small.sum()).to(torch.bfloat16).item():.5f}")
# 3. Range: fp16 overflows early, and one inf becomes NaN.
print("\nvalue 70000 stored as"); a = torch.tensor(70000.)
for n, d in T.items(): print(f"  {n}: {a.to(d).item()}")
assert a.to(torch.float16).item() == float("inf")
x = torch.tensor([300., 1.], dtype=torch.float16); sq = x * x; print("fp16: 300^2 =", sq[0].item(), "  then normalising:", (sq / sq.sum()).tolist())
assert sq[0].item() == float("inf")
print("smallest fp16 value before underflow to zero:", torch.tensor(1e-8).to(torch.float16).item(), " bf16 keeps it:", f"{torch.tensor(1e-8).to(torch.bfloat16).item():.3e}")
print("\nmemory for 1 billion parameters: " + "  ".join(f"{n} {b:.1f} GiB" for n, b in (("fp32", 4e9 / 2 ** 30), ("fp16/bf16", 2e9 / 2 ** 30), ("fp8", 1e9 / 2 ** 30))))
