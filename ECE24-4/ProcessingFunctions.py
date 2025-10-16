#Imports
import pywt #pip install PyWavelets - Installation can be finicky on this import
import numpy as np
import matplotlib.pyplot as plt
import os
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
#_______________________________________________________________________________#

#Classes

#Moving averages
class LiveMovingAverage:

    def __init__(self, window_size):
        if window_size <= 0:
            raise ValueError("Window size should be positive")
        self.window_size = window_size
        self.data = []
        self.total = 0.0

    def update(self, new_data):
        if not isinstance(new_data, (int, float)):
            raise ValueError("New data should be numerical")

        self.data.append(new_data)
        self.total += new_data

        if len(self.data) > self.window_size:
            self.total -= self.data[0]
            self.data.pop(0)

    def calculate_moving_average(self):
        if len(self.data) == 0:
            return 0  

        return self.total / len(self.data)

#Discrete Wave Transform
class DiscreteWaveletTransform:
    def __init__(self, wavelet='haar', level=1):
        self.wavelet = wavelet
        self.level = level
    
    def clean_wave_data(self, data):
        #Perform Discrete Wavelet Transform (DWT)
        coeffs = pywt.wavedec(data, self.wavelet, level=self.level)

        #Thresholding to remove noise
        threshold = np.std(coeffs[-1]) * np.sqrt(2 * np.log(len(data)))
        new_coeffs = [pywt.threshold(c, threshold, mode='soft') for c in coeffs]

        #Reconstruct the cleaned signal
        cleaned_data = pywt.waverec(new_coeffs, self.wavelet)

        return cleaned_data


#Error Stats
class error_stats:
    def __init__(self, data):
        self.data = data

    def calculate_stats(self):
        max_val = np.max(self.data)
        min_val = np.min(self.data)
        mean_val = np.mean(self.data)
        std_dev_val = np.std(self.data)

        max_val = np.round(max_val,3)
        min_val = np.round(min_val,3)
        mean_val = np.round(mean_val,3)
        std_dev_val = np.round(std_dev_val,3)

        stats = {
            'max': max_val,
            'min': min_val,
            'mean': mean_val,
            'std_dev': std_dev_val
        }

        return stats

    @staticmethod
    def calculate_percent_difference(stats1, stats2):
        percent_diff = {}
        for key in stats1.keys():
            if key in stats2.keys():
                diff = abs(stats2[key] - stats1[key])
                avg = (stats2[key] + stats1[key]) / 2
                percent_diff[key] = (diff / stats1[key]) * 100 if stats1[key] != 0 else float('inf')

        return percent_diff

    @staticmethod
    def assign_flags(percent_diff):
        flags = {}
        for key, value in percent_diff.items():
            if value < 0:
                if value >= -15:
                    flags[key] = 'Normal'
                elif value >= -25:
                    flags[key] = 'Mild Response'
                elif value >= -35:
                    flags[key] = 'Moderate Response'
                else:
                    flags[key] = 'Severe Response'
            else:
                if value <= 15:
                    flags[key] = 'Normal'
                elif value <= 25:
                    flags[key] = 'Mild Response'
                elif value <= 35:
                    flags[key] = 'Moderate Response'
                else:
                    flags[key] = 'Severe Response'
        return flags

    @staticmethod
    def calculate_sectioned_stats(data, section_size):
        num_sections = len(data) // section_size

        stats = {}

        for i in range(num_sections):
            section = data[i * section_size:(i + 1) * section_size]
            max_val = np.max(section)
            min_val = np.min(section)
            mean_val = np.mean(section)
            std_dev_val = np.std(section)

            max_val = np.round(max_val,3)
            min_val = np.round(min_val,3)
            mean_val = np.round(mean_val,3)
            std_dev_val = np.round(std_dev_val,3)


            stats[f'{i + 1}'] = { #changed from 'secton_{i + 1}' tp {i+1} for plotting axis crowding
                'max': max_val,
                'min': min_val,
                'mean': mean_val,
                'std_dev': std_dev_val
            }
        return stats

    @staticmethod
    def plot_sectioned_stats(stats_result, title):
        section_numbers = []
        max_values = []
        min_values = []
        mean_values = []
        std_dev_values = []

        for section_name, stats in stats_result.items():
            section_numbers.append(section_name)
            max_values.append(stats['max'])
            min_values.append(stats['min'])
            mean_values.append(stats['mean'])
            std_dev_values.append(stats['std_dev'])
        
        fig = Figure(figsize=(10, 6), dpi=75)
        fig.suptitle(title, fontsize=16)

        ax1 = fig.add_subplot(2, 2, 1)
        ax1.plot(section_numbers, max_values, marker='o')
        ax1.set_title('Maximum Values per Section')
        ax1.set_xlabel('Section')
        ax1.set_ylabel('Max Value')

        ax2 = fig.add_subplot(2, 2, 2)
        ax2.plot(section_numbers, min_values, marker='o')
        ax2.set_title('Minimum Values per Section')
        ax2.set_xlabel('Section')
        ax2.set_ylabel('Min Value')

        ax3 = fig.add_subplot(2, 2, 3)
        ax3.plot(section_numbers, mean_values, marker='o')
        ax3.set_title('Mean Values per Section')
        ax3.set_xlabel('Section')
        ax3.set_ylabel('Mean Value')

        ax4 = fig.add_subplot(2, 2, 4)
        ax4.plot(section_numbers, std_dev_values, marker='o')
        ax4.set_title('Standard Deviation Values per Section')
        ax4.set_xlabel('Section')
        ax4.set_ylabel('Std Dev Value')

        fig.tight_layout(pad=2.0)

        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        
        return fig
    

