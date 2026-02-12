# ecg_filtering.py
# Author: Anna Lee / Team Wisteria
#   • filtering used for ECG, EMG, EDA signal processing
#   • requires user to input ecg data (excel format)
#   • excel format looking for a sheet named 'Baseline Data' and 'Test Data'
#       • using the ECE24-4 format of data collection
#   • includes functions for bandpass and lowpass filtering
#   • includes plotting functions for visualizing original vs filtered signals
#_______________________________________________________________________________#

# last updated: 2/12/26

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, find_peaks

# -------------------------------
# 1. Read Excel Data
# -------------------------------

#file_path = '/Users/annalee/Desktop/Fall 2025-26/EE97/dr. solet data/2_1.xlsx'
# file_path = '/Users/annalee/Desktop/Spring 2026/EE98/01:18:26 testing/4_1.xlsx'
file_path = r"C:\Users\kbei5\Downloads\4_1.xlsx"
sheets = ['Baseline Data', 'Test Data']

#read the recording info tab in excel sheet to get sampling rate
recording_info = pd.read_excel(
    file_path,
    sheet_name='Recording Info',
    header=None
)

data = {sheet: pd.read_excel(file_path, sheet_name=sheet) for sheet in sheets}
info_df = pd.read_excel(file_path, sheet_name='Recording Info', header=None)


# -------------------------------
# 2. Filter Functions
# -------------------------------
def get_sampling_rate(info_df):
    for _, row in info_df.iterrows():
        if isinstance(row[0], str) and 'Sample Rate' in row[0]:
            return float(row[1])
    raise ValueError("Sample Rate not found in Recording Info")

def filter_ecg_for_r_peaks(ecg, fs):
    b, a = butter(4, [5/(fs/2), 15/(fs/2)], btype='bandpass')
    return filtfilt(b, a, ecg)

def detect_r_peaks(ecg_filtered, fs):
    peaks, properties = find_peaks(
        ecg_filtered,
        height=np.mean(ecg_filtered) + 0.5 * np.std(ecg_filtered),
        distance=int(0.25 * fs)   # ≥ 250 ms between beats (max ~240 BPM)
    )
    return peaks, properties

