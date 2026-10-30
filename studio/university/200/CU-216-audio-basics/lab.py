import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# 1. Synthesize a 440 Hz + 880 Hz tone
# Sample rate: 44100 Hz (standard audio)
sr = 44100
duration = 1.0  # seconds
n_samples = int(sr * duration)

# Time vector
t = torch.linspace(0, duration, n_samples, dtype=torch.float32)

# Generate sine waves for 440 Hz and 880 Hz
freq1 = 440.0
freq2 = 880.0
wave1 = torch.sin(2 * math.pi * freq1 * t)
wave2 = torch.sin(2 * math.pi * freq2 * t)

# Combine the two tones
signal = wave1 + wave2

# 2. Compute the STFT with torch.stft
# Use a window size of 1024 samples, hop size of 256
n_fft = 1024
hop_length = 256
window = torch.hann_window(n_fft, dtype=torch.float32)

# Compute STFT
stft_result = torch.stft(signal, n_fft=n_fft, hop_length=hop_length, window=window, return_complex=True)

# Get magnitude spectrum
magnitude = torch.abs(stft_result)

# Average magnitude over time to get a stable spectrum
avg_magnitude = magnitude.mean(dim=1)

# Find the peak frequency bins
# The frequency resolution is sr / n_fft
freq_resolution = sr / n_fft
peak_indices = torch.argmax(avg_magnitude)

# The peak should be near 440 Hz or 880 Hz
# Let's find the top two peaks
top_k = 2
top_indices = torch.topk(avg_magnitude, k=top_k).indices

# Convert indices to frequencies
peak_freqs = top_indices * freq_resolution

# Sort peak frequencies
peak_freqs_sorted = sorted(peak_freqs.tolist())

# 3. Show aliasing by sampling an 8 kHz tone at 10 kHz
# Nyquist limit for 10 kHz sampling rate is 5 kHz
sr_alias = 10000
nyquist_limit = sr_alias / 2.0

# Generate an 8 kHz tone (above Nyquist limit)
freq_alias = 8000.0
duration_alias = 0.1  # shorter duration for speed
n_samples_alias = int(sr_alias * duration_alias)
t_alias = torch.linspace(0, duration_alias, n_samples_alias, dtype=torch.float32)

# Generate the 8 kHz tone
signal_alias = torch.sin(2 * math.pi * freq_alias * t_alias)

# Compute STFT for the aliased signal
n_fft_alias = 1024
hop_length_alias = 256
window_alias = torch.hann_window(n_fft_alias, dtype=torch.float32)

stft_alias = torch.stft(signal_alias, n_fft=n_fft_alias, hop_length=hop_length_alias, window=window_alias, return_complex=True)
magnitude_alias = torch.abs(stft_alias)
avg_magnitude_alias = magnitude_alias.mean(dim=1)

# Find the peak frequency bin for the aliased signal
freq_resolution_alias = sr_alias / n_fft_alias
peak_index_alias = torch.argmax(avg_magnitude_alias)
peak_freq_alias = peak_index_alias * freq_resolution_alias

# Due to aliasing, the 8 kHz tone appears at |8000 - 10000| = 2000 Hz
# Let's verify this

# 4. Report results
# Peak frequencies for the 440 Hz + 880 Hz tone
print(f"RESULT peak_freq_1 = {peak_freqs_sorted[0]:.6g}")
print(f"RESULT peak_freq_2 = {peak_freqs_sorted[1]:.6g}")

# Aliased frequency
print(f"RESULT aliased_freq = {peak_freq_alias:.6g}")

# Nyquist limit
print(f"RESULT nyquist_limit = {nyquist_limit:.6g}")

# 5. Assertions to check concepts
# Check that the peak frequencies are close to 440 Hz and 880 Hz
assert abs(peak_freqs_sorted[0] - 440.0) < 50.0, "First peak should be near 440 Hz"
assert abs(peak_freqs_sorted[1] - 880.0) < 50.0, "Second peak should be near 880 Hz"

# Check that the aliased frequency is close to 2000 Hz
assert abs(peak_freq_alias - 2000.0) < 100.0, "Aliased frequency should be near 2000 Hz"
