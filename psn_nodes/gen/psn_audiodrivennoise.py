"""
PSN_AudioDrivenNoise: Drives dynamic latent noise patterns based on audio analysis.

This node analyzes a simplified audio waveform (list of floats) to estimate frequency
energy and modulates a noise pattern accordingly. It is a pure-logic implementation
without external dependencies (no numpy, no librosa).

Inputs:
- audio: List of floats representing the audio waveform.
- latent: List of floats representing the latent tensor (flattened).
- sensitivity: Float controlling how strongly audio peaks affect noise.

Outputs:
- noise: List of floats representing the modulated noise pattern.
"""

import math
import random

# Constants
CAT = "ParametricStudio/Audio"

class PSN_AudioDrivenNoise:
    """
    Analyzes audio frequency spectrum (simplified) and modulates noise intensity.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}), # Placeholder for type hint, actual input is list
                "latent": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}), # Placeholder for type hint, actual input is list
                "sensitivity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.1}),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }
    
    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("noise",)
    FUNCTION = "run"
    CATEGORY = CAT

    def _compute_energy(self, audio):
        """
        Computes a simplified frequency energy profile from the audio waveform.
        Uses a basic approach: divide audio into bins and compute RMS energy per bin.
        """
        if not audio or len(audio) == 0:
            return []
        
        # Simplified frequency analysis: 
        # We'll create 8 frequency bins by grouping samples.
        # This is a very rough approximation of a spectrum.
        num_bins = 8
        bin_size = max(1, len(audio) // num_bins)
        energies = []
        
        for i in range(num_bins):
            start = i * bin_size
            end = start + bin_size
            if start >= len(audio):
                break
            segment = audio[start:end]
            if not segment:
                energies.append(0.0)
                continue
            
            # Compute RMS energy
            sum_sq = 0.0
            for sample in segment:
                sum_sq += sample * sample
            rms = math.sqrt(sum_sq / len(segment))
            energies.append(rms)
        
        # Normalize energies to 0-1 range
        max_energy = max(energies) if energies else 0.0
        if max_energy > 0:
            energies = [e / max_energy for e in energies]
        
        return energies

    def run(self, audio, latent, sensitivity, seed=0):
        """
        Main execution function.
        """
        # Validate inputs
        if not isinstance(audio, list) or not all(isinstance(x, (int, float)) for x in audio):
            raise ValueError("audio must be a list of numbers")
        if not isinstance(latent, list) or not all(isinstance(x, (int, float)) for x in latent):
            raise ValueError("latent must be a list of numbers")
        if not isinstance(sensitivity, (int, float)):
            raise ValueError("sensitivity must be a number")
        
        # Compute audio energy profile
        energies = self._compute_energy(audio)
        
        # If no audio data, return zero noise
        if not energies:
            return (tuple([0.0] * len(latent)),)
        
        # Generate base noise using a simple PRNG
        rng = random.Random(seed)
        base_noise = [rng.uniform(-1.0, 1.0) for _ in range(len(latent))]
        
        # Modulate noise based on audio energies
        # Map each latent element to a frequency bin
        num_bins = len(energies)
        modulated_noise = []
        
        for i, latent_val in enumerate(latent):
            # Determine which frequency bin this latent element corresponds to
            bin_index = int((i / len(latent)) * num_bins)
            bin_index = min(bin_index, num_bins - 1)
            
            # Get energy for this bin
            energy = energies[bin_index]
            
            # Modulate noise: higher energy -> higher noise intensity
            # Use sensitivity to scale the effect
            modulation = 1.0 + (energy * sensitivity)
            
            # Apply modulation to base noise
            modulated_val = base_noise[i] * modulation
            
            # Clamp to reasonable range
            modulated_val = max(-10.0, min(10.0, modulated_val))
            
            modulated_noise.append(modulated_val)
        
        return (tuple(modulated_noise),)

NODE_CLASS_MAPPINGS = {
    "PSN_AudioDrivenNoise": PSN_AudioDrivenNoise
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_AudioDrivenNoise": "Audio Driven Noise"
}
