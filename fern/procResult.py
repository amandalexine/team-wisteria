# procResults.py
#
# Performs signal analysis on baseline and test bioelectric data, including:
#    - Importing raw signals from text files
#    - Preprocessing (conversion, filtering, wavelet denoising)
#    - Peak detection and rate computation (EDA, ECG, EMG)
#    - Statistical analysis and adaptive filtering
#    - Graph generation and visualization
#    - Displaying and saving results
#
#
# Internal packages:
#    - ProcessingFunctions (signal processing utilities)
#    - saveFunc (handles saving graphs/results)
#    - test_settings (stores shared variables between modules)
#_______________________________________________________________________________#


# -------------------------- External Imports --------------------------
import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
import typing

# -------------------------- Internal Imports --------------------------
import ProcessingFunctions as proc  # for signal processing utilities
import saveFunc as sv  
import test_settings as set  # shared state across modules

# -------------------------- Global Variables --------------------------
# Dictionaries to hold statistical results for baseline signals
eda_stats_baseline = dict[str, typing.Any]
ecg_stats_baseline = dict[str, typing.Any]
emg_stats_baseline = dict[str, typing.Any]

# Lists to store adaptive filter results
filter_eda_stats_baseline = []
filter_ecg_stats_base = []
filter_emg_stats_baseline = []

# Global baseline ECG heart rate (used for comparison)
ecg_bpm_base = 0


