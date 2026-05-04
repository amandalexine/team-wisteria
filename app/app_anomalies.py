# app_anomalies.py
# Author: Anna Lee / Team Wisteria
#   • helper file for app.py
#   • performs anomaly detection for ECG signals in Streamlit app
#   • loads pretrained autoencoder and preprocessing parameters
#   • handles:
#       • signal resampling
#       • normalization using training statistics
#       • windowing for model input
#       • reconstruction error computation
#   • detects anomalies based on reconstruction error threshold
#   • maps window-level anomalies to sample-level indices
#   • includes plotting function for visualization in Streamlit
#_______________________________________________________________________________#

# last updated: 4/15/26

import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
from app_autoencoders import Autoencoder

from scipy.signal import resample


# ----------------------------
# Parameters
# ----------------------------

TARGET_FS = 100

# Windowing
# ----------------------------
def create_windows(data, window_size):
    """
    Splits a time-series signal into overlapping windows.

    Parameters:
        data (np.ndarray): Input signal of shape (num_samples, num_channels).
        window_size (int): Number of samples per window.

    Returns:
        np.ndarray: Array of windows with shape (num_windows, window_size, num_channels), where num_windows = len(data) - window_size.

    """

    return np.array([
        data[i:i+window_size]
        for i in range(len(data) - window_size)
    ])


def load_model(model_path="models/autoencoder.pth", mean_path="models/scaler_mean.npy", scale_path="models/scaler_scale.npy", threshold_path="models/threshold.npy"):
    """
    Loads trained autoencoder and preprocessing parameters.

    Parameters:
        model_path (str): Path to saved PyTorch model checkpoint.
        mean_path (str): Path to saved scaler mean.
        scale_path (str): Path to saved scaler standard deviation.
        threshold_path (str): Path to saved anomaly detection threshold.

    Returns:
        model (torch.nn.Module): Loaded autoencoder model.
        mean (np.ndarray): Training data mean.
        scale (np.ndarray): Training data standard deviation.
        threshold (float): Reconstruction error threshold.
        window_size (int):Window size used during training.

    """
    # Load the saved model checkpoint (contains weights + architecture params)
    checkpoint = torch.load(model_path)

    model = Autoencoder(
        checkpoint["window_size"],
        checkpoint["num_channels"]
    )

    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    mean = np.load(mean_path)
    scale = np.load(scale_path)
    threshold = np.load(threshold_path)

    return model, mean, scale, threshold, checkpoint["window_size"]


def detect_anomalies(model, signals, fs, mean, scale, threshold, window_size):
    """
    Detects anomalies in ECG signal using autoencoder reconstruction error.

    Parameters:
        model (torch.nn.Module): Trained autoencoder.
        signals (np.ndarray): Input ECG signal (num_samples, num_channels).
        fs (float): Sampling frequency of input signal.
        mean (np.ndarray): Training data mean for normalization.
        scale (np.ndarray): Training data standard deviation.
        threshold (float): Error threshold for anomaly detection.
        window_size (int): Window length used for model input.

    Returns:
        dict:
            { "errors": np.ndarray Per-window, per-timestep reconstruction errors,
                "anomalies": np.ndarray Boolean flags indicating anomalous points/windows,
                "anomaly_indices": np.ndarray Sample indices identified as anomalies,
                "reconstruction": np.ndarray Reconstructed full signal,
                "proc_signals": np.ndarray Processed (resampled) signal
            }
    """
    if fs != TARGET_FS:
        num_samples = int(len(signals) * TARGET_FS / fs)
        signals = resample(signals, num_samples)
        print(f"Resampled test signal from {fs} Hz → {TARGET_FS} Hz")
        fs = TARGET_FS

    signals_scaled = (signals - mean) / scale

    X = torch.tensor(
        create_windows(signals_scaled, window_size),
        dtype=torch.float32
    )

    with torch.no_grad():
        recon = model(X)
        # point_errors shape: (num_windows, num_channels)
        point_errors = ((recon - X) ** 2).mean(dim=2).numpy()

    # Collapse across channels to get one error score per window
    # shape: (num_windows,)
    
    window_error = point_errors.mean(axis=1)
    anomalies = window_error > threshold

    #anomalies = np.any(window_error > threshold, axis=1)  # shape: (num_windows,)

    # Compute z-scores per window (not flattened)
    #z_scores = (window_errors - window_errors.mean()) / window_errors.std()
    # One anomaly flag per window
    #anomalies = z_scores > 3  # shape: (num_windows,)

    # Map anomalous windows back to sample indices
    anomaly_indices = []

    for i, is_anom in enumerate(anomalies):
        if is_anom:
            # Find the peak error location within this window
            local_idx = np.argmax(point_errors[i])  # now safe: i < num_windows
            global_idx = i + local_idx
            anomaly_indices.append(global_idx)

    anomaly_indices = np.unique(anomaly_indices)

    full_recon = np.zeros_like(signals)
    counts = np.zeros_like(signals)

    for i in range(len(X)):
        full_recon[i:i+window_size, 0] += (
            recon[i, :, 0].numpy() * scale[0] + mean[0]
        )
        counts[i:i+window_size, 0] += 1

    counts[counts == 0] = 1
    full_recon /= counts

    return {
        "errors": point_errors,
        "anomalies": anomalies,
        "anomaly_indices": anomaly_indices,
        "reconstruction": full_recon,
        "proc_signals": signals
    }

def plot_anomalies(proc_signal, anomaly_idx, fs, reconstruction=None):
    """
    Generates a plot of ECG signal with detected anomalies.

    Parameters:
        proc_signal (np.ndarray): Processed ECG signal (num_samples, num_channels).
        anomaly_idx (np.ndarray): Indices of detected anomalies.
        fs (float): Sampling frequency (Hz).
        reconstruction (np.ndarray, optional): Reconstructed signal for comparison.

    Returns:
        matplotlib.figure.Figure: Figure object for rendering in Streamlit.
    """
    time = np.arange(len(proc_signal)) / fs

    fig, ax = plt.subplots()

    ax.plot(time, proc_signal[:, 0], label=" Original ECG")

    # Reconstruction (if provided)
    if reconstruction is not None:
        ax.plot(
            time,
            reconstruction[:, 0],
            color="orange",
            label="Reconstruction",
            alpha=0.8
        )

    ax.scatter(
        time[anomaly_idx],
        proc_signal[anomaly_idx, 0],
        color="red",
        s=10,
        label="Anomaly"
    )
 

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title("ECG Anomalies")
    ax.legend()

    return fig

