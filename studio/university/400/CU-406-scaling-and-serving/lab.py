import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# --- Cost Model Parameters ---
# Fixed overhead per batch (e.g., kernel launch, synchronization)
FIXED_OVERHEAD = 1.0
# Per-item cost (e.g., FLOPs per token/item)
PER_ITEM_COST = 0.1
# Memory cap: max number of items that can fit in memory at once
MEMORY_CAP = 32

# --- Helper: Calculate total cost for a batch ---
def batch_cost(batch_size):
    """
    Total time/cost to process a batch of size B.
    Cost = Fixed Overhead + (Per-Item Cost * B)
    """
    return FIXED_OVERHEAD + PER_ITEM_COST * batch_size

# --- Helper: Calculate throughput (items per unit time) ---
def throughput(batch_size):
    """
    Throughput = Number of items / Total Cost
    """
    if batch_size == 0:
        return 0.0
    return batch_size / batch_cost(batch_size)

# --- Step 1: Compare throughput for batch sizes 1, 4, 16 ---
# We simulate a simple scenario where we process a fixed number of total items
# and measure how efficiently different batch sizes handle them.

total_items_to_process = 1000

results = {}

for bs in [1, 4, 16]:
    # Number of batches needed
    num_batches = math.ceil(total_items_to_process / bs)
    
    # Total cost = num_batches * cost_per_batch
    total_cost = num_batches * batch_cost(bs)
    
    # Throughput = total_items / total_cost
    tp = total_items_to_process / total_cost
    results[f"throughput_bs_{bs}"] = tp

# Print results for batch sizes 1, 4, 16
for bs in [1, 4, 16]:
    print(f"RESULT throughput_bs_{bs} = {results[f'throughput_bs_{bs}']:.6g}")

# --- Step 2: Find the optimal batch size given a memory cap ---
# We want to find the batch size B (1 <= B <= MEMORY_CAP) that maximizes throughput.
# Throughput(B) = B / (FIXED_OVERHEAD + PER_ITEM_COST * B)

best_bs = 1
best_tp = -1.0

for bs in range(1, MEMORY_CAP + 1):
    tp = throughput(bs)
    if tp > best_tp:
        best_tp = tp
        best_bs = bs

print(f"RESULT optimal_batch_size = {best_bs:.6g}")
print(f"RESULT max_throughput = {best_tp:.6g}")

# --- Step 3: Verify the concept with assertions ---

# Assertion 1: Throughput should increase as batch size increases from 1 to 4
# because the fixed overhead is amortized over more items.
assert results["throughput_bs_4"] > results["throughput_bs_1"], \
    "Throughput for batch size 4 should be higher than for batch size 1"

# Assertion 2: The optimal batch size should be within the memory cap
# and should be greater than 1 (since batching helps amortize overhead).
assert 1 < best_bs <= MEMORY_CAP, \
    "Optimal batch size should be greater than 1 and within memory cap"

# Additional check: Throughput should be monotonically increasing up to a point
# In this linear cost model, throughput = B / (a + bB) = 1 / (a/B + b)
# As B increases, a/B decreases, so throughput increases asymptotically to 1/b.
# So for any B1 < B2, throughput(B1) < throughput(B2)
tp_1 = throughput(1)
tp_2 = throughput(2)
tp_4 = throughput(4)
assert tp_1 < tp_2 < tp_4, "Throughput should increase with batch size in this model"

# Print a few more diagnostic values
print(f"RESULT cost_bs_1 = {batch_cost(1):.6g}")
print(f"RESULT cost_bs_4 = {batch_cost(4):.6g}")
print(f"RESULT cost_bs_16 = {batch_cost(16):.6g}")