# ---------------------------------------------------------------------
#                          BASELINE ANALYSIS
# ---------------------------------------------------------------------
def analyze_baseline(channel, samplingRate):
    """
    Processes baseline bioelectric data for EDA, ECG, and EMG.

    Steps:
        1. Import raw baseline signals from 'baseline_sequence.txt'
        2. Convert raw ADC data to physical units
        3. Denoise signals using Discrete Wavelet Transform (DWT)
        4. Detect peaks and compute per-channel rates (bpm)
        5. Plot baseline signals with detected peaks
        6. Compute error statistics and sectioned stats plots
        7. Apply Least Means Squares (LMS) adaptive filtering
        8. Return list of generated matplotlib figures

    Args:
        channel (list[bool]): [EMG, ECG, EDA] flags indicating active channels
        samplingRate (float): Sampling rate of recorded signals

    Returns:
        list[matplotlib.figure.Figure]: Figures for visualization and export
    """

    graphs_list = []  # Store generated graphs for saving/export
    emg_raw, ecg_raw, eda_raw, error = proc.import_matrix_from_txt('baseline_sequence.txt')

    if error == 1:
        print("Error in baseline recording.\n")
        return

    # -------------------- Step 1: Convert Raw Signals --------------------
    if channel[2]:
        eda_proced = proc.convert_raw_eda(eda_raw)
    if channel[1]:
        ecg_proced = proc.convert_raw_ecg(ecg_raw)
    if channel[0]:
        emg_proced = proc.convert_raw_emg(emg_raw)

    # -------------------- Step 2: Apply DWT Denoising --------------------
    dwt = proc.DiscreteWaveletTransform(wavelet='db4', level=7)

    if channel[2]:
        eda_proced = dwt.clean_wave_data(eda_proced)
    if channel[1]:
        ecg_proced = dwt.clean_wave_data(ecg_proced)
    if channel[0]:
        emg_proced = dwt.clean_wave_data(emg_proced)

    # -------------------- Step 3: Peak Detection -------------------------
    if channel[2]:
        eda_threshold = proc.simple_threshold(eda_proced)
        eda_peaks_location = proc.peakLocation(eda_proced, eda_threshold)
        eda_bpm_array = proc.calculate_peak_rate_over_interval(eda_peaks_location, interval=5)

    if channel[1]:
        ecg_threshold = proc.simple_threshold(ecg_proced)
        ecg_peaks_location = proc.peakLocation(ecg_proced, ecg_threshold)
        ecg_bpm_array = proc.calculate_peak_rate_over_interval(ecg_peaks_location, interval=5)
        global ecg_bpm_base
        ecg_bpm_base = proc.calculate_peak_rate(ecg_peaks_location)  # store baseline HR

    if channel[0]:
        emg_threshold = proc.simple_threshold(emg_proced)
        emg_peaks_location = proc.peakLocation(emg_proced, emg_threshold)
        emg_bpm_array = proc.calculate_peak_rate_over_interval(emg_peaks_location, interval=5)

    # -------------------- Step 4: Graph Raw Signals ----------------------
    graph1 = plt.figure(figsize=(12, 8))

    ax1_eda = graph1.add_subplot(311)
    ax2_ecg = graph1.add_subplot(312)
    ax3_emg = graph1.add_subplot(313)

    # Plot EDA
    ax1_eda.plot(eda_proced, label='EDA Signal')
    ax1_eda.scatter([x[0] for x in eda_peaks_location], [x[1] for x in eda_peaks_location],
                    color='red', label='Peaks')
    ax1_eda.set_title('Baseline EDA')
    ax1_eda.set_ylabel('Conductivity (µS)')
    ax1_eda.legend()

    # Plot ECG
    ax2_ecg.plot(ecg_proced, label='ECG Signal')
    ax2_ecg.scatter([x[0] for x in ecg_peaks_location], [x[1] for x in ecg_peaks_location],
                    color='red', label='Peaks')
    ax2_ecg.set_title('Baseline ECG')
    ax2_ecg.set_ylabel('Amplitude (mV)')
    ax2_ecg.legend()

    # Plot EMG
    ax3_emg.plot(emg_proced, label='EMG Signal')
    ax3_emg.scatter([x[0] for x in emg_peaks_location], [x[1] for x in emg_peaks_location],
                    color='red', label='Peaks')
    ax3_emg.set_title('Baseline EMG')
    ax3_emg.set_xlabel('Time (ms)')
    ax3_emg.set_ylabel('Muscle Amplitude (mV)')
    ax3_emg.legend()

    plt.tight_layout()
    plt.show()
    graphs_list.append(graph1)

    # -------------------- Step 5: Compute Error Statistics ----------------
    section_size = 2000

    if channel[2]:
        eda_stats_obj = proc.error_stats(eda_proced)
        eda_stats = eda_stats_obj.calculate_stats()
        eda_stats_sectioned_result = proc.error_stats.calculate_sectioned_stats(eda_proced, section_size)
        graphs_list.append(proc.error_stats.plot_sectioned_stats(eda_stats_sectioned_result, "EDA Stats Plot"))

    if channel[1]:
        ecg_stats_obj = proc.error_stats(ecg_proced)
        ecg_stats = ecg_stats_obj.calculate_stats()
        ecg_stats_sectioned_result = proc.error_stats.calculate_sectioned_stats(ecg_proced, section_size)
        graphs_list.append(proc.error_stats.plot_sectioned_stats(ecg_stats_sectioned_result, "ECG Stats Plot"))

    if channel[0]:
        emg_stats_obj = proc.error_stats(emg_proced)
        emg_stats = emg_stats_obj.calculate_stats()
        emg_stats_sectioned_result = proc.error_stats.calculate_sectioned_stats(emg_proced, section_size)
        graphs_list.append(proc.error_stats.plot_sectioned_stats(emg_stats_sectioned_result, "EMG Stats Plot"))

    # -------------------- Step 6: LMS Adaptive Filtering ------------------
    if channel[2]:
        filter_eda = proc.LMSAdaptiveFilter(eda_proced)
        filter_eda.update()
        filter_eda.error()
        filter_eda_stats_base = filter_eda.e

    if channel[1]:
        filter_ecg = proc.LMSAdaptiveFilter(ecg_proced)
        filter_ecg.update()
        filter_ecg.error()
        filter_ecg_stats_base = filter_ecg.e

    if channel[0]:
        filter_emg = proc.LMSAdaptiveFilter(emg_proced)
        filter_emg.update()
        filter_emg.error()
        filter_emg_stats_base = filter_emg.e

    # Plot LMS filter outputs
    graph4 = plt.figure(figsize=(12, 8))
    graph4.suptitle('Least Means Squares Adaptive Filter')

    ax1 = graph4.add_subplot(311)
    ax2 = graph4.add_subplot(312)
    ax3 = graph4.add_subplot(313)

    ax1.plot(filter_eda.n, filter_eda.y, 'g', label='Original EDA')
    ax1.plot(filter_eda.n, filter_eda.yHat, 'b', label='Estimated EDA')
    ax1.plot(filter_eda.n, filter_eda.e, 'r', label='Error')
    ax1.set_title('EDA Estimation')
    ax1.legend()

    ax2.plot(filter_ecg.n, filter_ecg.y, 'g', label='Original ECG')
    ax2.plot(filter_ecg.n, filter_ecg.yHat, 'b', label='Estimated ECG')
    ax2.plot(filter_ecg.n, filter_ecg.e, 'r', label='Error')
    ax2.set_title('ECG Estimation')
    ax2.legend()

    ax3.plot(filter_emg.n, filter_emg.y, 'g', label='Original EMG')
    ax3.plot(filter_emg.n, filter_emg.yHat, 'b', label='Estimated EMG')
    ax3.plot(filter_emg.n, filter_emg.e, 'r', label='Error')
    ax3.set_title('EMG Estimation')
    ax3.legend()

    plt.tight_layout()
    plt.show()
    graphs_list.append(graph4)

    # -------------------- Step 7: Store Stats Globally -------------------
    if channel[2]:
        eda_stats_baseline = eda_stats
    if channel[1]:
        ecg_stats_baseline = ecg_stats
    if channel[0]:
        emg_stats_baseline = emg_stats

    return graphs_list


