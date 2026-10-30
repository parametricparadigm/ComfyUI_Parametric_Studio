import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# Define a small 2x2 image as a float32 tensor on CPU
true_image = torch.tensor([[0.1, 0.2],
                           [0.3, 0.4]], dtype=torch.float32)

# Flatten the image into a 1D sequence for autoregressive processing
flat_true = true_image.flatten()

# Function to simulate autoregressive prediction:
# In a real model, this would be a neural network conditioned on previous pixels.
# Here, we use a simple heuristic: predict the next pixel as the mean of all previous pixels.
def predict_next_pixel(prev_pixels):
    if len(prev_pixels) == 0:
        return torch.tensor(0.0, dtype=torch.float32)
    return torch.mean(prev_pixels)

# Predict each pixel in the sequence autoregressively
predictions = []
for i in range(len(flat_true)):
    # Get all previous pixels (up to but not including current index)
    prev_pixels = flat_true[:i]
    # Predict the current pixel based on previous ones
    pred = predict_next_pixel(prev_pixels)
    predictions.append(pred.item())

# Convert predictions to a tensor for comparison
pred_tensor = torch.tensor(predictions, dtype=torch.float32)

# Compute the mean squared error between predictions and ground truth
mse = torch.mean((pred_tensor - flat_true) ** 2).item()

# Print results in the required format
print(f"RESULT mse = {mse:.6g}")
print(f"RESULT pred_0 = {predictions[0]:.6g}")
print(f"RESULT pred_1 = {predictions[1]:.6g}")
print(f"RESULT pred_2 = {predictions[2]:.6g}")
print(f"RESULT pred_3 = {predictions[3]:.6g}")

# Assert that the first prediction is 0.0 (no previous pixels, so mean is 0)
assert abs(predictions[0] - 0.0) < 1e-6, "First prediction should be 0.0"

# Assert that the MSE is non-negative and reasonably small for this simple heuristic
assert mse >= 0.0, "MSE must be non-negative"
assert mse < 0.1, "MSE should be small for this simple case"
