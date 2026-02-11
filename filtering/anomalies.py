import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
from autoencoders import Autoencoder

# ----------------------------
# Load sampling rate (for plotting only)
# ----------------------------
file_path = '/Users/annalee/Desktop/Spring 2026/EE98/01:18:26 testing/4_1.xlsx'
info_df = pd.read_excel(file_path, sheet_name='Recording Info', header=None)

def get_sampling_rate(info_df):
    for _, row in info_df.iterrows():
        if isinstance(row[0], str) and 'Sample Rate' in row[0]:
            return float(row[1])
    raise ValueError("Sample Rate not found")

fs = get_sampling_rate(info_df)

# ----------------------------
# Load test data
# ----------------------------
df = pd.read_csv("filtered_test.csv")
signals = df[['ECG', 'EMG', 'EDA']].values

# ----------------------------
# Load scaler + model info
# ----------------------------
mean = np.load("models/scaler_mean.npy")
scale = np.load("models/scaler_scale.npy")
threshold = np.load("models/threshold.npy")

signals_scaled = (signals - mean) / scale

checkpoint = torch.load("models/autoencoder.pth")
WINDOW_SIZE = checkpoint["window_size"]
NUM_CHANNELS = checkpoint["num_channels"]

model = Autoencoder(WINDOW_SIZE, NUM_CHANNELS)
model.load_state_dict(checkpoint["model_state"])
model.eval()

# ----------------------------
# Windowing
# ----------------------------
def create_windows(data, window_size):
    return np.array([
        data[i:i+window_size]
        for i in range(len(data) - window_size)
    ])

X = torch.tensor(
    create_windows(signals_scaled, WINDOW_SIZE),
    dtype=torch.float32
)

# ----------------------------
# Reconstruction error
# ----------------------------
with torch.no_grad():
    recon = model(X)
    errors = ((recon - X) ** 2).mean(dim=(1,2)).numpy()

anomalies = errors > threshold

# ----------------------------
# Map windows to samples
# ----------------------------
anomaly_indices = np.unique([
    idx
    for i, is_anom in enumerate(anomalies)
    if is_anom
    for idx in range(i, i + WINDOW_SIZE)
])

# ----------------------------
# Plot
# ----------------------------
time = np.arange(len(signals)) / fs
names = ['ECG', 'EMG', 'EDA']

fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)

for i, name in enumerate(names):
    axes[i].plot(time, signals[:, i])
    axes[i].scatter(
        time[anomaly_indices],
        signals[anomaly_indices, i],
        s=8,
        color='red'
    )
    axes[i].set_ylabel(name)

axes[-1].set_xlabel("Time (s)")
plt.suptitle("Detected Anomalies")
plt.tight_layout()
plt.show()

window_idx = 0
plt.plot(X[window_idx,:,0].numpy(), label="Original ECG")
plt.plot(recon[window_idx,:,0].numpy(), label="Reconstructed ECG")
plt.legend()
plt.show()


print(f"Anomalous windows: {anomalies.sum()} / {len(anomalies)}")
