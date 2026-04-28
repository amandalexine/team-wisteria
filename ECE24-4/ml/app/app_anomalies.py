# app_anomalies.py
# Author: Anna Lee / Team Wisteria
#   • anomaly detection for ECG signals
#   • loads pretrained autoencoder and preprocessing parameters
#   • handles resampling, normalization, windowing, reconstruction error
#   • detects anomalies based on reconstruction error threshold
#_______________________________________________________________________________#

import os
import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import resample

# ── same-directory import (was filtering.app.app_autoencoders) ──────────────
from .autoencoders import Autoencoder

# ----------------------------
# Parameters
# ----------------------------
TARGET_FS = 100

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ----------------------------
# Windowing
# ----------------------------
def create_windows(data, window_size):
    """
    Splits a time-series signal into overlapping windows.

    Parameters:
        data (np.ndarray): Shape (num_samples, num_channels).
        window_size (int): Samples per window.

    Returns:
        np.ndarray: Shape (num_windows, window_size, num_channels).
    """
    return np.array([
        data[i:i + window_size]
        for i in range(len(data) - window_size)
    ])


# ----------------------------
# Model loading
# ----------------------------
def load_model(
    model_path=None,
    mean_path=None,
    scale_path=None,
    threshold_path=None,
):
    """
    Loads trained autoencoder and preprocessing parameters from the models/
    subdirectory (relative to this file).

    Returns:
        model, mean, scale, threshold, window_size
    """
    model_path     = model_path     or os.path.join(BASE_DIR, "models", "autoencoder.pth")
    mean_path      = mean_path      or os.path.join(BASE_DIR, "models", "scaler_mean.npy")
    scale_path     = scale_path     or os.path.join(BASE_DIR, "models", "scaler_scale.npy")
    threshold_path = threshold_path or os.path.join(BASE_DIR, "models", "threshold.npy")

    checkpoint = torch.load(model_path, map_location="cpu")
    model = Autoencoder(checkpoint["window_size"], checkpoint["num_channels"])
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    mean      = np.load(mean_path)
    scale     = np.load(scale_path)
    threshold = np.load(threshold_path)

    return model, mean, scale, threshold, checkpoint["window_size"]


# ----------------------------
# Anomaly detection
# ----------------------------
def detect_anomalies(model, signals, fs, mean, scale, threshold, window_size):
    """
    Detects anomalies in an ECG signal using autoencoder reconstruction error.

    Parameters:
        model         : Trained Autoencoder.
        signals       : np.ndarray (num_samples, num_channels).
        fs            : Sampling frequency of input signal.
        mean          : Training mean for normalization.
        scale         : Training std for normalization.
        threshold     : Per-window error threshold.
        window_size   : Window length used during training.

    Returns:
        dict with keys:
            errors          – per-window reconstruction errors
            anomalies       – boolean flags per window
            anomaly_indices – sample indices identified as anomalous
            reconstruction  – reconstructed full signal
            proc_signals    – resampled signal used for inference
    """
    # Resample if needed
    if fs != TARGET_FS:
        num_samples = int(len(signals) * TARGET_FS / fs)
        signals = resample(signals, num_samples)
        fs = TARGET_FS

    signals_scaled = (signals - mean) / scale

    X = torch.tensor(
        create_windows(signals_scaled, window_size),
        dtype=torch.float32,
    )

    with torch.no_grad():
        recon = model(X)
        point_errors = ((recon - X) ** 2).mean(dim=2).numpy()  # (num_windows, num_channels)

    window_error = point_errors.mean(axis=1)   # (num_windows,)
    anomalies    = window_error > threshold

    anomaly_indices = []
    for i, is_anom in enumerate(anomalies):
        if is_anom:
            anomaly_indices.append(i)
    anomaly_indices = np.unique(np.array(anomaly_indices, dtype=np.int64))

    # Reconstruct full signal by averaging overlapping windows
    full_recon = np.zeros_like(signals)
    counts     = np.zeros_like(signals)
    for i in range(len(X)):
        full_recon[i:i + window_size, 0] += recon[i, :, 0].numpy() * scale[0] + mean[0]
        counts[i:i + window_size, 0]     += 1
    counts[counts == 0] = 1
    full_recon /= counts

    return {
        "errors":          point_errors,
        "anomalies":       anomalies,
        "anomaly_indices": anomaly_indices,
        "reconstruction":  full_recon,
        "proc_signals":    signals,
    }


# ----------------------------
# Plotting
# ----------------------------
def plot_anomalies(proc_signal, anomaly_idx, fs, reconstruction=None):
    """
    Plots original ECG, optional reconstruction, and anomaly markers.

    Parameters:
        proc_signal   : np.ndarray (num_samples, num_channels).
        anomaly_idx   : np.ndarray of anomalous sample indices.
        fs            : Sampling frequency.
        reconstruction: optional np.ndarray same shape as proc_signal.

    Returns:
        matplotlib Figure
    """
    proc_signal = np.asarray(proc_signal)
    anomaly_idx = np.asarray(anomaly_idx, dtype=np.int64)
    time        = np.arange(len(proc_signal)) / fs

    fig, ax = plt.subplots()
    ax.plot(time, proc_signal[:, 0], label="Original ECG")

    if reconstruction is not None:
        ax.plot(time, np.asarray(reconstruction)[:, 0],
                color="orange", label="Reconstruction")

    valid_idx = anomaly_idx[(anomaly_idx >= 0) & (anomaly_idx < len(proc_signal))]
    if len(valid_idx) > 0:
        ax.scatter(time[valid_idx], proc_signal[valid_idx, 0],
                   color="red", s=10, label="Anomaly")

    ax.set_title("ECG Anomalies")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.legend()

    return fig