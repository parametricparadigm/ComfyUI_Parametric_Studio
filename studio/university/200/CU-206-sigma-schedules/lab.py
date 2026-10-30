# CU-206 lab: the ComfyUI scheduler formulas, tested on one ODE with the exact denoiser.
# Run: python lab.py  (CPU only, about 10 s).
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
# The discrete SD 1.x noise levels, as ModelSamplingDiscrete builds them.
beta = torch.linspace(0.00085 ** .5, 0.012 ** .5, 1000, dtype=D) ** 2; ab = torch.cumprod(1 - beta, 0); SIG = ((1 - ab) / ab).sqrt(); LS = SIG.log()
smin, smax = SIG[0].item(), SIG[-1].item()
def sigma_at(t):                                   # log-linear interpolation between the discrete levels
    t = t.clamp(0, 999); lo = t.floor().long(); hi = t.ceil().long(); w = t - lo; return ((1 - w) * LS[lo] + w * LS[hi]).exp()
def tail(s): return torch.cat([s, torch.zeros(1, dtype=D)])
def simple(n): return tail(torch.stack([SIG[-(1 + int(i * 1000 / n))] for i in range(n)]))
def normal(n): return tail(sigma_at(torch.linspace(999, 0, n, dtype=D)))
def sgm_uniform(n): return tail(sigma_at(torch.linspace(999, 0, n + 1, dtype=D)[:-1]))
def karras(n, rho=7.): r = torch.linspace(0, 1, n, dtype=D); return tail((smax ** (1 / rho) + r * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho)
def exponential(n): return tail(torch.linspace(math.log(smax), math.log(smin), n, dtype=D).exp())
def kl_optimal(n): a = torch.arange(n, dtype=D) / (n - 1); return tail((a * math.atan(smin) + (1 - a) * math.atan(smax)).tan())
def beta_sched(n, al=.6, be=.6):                   # inverse CDF of Beta(0.6, 0.6) on a fine grid, in place of scipy
    g = (torch.arange(2_000_000, dtype=D) + .5) / 2_000_000; c = (g ** (al - 1) * (1 - g) ** (be - 1)).cumsum(0); c = c / c[-1]
    q = 1 - torch.arange(n, dtype=D) / n; ts = (g[torch.searchsorted(c, q).clamp(max=len(g) - 1)] * 999).round().long(); return tail(torch.stack([SIG[t] for t in ts.unique_consecutive()]))
SCHED = {"normal": normal, "simple": simple, "sgm_uniform": sgm_uniform, "karras": karras, "exponential": exponential, "kl_optimal": kl_optimal, "beta": beta_sched}
print("10 steps, first six sigmas and the smallest non-zero one")
for k, f in SCHED.items():
    s = f(10); print(f"{k:12s} " + " ".join(f"{v:7.3f}" for v in s[:6]) + f"  ... {s[-2]:.3f}")
s = karras(10); assert abs(s[0] - 14.6146) < 1e-3 and abs(s[-2] - 0.0292) < 1e-3 and s[-1] == 0

W, M, S = torch.tensor([.3, .7], dtype=D), torch.tensor([-1.2, .9], dtype=D), torch.tensor([.3, .4], dtype=D)   # data with a latent-like spread of about 1
def den(x, sigma):
    v = S ** 2 + sigma ** 2; r = torch.softmax(W.log() - .5 * (x[..., None] - M) ** 2 / v - .5 * v.log(), -1)
    return (r * (S ** 2 * x[..., None] + sigma ** 2 * M) / v).sum(-1)
def euler(x, s):
    for i in range(len(s) - 1): x = x + (x - den(x, s[i])) / s[i] * (s[i + 1] - s[i])
    return x
def dpmpp2m(x, s):
    old = None
    for i in range(len(s) - 1):
        d = den(x, s[i])
        if s[i + 1] == 0: x = d; break
        t, tn = -s[i].log(), -s[i + 1].log(); h = tn - t
        if old is None: x = s[i + 1] / s[i] * x - (-h).expm1() * d
        else: r = (t + s[i - 1].log()) / h; x = s[i + 1] / s[i] * x - (-h).expm1() * ((1 + 1 / (2 * r)) * d - 1 / (2 * r) * old)
        old = d
    return x
# As ComfyUI does at full denoise: scale the first noise by sqrt(1 + sigma_max^2), not sigma_max.
start = (1 + smax ** 2) ** .5 * torch.randn(20000, dtype=D); ref = euler(start, karras(6000))
print("\nRMS error against a 6000-step reference")
print("schedule       euler@10   euler@20   dpm2m@10   dpm2m@20")
res = {}
for k, f in SCHED.items():
    r = [((g(start, f(n)) - ref) ** 2).mean().sqrt().item() for g in (euler, dpmpp2m) for n in (10, 20)]; res[k] = r
    print(f"{k:12s}   " + "   ".join(f"{v:.5f}" for v in r))
assert res["karras"][2] < res["simple"][2]

# Flow-model schedules. time_snr_shift(a, t) = a t / (1 + (a-1) t) spends more of the same steps at high noise.
print("\nflow schedule, 8 steps, sigma = shift(linspace(1, 0))")
def flow(n, a): t = torch.linspace(1, 0, n + 1, dtype=D); return a * t / (1 + (a - 1) * t)
for a in (1., 1.5, 3., 6.): print(f"shift {a:<4.1f}" + " ".join(f"{v:6.3f}" for v in flow(8, a)[:8]))
def vel(x, t): y = x / (1 - t); sg = t / (1 - t); return (x - den(y, sg)) / t
def feuler(x, s):
    for i in range(len(s) - 1):
        t = s[i].clamp(max=1 - 1e-9); x = x + vel(x, t) * (s[i + 1] - s[i])
    return x
st = torch.randn(20000, dtype=D); rf = feuler(st, flow(6000, 1.))
print("\nEuler RMS error on this 1-D toy, against a reference")
print("steps  " + "  ".join(f"shift={a:<3.1f}" for a in (1., 1.5, 3., 6.)))
for n in (4, 8, 16, 32): print(f"{n:<6d} " + "  ".join(f"{((feuler(st, flow(n, a)) - rf) ** 2).mean().sqrt():.5f}  " for a in (1., 1.5, 3., 6.)))
# ModelSamplingFlux turns image size into a shift: mu grows linearly in the token count.
print("\nFLUX mu = base + (max-base) * (tokens-256)/(4096-256), with base_shift 0.5, max_shift 1.15, exp(mu) is the effective shift")
for side in (512, 768, 1024, 1536):
    tok = (side / 16) ** 2; mu = .5 + (1.15 - .5) * (tok - 256) / (4096 - 256); print(f"{side:>5d} px  {int(tok):>5d} tokens  mu={mu:.3f}  exp(mu)={math.exp(mu):.3f}")
