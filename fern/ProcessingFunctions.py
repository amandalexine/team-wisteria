# ProcessingFunctions.py
# 
# This module contains various signal processing utilities used throughout the system.
# It includes:
#   • Live moving average filters for real-time data smoothing
#   • Discrete Wavelet Transform (DWT) for noise reduction
#   • Error statistics computation and visualization tools
#   • Least Means Squared (LMS) Adaptive Filter for error tracking
#   • Import/conversion functions for sensor data (e.g., ECG, EDA, EMG)
#   • Peak detection and rate calculation utilities for physiological signals
#
#_______________________________________________________________________________#

import pywt  # PyWavelets (for wavelet transforms)
import numpy as np  
import matplotlib.pyplot as plt
import os  # file handling

#===============================================================================
# CLASS: LiveMovingAverage
#===============================================================================
class LiveMovingAverage:
    """
    Implements a simple moving average (SMA) over a fixed window size.
    Useful for smoothing real-time or streaming sensor data.

    Attributes:
        window_size (int): Number of samples in the moving average window.
        data (list): Stores recent data points within the window.
        total (float): Running total of values (for efficient average computation).
    """

    def __init__(self, window_size):
        if window_size <= 0:
            raise ValueError("Window size should be positive")
        self.window_size = window_size
        self.data = []
        self.total = 0.0

    def update(self, new_data):
        """
        Adds a new data point and updates the moving average window.
        Drops the oldest sample if the window exceeds the defined size.
        """
        if not isinstance(new_data, (int, float)):
            raise ValueError("New data should be numerical")

        self.data.append(new_data)
        self.total += new_data

        # Maintain fixed window size
        if len(self.data) > self.window_size:
            self.total -= self.data[0]
            self.data.pop(0)

    def calculate_moving_average(self):
        """Returns the current moving average value."""
        if len(self.data) == 0:
            return 0  
        return self.total / len(self.data)

#===============================================================================
# CLASS: DiscreteWaveletTransform
#===============================================================================
class DiscreteWaveletTransform:
    """
    Uses Discrete Wavelet Transform (DWT) for noise reduction and signal cleaning.
    Decomposes the input signal into frequency components, applies thresholding,
    and reconstructs a denoised version of the signal.
    """

    def __init__(self, wavelet='haar', level=1):
        self.wavelet = wavelet
        self.level = level
    
    def clean_wave_data(self, data):
        """
        Applies wavelet decomposition and soft thresholding to remove high-frequency noise.
        """
        coeffs = pywt.wavedec(data, self.wavelet, level=self.level)

        # Noise threshold based on standard deviation of detail coefficients
        threshold = np.std(coeffs[-1]) * np.sqrt(2 * np.log(len(data)))
        new_coeffs = [pywt.threshold(c, threshold, mode='soft') for c in coeffs]

        # Reconstruct cleaned signal
        cleaned_data = pywt.waverec(new_coeffs, self.wavelet)
        return cleaned_data