#LMS Adaptive filter
class LMSAdaptiveFilter:
    def __init__(self, data):
        self.N = len(data)         # total number of data points
        self.n = np.arange(0, self.N, 1)   # [0,..., N-1] (vector)          
        self.x = np.arange(0, self.N, 1)   # time values for X
        self.y = data              # mV values for Y
        self.x.fill(5)                # constant measured x concentration investigate further
        self.a1 = np.linspace(0.6, 0.3, num=self.N)  # a1 parameter decreasing from 0.6 to 0.3 (vector)
        self.b1 = np.linspace(0.9, 0.2, num=self.N)  # b1 parameter decreasing from 0.9 to 0.2 (vector)
        self.m = 0                    # mean of Gaussian noise
        self.sd = 0.2                 # standard deviation of Gaussian noise 
        
        self.yHat = np.empty(self.N)       # estimated mV  (vector)
        self.a1Hat = np.empty(self.N)      # estimated a1 parameter (vector)                                                          
        self.b1Hat = np.empty(self.N)      # estimated b1 parameter (vector)                                                        
        self.e = np.empty(self.N)          # y estimation error in mV (vector) (= y - yHat)
        self.error_range = []              #error catergorization
        self.a1Hat[1] = 0             # initial estimated a1 parameter                                                   
        self.b1Hat[1] = 0             # initial estimated b1 parameter 
        self.u = 0.001                # step size (mu)
    
    def update(self):
        for i in range (1, self.N-1):                             
            # Least Mean Squares(LMS) adaptive filter                          
            self.yHat[i] = self.a1Hat[i]*self.x[i-1] + self.b1Hat[i]*self.y[i-1]      # estimated mV concentration
            self.e[i] = self.y[i] - self.yHat[i]                            # mV estimation error
            self.a1Hat[i+1] = self.a1Hat[i] + self.u*self.x[i-1]*self.e[i]            # estimated a1 parameter
            self.b1Hat[i+1] = self.b1Hat[i] + self.u*self.y[i-1]*self.e[i]            # estimated b1 parameter

        self.yHat[self.N-1] = self.a1Hat[self.N-1] * self.x[self.N-2] + self.b1Hat[self.N-1] * self.y[self.N-2]  # last estimated mV concentration
        self.e[self.N-1] = self.y[self.N-1] - self.yHat[self.N-1]  # last mV estimation error

    def error(self):
        threshold_1 = 15  # normal
        threshold_2 = 25  # slight response
        threshold_3 = 35  # mild response
        threshold_4 = 45  # moderate response
        threshold_5 = 55  # severe response
        for i in range(1, len(self.n)): 
            if self.e[i] <= threshold_1:
                self.error_range.append((i, "normal"))
            elif threshold_1 < self.e[i] <= threshold_2:
                self.error_range.append((i, "slight response"))
            elif threshold_2 < self.e[i] <= threshold_3:
                self.error_range.append((i, "mild response"))
            elif threshold_3 < self.e[i] <= threshold_4:
                self.error_range.append((i, "moderate response"))
            elif threshold_4 < self.e[i] <= threshold_5:
                self.error_range.append((i, "severe response"))
            else:
                self.error_range.append((i, "unknown"))

    def error_lms_section(self, section_size, sampling_rate = 1000):
        section_size = section_size * sampling_rate
        sections = [self.error_range[i:i + section_size] for i in range(0, len(self.error_range), section_size)]
        section_labels = []
        for section in sections:
            labels = {}
            for _, label in section:
                if label in labels:
                    labels[label] += 1
                else:
                    labels[label] = 1
            if labels:
                max_label = max(labels, key=labels.get)
                section_labels.append(max_label)
            else:
                section_labels.append("unknown")
        return section_labels
        
    def average_threshold(self):
        label_counts = {
            "normal": 0,
            "slight response": 0,
            "mild response": 0,
            "moderate response": 0,
            "severe response": 0,
            "unknown": 0
        }
        for _, label in self.error_range:
            if label in label_counts:
                label_counts[label] += 1
                
        max_label = max(label_counts, key=label_counts.get)
        return max_label



    def plot(self): 
        graph1 = plt.figure(figsize=(10, 8), dpi=75)                                       
        plt.plot(self.n, self.y, 'g', label='mV values')
        plt.plot(self.n, self.yHat, 'b', label='estimated mV values')
        plt.plot(self.n, self.e, 'r', label='estimation error')
        #error annotations
        # Plotting error reactions based on error_range
        for i, error_type in self.error_range:
            if error_type == "normal":
                pass  # Do nothing for "normal" case
            elif error_type == "slight response":
                plt.annotate('Slight Response', xy=(i, self.e[i]), xytext=(i, self.e[i]+0.1),
                            arrowprops=dict(facecolor='black', shrink=0.05))
            elif error_type == "mild response":
                plt.annotate('Mild Response', xy=(i, self.e[i]), xytext=(i, self.e[i]+0.1),
                            arrowprops=dict(facecolor='black', shrink=0.05))
            elif error_type == "moderate response":
                plt.annotate('Moderate Response', xy=(i, self.e[i]), xytext=(i, self.e[i]+0.1),
                            arrowprops=dict(facecolor='black', shrink=0.05))
            elif error_type == "severe response":
                plt.annotate('Severe Response', xy=(i, self.e[i]), xytext=(i, self.e[i]+0.1),
                            arrowprops=dict(facecolor='black', shrink=0.05))
            else:
                plt.annotate('Unknown', xy=(i, self.e[i]), xytext=(i, self.e[i]+0.1),
                            arrowprops=dict(facecolor='black', shrink=0.05))
        #end annotations
        plt.xlabel('time (i)')                                                         
        plt.ylabel('mV values')
        plt.legend(loc='upper right')
        plt.title('LMS Adaptive Filter')
        plt.axis([0, self.N, 0, 2])  # Set y-axis limits for HR data
        plt.grid(True)
        plt.tight_layout()
        # plt.subplots_adjust(top=0.90, bottom=0.10)
        # plt.show()


        graph2 = plt.figure(figsize=(10, 8), dpi=75)
        plt.plot(self.n, self.a1Hat, 'm', label='estimated a1')
        plt.plot(self.n, self.b1Hat, 'c', label='estimated b1')
        plt.xlabel('time (i)')                                                         
        plt.ylabel('parameter value')
        plt.legend(loc='upper right')
        plt.title('Training Estimated Parameter Values')
        plt.axis([0, self.N, 0, 2])  # Set y-axis limits for parameter values
        plt.grid(True)
        plt.tight_layout()
        # plt.subplots_adjust(top=0.90, bottom=0.10)
        # plt.show()

        return graph1, graph2
