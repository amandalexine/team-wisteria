# anomalies.py
# Author: Anna Lee / Team Wisteria
#   • performs anomaly detection on ECG signals using a trained autoencoder
#   • requires preprocessed test data in CSV format (e.g., filtered_test_7.csv)
#       • must include columns: 'ECG' and 'fs' (sampling frequency)
#   • loads trained model, scaler parameters, and anomaly threshold from /models
#   • rescales and windows ECG signal before reconstruction
#   • computes reconstruction error to detect anomalies
#   • maps window-level anomalies back to sample indices
#   • includes visualization of:
#       • ECG signal with detected anomalies
#       • original vs reconstructed ECG signal
#_______________________________________________________________________________#

# last updated: 4/15/26 : added function contracts 

import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
from autoencoders import Autoencoder

from scipy.signal import resample


# ----------------------------
# Parameters
# ----------------------------

TARGET_FS = 100

# ----------------------------
# Load test data (ECG ONLY)
# ----------------------------
df = pd.read_csv("filtered_test_anna.csv")

# read fs from the test file itself
if 'fs' not in df.columns:
    raise ValueError("No 'fs' column in filtered_test.csv — re-run ecg_filtering.py to regenerate it")

#extract sampling frequency and ECG signal
fs = df['fs'].iloc[0]
signals = df[['ECG']].values


# resample to TARGET_FS if needed (to match training sampling)
if fs != TARGET_FS:
    num_samples = int(len(signals) * TARGET_FS / fs)
    signals = resample(signals, num_samples)
    print(f"Resampled test signal from {fs} Hz → {TARGET_FS} Hz")
    fs = TARGET_FS

#sanity check print statements
print(f"Test file fs: {fs}")
print(f"Test ECG min: {signals.min():.4f}, max: {signals.max():.4f}")


# ----------------------------
# Load scaler + model
# ----------------------------
# Load the mean, standard deviation, and threshold saved during training
mean = np.load("models/scaler_mean.npy")
scale = np.load("models/scaler_scale.npy")
threshold = np.load("models/threshold.npy")

# Normalize the test signal using training statistics (z-score normalization)
signals_scaled = (signals - mean) / scale

# Load the saved model checkpoint (contains weights + architecture params)
checkpoint = torch.load("models/autoencoder.pth")
WINDOW_SIZE = checkpoint["window_size"]
NUM_CHANNELS = checkpoint["num_channels"]

# Reconstruct the model architecture and load the trained weights
model = Autoencoder(WINDOW_SIZE, NUM_CHANNELS)
model.load_state_dict(checkpoint["model_state"])
model.eval()

# sanity check print statements
print("Test signal mean:", signals.mean(), "std:", signals.std())
print("Scaler mean:", mean, "scale:", scale)
print("Threshold:", threshold)
signals_scaled = (signals - mean) / scale
print("Scaled test signal mean:", signals_scaled.mean())
print("Scaled test signal std:", signals_scaled.std())
print("Scaled test signal range:", signals_scaled.min(), "-", signals_scaled.max())

# Windowing
# ----------------------------
def create_windows(data, window_size):
    """
    Splits a time-series signal into overlapping windows.

    Parameters:
        data (np.ndarray):
            Input signal of shape (num_samples, num_channels).
            Expected to already be normalized/scaled.
        
        window_size (int):
            Number of samples per window.

    Returns:
        np.ndarray:
            Array of overlapping windows with shape
            (num_windows, window_size, num_channels),
            where num_windows = len(data) - window_size.

    Notes:
        • Uses stride = 1 (maximum overlap between windows)
        • No padding is applied — trailing samples are dropped
    """

    return np.array([
        data[i:i+window_size]
        for i in range(len(data) - window_size)
    ])

#convert full signal into overlapping windows for model input
X = torch.tensor(
    create_windows(signals_scaled, WINDOW_SIZE),
    dtype=torch.float32
)

# ----------------------------
# Reconstruction error
# ----------------------------
#perform forward pass without gradient tracking
with torch.no_grad():
    recon = model(X)
    #mean squared error per window (averaged over time + channels)
    errors = ((recon - X) ** 2).mean(dim=(1,2)).numpy()

#classify windows as anomalous if their reconstruction error exceeds the threshold
anomalies = errors > threshold
#z_scores = (errors - errors.mean()) / errors.std()
#anomalies = z_scores > 3

#sanity check print statements
scaled = (signals - mean) / scale
extreme_indices = np.where(np.abs(scaled) > 3)[0]
print(f"Samples with |scaled value| > 3: {len(extreme_indices)}")
print(f"Percentage of signal: {len(extreme_indices)/len(signals)*100:.2f}%")
print(f"Their raw values min/max: {signals[extreme_indices, 0].min():.4f} / {signals[extreme_indices, 0].max():.4f}")
print(f"Where are they: first few indices: {extreme_indices[:10]}")
# ----------------------------

# ----------------------------
# Map windows to samples
# ----------------------------
# Each anomalous window covers WINDOW_SIZE consecutive samples.
# This expands window-level anomaly flags back to individual sample indices,
# then deduplicates so each sample index only appears once.
anomaly_indices = np.unique([
    idx
    for i, is_anom in enumerate(anomalies)
    if is_anom
    for idx in range(i, i + WINDOW_SIZE)
]).astype(int)

# ----------------------------
# Plot ECG only
# ----------------------------
time = np.arange(len(signals)) / fs

plt.figure(figsize=(14,6))
plt.plot(time, signals[:, 0], label="ECG")

#red dots = detected anomalies
plt.scatter(
    time[anomaly_indices],
    signals[anomaly_indices, 0],
    s=8,
    color='red',
    label="Anomaly"
)

plt.xlabel("Time (s)")
plt.ylabel("ECG")
plt.title("Detected ECG Anomalies")
plt.legend()
plt.tight_layout()
plt.show()

# ----------------------------
# Plot reconstruction example
# ----------------------------
#reconstruct full signal from overlapping window reconstructions

#accumulate overlapping predictions
full_recon = np.zeros_like(signals)
for i in range(len(X)):
    full_recon[i:i+WINDOW_SIZE,0] += recon[i,:,0].numpy() * scale[0] + mean[0]

# average overlapping windows
counts = np.zeros_like(signals)
for i in range(len(X)):
    counts[i:i+WINDOW_SIZE,0] += 1
counts[counts == 0] = 1 # prevent division by zero
full_recon /= counts

plt.figure(figsize=(14,6))
plt.plot(time, signals[:,0], label="Original ECG")
plt.plot(time, full_recon[:,0], label="Reconstructed ECG")
plt.scatter(
    time[anomaly_indices],
    signals[anomaly_indices,0],
    s=8,
    color='red',
    label="Anomaly"
)
plt.xlabel("Time (s)")
plt.ylabel("ECG")
plt.title("ECG vs Autoencoder Reconstruction with Anomalies")
plt.legend()
plt.show()

print(f"Anomalous windows: {anomalies.sum()} / {len(anomalies)}")