#===============================================================================
# CLASS: error_stats
#===============================================================================
class error_stats:
    """
    Provides statistical analysis tools for datasets and error computations.
    Includes helper methods for sectioned stats, percent differences, and flag categorization.
    """

    def __init__(self, data):
        self.data = data

    def calculate_stats(self):
        """Computes max, min, mean, and standard deviation for the given dataset."""
        max_val = np.round(np.max(self.data), 3)
        min_val = np.round(np.min(self.data), 3)
        mean_val = np.round(np.mean(self.data), 3)
        std_dev_val = np.round(np.std(self.data), 3)

        return {
            'max': max_val,
            'min': min_val,
            'mean': mean_val,
            'std_dev': std_dev_val
        }

    @staticmethod
    def calculate_percent_difference(stats1, stats2):
        """Computes percent difference between two sets of statistics."""
        percent_diff = {}
        for key in stats1.keys():
            if key in stats2.keys():
                diff = stats2[key] - stats1[key]
                percent_diff[key] = (diff / stats1[key]) * 100 if stats1[key] != 0 else float('inf')
        return percent_diff

    @staticmethod
    def assign_flags(percent_diff):
        """
        Assigns qualitative flags based on the magnitude of percent differences.
        Used to categorize physiological response strength.
        """
        flags = {}
        for key, value in percent_diff.items():
            if value < 0:  # Decrease
                if value >= -15: flags[key] = 'Normal'
                elif value >= -25: flags[key] = 'Mild Response'
                elif value >= -35: flags[key] = 'Moderate Response'
                else: flags[key] = 'Severe Response'
            else:  # Increase
                if value <= 15: flags[key] = 'Normal'
                elif value <= 25: flags[key] = 'Mild Response'
                elif value <= 35: flags[key] = 'Moderate Response'
                else: flags[key] = 'Severe Response'
        return flags

    @staticmethod
    def calculate_sectioned_stats(data, section_size):
        """
        Divides data into equal-sized sections and computes stats per section.
        Useful for analyzing time-varying signals.
        """
        num_sections = len(data) // section_size
        stats = {}

        for i in range(num_sections):
            section = data[i * section_size:(i + 1) * section_size]
            stats[f'{i + 1}'] = {
                'max': np.round(np.max(section), 3),
                'min': np.round(np.min(section), 3),
                'mean': np.round(np.mean(section), 3),
                'std_dev': np.round(np.std(section), 3)
            }
        return stats

    @staticmethod
    def plot_sectioned_stats(stats_result, title):
        """Plots sectioned statistics for visual analysis."""
        section_numbers = list(stats_result.keys())
        max_values = [v['max'] for v in stats_result.values()]
        min_values = [v['min'] for v in stats_result.values()]
        mean_values = [v['mean'] for v in stats_result.values()]
        std_dev_values = [v['std_dev'] for v in stats_result.values()]
        
        graph = plt.figure(figsize=(12, 6))
        plt.suptitle(title)

        plt.subplot(2, 2, 1)
        plt.plot(section_numbers, max_values, marker='o')
        plt.title('Maximum per Section')

        plt.subplot(2, 2, 2)
        plt.plot(section_numbers, min_values, marker='o')
        plt.title('Minimum per Section')

        plt.subplot(2, 2, 3)
        plt.plot(section_numbers, mean_values, marker='o')
        plt.title('Mean per Section')

        plt.subplot(2, 2, 4)
        plt.plot(section_numbers, std_dev_values, marker='o')
        plt.title('Standard Deviation per Section')

        plt.tight_layout()
        plt.show()
        return graph

#===============================================================================
# CLASS: LMSAdaptiveFilter
#===============================================================================
class LMSAdaptiveFilter:
    """
    Implements the Least Mean Squares (LMS) adaptive filtering algorithm.
    Used to minimize estimation error between actual and predicted signals.

    Tracks filter coefficients (a1Hat, b1Hat) over time and visualizes their convergence.
    """

    def __init__(self, data):
        self.N = len(data)
        self.n = np.arange(0, self.N, 1)
        self.x = np.full(self.N, 5)  # input values
        self.y = data                # measured signal

        # Initialize parameters and noise properties
        self.a1 = np.linspace(0.6, 0.3, num=self.N)
        self.b1 = np.linspace(0.9, 0.2, num=self.N)
        self.m, self.sd = 0, 0.2
        self.u = 0.001  # step size (learning rate)

        # Initialize tracking arrays
        self.yHat = np.empty(self.N)
        self.a1Hat = np.empty(self.N)
        self.b1Hat = np.empty(self.N)
        self.e = np.empty(self.N)
        self.error_range = []

        self.a1Hat[1], self.b1Hat[1] = 0, 0

    def update(self):
        """Performs iterative LMS filter updates."""
        for i in range(1, self.N-1):
            self.yHat[i] = self.a1Hat[i]*self.x[i-1] + self.b1Hat[i]*self.y[i-1]
            self.e[i] = self.y[i] - self.yHat[i]
            self.a1Hat[i+1] = self.a1Hat[i] + self.u*self.x[i-1]*self.e[i]
            self.b1Hat[i+1] = self.b1Hat[i] + self.u*self.y[i-1]*self.e[i]

        # Handle final sample
        self.yHat[-1] = self.a1Hat[-1]*self.x[-2] + self.b1Hat[-1]*self.y[-2]
        self.e[-1] = self.y[-1] - self.yHat[-1]

    def error(self):
        """Classifies error magnitudes into qualitative response levels."""
        thresholds = [15, 25, 35, 45, 55]
        for i in range(1, len(self.n)):
            val = self.e[i]
            if val <= thresholds[0]: label = "normal"
            elif val <= thresholds[1]: label = "slight response"
            elif val <= thresholds[2]: label = "mild response"
            elif val <= thresholds[3]: label = "moderate response"
            elif val <= thresholds[4]: label = "severe response"
            else: label = "unknown"
            self.error_range.append((i, label))

    def plot(self):
        """Plots estimated signal vs true signal, error evolution, and parameter updates."""
        # --- Error plot ---
        plt.figure()
        plt.plot(self.n, self.y, 'g', label='Measured Signal')
        plt.plot(self.n, self.yHat, 'b', label='Estimated Signal')
        plt.plot(self.n, self.e, 'r', label='Error')
        plt.title('LMS Adaptive Filter Performance')
        plt.xlabel('Time index (i)')
        plt.ylabel('Signal amplitude (mV)')
        plt.legend()
        plt.grid(True)
        plt.show()

        # --- Parameter tracking plot ---
        plt.figure()
        plt.plot(self.n, self.a1Hat, 'm', label='a1 Estimate')
        plt.plot(self.n, self.b1Hat, 'c', label='b1 Estimate')
        plt.title('Filter Coefficient Convergence')
        plt.xlabel('Time index (i)')
        plt.ylabel('Coefficient value')
        plt.legend()
        plt.grid(True)
        plt.show()

