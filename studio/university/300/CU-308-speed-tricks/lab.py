import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Define a simple toy ODE function for distillation/sampling simulation
# This simulates a neural network that predicts velocity/gradient
def toy_ode_fn(x, t):
    """
    Toy ODE function: dx/dt = -x + sin(t)
    This is a simple linear ODE with known solution for error checking.
    """
    return -x + torch.sin(t)

def solve_ode_euler(x0, t0, t1, num_steps, ode_fn):
    """
    Solve ODE using Euler method with given number of steps.
    Returns final state and number of function evaluations (NFE).
    """
    x = x0.clone()
    dt = (t1 - t0) / num_steps
    nfe = 0
    for i in range(num_steps):
        t = t0 + i * dt
        # Each step requires one evaluation of the ODE function
        dx = ode_fn(x, t)
        x = x + dt * dx
        nfe += 1
    return x, nfe

def solve_ode_exact(x0, t0, t1):
    """
    Exact solution for dx/dt = -x + sin(t)
    Solution: x(t) = C*e^(-t) + 0.5*sin(t) - 0.5*cos(t)
    Using initial condition x(t0) = x0:
    C = x0 - 0.5*sin(t0) + 0.5*cos(t0)
    """
    C = x0 - 0.5 * torch.sin(t0) + 0.5 * torch.cos(t0)
    return C * torch.exp(-t1) + 0.5 * torch.sin(t1) - 0.5 * torch.cos(t1)

# Simulate a sampler with different step counts and CFG
# CFG (Classifier-Free Guidance) doubles the NFE per step
def simulate_sampler(steps, use_cfg):
    """
    Simulate a diffusion sampler.
    Each step requires 1 NFE without CFG, 2 NFE with CFG.
    """
    nfe_per_step = 2 if use_cfg else 1
    total_nfe = steps * nfe_per_step
    return total_nfe

# Measure NFE for different configurations
steps_list = [50, 20, 8, 4]
results = {}

# Without CFG
for steps in steps_list:
    nfe = simulate_sampler(steps, use_cfg=False)
    results[f"nfe_steps_{steps}_no_cfg"] = nfe

# With CFG
for steps in steps_list:
    nfe = simulate_sampler(steps, use_cfg=True)
    results[f"nfe_steps_{steps}_with_cfg"] = nfe

# Calculate speedup factors relative to 50 steps without CFG
baseline_nfe = results["nfe_steps_50_no_cfg"]
for steps in steps_list:
    nfe_no_cfg = results[f"nfe_steps_{steps}_no_cfg"]
    nfe_with_cfg = results[f"nfe_steps_{steps}_with_cfg"]
    speedup_no_cfg = baseline_nfe / nfe_no_cfg
    speedup_with_cfg = baseline_nfe / nfe_with_cfg
    results[f"speedup_steps_{steps}_no_cfg"] = speedup_no_cfg
    results[f"speedup_steps_{steps}_with_cfg"] = speedup_with_cfg

# Toy 1-step vs 4-step ODE solve error trade-off
x0 = torch.tensor([1.0], dtype=torch.float32)
t0 = torch.tensor(0.0, dtype=torch.float32)
t1 = torch.tensor(1.0, dtype=torch.float32)

# Exact solution
x_exact = solve_ode_exact(x0, t0, t1)

# 1-step Euler
x_1step, nfe_1step = solve_ode_euler(x0, t0, t1, num_steps=1, ode_fn=toy_ode_fn)
error_1step = torch.abs(x_1step - x_exact).item()

# 4-step Euler
x_4step, nfe_4step = solve_ode_euler(x0, t0, t1, num_steps=4, ode_fn=toy_ode_fn)
error_4step = torch.abs(x_4step - x_exact).item()

results["nfe_1step_ode"] = nfe_1step
results["nfe_4step_ode"] = nfe_4step
results["error_1step_ode"] = error_1step
results["error_4step_ode"] = error_4step
results["error_reduction_factor"] = error_1step / error_4step if error_4step > 0 else float('inf')

# Assertions to verify concepts
# 1. Fewer steps should give higher speedup
assert results["speedup_steps_4_no_cfg"] > results["speedup_steps_50_no_cfg"], "Fewer steps should give higher speedup"
# 2. More steps should give lower error
assert error_4step < error_1step, "More steps should give lower error"

# Print results
for name, value in results.items():
    if isinstance(value, float):
        print(f"RESULT {name} = {value:.6g}")
    else:
        print(f"RESULT {name} = {value}")
