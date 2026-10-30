# CU-202 lab: the forward process, its closed form, and a tiny DDPM trained on a CPU.
# Run: python lab.py  (CPU only, about 20 s). Prints the same numbers every time.
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64

# 1. Two noise schedules: Ho et al. 2020 (linear beta) and Stable Diffusion 1.x ("scaled linear").
def alphabar(betas): return torch.cumprod(1 - betas, 0)
ddpm = alphabar(torch.linspace(1e-4, 0.02, 1000, dtype=D))
sd = alphabar(torch.linspace(0.00085 ** 0.5, 0.012 ** 0.5, 1000, dtype=D) ** 2)
print("schedule     alphabar_T   SNR_T       sigma_min  sigma_max")
for name, a in (("ddpm linear", ddpm), ("sd scaled", sd)):
    s = ((1 - a) / a).sqrt(); print(f"{name:12s} {a[-1]:.4e}  {(a[-1] / (1 - a[-1])):.4e}  {s[0]:.4f}     {s[-1]:.2f}")
assert abs(((1 - sd) / sd).sqrt()[-1] - 14.6146) < 0.001   # the sigma_max ComfyUI reports for SD 1.x

# 2. Data: a 1-D mixture of two Gaussians.
W, M, S = torch.tensor([.3, .7], dtype=D), torch.tensor([-2., 1.5], dtype=D), torch.tensor([.3, .5], dtype=D)
def data(n): k = torch.multinomial(W, n, True); return M[k] + S[k] * torch.randn(n, dtype=D)

# 3. Closed form against simulation. Run the 1000-step Markov chain for real, then compare with one jump.
betas = torch.linspace(1e-4, 0.02, 1000, dtype=D); x = data(100_000); x0 = x.clone()
print("\nt     chain mean  chain var   jump mean   jump var")
for t in range(1000):
    x = (1 - betas[t]).sqrt() * x + betas[t].sqrt() * torch.randn_like(x)
    if t + 1 in (100, 500, 1000):
        a = ddpm[t]; j = a.sqrt() * x0 + (1 - a).sqrt() * torch.randn_like(x0)
        print(f"{t + 1:<5d} {x.mean():+.4f}     {x.var():.4f}      {j.mean():+.4f}     {j.var():.4f}")
        assert abs(x.var() - j.var()) < 0.02
print(f"variance the formula predicts at t=1000: {ddpm[-1] * x0.var() + 1 - ddpm[-1]:.4f}")

# 4. Train an epsilon predictor with L_simple = E || eps - eps_theta(x_t, t) ||^2 (Ho et al. 2020, eq. 14).
class Net(torch.nn.Module):
    def __init__(s, w=128):
        super().__init__(); s.f = torch.nn.Sequential(torch.nn.Linear(10, w), torch.nn.SiLU(), torch.nn.Linear(w, w), torch.nn.SiLU(), torch.nn.Linear(w, w), torch.nn.SiLU(), torch.nn.Linear(w, 1))
    def forward(s, x, t):
        f = t[:, None] / 1000 * torch.tensor([1, 2, 4, 8], dtype=torch.float32) * math.pi
        return s.f(torch.cat([x[:, None], t[:, None] / 1000, f.sin(), f.cos()], 1))[:, 0]
net = Net(); opt = torch.optim.Adam(net.parameters(), 2e-3); ab = ddpm.float()
print("\nstep   loss (a perfect guesser that ignores x scores 1.0)")
for i in range(2000):
    x0b = data(1024).float(); t = torch.randint(0, 1000, (1024,)); e = torch.randn(1024)
    xt = ab[t].sqrt() * x0b + (1 - ab[t]).sqrt() * e
    loss = ((net(xt, t.float()) - e) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step()
    if (i + 1) % 500 == 0: print(f"{i + 1:<6d} {loss.item():.4f}")

# 5. The exact answer exists for this data, so the network can be graded against it.
def eps_exact(x, t):
    a = ddpm[t]; sigma = ((1 - a) / a).sqrt(); y = x / a.sqrt(); v = S ** 2 + sigma ** 2     # y = x0 + sigma * eps
    r = torch.softmax(W.log() - .5 * (y[:, None] - M) ** 2 / v - .5 * v.log(), 1); x0 = (r * (S ** 2 * y[:, None] + sigma ** 2 * M) / v).sum(1)
    return (y - x0) / sigma
print("\nt     RMS(net eps - exact eps)")
with torch.no_grad():
    for t in (10, 100, 300, 600, 900):
        x = ddpm[t].sqrt() * data(20000) + (1 - ddpm[t]).sqrt() * torch.randn(20000, dtype=D)
        print(f"{t:<5d} {((net(x.float(), torch.full((20000,), float(t))).double() - eps_exact(x, t)) ** 2).mean().sqrt():.4f}")

# 6. Ancestral DDPM sampling, Algorithm 2 of the paper, with both predictors.
def sample(pred, n=8000):
    x = torch.randn(n, dtype=D)
    for t in range(999, -1, -1):
        a, b, abar = 1 - betas[t], betas[t], ddpm[t]
        x = (x - b / (1 - abar).sqrt() * pred(x, t)) / a.sqrt()
        if t > 0: x = x + b.sqrt() * torch.randn_like(x)
    return x
def w1(x): return (x.sort().values - data(len(x)).sort().values).abs().mean().item()
with torch.no_grad():
    xe = sample(eps_exact); xn = sample(lambda x, t: net(x.float(), torch.full((len(x),), float(t))).double())
floor = (data(8000).sort().values - data(8000).sort().values).abs().mean().item()
print(f"\nWasserstein-1 to the data  exact eps: {w1(xe):.4f}   trained net: {w1(xn):.4f}   two real samples: {floor:.4f}")
print(f"fraction in the right-hand mode (truth 0.700)  exact: {(xe > 0).double().mean():.3f}   trained: {(xn > 0).double().mean():.3f}")
assert w1(xe) < 0.1 and w1(xn) < 0.25