#_______________________________________________________________________________#


#Functions 

#import data from txt file
def import_array_from_txt(filename):
    #simple loader for one channel and testing
    try:
        array_data = np.loadtxt(filename)
        return array_data
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return 0

def import_matrix_from_txt(filename): #code for importing matrix into arrays
    #advanced loader for multiple channel capture
    if not os.path.exists(filename):
        return None, None,None, 1
    
    with open(filename, 'r') as file:
        lines = file.readlines()

    channel_0_data = []
    channel_1_data = []
    channel_2_data = []

    for line in lines:
        # Split the line on commas to get individual elements
        elements = line.strip().split(',')
        channel_0_data.append(float(elements[0]))  #Skip the first value, index 0
        channel_1_data.append(float(elements[1]))
        channel_2_data.append(float(elements[2]))

    return channel_0_data, channel_1_data, channel_2_data, 0

def import_matrix_full_from_text(filename):
    matrix = []
    try:
        with open(filename, 'r') as file:
            for line in file:
                values = line.strip().split()
                row = [int(value) for value in values]
                matrix.append(row)
    except FileNotFoundError:
        return None, 1
    except ValueError:
        return None, 1
    
    result = [list(row) for row in matrix]
    return result, 0
    
    

#data Conversion to proper voltage range
def convert_raw_to_voltage(raw_data, input_range=3.3):
    #10-bit ADC -> 0-3.3V(0 to input range)
    #simple ADC conversion for 10 bit(0-1023) conversion
    #note that only 4 channels can be run at 10 bit at once for BITalino 
    normalized_data = raw_data / 1023.0
    voltage_data = normalized_data * input_range
    
    return voltage_data

