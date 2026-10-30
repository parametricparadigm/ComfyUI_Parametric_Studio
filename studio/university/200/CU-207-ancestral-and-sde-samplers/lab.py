# CU-207 lab: the ancestral step, its bookkeeping, and how it behaves as steps grow.
# Run: python lab.py  (CPU only, about 10 s).
import torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
W, M, S = torch.tensor([.3, .7], dtype=D), torch.tensor([-2., 1.5], dtype=D), torch.tensor([.3, .5], dtype=D)
def data(n): k = torch.multinomial(W, n, True); return M[k] + S[k] * torch.randn(n, dtype=D)
def den(x, sigma):
    v = S ** 2 + sigma ** 2; r = torch.softmax(W.log() - .5 * (x[..., None] - M) ** 2 / v - .5 * v.log(), -1)
    return (r * (S ** 2 * x[..., None] + sigma ** 2 * M) / v).sum(-1)
def karras(n, smin=.002, smax=80., rho=7.): r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(smax ** (1 / rho) + r * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
def anc_step(a, b, eta=1.):          # get_ancestral_step
    up = min(b, eta * (b ** 2 * (a ** 2 - b ** 2) / a ** 2) ** .5); return (b ** 2 - up ** 2) ** .5, up
print("from    to      sigma_down  sigma_up   down^2+up^2  to^2")
for a, b in ((14., 8.), (8., 3.), (3., 1.), (1., .2)):
    d, u = anc_step(a, b); print(f"{a:<7.1f} {b:<7.1f} {d:<11.4f} {u:<10.4f} {d ** 2 + u ** 2:<12.4f} {b ** 2:.4f}"); assert abs(d ** 2 + u ** 2 - b ** 2) < 1e-9
def euler(x, s, g=None):
    for i in range(len(s) - 1): x = x + (x - den(x, s[i])) / s[i] * (s[i + 1] - s[i])
    return x
def ancestral(x, s, g, eta=1.):
    for i in range(len(s) - 1):
        d = den(x, s[i])
        if s[i + 1] == 0: x = d; continue
        dn, up = anc_step(s[i].item(), s[i + 1].item(), eta); x = x + (x - d) / s[i] * (dn - s[i]) + up * torch.randn(x.shape, dtype=D, generator=g)
    return x
def w1(x): return (x.sort().values - data(len(x)).sort().values).abs().mean().item()

# 1. Marginals: both target the same data distribution.
start = 80. * torch.randn(20000, dtype=D)
print("\nsteps  W1 euler   W1 ancestral")
wa = {}
for n in (10, 20, 40, 80, 320):
    wa[n] = w1(ancestral(start, karras(n), torch.Generator().manual_seed(n))); print(f"{n:<6d} {w1(euler(start, karras(n))):.4f}     {wa[n]:.4f}")
print(f"floor  {(data(20000).sort().values - data(20000).sort().values).abs().mean():.4f}")
assert wa[320] < .05

# 2. Convergence of one image. Same noise and sampler seed at N and 2N steps: does the answer settle?
print("\nsame start, N against 2N steps, RMS change of the result")
print("N      euler     ancestral  ancestral(eta=0.5)")
last = None
for n in (10, 20, 40, 80, 160):
    e = ((euler(start, karras(n)) - euler(start, karras(2 * n))) ** 2).mean().sqrt().item()
    a = ((ancestral(start, karras(n), torch.Generator().manual_seed(1)) - ancestral(start, karras(2 * n), torch.Generator().manual_seed(1))) ** 2).mean().sqrt().item()
    h = ((ancestral(start, karras(n), torch.Generator().manual_seed(1), .5) - ancestral(start, karras(2 * n), torch.Generator().manual_seed(1), .5)) ** 2).mean().sqrt().item()
    print(f"{n:<6d} {e:.4f}    {a:.4f}     {h:.4f}"); last = (e, a)
assert last[0] < .05 and last[1] > 1.

# 2b. A fixed noise path. This is the job of BrownianTreeNoiseSampler: the noise between two sigmas depends only on those sigmas, not on the step count.
# Grids are nested in log sigma so that a coarse step adds up exactly the fine increments of the same path.
F = 1280; fine = torch.logspace(torch.log10(torch.tensor(80.)), torch.log10(torch.tensor(.002)), F + 1, dtype=D); g = torch.Generator().manual_seed(11); st = 80. * torch.randn(2000, dtype=D, generator=g)
dW = torch.randn(F, 2000, dtype=D, generator=g) * (fine[:-1] ** 2 - fine[1:] ** 2).sqrt()[:, None]
def sde_path(n):
    x = st; k = F // n
    for i in range(n):
        a, b = fine[i * k], fine[(i + 1) * k]; x = x + 2 * (x - den(x, a)) / a * (b - a) + dW[i * k:(i + 1) * k].sum(0)
    return den(x, fine[-1])
print("\nSDE sampler on one fixed Brownian path, RMS change from N to 2N steps")
ch = {}
for n in (10, 20, 40, 80, 160, 320, 640): ch[n] = ((sde_path(n) - sde_path(2 * n)) ** 2).mean().sqrt().item(); print(f"{n:<6d} {ch[n]:.4f}")
assert ch[640] < ch[10] / 3

# 3. Noise forgets the start. Two different starting noises: how much of the final value still depends on where you began?
s = karras(80); a1 = 80. * torch.randn(20000, dtype=D); a2 = a1 + 8. * torch.randn(20000, dtype=D)   # start 2 is a nudge of start 1 by a tenth of sigma_max
g = lambda: torch.Generator().manual_seed(3)
print(f"\nnudged start, same sampler seed: RMS change of the result   euler {((euler(a1, s) - euler(a2, s)) ** 2).mean().sqrt():.4f}   ancestral {((ancestral(a1, s, g()) - ancestral(a2, s, g())) ** 2).mean().sqrt():.4f}")

# 4. An imperfect denoiser: a fixed small shrink, the kind of error a real network makes. Stochasticity can absorb some of it.
def bad(x, sigma, k=.03): return den(x, sigma) + k * (1 / (1 + sigma)) * 2.0 * torch.tanh(x)    # adds a bias towards the outer modes
def run(step, s, g):
    x = 80. * torch.randn(40000, dtype=D, generator=torch.Generator().manual_seed(5))
    for i in range(len(s) - 1):
        d = bad(x, s[i])
        if s[i + 1] == 0: x = d; continue
        if step == "euler": x = x + (x - d) / s[i] * (s[i + 1] - s[i])
        else: dn, up = anc_step(s[i].item(), s[i + 1].item()); x = x + (x - d) / s[i] * (dn - s[i]) + up * torch.randn(x.shape, dtype=D, generator=g)
    return x
g5 = torch.Generator().manual_seed(9)
print(f"biased denoiser, 80 steps, W1 to data   euler {w1(run('euler', s, g5)):.4f}   ancestral {w1(run('anc', s, g5)):.4f}")
