# CU-203 lab: Tweedie's formula, Vincent's identity, and SDE versus ODE, all with an exact score.
# Run: python lab.py  (CPU only, about 10 s).
import torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
W, M, S = torch.tensor([.3, .7], dtype=D), torch.tensor([-2., 1.5], dtype=D), torch.tensor([.3, .5], dtype=D)
def data(n): k = torch.multinomial(W, n, True); return M[k] + S[k] * torch.randn(n, dtype=D)
def denoiser(x, sigma):
    v = S ** 2 + sigma ** 2; r = torch.softmax(W.log() - .5 * (x[..., None] - M) ** 2 / v - .5 * v.log(), -1)
    return (r * (S ** 2 * x[..., None] + sigma ** 2 * M) / v).sum(-1)
def score(x, sigma):      # d/dx log p_sigma(x), written directly from the mixture density
    v = S ** 2 + sigma ** 2; r = torch.softmax(W.log() - .5 * (x[..., None] - M) ** 2 / v - .5 * v.log(), -1)
    return (r * (M - x[..., None]) / v).sum(-1)

# 1. Tweedie: E[x0 | x] = x + sigma^2 * score(x). Check it against a brute-force average of real pairs.
sigma = 1.0; x0 = data(4_000_000); x = x0 + sigma * torch.randn_like(x0)
print("x     E[x0|x] measured   x + sigma^2 score(x)")
for c in (-3., -1., 0., 1., 2.5):
    m = x0[(x - c).abs() < 0.02].mean(); t = c + sigma ** 2 * score(torch.tensor([c], dtype=D), sigma)[0]
    print(f"{c:+.1f}  {m:+.4f}            {t:+.4f}"); assert abs(m - t) < 0.02
# The score by finite differences of log p, so the "direct" score above is not just assumed.
def logp(x, sigma): v = S ** 2 + sigma ** 2; return torch.logsumexp(W.log() - .5 * (x[..., None] - M) ** 2 / v - .5 * (v * 2 * torch.pi).log(), -1)
h = 1e-5; xs = torch.linspace(-4, 4, 81, dtype=D); fd = (logp(xs + h, sigma) - logp(xs - h, sigma)) / (2 * h)
print(f"max |finite difference - score| on [-4,4]: {(fd - score(xs, sigma)).abs().max():.2e}")
assert (fd - score(xs, sigma)).abs().max() < 1e-6

# 2. Vincent 2011: explicit and denoising score matching differ by a constant that does not depend on the model.
# ESM = E|s(x) - true score(x)|^2.  DSM = E|s(x) - (x0 - x)/sigma^2|^2.
n = 2_000_000; x0 = data(n); x = x0 + sigma * torch.randn(n, dtype=D); target = (x0 - x) / sigma ** 2; true = score(x, sigma)
models = {"s(x)=0": lambda x: 0 * x, "s(x)=-x": lambda x: -x, "s(x)=sin(x)": lambda x: x.sin(), "s(x)=exact": lambda x: score(x, sigma)}
print("\nmodel         ESM       DSM       DSM-ESM")
gaps = []
for k, s in models.items():
    e = ((s(x) - true) ** 2).mean().item(); d = ((s(x) - target) ** 2).mean().item(); gaps.append(d - e); print(f"{k:13s} {e:.4f}    {d:.4f}    {d - e:.4f}")
assert max(gaps) - min(gaps) < 0.01

# 3. A network trained only on DSM learns the true score, without ever seeing it.
net = torch.nn.Sequential(torch.nn.Linear(1, 64), torch.nn.SiLU(), torch.nn.Linear(64, 64), torch.nn.SiLU(), torch.nn.Linear(64, 1)); opt = torch.optim.Adam(net.parameters(), 3e-3)
for i in range(2000):
    x0b = data(1024).float(); xb = x0b + sigma * torch.randn(1024); loss = ((net(xb[:, None])[:, 0] - (x0b - xb) / sigma ** 2) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step()
with torch.no_grad():
    xt = (data(50000) + sigma * torch.randn(50000, dtype=D)); err = ((net(xt.float()[:, None])[:, 0].double() - score(xt, sigma)) ** 2).mean().sqrt().item()
print(f"\nRMS(net - true score) after training on DSM only: {err:.4f}   (RMS of the score itself: {(score(xt, sigma) ** 2).mean().sqrt():.4f})")
assert err < 0.15

# 4. The same marginals by two routes. With sigma(t)=t the reverse SDE is dx = -2 t score dt + sqrt(2t) dW and the probability-flow ODE is dx = -t score dt.
def grid(n, smax=20., smin=.002, rho=7.): r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(smax ** (1 / rho) + r * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
def ode(x, s):
    for i in range(len(s) - 1): x = x + (x - denoiser(x, s[i])) / s[i] * (s[i + 1] - s[i])
    return x
def sde(x, s, g):
    for i in range(len(s) - 1):
        x = x + 2 * (x - denoiser(x, s[i])) / s[i] * (s[i + 1] - s[i])      # drift doubled against the ODE
        if s[i + 1] > 0: x = x + (s[i] ** 2 - s[i + 1] ** 2).sqrt() * torch.randn(x.shape, dtype=D, generator=g)
    return x
def w1(x): return (x.sort().values - data(len(x)).sort().values).abs().mean().item()
s = grid(400); start = 20. * torch.randn(20000, dtype=D)
g1, g2 = torch.Generator().manual_seed(1), torch.Generator().manual_seed(2)
a = ode(start, s); b = ode(start, s); c = sde(start, s, g1); d = sde(start, s, g2)
print(f"\nWasserstein-1 to data   ODE: {w1(a):.4f}   SDE: {w1(c):.4f}   floor (two real samples): {(data(20000).sort().values - data(20000).sort().values).abs().mean():.4f}")
print(f"same start, run twice   ODE RMS difference: {((a - b) ** 2).mean().sqrt():.4f}   SDE RMS difference: {((c - d) ** 2).mean().sqrt():.4f}")
assert w1(a) < .08 and w1(c) < .05 and ((a - b) ** 2).mean() == 0 and ((c - d) ** 2).mean() > .1
