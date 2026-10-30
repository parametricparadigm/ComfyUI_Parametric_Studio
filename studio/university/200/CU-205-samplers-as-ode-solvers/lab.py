# CU-205 lab: three samplers against the exact probability-flow ODE, with the exact denoiser in place of a network.
# Run: python lab.py  (CPU only, about 10 s).
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
W, M, S = torch.tensor([.3, .7], dtype=D), torch.tensor([-2., 1.5], dtype=D), torch.tensor([.3, .5], dtype=D)
def data(n): k = torch.multinomial(W, n, True); return M[k] + S[k] * torch.randn(n, dtype=D)
NFE = [0]
def denoiser(x, sigma):
    NFE[0] += 1; v = S ** 2 + sigma ** 2; r = torch.softmax(W.log() - .5 * (x[..., None] - M) ** 2 / v - .5 * v.log(), -1)
    return (r * (S ** 2 * x[..., None] + sigma ** 2 * M) / v).sum(-1)
def karras(n, smin=.002, smax=80., rho=7.):   # same formula as get_sigmas_karras
    r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(smax ** (1 / rho) + r * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
def euler(x, s):
    for i in range(len(s) - 1): x = x + (x - denoiser(x, s[i])) / s[i] * (s[i + 1] - s[i])
    return x
def heun(x, s):
    for i in range(len(s) - 1):
        d = (x - denoiser(x, s[i])) / s[i]; dt = s[i + 1] - s[i]
        if s[i + 1] == 0: x = x + d * dt                                      # last step: no corrector, as in the paper
        else: x2 = x + d * dt; d2 = (x2 - denoiser(x2, s[i + 1])) / s[i + 1]; x = x + (d + d2) / 2 * dt
    return x
def dpmpp2m(x, s):
    old = None
    for i in range(len(s) - 1):
        den = denoiser(x, s[i])
        if s[i + 1] == 0: x = den; break
        t, tn = -s[i].log(), -s[i + 1].log(); h = tn - t
        if old is None: x = s[i + 1] / s[i] * x - (-h).expm1() * den
        else:
            r = (t + s[i - 1].log()) / h; dd = (1 + 1 / (2 * r)) * den - (1 / (2 * r)) * old
            x = s[i + 1] / s[i] * x - (-h).expm1() * dd
        old = den
    return x

start = 80. * torch.randn(4000, dtype=D)
NFE[0] = 0; ref = heun(start, karras(6000))     # the "true" endpoint of each path
print(f"reference: Heun with 6000 steps, {NFE[0]} denoiser calls")
samplers = (("euler", euler), ("heun", heun), ("dpmpp_2m", dpmpp2m))
Ns = (5, 10, 20, 40, 80, 160, 320, 640); table = {}
print("\nmedian |error| of the final sample against the reference, and share of samples that landed in the wrong mode")
print("steps  " + "".join(f"{k:>10s} NFE  wrong  " for k, _ in samplers))
for n in Ns:
    row = f"{n:<6d} "
    for k, f in samplers:
        NFE[0] = 0; x = f(start, karras(n)); table[k, n] = (x - ref).abs().median().item(); row += f"{table[k, n]:10.6f} {NFE[0]:<5d}{((x > 0) != (ref > 0)).double().mean():.4f} "
    print(row)
print("\nmeasured order: slope of log(median error) against log(steps)")
print("sampler    10-40   40-160  160-640")
order = lambda k, a, b: math.log(table[k, a] / table[k, b]) / math.log(b / a)
for k, _ in samplers: print(f"{k:9s}  {order(k, 10, 40):.2f}    {order(k, 40, 160):.2f}    {order(k, 160, 640):.2f}")
assert 0.8 < order("euler", 160, 640) < 1.2 and order("heun", 40, 160) > 1.7 and order("dpmpp_2m", 40, 160) > 1.7
print("\nsame budget of about 20 denoiser calls, distance of the whole sample set from the data")
def w1(x): return (x.sort().values - data(len(x)).sort().values).abs().mean().item()
big = 80. * torch.randn(40000, dtype=D)
for k, f, n in (("euler", euler, 20), ("heun", heun, 10), ("dpmpp_2m", dpmpp2m, 20)):
    NFE[0] = 0; x = f(big, karras(n)); print(f"{k:9s} {n:>3d} steps  {NFE[0]:>3d} calls  W1 = {w1(x):.4f}")
print(f"floor, two real samples of this size: W1 = {(data(40000).sort().values - data(40000).sort().values).abs().mean():.4f}")
# Solvers can only be compared on the same ODE. With guidance > 1 the ODE changes: see CU-208.