#===============================================================================
# IMPORT & CONVERSION FUNCTIONS
#===============================================================================
def import_array_from_txt(filename):
    """Imports a single-channel data file as a 1D NumPy array."""
    try:
        return np.loadtxt(filename)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return 0

def import_matrix_from_txt(filename):
    """Imports multi-channel (comma-separated) sensor data."""
    if not os.path.exists(filename):
        return None, None, None, 1

    with open(filename, 'r') as file:
        lines = file.readlines()

    ch0, ch1, ch2 = [], [], []
    for line in lines:
        elements = line.strip().split(',')
        ch0.append(int(elements[0]))
        ch1.append(int(elements[1]))
        ch2.append(int(elements[2]))

    return ch0, ch1, ch2, 0

def convert_raw_to_voltage(raw_data, input_range=3.3):
    """Converts 10-bit ADC raw data to voltage (0–input_range V)."""
    normalized = raw_data / 1023.0
    return normalized * input_range

#===============================================================================
# PEAK DETECTION FUNCTIONS
#===============================================================================
def simple_threshold(data, window=2, index=0, sample_rate=1000):
    """
    Determines a dynamic threshold using a short time window.
    """
    window *= sample_rate
    section = data[index:index+window]
    if len(section) == 0:
        return None
    return max(section) - abs(np.std(section))

def peakLocation(array, threshold=1.9):
    """
    Scans array for peaks above threshold.
    Groups local peaks and returns their maximum value/index.
    """
    idx = 0
    peak_array, local_peak_array = [], []
    peak_found = False
    while idx < len(array):
        if array[idx] > threshold:
            peak_found = True
            local_peak_array.append((idx, array[idx]))
        elif peak_found:
            # Record strongest peak in local group
            max_index, max_value = max(local_peak_array, key=lambda x: x[1])
            peak_array.append((max_index, max_value))
            local_peak_array.clear()
            peak_found = False
        idx += 1
    return peak_array

def calculate_peak_rate(peak_tuples, samplerate=1000):
    """Computes overall rate (e.g. heart rate) from detected peaks."""
    sorted_peaks = sorted(peak_tuples, key=lambda x: x[0])
    time_diffs = [sorted_peaks[i+1][0] - sorted_peaks[i][0] for i in range(len(sorted_peaks)-1)]
    time_diffs_sec = [d / samplerate for d in time_diffs]
    heart_rate = 60 / (sum(time_diffs_sec) / len(time_diffs_sec))
    return np.round(heart_rate, 2)

#_______________________________________________________________________________#
