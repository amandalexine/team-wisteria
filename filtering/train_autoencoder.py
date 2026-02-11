import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import os
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
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
# Parameters (FIXED)
# ----------------------------
WINDOW_SIZE = int(fs)       # samples (DO NOT CHANGE AT INFERENCE)
BATCH_SIZE = 64
EPOCHS = 40
LR = 1e-3
NUM_CHANNELS = 3

# ----------------------------
# Load baseline data
# ----------------------------
df = pd.read_csv("filtered_baseline.csv")
signals = df[['ECG', 'EMG', 'EDA']].values

# ----------------------------
# Normalize
# ----------------------------
scaler = StandardScaler()
signals_scaled = scaler.fit_transform(signals)

# ----------------------------
# Windowing
# ----------------------------
def create_windows(data, window_size):
    return np.array([
        data[i:i+window_size]
        for i in range(len(data) - window_size)
    ])

X = create_windows(signals_scaled, WINDOW_SIZE)
X = torch.tensor(X, dtype=torch.float32)

loader = DataLoader(
    TensorDataset(X),
    batch_size=BATCH_SIZE,
    shuffle=True
)

# ----------------------------
# Model
# ----------------------------
model = Autoencoder(WINDOW_SIZE, NUM_CHANNELS)
optimizer = torch.optim.Adam(model.parameters(), lr=LR)
criterion = nn.MSELoss()

# ----------------------------
# Training
# ----------------------------
for epoch in range(EPOCHS):
    total_loss = 0.0
    for (x,) in loader:
        optimizer.zero_grad()
        recon = model(x)
        loss = criterion(recon, x)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {total_loss/len(loader):.6f}")

# ----------------------------
# Compute baseline reconstruction error
# ----------------------------
model.eval()
with torch.no_grad():
    recon = model(X)
    baseline_errors = ((recon - X) ** 2).mean(dim=(1,2)).numpy()

threshold = np.percentile(baseline_errors, 95)

# ----------------------------
# Save artifacts
# ----------------------------
os.makedirs("models", exist_ok=True)

torch.save({
    "model_state": model.state_dict(),
    "window_size": WINDOW_SIZE,
    "num_channels": NUM_CHANNELS
}, "models/autoencoder.pth")

np.save("models/scaler_mean.npy", scaler.mean_)
np.save("models/scaler_scale.npy", scaler.scale_)
np.save("models/threshold.npy", threshold)

print("Model, scaler, and threshold saved.")
