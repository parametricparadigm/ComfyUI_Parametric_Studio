# CU-208 lab: CFG on a problem where every density is known, against the tilted target it is usually said to sample.
# Run: python lab.py  (CPU only, about 10 s).
import torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
# Two classes. The conditional is class B, the unconditional is the whole mixture.
W = torch.tensor([.5, .5], dtype=D); M = torch.tensor([-1., 1.5], dtype=D); S = torch.tensor([.5, .5], dtype=D)
def den_mix(x, sigma, w, m, s):
    v = s ** 2 + sigma ** 2; r = torch.softmax(w.log() - .5 * (x[..., None] - m) ** 2 / v - .5 * v.log(), -1)
    return (r * (s ** 2 * x[..., None] + sigma ** 2 * m) / v).sum(-1)
def den_u(x, sigma): return den_mix(x, sigma, W, M, S)
def den_c(x, sigma): return den_mix(x, sigma, torch.ones(1, dtype=D), M[1:], S[1:])
def cfg(x, sigma, w): u = den_u(x, sigma); return u + (den_c(x, sigma) - u) * w   # exactly cfg_function, in denoised space
def karras(n, smin=.002, smax=80., rho=7.): r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(smax ** (1 / rho) + r * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
def heun(x, s, w):
    for i in range(len(s) - 1):
        d = (x - cfg(x, s[i], w)) / s[i]; dt = s[i + 1] - s[i]
        if s[i + 1] == 0: x = x + d * dt
        else: x2 = x + d * dt; d2 = (x2 - cfg(x2, s[i + 1], w)) / s[i + 1]; x = x + (d + d2) / 2 * dt
    return x
# The density CFG is usually said to sample: p_w(x) proportional to p(x) p(c|x)^w, which is p(x)^(1-w) p(x|c)^w.
xs = torch.linspace(-12, 16, 56001, dtype=D); dx = xs[1] - xs[0]
def normal(x, m, s): return (-.5 * ((x - m) / s) ** 2).exp() / (s * (2 * torch.pi) ** .5)
def tilted(w):
    pc = normal(xs, M[1], S[1]); pu = .5 * normal(xs, M[0], S[0]) + .5 * pc; log = w * pc.log() + (1 - w) * pu.log(); p = (log - log.max()).exp(); p = p / (p.sum() * dx); m = (p * xs).sum() * dx; return m.item(), (((xs - m) ** 2 * p).sum() * dx).sqrt().item()
start = 80. * torch.randn(40000, dtype=D); s = karras(200)
print("w      sample mean  sample std   tilted mean  tilted std")
rows = {}
for w in (1., 1.5, 2., 3., 5., 7.5, 12.):
    x = heun(start, s, w); tm, ts = tilted(w); rows[w] = (x.mean().item(), x.std().item(), tm, ts)
    print(f"{w:<6.1f} {x.mean():<12.4f} {x.std():<12.4f} {tm:<12.4f} {ts:.4f}")
assert abs(rows[1.][0] - 1.5) < .02 and abs(rows[1.][1] - .5) < .02        # w = 1 is the plain conditional
assert abs(rows[7.5][0] - rows[7.5][2]) > .5 or abs(rows[7.5][1] - rows[7.5][3]) > .05   # at high w the two differ
# Where the push happens: the size of the guidance term along the path.
print("\nsigma    guidance term |D_c - D_u| at x = 1.5 + sigma     the same times 7.5")
for sg in (40., 10., 3., 1., .3, .03):
    x = torch.tensor([1.5 + sg], dtype=D); g = (den_c(x, sg) - den_u(x, sg)).abs().item(); print(f"{sg:<8.2f} {g:<47.4f} {g * 7.5:.4f}")
# Range: how far the guided denoised prediction leaves the data range, per step. This is why high CFG burns.
print("\nw      largest |predicted x0| along the path   true data range is about +-3")
for w in (1., 3., 7.5, 15., 30.):
    x = start[:5000].clone(); mx = 0.
    for i in range(len(s) - 1):
        d = cfg(x, s[i], w); mx = max(mx, d.abs().quantile(.999).item()); x = x + (x - d) / s[i] * (s[i + 1] - s[i])
    print(f"{w:<6.1f} {mx:.2f}")
    if w == 30.: assert mx > 10
# Cost: cfg != 1 runs the model twice per step. sampling_function skips the second run when cond_scale is 1.
print("\nmodel calls per step: cfg=1 -> 1, cfg!=1 -> 2.  20 steps of Euler: 20 calls against 40 calls.")
