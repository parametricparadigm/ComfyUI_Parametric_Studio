import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# CU-409 Lab: Distillation math - teacher, student, consistency
# We simulate a simple 1D diffusion/flow process where the true data is N(0,1).
# Teacher: performs small Euler steps towards the mean (0) with noise.
# Student: a consistency model that attempts to jump directly to the clean estimate.

def teacher_step(x, sigma, dt):
    """
    One step of the teacher (diffusion/flow) process.
    Moves x towards 0 (the mean) with a small amount of noise.
    dx = -x * dt + noise * sqrt(dt)
    """
    noise = torch.randn_like(x) * 0.1
    return x - x * dt + noise * math.sqrt(dt)

def student_consistency(x, sigma):
    """
    Consistency model: predicts the clean x0 directly from noisy x.
    For a linear flow towards 0, a reasonable approximation is x0 = x / (1 + sigma^2).
    This simulates a 'distilled' jump that is closer to the true mean.
    """
    return x / (1.0 + sigma ** 2)

# Initialize a small tensor of noisy data points
# True data is N(0,1), so we start with samples from N(0,1)
x_true = torch.randn(100)  # 100 samples from N(0,1)

# Start with noisy version: add some noise to simulate diffusion
sigma_start = 1.0
x_noisy = x_true + sigma_start * torch.randn_like(x_true)

# Teacher: take multiple small steps to denoise
dt = 0.01
num_teacher_steps = 100
x_teacher = x_noisy.clone()
for i in range(num_teacher_steps):
    x_teacher = teacher_step(x_teacher, sigma_start, dt)

# Student: single consistency jump
x_student = student_consistency(x_noisy, sigma_start)

# Compute metrics
# Mean squared error to the true data
mse_teacher = torch.mean((x_teacher - x_true) ** 2).item()
mse_student = torch.mean((x_student - x_true) ** 2).item()

# The student should have lower MSE than the teacher in this simplified setup
# because the consistency model directly estimates x0, while the teacher
# takes many small steps with accumulated noise.

# Check that the student is closer to the true data on average
assert mse_student < mse_teacher, f"Student MSE ({mse_student:.6g}) should be less than Teacher MSE ({mse_teacher:.6g})"

# Check that both are reasonable estimates (not wildly off)
assert mse_teacher < 1.0, f"Teacher MSE ({mse_teacher:.6g}) should be less than 1.0"
assert mse_student < 1.0, f"Student MSE ({mse_student:.6g}) should be less than 1.0"

# Print results
print(f"RESULT mse_teacher = {mse_teacher:.6g}")
print(f"RESULT mse_student = {mse_student:.6g}")
print(f"RESULT improvement_ratio = {mse_teacher / mse_student:.6g}")