def butter_bandpass(lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def butter_lowpass(cutoff, fs, order=4):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low')
    return b, a

def apply_filter(signal, filter_type='bandpass', **kwargs):
    if filter_type == 'bandpass':
        b, a = butter_bandpass(kwargs['lowcut'], kwargs['highcut'], kwargs['fs'], kwargs.get('order', 4))
    elif filter_type == 'lowpass':
        b, a = butter_lowpass(kwargs['cutoff'], kwargs['fs'], kwargs.get('order', 4))
    else:
        raise ValueError("filter_type must be 'bandpass' or 'lowpass'")
    return filtfilt(b, a, signal)

# -------------------------------
# 3. Plotting Function
# -------------------------------
def plot_signals(time, original, filtered, title):
    
    plt.figure(figsize=(12, 6))

    # Original signal on top
    plt.subplot(2, 1, 1)
    plt.plot(time, original, color='blue')
    plt.title(f"{title} - Original")
    plt.xlabel('Time')
    plt.ylabel('Amplitude')
    
    # Filtered signal below
    plt.subplot(2, 1, 2)
    plt.plot(time, filtered, color='red')
    plt.title(f"{title} - Filtered")
    plt.xlabel('Time')
    plt.ylabel('Amplitude')
    
    #plt.tight_layout()
    #plt.show()

def plot_ecg_with_r_peaks(time, ecg_filtered, r_peaks):
    plt.figure(figsize=(12,6))

    plt.plot(time, ecg_filtered, label="Filtered ECG")
    plt.plot(time[r_peaks], ecg_filtered[r_peaks],
             'ro', label="R-peaks")

    plt.title("ECG with R-peak Detection")
    plt.xlabel("Time")
    plt.ylabel("Amplitude")
    plt.legend()
    #plt.tight_layout()
    #plt.show()

# look at frequency spectrum to see structure of signal
def plot_signal_spectra(orig_signal, processed_signal=None, fs=1.0, title_prefix="Signal", rectified=False):
    """
    Plots the frequency content of a signal (or two signals side by side) using 1x2 subplots.

    Parameters:
    - orig_signal: 1D array of original signal
    - processed_signal: optional 1D array of processed signal (e.g., filtered/rectified)
    - fs: sampling rate in Hz
    - title_prefix: string prefix for plot titles
    - rectified: if True, takes absolute value of processed_signal
    """
    # Determine number of subplots
    ncols = 2 if processed_signal is not None else 1
    fig, axes = plt.subplots(1, ncols, figsize=(7*ncols, 5))

    # Make axes indexable in both cases
    if ncols == 1:
        axes = [axes]

    # ---------- Original signal ----------
    N = len(orig_signal)
    freqs = np.fft.rfftfreq(N, d=1/fs)
    fft_orig = np.fft.rfft(orig_signal)
    mag_orig = np.abs(fft_orig) / N
    axes[0].plot(freqs, mag_orig)
    axes[0].set_title(f"{title_prefix} - Original Spectrum")
    axes[0].set_xlabel("Frequency (Hz)")
    axes[0].set_ylabel("Magnitude")
    axes[0].grid(True)
    axes[0].set_xlim(0, fs/2)

    # ---------- Processed signal ----------
    if processed_signal is not None:
        sig = np.abs(processed_signal) if rectified else processed_signal
        fft_proc = np.fft.rfft(sig)
        mag_proc = np.abs(fft_proc) / N
        axes[1].plot(freqs, mag_proc, color='orange')
        axes[1].set_title(f"{title_prefix} - Processed Spectrum")
        axes[1].set_xlabel("Frequency (Hz)")
        axes[1].set_ylabel("Magnitude")
        axes[1].grid(True)
        axes[1].set_xlim(0, fs/2)

    plt.tight_layout()

# -------------------------------
# 4. Apply filters & plot
# -------------------------------
# sampling rates
fs = get_sampling_rate(info_df)
print(f"Using sampling rate: {fs} Hz")
fs_ecg = fs  # Hz
fs_emg = fs  # Hz
fs_eda = fs  # Hz (EDA usually low frequency)

filtered_outputs = {}

# -------------------------------
# Create 6-panel figure
# -------------------------------
fig, axes = plt.subplots(3, 2, figsize=(16, 10), sharex='col')

row_map = {
    'ECG': 0,
    'EMG': 1,
    'EDA': 2
}

col_map = {
    'Baseline Data': 0,
    'Test Data': 1
}

for sheet_name in sheets:
    print(f"\nProcessing {sheet_name}")
    df = data[sheet_name]

    time = df['Time'] if 'Time' in df.columns else np.arange(len(df))

    filtered_df = pd.DataFrame()
    filtered_df['Time'] = time

    # ---------------- ECG ----------------
    if 'ECG' in df.columns:
        ecg_filtered = apply_filter(
            df['ECG'], filter_type='bandpass',
            lowcut=0.5, highcut=40, fs=fs_ecg
        )
        filtered_df['ECG'] = ecg_filtered
        #plot_signals(time, df['ECG'], ecg_filtered, f"{sheet_name} - ECG")
        ax = axes[row_map['ECG'], col_map[sheet_name]]
        ax.plot(time, df['ECG'], alpha=0.4, label='Original')
        ax.plot(time, ecg_filtered, label='Filtered')
        ax.set_title(f"{sheet_name} - ECG")
        ax.legend()

        # -------------------------------
        # R-PEAK DETECTION (ECG ONLY)
        # -------------------------------
        ecg_raw = df['ECG'].values
        time_sec = time if 'Time' in df.columns else np.arange(len(ecg_raw)) / fs_ecg

        # QRS-specific filter
        ecg_qrs = filter_ecg_for_r_peaks(ecg_raw, fs_ecg)

        # Detect R-peaks
        r_peaks, properties = detect_r_peaks(ecg_qrs, fs_ecg)

        # plot_ecg_with_r_peaks(time_sec, ecg_qrs, r_peaks)

    # ---------------- EMG ----------------
    if 'EMG' in df.columns:
        nyq = 0.5 * fs_emg
        highcut = min(450, 0.9 * nyq)
        emg_filtered = apply_filter(
            df['EMG'], filter_type='bandpass',
            lowcut=20, highcut=highcut, fs=fs_emg
        )
        emg_rectified = np.abs(emg_filtered)
        filtered_df['EMG'] = emg_rectified
        #plot_signals(time, df['EMG'], emg_filteed, f"{sheet_name} - EMG")
        ax = axes[row_map['EMG'], col_map[sheet_name]]
        ax.plot(time, df['EMG'], alpha=0.4, label='Original')
        ax.plot(time, emg_filtered, label='Filtered')
        ax.set_title(f"{sheet_name} - EMG")
        ax.legend()

    # ---------------- EDA ----------------
    if 'EDA' in df.columns:
        eda_filtered = apply_filter(
            df['EDA'], filter_type='lowpass',
            cutoff=1.0, fs=fs_eda
        )
        filtered_df['EDA'] = eda_filtered
        #plot_signals(time, df['EDA'], eda_filtered, f"{sheet_name} - EDA")
        ax = axes[row_map['EDA'], col_map[sheet_name]]
        ax.plot(time, df['EDA'], alpha=0.4, label='Original')
        ax.plot(time, eda_filtered, label='Filtered')
        ax.set_title(f"{sheet_name} - EDA")
        ax.legend()

    filtered_outputs[sheet_name] = filtered_df

plt.tight_layout()

# plot frequency spectrums
# Define which signals to process
signal_types = ['ECG', 'EMG', 'EDA']

for sheet_name in sheets:
    print(f"\nProcessing frequency content for {sheet_name}...")
    raw_df = data[sheet_name]
    filt_df = filtered_outputs[sheet_name]  # filtered/rectified signals
    
    for sig in signal_types:
        if sig in raw_df.columns:
            orig_signal = raw_df[sig].values
            # Use filtered signal if it exists, otherwise None
            processed_signal = filt_df[sig].values if sig in filt_df.columns else None
            # Rectify EMG for plotting spectrum
            rectified = True if sig == 'EMG' else False
            
            plot_signal_spectra(
                orig_signal=orig_signal,
                processed_signal=processed_signal,
                fs=fs,  # use the correct sampling rate for this sheet
                title_prefix=f"{sheet_name} - {sig}",
                rectified=rectified
            )


plt.show()


# -------------------------------
# 5. Save filtered data for ML
# -------------------------------
filtered_outputs['Baseline Data'].to_csv(
    "filtered_baseline.csv", index=False
)

filtered_outputs['Test Data'].to_csv(
    "filtered_test.csv", index=False
)

print("\nFiltered data saved:")
print(" - filtered_baseline.csv")
print(" - filtered_test.csv")
