# autoencoders.py
# Author: Anna Lee / Team Wisteria
#   • defines neural network architectures for anomaly detection
#   • fully-connected autoencoder for ECG signals
#   • designed for windowed time-series input
#_______________________________________________________________________________#

import torch
import torch.nn as nn


class Autoencoder(nn.Module):
    """
    Fully-connected autoencoder for time-series reconstruction.

    Parameters:
        window_size (int): Number of time steps per input window.
        num_channels (int): Number of signal channels. Default 1 (ECG only).

    Input:  (batch_size, window_size, num_channels)
    Output: (batch_size, window_size, num_channels)
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
            nn.Linear(256, 64),
        )
        self.decoder = nn.Sequential(
            nn.Linear(64, 256),
            nn.ReLU(),
            nn.Linear(256, input_dim),
            nn.Unflatten(1, (window_size, num_channels)),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))