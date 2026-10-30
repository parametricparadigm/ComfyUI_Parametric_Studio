# CU-201 lab: a small VAE on 8x8 images of one soft vertical bar. Position is the only true degree of freedom.
# Run: python lab.py  (CPU only, about 15 s).
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
xs = torch.arange(8.)
def bars(p): return torch.exp(-.5 * ((xs[None] - p[:, None]) / .7) ** 2)[:, None, :].repeat(1, 8, 1).flatten(1)     # one bar per row of p, image flattened to 64
def batch(n): return bars(torch.rand(n) * 5 + 1)
class VAE(torch.nn.Module):
    def __init__(s, z=2, w=128):
        super().__init__(); s.e = torch.nn.Sequential(torch.nn.Linear(64, w), torch.nn.SiLU(), torch.nn.Linear(w, w), torch.nn.SiLU(), torch.nn.Linear(w, 2 * z)); s.d = torch.nn.Sequential(torch.nn.Linear(z, w), torch.nn.SiLU(), torch.nn.Linear(w, w), torch.nn.SiLU(), torch.nn.Linear(w, 64))
    def enc(s, x): m, lv = s.e(x).chunk(2, 1); return m, lv
def train(beta, steps=1800):
    v = VAE(); opt = torch.optim.Adam(v.parameters(), 2e-3)
    for i in range(steps):
        x = batch(256); m, lv = v.enc(x); z = m + (.5 * lv).exp() * torch.randn_like(m)      # reparameterisation: noise outside the gradient path
        rec = ((v.d(z) - x) ** 2).sum(1).mean(); kl = (.5 * (m ** 2 + lv.exp() - 1 - lv)).sum(1).mean(); loss = rec + beta * kl; opt.zero_grad(); loss.backward(); opt.step()
    return v
# Closed-form KL against a Monte Carlo estimate, so the formula is not taken on trust.
m0, s0 = torch.tensor(1.2), torch.tensor(.6); z = m0 + s0 * torch.randn(2_000_000); mc = (-.5 * ((z - m0) / s0) ** 2 - s0.log() + .5 * z ** 2).mean(); cf = .5 * (m0 ** 2 + s0 ** 2 - 1 - 2 * s0.log())
print(f"KL(N(1.2,0.6^2) || N(0,1))  closed form {cf:.4f}   Monte Carlo {mc:.4f}"); assert abs(cf - mc) < .01
print("\nbeta    reconstruction MSE per image   KL per image   latent std")
models = {}
torch.manual_seed(0); test = batch(4000)
for beta in (0., .001, .05, 1.):
    torch.manual_seed(1); v = train(beta); models[beta] = v
    with torch.no_grad():
        m, lv = v.enc(test); r = ((v.d(m) - test) ** 2).sum(1).mean().item(); k = (.5 * (m ** 2 + lv.exp() - 1 - lv)).sum(1).mean().item(); print(f"{beta:<7} {r:<30.4f} {k:<14.3f} {m.std().item():.3f}")
v = models[.001]
# Scale factor: Stable Diffusion divides latents by a constant so that they have about unit variance before diffusion.
with torch.no_grad(): z = v.enc(test)[0]
print(f"\nlatent std per channel with a weak KL: {z.std(0)[0]:.3f} {z.std(0)[1]:.3f}   scale factor 1/std: {1 / z.std():.4f}   std after scaling: {(z / z.std()).std():.3f}")
# Interpolation: the midpoint of two images is a double exposure. What the midpoint of their latents gives depends on how regular the latent space is.
a, b = bars(torch.tensor([1.5])), bars(torch.tensor([5.5])); mid_px = (a + b) / 2; true_mid = bars(torch.tensor([3.5]))
def row(x): return " ".join(f"{t:.2f}" for t in x.view(8, 8)[0].tolist())
print("\none row of pixels"); print("image A                 ", row(a)); print("image B                 ", row(b)); print("pixel midpoint          ", row(mid_px)); print("true bar at the middle  ", row(true_mid))
e_px = ((mid_px - true_mid) ** 2).sum().item(); errs = {}
for beta in (.001, .05, 1.):
    with torch.no_grad(): za, zb = models[beta].enc(a)[0], models[beta].enc(b)[0]; ml = models[beta].d((za + zb) / 2)
    errs[beta] = ((ml - true_mid) ** 2).sum().item(); print(f"latent midpoint, beta {beta:<6}" + row(ml))
print(f"distance from a real bar at the middle:  pixel midpoint {e_px:.3f}   " + "   ".join(f"beta {k}: {v:.3f}" for k, v in errs.items()))
assert min(errs.values()) < e_px / 3
# Compression of real formats: pixels x 3 channels against latent x channels. Purely arithmetic.
print("\nformat          factor  channels  values in 1024x1024   compression")
for n, f, c in (("SD 1.x, SDXL", 8, 4), ("SD3, FLUX.1", 8, 16)): print(f"{n:15s} {f:<7d} {c:<9d} {(1024 // f) ** 2 * c:<21,d} {1024 ** 2 * 3 / ((1024 // f) ** 2 * c):.0f}x")
