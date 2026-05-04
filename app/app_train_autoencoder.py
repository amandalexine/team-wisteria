# autoencoder_training.py
# Author: Anna Lee / Team Wisteria
#   • trains an autoencoder model for ECG anomaly detection
#   • requires baseline (normal) ECG data in CSV format
#       • each CSV must include columns: 'ECG' and 'fs'
#   • loads multiple baseline recordings from a specified directory
#   • resamples all signals to a consistent sampling frequency
#   • normalizes data using StandardScaler fit across all sessions
#   • segments signals into overlapping windows for training
#   • trains a denoising autoencoder using MSE reconstruction loss
#   • computes anomaly detection threshold from reconstruction error
#   • saves:
#       • trained model weights and architecture parameters
#       • normalization statistics (mean, scale)
#       • anomaly detection threshold
#_______________________________________________________________________________#

# last updated: 4/15/26: added function contracts

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import os
import matplotlib.pyplot as plt
from scipy.signal import resample
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from app_autoencoders import Autoencoder

# ----------------------------
# Parameters
# ----------------------------
TARGET_FS = 100      # all recordings resampled to this rate
WINDOW_SIZE_SEC = 1    # window length in seconds
WINDOW_SIZE = int(WINDOW_SIZE_SEC * TARGET_FS)
BATCH_SIZE = 64
EPOCHS = 100
LR = 1e-3
NUM_CHANNELS = 1       # ECG only

# ----------------------------
# Load all baseline CSVs
# ----------------------------
baseline_folder = "/Users/annalee/Desktop/Spring 2026/EE98/team-wisteria/filtering/training_data"

baseline_files = [
    os.path.join(baseline_folder, f)
    for f in os.listdir(baseline_folder)
    if f.endswith(".csv")
]

#ensure at least one file was found
if not baseline_files:
    raise ValueError(f"No CSV files found in {baseline_folder}")

# Load each file, resample if needed, collect raw signals
all_signals = []
for file in baseline_files:
    df = pd.read_csv(file)

    #check that sampling rate exists
    if 'fs' not in df.columns:
        raise ValueError(f"No 'fs' column in {file} — please add sampling rate when generating filtered CSVs")

    #extract ECG
    file_fs = df['fs'].iloc[0]      # read this file's sampling rate
    sig = df[['ECG']].values        # shape: (N, 1)
    print(f"{os.path.basename(file)} | ECG min={sig.min():.4f}, max={sig.max():.4f}, std={sig.std():.4f}")

    # Resample to TARGET_FS if needed to match target frequency
    if file_fs != TARGET_FS:
        num_samples = int(len(sig) * TARGET_FS / file_fs)
        sig = resample(sig, num_samples)
        print(f"Resampled {os.path.basename(file)} from {file_fs} Hz → {TARGET_FS} Hz")
        fs = TARGET_FS

    #store all ECG signals together
    all_signals.append(sig)
    print(f"Loaded {os.path.basename(file)} | fs={file_fs} | samples={len(sig)}")

# ----------------------------
# Normalize
# ----------------------------
# Fit scaler on ALL data combined so mean/std is consistent across sessions
signals_combined = np.concatenate(all_signals, axis=0)
scaler = StandardScaler()
scaler.fit(signals_combined)   # fit once on everything

# ----------------------------
# Windowing (per file to avoid garbage boundary windows)
# ----------------------------

def create_windows(data, window_size):
    """
    Splits a time-series signal into overlapping windows.

    Parameters:
        data (np.ndarray):
            Input signal of shape (num_samples, num_channels).
            Expected to be normalized prior to windowing.
        
        window_size (int): Number of samples per window.

    Returns:
        np.ndarray: Array of overlapping windows with shape
            (num_windows, window_size, num_channels),
            where num_windows = len(data) - window_size.

    """
    return np.array([
        data[i:i+window_size]
        for i in range(len(data) - window_size)
    ])

# apply normalization and windowing for each file
all_windows = []
for sig in all_signals:
    sig_scaled = scaler.transform(sig)   # normalize using combined scaler
    all_windows.append(create_windows(sig_scaled, WINDOW_SIZE))

#convert all to a single PyTorch tensor for training
X = torch.tensor(np.concatenate(all_windows, axis=0), dtype=torch.float32)
print(f"Total training windows: {len(X)}")

# splits data into batches for training
loader = DataLoader(
    TensorDataset(X),
    batch_size=BATCH_SIZE,
    shuffle=True
)

# ----------------------------
# Model
# ----------------------------
#initialize autoencoder model
model = Autoencoder(WINDOW_SIZE, NUM_CHANNELS)
optimizer = torch.optim.Adam(model.parameters(), lr=LR)
# MSE loss for reconstruction
criterion = nn.MSELoss()

# ----------------------------
# Training
# ----------------------------
#train model over multiple epochs
for epoch in range(EPOCHS):
    total_loss = 0.0
    for (x,) in loader:
        optimizer.zero_grad()
        noise = 0.1 * torch.randn_like(x) #add noise for denoising autoencoder
        recon = model(x + noise) #forward pass 
        loss = criterion(recon, x) #compute loss
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {total_loss/len(loader):.6f}")

# ----------------------------
# Compute anomaly threshold
# ----------------------------
#evaluate reconstruction error on training data to set threshold
model.eval()
with torch.no_grad():
    recon = model(X)
    #mean squared error per window
    baseline_errors = ((recon - X) ** 2).mean(dim=(1,2)).numpy()

#saving threshold
#threshold = np.percentile(baseline_errors, 90)
threshold = baseline_errors.mean() + 1.5 * baseline_errors.std()
#threshold = baseline_errors.mean() + 5 * baseline_errors.std()
print(f"Anomaly threshold: {threshold:.6f}")

# ----------------------------
# Save everything
# ----------------------------
#make directory for artifacts 
os.makedirs("models", exist_ok=True)

#save parameters 
torch.save({
    "model_state": model.state_dict(),
    "window_size": WINDOW_SIZE,
    "num_channels": NUM_CHANNELS
}, "models/autoencoder.pth")

np.save("models/scaler_mean.npy", scaler.mean_)
np.save("models/scaler_scale.npy", scaler.scale_)
np.save("models/threshold.npy", threshold)

print("Model, scaler, and threshold saved.")