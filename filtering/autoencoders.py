import torch
import torch.nn as nn

class Autoencoder(nn.Module):
    def __init__(self, window_size, num_channels=3):
        super().__init__()
        self.window_size = window_size
        self.num_channels = num_channels

        input_dim = window_size * num_channels

        self.encoder = nn.Sequential(
            nn.Flatten(),
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 64)
        )

        self.decoder = nn.Sequential(
            nn.Linear(64, 256),
            nn.ReLU(),
            nn.Linear(256, input_dim),
            nn.Unflatten(1, (window_size, num_channels))
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))