# ---------------------------------------------------------------------
#                           RESULT ANALYSIS
# ---------------------------------------------------------------------
def analyze_result(channel, samplingRate):
    """
    Processes test sequence data and compares it to baseline data.

    Steps:
        1. Import and preprocess test sequence
        2. Apply DWT denoising and peak detection
        3. Compute per-channel statistics and filtering
        4. Compare test vs baseline using percent difference
        5. Display summary statistics in a GUI window

    Args:
        channel (list[bool]): [EMG, ECG, EDA] flags
        samplingRate (float): Signal sampling rate

    Returns:
        list[matplotlib.figure.Figure]: Figures for visualization/export
    """
    # (rest of function remains identical; comments would follow same structure)

    graphs_list = []    #graph list for save function
    emg_raw,ecg_raw,eda_raw, error = proc.import_matrix_from_txt('test_sequence.txt')
    if error == 1:
        print("Error in Results recording \n")
        return
    #______________________________Reinterpreting the signals from ADC to intended Precision______________________________
    eda_proced = proc.convert_raw_eda(eda_raw)
    ecg_proced = proc.convert_raw_ecg(ecg_raw)
    emg_proced = proc.convert_raw_emg(emg_raw)
    

    #_______________________________Running data through DWT class_________________________________________________________
    dwt = proc.DiscreteWaveletTransform(wavelet='db4', level=7)

    eda_proced =  dwt.clean_wave_data(eda_proced)
    ecg_proced =  dwt.clean_wave_data(ecg_proced)
    emg_proced =  dwt.clean_wave_data(emg_proced)

    #_______________________________Peak detection on data_________________________________________________________________

    #____EDA____
    eda_threshold = proc.simple_threshold(eda_proced)
    eda_peaks_location = proc.peakLocation(eda_proced,eda_threshold)

    eda_bpm_array = proc.calculate_peak_rate_over_interval(eda_peaks_location, interval=5)

    #____ECG____
    ecg_threshold = proc.simple_threshold(ecg_proced)
    ecg_peaks_location = proc.peakLocation(ecg_proced,ecg_threshold)


    ecg_bpm_array = proc.calculate_peak_rate_over_interval(ecg_peaks_location, interval=5)

    ecg_bpm = proc.calculate_peak_rate(ecg_peaks_location)

    #____EMG____
    emg_threshold = proc.simple_threshold(emg_proced)
    emg_peaks_location = proc.peakLocation(emg_proced,emg_threshold)

    emg_bpm_array = proc.calculate_peak_rate_over_interval(emg_peaks_location, interval=5)
    

    #___Graphing___
    # Create a figure
    graph1 = plt.figure()
    graph1.set_size_inches(12, 8) 
    

    # Create subplots within the figure
    ax1_eda = graph1.add_subplot(311)
    ax2_ecg = graph1.add_subplot(312)
    ax3_emg = graph1.add_subplot(313)

    # Plot data on each subplot
    ax1_eda.plot(eda_proced, label='EDA Signal')
    ax1_eda.legend()
    ax1_eda.scatter([x[0] for x in eda_peaks_location], [x[1] for x in eda_peaks_location], color='red', label='Peaks')
    ax1_eda.set_title('Result EDA')
    ax1_eda.set_xlabel('Time(mS)')
    ax1_eda.set_ylabel('Conductivity(us)')

    ax2_ecg.plot(ecg_proced, label='ECG Signal')
    ax2_ecg.legend()
    ax2_ecg.scatter([x[0] for x in ecg_peaks_location], [x[1] for x in ecg_peaks_location], color='red', label='Peaks')
    ax2_ecg.set_title('Result ECG')
    ax2_ecg.set_xlabel('Time(mS)')
    ax2_ecg.set_ylabel('Heartrate Amplitude(mV)')

    ax3_emg.plot(emg_proced, label='EMG Signal')
    ax3_emg.legend()
    ax3_emg.scatter([x[0] for x in emg_peaks_location], [x[1] for x in emg_peaks_location], color='red', label='Peaks')
    ax3_emg.set_title('Result EMG')
    ax3_emg.set_xlabel('Time(mS)')
    ax3_emg.set_ylabel('Muscle Amplitude(mV)')

    plt.tight_layout()
    plt.grid(True)
    plt.show()
    graphs_list.append(graph1)
    #_______________________________Error Stats_____________________________________________________________________
    section_size = 2000

     #____EDA____
    eda_stats_obj = proc.error_stats(eda_proced)
    eda_stats = eda_stats_obj.calculate_stats()
    eda_stats_baseline = eda_stats
    eda_stats_sectioned_result = proc.error_stats.calculate_sectioned_stats(eda_proced, section_size)
    graph2 = proc.error_stats.plot_sectioned_stats(eda_stats_sectioned_result,"EDA Stats Plot")
    graphs_list.append(graph2)

    #____ECG____
    ecg_stats_obj = proc.error_stats(ecg_proced)
    ecg_stats = ecg_stats_obj.calculate_stats()
    ecg_stats_baseline = ecg_stats
    ecg_stats_sectioned_result = proc.error_stats.calculate_sectioned_stats(ecg_proced, section_size)
    graph3 = proc.error_stats.plot_sectioned_stats(ecg_stats_sectioned_result,"ECG Stats Plot")
    graphs_list.append(graph3)

    #____EMG____
    emg_stats_obj = proc.error_stats(emg_proced)
    emg_stats = emg_stats_obj.calculate_stats()
    emg_stats_baseline = emg_stats
    emg_stats_sectioned_result = proc.error_stats.calculate_sectioned_stats(emg_proced, section_size)
    graph4 = proc.error_stats.plot_sectioned_stats(emg_stats_sectioned_result,"EMG Stats Plot")
    graphs_list.append(graph4)

    #____Graphs____


    #_______________________________Least Means Squared Adaptive Filtering__________________________________________
    filter_eda = proc.LMSAdaptiveFilter(eda_proced)
    filter_eda.update()
    filter_eda.error()

    filter_ecg = proc.LMSAdaptiveFilter(ecg_proced)
    filter_ecg.update()
    filter_ecg.error()

    filter_emg = proc.LMSAdaptiveFilter(emg_proced)
    filter_emg.update()
    filter_emg.error()

    # Set the figure size
    graph4 = plt.figure()
    graph4.set_size_inches(12, 8)  #Assuming inches for the size
    graph4.suptitle('Least Means Squared Adaptive Filter')

    # Create subplots
    ax1 = graph4.add_subplot(311)
    ax2 = graph4.add_subplot(312)
    ax3 = graph4.add_subplot(313)

    #Plot EDA
    ax1.plot(filter_eda.n, filter_eda.y,'g', label='Original EDA')
    ax1.plot(filter_eda.n, filter_eda.yHat,'b', label='Estimated EDA')
    ax1.plot(filter_eda.n, filter_eda.e,'r', label='Estimation Error')
    ax1.set_title('EDA Estimation')
    ax1.set_xlabel('Time(mS)')
    ax1.set_ylabel('Conductivity(us)')
    ax1.legend()

    #Plot ECG
    ax2.plot(filter_ecg.n, filter_ecg.y,'g', label='Original ECG')
    ax2.plot(filter_ecg.n, filter_ecg.yHat,'b', label='Estimated ECG')
    ax2.plot(filter_ecg.n, filter_ecg.e,'r', label='Estimation Error')
    ax2.set_title('ECG Estimation')
    ax2.set_xlabel('Time(mS)')
    ax2.set_ylabel('Heartrate Amplitude(mV)')
    ax2.legend()

    #Plot EMG
    ax3.plot(filter_emg.n, filter_emg.y,'g', label='Original EMG')
    ax3.plot(filter_emg.n, filter_emg.yHat,'b', label='Estimated EMG')
    ax3.plot(filter_emg.n, filter_emg.e,'r', label='Estimation Error')
    ax3.set_title('EMG Estimation')
    ax3.set_xlabel('Time(mS)')
    ax3.set_ylabel('Muscle Amplitude(mV)')
    ax3.legend()

    plt.tight_layout()
    plt.show()
    graphs_list.append(graph4)

    #___________________________________________________stats______________________________________-
    #needs second set of data
    eda_stats_compare = proc.error_stats.calculate_percent_difference(eda_stats_baseline, eda_stats)
    eda_stats_compared_flags = proc.error_stats.assign_flags(eda_stats_compare)
    ecg_stats_compare = proc.error_stats.calculate_percent_difference(ecg_stats_baseline, ecg_stats)
    ecg_stats_compared_flags = proc.error_stats.assign_flags(ecg_stats_compare)
    emg_stats_compare = proc.error_stats.calculate_percent_difference(emg_stats_baseline, emg_stats)
    emg_stats_compared_flags = proc.error_stats.assign_flags(emg_stats_compare)

    eda_filter_stats_section = filter_eda.error_lms_section
    ecg_filter_stats_section = filter_ecg.error_lms_section
    emg_filter_stats_section = filter_emg.error_lms_section

    filter_eda_stats_baseline = filter_eda.average_threshold
    filter_ecg_stats_baseline = filter_ecg.average_threshold
    filter_emg_stats_baseline = filter_emg.average_threshold

    #print("LMS stats EDA: ")
    #print(filter_eda_stats_baseline)
    # i_eda = 1
    # for elements in filter_eda_stats_baseline:
    #     print("Section {i_eda} : element")
    #     i_eda = i_eda + 1
    
    #print("LMS stats ECG: ")
    #print(filter_emg_stats_baseline)
    # i_ecg = 1
    # for elements in filter_ecg_stats_baseline:
    #     print("Section {i_ecg} : element")
    #     i_ecg = i_ecg + 1

    # i_emg = 1
    #print("LMS stats EMG: ")
    #print(filter_emg_stats_baseline)
    # for elements in filter_emg_stats_baseline:
    #     print("Section {i_emg} : element")
    #     i_emg = i_emg + 1

    
    stats_text = (
        "Baseline Heartrate: {}\n"
        "Test Heartrate: {}\n"

        "Stats Baseline EDA: {}\n"
        "Stats Test EDA: {}\n"
        "Percent Difference EDA: {}\n"
        "Flags EDA: {}\n\n"

        "Stats Baseline ECG: {}\n"
        "Stats Test ECG: {}\n"
        "Percent Difference ECG: {}\n"
        "Flags ECG: {}\n\n"

        "Stats Baseline EMG: {}\n"
        "Stats Test EMG: {}\n"
        "Percent Difference EMG: {}\n"
        "Flags EMG: {}\n\n"
    ).format(
        ecg_bpm_base, ecg_bpm,
        eda_stats_baseline, eda_stats, eda_stats_compare, eda_stats_compared_flags,
        ecg_stats_baseline, ecg_stats, ecg_stats_compare, ecg_stats_compared_flags,
        emg_stats_baseline, emg_stats, emg_stats_compare, emg_stats_compared_flags
    )

    stats_window = tk.Tk()
    stats_window.title("Statistics")

    text = tk.Text(stats_window, height=200, width=500)
    text.config(font=("Helvetica",12))
    text.insert(tk.END, stats_text)
    text.pack()

    return graphs_list
    

# --------------------------------MAIN FUNCTION-----------------------------------------
def main(file_path,channel,samplingRate):
    channel = [True, True, True]
    print("main")
    graphs = analyze_baseline(channel,samplingRate)
    print("back in main")
    sv.save_graphs_to_excel(file_path, graphs)
    graphs = analyze_result(channel,samplingRate)
    sv.save_graphs_to_excel(file_path, graphs)

    return
