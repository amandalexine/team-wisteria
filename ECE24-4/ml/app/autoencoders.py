# autoencoders.py
# Author: Anna Lee / Team Wisteria
#   • defines neural network architectures for anomaly detection
#   • currently includes a fully-connected autoencoder for ECG signals
#   • designed for windowed time-series input
#   • encoder compresses input into a low-dimensional latent representation
#   • decoder reconstructs signal from latent space
#   • used for reconstruction-based anomaly detection (MSE error)
#   • compatible with training and inference pipelines in project
#_______________________________________________________________________________#

# last updated: 4/15/26 : added function contracts

import torch
import torch.nn as nn

class Autoencoder(nn.Module):
    """
    Fully-connected autoencoder for time-series reconstruction.

    Parameters:
        window_size (int):
            Number of time steps per input window.

        num_channels (int, optional):
            Number of signal channels per time step.
            Default is 1 (ECG only).

    Input Shape:
        x: torch.Tensor of shape (batch_size, window_size, num_channels)

    Output Shape:
        torch.Tensor of shape (batch_size, window_size, num_channels)

    """
    def __init__(self, window_size, num_channels=1):
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
