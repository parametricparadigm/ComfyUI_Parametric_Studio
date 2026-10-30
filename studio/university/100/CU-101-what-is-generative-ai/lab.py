# CU-101 lab: three "generative models" of the same data, from a copying machine to a real fit.
# Run: python lab.py  (CPU only, a few seconds).
import math, torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
def truth(n): k = torch.multinomial(torch.tensor([.3, .7], dtype=D), n, True); return torch.tensor([-2., 1.5], dtype=D)[k] + torch.tensor([.3, .5], dtype=D)[k] * torch.randn(n, dtype=D)
train, test = truth(2000), truth(20000)
def w1(x): return (x.sort().values - truth(len(x)).sort().values).abs().mean().item()
def gauss_logp(x, m, s): return -.5 * ((x - m) / s) ** 2 - s.log() - .5 * math.log(2 * math.pi)

# Model 1: the copier. Generating means picking a training point again.
copied = train[torch.randint(0, len(train), (5000,))]
# Model 2: one Gaussian, fitted by mean and variance. Two numbers.
m, s = train.mean(), train.std(); g1 = m + s * torch.randn(5000, dtype=D); ll1 = gauss_logp(test, m, s).mean().item()
# Model 3: a two-component mixture, fitted by expectation-maximisation. Five numbers.
w = torch.tensor([.5, .5], dtype=D); mu = torch.tensor([-1., 1.], dtype=D); sd = torch.tensor([1., 1.], dtype=D)
for it in range(60):
    log_r = w.log() + gauss_logp(train[:, None], mu, sd); r = torch.softmax(log_r, 1); n = r.sum(0)    # E step, then M step
    w = n / n.sum(); mu = (r * train[:, None]).sum(0) / n; sd = ((r * (train[:, None] - mu) ** 2).sum(0) / n).sqrt()
print(f"fitted mixture: weights {w[0]:.3f} {w[1]:.3f}  means {mu[0]:.3f} {mu[1]:.3f}  stds {sd[0]:.3f} {sd[1]:.3f}   truth: .300 .700  -2.000 1.500  .300 .500")
assert abs(w[0] - .3) < .03 and abs(mu[1] - 1.5) < .05
k = torch.multinomial(w, 5000, True); g2 = mu[k] + sd[k] * torch.randn(5000, dtype=D)
ll2 = torch.logsumexp(w.log() + gauss_logp(test[:, None], mu, sd), 1).mean().item(); best = torch.logsumexp(torch.tensor([.3, .7], dtype=D).log() + gauss_logp(test[:, None], torch.tensor([-2., 1.5], dtype=D), torch.tensor([.3, .5], dtype=D)), 1).mean().item()
trainset = set(train.tolist())
print("\nmodel        numbers stored  new samples  W1 to truth  log-likelihood on unseen data")
print(f"copier       {len(train):<15d} {sum(x not in trainset for x in copied.tolist()) / 5000:<12.3f} {w1(copied):<12.4f} undefined: it gives unseen values no density")
print(f"one Gaussian {2:<15d} {sum(x not in trainset for x in g1.tolist()) / 5000:<12.3f} {w1(g1):<12.4f} {ll1:.4f}")
print(f"mixture      {5:<15d} {sum(x not in trainset for x in g2.tolist()) / 5000:<12.3f} {w1(g2):<12.4f} {ll2:.4f}")
print(f"the truth itself                                       {best:.4f}")
assert ll2 > ll1 and sum(x in trainset for x in copied.tolist()) == 5000 and abs(ll2 - best) < .02
print(f"\nshare of one-Gaussian samples in the empty gap between the modes (-1 < x < 0.5): {((g1 > -1) & (g1 < .5)).double().mean():.3f}   truth: {((test > -1) & (test < .5)).double().mean():.3f}")
print(f"\nwhy images need more: a 512x512 RGB image has 256^(3*512*512) possible values, a number with {int(3 * 512 * 512 * math.log10(256)):,} digits")
