import torch
import math
import random
import json
import itertools
import collections

torch.manual_seed(0)

# Define a simple VAE-like structure for demonstration
class SimpleVAE(torch.nn.Module):
    def __init__(self, input_dim=10, latent_dim=2):
        super(SimpleVAE, self).__init__()
        # Encoder maps input to latent distribution parameters
        self.encoder = torch.nn.Sequential(
            torch.nn.Linear(input_dim, 16),
            torch.nn.ReLU(),
            torch.nn.Linear(16, latent_dim * 2)  # mean and log_var
        )
        # Decoder maps latent space back to input space
        self.decoder = torch.nn.Sequential(
            torch.nn.Linear(latent_dim, 16),
            torch.nn.ReLU(),
            torch.nn.Linear(16, input_dim)
        )

    def reparameterize(self, mu, log_var):
        # Reparameterization trick: sample z = mu + eps * std
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        # Encode input to get latent distribution parameters
        h = self.encoder(x)
        mu = h[:, :2]
        log_var = h[:, 2:]

        # Sample from the latent distribution
        z = self.reparameterize(mu, log_var)

        # Decode the latent sample back to input space
        x_recon = self.decoder(z)

        return x_recon, mu, log_var

# Create a small dataset for demonstration
input_dim = 10
latent_dim = 2
batch_size = 8

# Generate random input data
x = torch.randn(batch_size, input_dim)

# Initialize the VAE
vae = SimpleVAE(input_dim=input_dim, latent_dim=latent_dim)

# Forward pass
x_recon, mu, log_var = vae(x)

# Calculate reconstruction loss (MSE)
recon_loss = torch.mean((x - x_recon) ** 2)

# Calculate KL divergence loss
# KL(q(z|x) || p(z)) = -0.5 * sum(1 + log_var - mu^2 - exp(log_var))
kl_loss = -0.5 * torch.mean(torch.sum(1 + log_var - mu**2 - torch.exp(log_var), dim=1))

# Total loss = reconstruction loss + KL divergence
total_loss = recon_loss + kl_loss

# Print results
print(f"RESULT recon_loss = {recon_loss.item():.6g}")
print(f"RESULT kl_loss = {kl_loss.item():.6g}")
print(f"RESULT total_loss = {total_loss.item():.6g}")
print(f"RESULT mu_shape = {list(mu.shape)}")
print(f"RESULT log_var_shape = {list(log_var.shape)}")
print(f"RESULT x_recon_shape = {list(x_recon.shape)}")

# Assert that the shapes are correct
assert mu.shape == (batch_size, latent_dim), "mu shape mismatch"
assert log_var.shape == (batch_size, latent_dim), "log_var shape mismatch"
assert x_recon.shape == x.shape, "reconstruction shape mismatch"

# Assert that the loss is finite
assert math.isfinite(total_loss.item()), "total loss is not finite"
