# CU-209 lab: what a negative prompt does, on a three-class problem with exact denoisers.
# Classes sit at the corners of a triangle in 2-D, so "away from fox" does not have to pass through another class.
# Run: python lab.py  (CPU only, about 10 s).
import torch
torch.manual_seed(0); torch.set_num_threads(1)
D = torch.float64
M = torch.tensor([[3., 0.], [-1.5, 2.598], [-1.5, -2.598]], dtype=D); S2 = .5 ** 2   # 0 cat, 1 dog, 2 fox
def den(x, sigma, w):
    w = torch.tensor(w, dtype=D); keep = w > 0; v = S2 + sigma ** 2; m = M[keep]
    r = torch.softmax(w[keep].log() - .5 * ((x[:, None] - m) ** 2).sum(-1) / v, -1)
    return (r[..., None] * (S2 * x[:, None] + sigma ** 2 * m) / v).sum(1)
ANY = [1 / 3, 1 / 3, 1 / 3]; FOX = [0, 0, 1.]; DOG_FOX = [0, .5, .5]; DOG = [0, 1., 0]
def karras(n, smin=.002, smax=80., rho=7.): r = torch.linspace(0, 1, n, dtype=D); return torch.cat([(smax ** (1 / rho) + r * (smin ** (1 / rho) - smax ** (1 / rho))) ** rho, torch.zeros(1, dtype=D)])
def sample(pos, neg, w, n=120):
    x = 80. * torch.randn(20000, 2, dtype=D, generator=torch.Generator().manual_seed(0)); s = karras(n)
    for i in range(n):
        c = den(x, s[i], pos)
        if w == 1.: d = c                                                 # sampling_function never evaluates the negative here
        else: u = den(x, s[i], neg); d = u + (c - u) * w                  # cfg_function
        x = x + (x - d) / s[i] * (s[i + 1] - s[i])
    return x
def share(x): k = ((x[:, None] - M) ** 2).sum(-1).argmin(1); return [(k == i).double().mean().item() for i in range(3)]
def far(x): return x.norm(dim=1).median().item()
print("share of samples nearest each class centre, and median distance from the origin (data sits at 3.0)")
print("settings                                 cat    dog    fox    distance")
def show(name, x): c, d, f = share(x); print(f"{name:40s} {c:.3f}  {d:.3f}  {f:.3f}  {far(x):.2f}")
show("cfg 1, positive any, no negative", sample(ANY, ANY, 1.))
show("cfg 1, positive any, negative fox", sample(ANY, FOX, 1.))
show("cfg 3, positive any, negative any", sample(ANY, ANY, 3.))
show("cfg 1.5, positive any, negative fox", sample(ANY, FOX, 1.5))
show("cfg 3, positive any, negative fox", sample(ANY, FOX, 3.))
show("cfg 7, positive any, negative fox", sample(ANY, FOX, 7.))
show("cfg 3, positive dog+fox, negative fox", sample(DOG_FOX, FOX, 3.))
show("cfg 3, positive dog, negative any", sample(DOG, ANY, 3.))
show("cfg 3, positive dog, negative fox", sample(DOG, FOX, 3.))
assert (sample(ANY, ANY, 1.) == sample(ANY, FOX, 1.)).all()                 # at cfg 1 the negative is not even evaluated
assert (sample(ANY, ANY, 3.) - sample(ANY, ANY, 1.)).abs().max() < 1e-9     # cond == uncond: cfg has nothing to amplify
assert share(sample(ANY, FOX, 3.))[2] < .02
assert far(sample(ANY, FOX, 7.)) > 6                                        # it also overshoots: the cost of a large cfg
print("\ncat and dog keep sharing the mass that fox lost, but nothing says the split stays even: it depends on where each path starts.")
