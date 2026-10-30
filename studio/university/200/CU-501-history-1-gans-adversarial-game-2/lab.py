import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(0)

# Define a simple Generator that maps 10-dim noise to 1-dim output
class Generator(nn.Module):
    def __init__(self):
        super(Generator, self).__init__()
        self.fc = nn.Linear(10, 1)
    def forward(self, x):
        return torch.sigmoid(self.fc(x))

# Define a simple Discriminator that maps 1-dim input to 1-dim probability
class Discriminator(nn.Module):
    def __init__(self):
        super(Discriminator, self).__init__()
        self.fc = nn.Linear(1, 1)
    def forward(self, x):
        return torch.sigmoid(self.fc(x))

# Initialize models
g = Generator()
d = Discriminator()

# Create fixed inputs: noise vector and a "real" data point
z = torch.randn(1, 10)
real_data = torch.ones(1, 1)

# Forward pass: generate fake data and get discriminator outputs
generated = g(z)
d_real = d(real_data)
d_fake = d(generated)

# Calculate discriminator loss: wants to classify real as 1 and fake as 0
loss_d = F.binary_cross_entropy(d_real, torch.ones(1, 1)) + F.binary_cross_entropy(d_fake, torch.zeros(1, 1))

# Calculate generator loss: wants discriminator to classify fake as 1
loss_g = F.binary_cross_entropy(d_fake, torch.ones(1, 1))

# Print results
print(f"RESULT d_real = {d_real.item():.6g}")
print(f"RESULT d_fake = {d_fake.item():.6g}")
print(f"RESULT loss_d = {loss_d.item():.6g}")
print(f"RESULT loss_g = {loss_g.item():.6g}")

# Assert that discriminator outputs are valid probabilities (between 0 and 1)
assert 0.0 <= d_real.item() <= 1.0, "Discriminator output for real data must be a valid probability"
assert 0.0 <= d_fake.item() <= 1.0, "Discriminator output for fake data must be a valid probability"