def convert_raw_ecg(adc_data):
    #0mV to 3300mV
    #adc = raw value samples from the channel
    vcc = 3.3   #operating voltage
    gain = 1100 #sensor gain
    #note that only 4 channels can be run at 10 bit at once for BITalino
    n = 10      #bit resolution 

    ecg_v = [(((adc_val)/(2**(n))-0.5)*vcc)/gain for adc_val in adc_data]
    ecg_mv = [ecg_v * 1000 for ecg_v in ecg_v]

    return ecg_mv

def convert_raw_eda(adc_data):
    #0us - 25us
    #adc = raw value samples from the channel
    vcc = 3.3       #operating voltage
    gain = 0.132    #sensor gain
    #note that only 4 channels can be run at 10 bit at once for BITalino
    n = 10          #bit resolution

    eda_us = [(((adc_val)/(2**(n)))*vcc)/(gain) for adc_val in adc_data]
    #eda_s = [eda_us * 1 * (10^(-6)) for ecg_v in eda_s] #optional conversion to s

    return eda_us

def convert_raw_emg(adc_data):
    #-1.64mV, 1.64mV
    #adc = raw value samples from the channel
    vcc = 3.3   #operating voltage
    gain = 1009 #sensor gain
    #note that only 4 channels can be run at 10 bit at once for BITalino
    n = 10      #bit resolution

    emg_v = [((adc_val)/(2**(n))-0.5)*vcc/gain for adc_val in adc_data]
    emg_mv = [emg_v * 1000 for emg_v in emg_v]


    return emg_mv

#Simple Threshold setter for peak identification
def simple_threshold(data, window=2, index=0, sample_rate=1000):
    window = window * sample_rate
    section = data[index:index+window]
    if len(section) == 0:
        return None  
    threshold = max(section) - abs(np.std(section))
    return threshold

#Peak Detection
def peakLocation(array,threshold = 1.9): 
    idx = 0
    peak_array = [] #array holds peak values
    local_peak_array = []
    peak_found = False  # Initialize peak_found outside the loop
    while idx < len(array):
        if (array[idx] > threshold):
            peak_found = True
            local_peak_array.append((idx, array[idx]))
        elif peak_found:  # If peak_found is True, meaning a peak was found previously
            max_value = float('-inf')  # Initialize with negative infinity to ensure any value will be greater
            max_index = None

            #Iterate through the local_peak_array to find the maximum value and its index
            for index, value in local_peak_array:
                if value > max_value:
                    max_value = value
                    max_index = index
            peak_array.append((max_index, max_value))
            local_peak_array.clear()
            peak_found = False
        idx += 1  # Increment idx inside the loop

    return peak_array

#peak rate calculation
def calculate_peak_rate(peak_tuples, samplerate=1000):
    sorted_peaks = sorted(peak_tuples, key=lambda x: x[0])
    
    #Calculate time differences between consecutive peaks
    time_diffs = [sorted_peaks[i+1][0] - sorted_peaks[i][0] for i in range(len(sorted_peaks)-1)]
    
    #Convert seconds
    time_diffs_sec = [time_diff / samplerate for time_diff in time_diffs]
    
    #Calculate rate per minute
    heart_rate = 60 / (sum(time_diffs_sec) / len(time_diffs_sec))
    heart_rate = np.round(heart_rate,2)
    
    return heart_rate

#peak rate calculation over interval
def calculate_peak_rate_over_interval(peak_tuples, samplerate=1000, interval=15, tolerance=5): #need more testing data longer
    sorted_peaks = sorted(peak_tuples, key=lambda x: x[0])
    heart_rates = []
    
    #Calculate time differences between consecutive peaks
    time_diffs = [sorted_peaks[i+1][0] - sorted_peaks[i][0] for i in range(len(sorted_peaks)-1)]
    
    #Convert seconds
    time_diffs_sec = [time_diff / samplerate for time_diff in time_diffs]
    
    #Calculate rate per minute
    for i in range(len(time_diffs_sec)):
        time_diff_sum = 0
        count = 0
        for j in range(i, len(time_diffs_sec)):
            time_diff_sum += time_diffs_sec[j]
            count += 1
            if time_diff_sum >= interval:
                heart_rate = 60 / (time_diff_sum / count)
                if len(heart_rates) == 0 or abs(heart_rate - heart_rates[-1]) <= tolerance:
                    heart_rates.append(heart_rate)
                break
                
    return heart_rates

#_______________________________________________________________________________#
