# CU-204 lab: conditional versus marginal velocity, Euler error on a curved field, and one step of reflow.
# Run: python lab.py  (CPU only, about 10 s).
import torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
W, M, S = torch.tensor([.3, .7], dtype=D), torch.tensor([-2., 1.5], dtype=D), torch.tensor([.3, .5], dtype=D)
def data(n): k = torch.multinomial(W, n, True); return M[k] + S[k] * torch.randn(n, dtype=D)
def denoiser(y, sigma):
    v = S ** 2 + sigma ** 2; r = torch.softmax(W.log() - .5 * (y[..., None] - M) ** 2 / v - .5 * v.log(), -1)
    return (r * (S ** 2 * y[..., None] + sigma ** 2 * M) / v).sum(-1)
# x_t = (1-t) x0 + t e. Dividing by (1-t) gives x0 + sigma e with sigma = t/(1-t), so the exact E[x0 | x_t] is known.
def x0hat(x, t): return denoiser(x / (1 - t), t / (1 - t))
def velocity(x, t): return (x - x0hat(x, t)) / t                       # E[e - x0 | x_t = x], the marginal field

# 1. One pair flies straight: its velocity e - x0 is constant by construction. The marginal field is the average.
n = 4_000_000; x0 = data(n); e = torch.randn(n, dtype=D)
print("t    x     E[e-x0 | x_t=x] measured   marginal u(x,t)")
for t, c in ((.2, -1.), (.5, 0.), (.5, 1.), (.8, .5)):
    x = (1 - t) * x0 + t * e; m = (e - x0)[(x - c).abs() < 0.01].mean(); u = velocity(torch.tensor([c], dtype=D), t)[0]
    print(f"{t:.1f}  {c:+.1f}  {m:+.4f}                    {u:+.4f}"); assert abs(m - u) < 0.03

# 2. Follow the marginal ODE from noise to data, and measure how far the velocity moves along one path.
def integrate(x, n, record=False):
    ts = torch.linspace(1, 0, n + 1, dtype=D); vs = []
    for i in range(n):
        v = velocity(x, ts[i].clamp(max=1 - 1e-9))   # at t=1 the field is x - E[x0]
        if record: vs.append(v.clone())
        x = x + v * (ts[i + 1] - ts[i])
    return (x, torch.stack(vs)) if record else x
start = torch.randn(20000, dtype=D); ref, vs = integrate(start, 4000, record=True)
print(f"\nalong one marginal path, RMS change of velocity from t=1 to t=0: {((vs[-1] - vs[0]) ** 2).mean().sqrt():.3f}  (zero would be a straight line)")
assert ((vs[-1] - vs[0]) ** 2).mean().sqrt() > 0.5

# 3. So Euler is not exact. Error against a 4000-step reference, against the case where the data is one point.
print("\nsteps  Euler RMS error   W1 to data   error if data were one point")
for n_ in (1, 2, 4, 8, 16, 32, 64):
    x = integrate(start, n_); er = ((x - ref) ** 2).mean().sqrt().item(); w = (x.sort().values - data(len(x)).sort().values).abs().mean().item()
    # one Dirac at 1.5: u(x,t) = (x - 1.5)/t is constant along each straight path, so Euler lands exactly
    y = start.clone(); ts = torch.linspace(1, 0, n_ + 1, dtype=D)
    for i in range(n_): y = y + (y - 1.5) / ts[i] * (ts[i + 1] - ts[i])
    print(f"{n_:<6d} {er:.4f}            {w:.4f}       {(y - 1.5).abs().max():.1e}")
    if n_ == 1: assert er > 0.3
    assert (y - 1.5).abs().max() < 1e-9

# 4. Rectification. Pair each noise with where its ODE path lands, then fly straight between those pairs.
pairs_x1 = start; pairs_x0 = ref
cost_indep = ((data(20000) - torch.randn(20000, dtype=D)) ** 2).mean().item(); cost_rect = ((pairs_x1 - pairs_x0) ** 2).mean().item()
cost_ot = ((pairs_x1.sort().values - pairs_x0.sort().values) ** 2).mean().item()
order = pairs_x1.argsort(); inversions = (pairs_x0[order][1:] < pairs_x0[order][:-1]).double().mean().item()
print(f"\ntransport cost E|x1-x0|^2   independent pairs: {cost_indep:.3f}   rectified pairs: {cost_rect:.3f}   optimal (sorted, 1-D): {cost_ot:.3f}")
print(f"fraction of neighbouring paths that cross after rectification: {inversions:.5f}")
assert cost_rect < cost_indep and abs(cost_rect - cost_ot) < .02 and inversions == 0
# A student network regressing x1 - x0 on the rectified line, compared with one on independent pairs, both judged at one Euler step.
def train(pairfn, steps=2500):
    net = torch.nn.Sequential(torch.nn.Linear(2, 128), torch.nn.SiLU(), torch.nn.Linear(128, 128), torch.nn.SiLU(), torch.nn.Linear(128, 128), torch.nn.SiLU(), torch.nn.Linear(128, 1)); opt = torch.optim.Adam(net.parameters(), 2e-3)
    for i in range(steps):
        x1b, x0b = pairfn(1024); t = torch.rand(1024); xt = (1 - t) * x0b + t * x1b
        loss = ((net(torch.stack([xt, t], 1))[:, 0] - (x1b - x0b)) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step()
    return net
def indep(n): return torch.randn(n), data(n).float()
def rect(n): i = torch.randint(0, 20000, (n,)); return pairs_x1[i].float(), pairs_x0[i].float()
n1, n2 = train(indep), train(rect)
with torch.no_grad():
    z = torch.randn(20000, dtype=D).float()
    one = lambda net: z - net(torch.stack([z, torch.ones_like(z)], 1))[:, 0]
    a, b = one(n1).double(), one(n2).double()
wa = (a.sort().values - data(20000).sort().values).abs().mean().item(); wb = (b.sort().values - data(20000).sort().values).abs().mean().item()
print(f"one Euler step, W1 to data   flow matching net: {wa:.4f}   rectified (reflow) net: {wb:.4f}")
assert wb < wa / 2
