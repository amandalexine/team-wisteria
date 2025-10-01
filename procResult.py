#external imports
import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
import typing


#internal imports
import ProcessingFunctions as proc
import saveFunc as sv
import test_settings as set #stored variables passed by refrence between files

#Globals
eda_stats_baseline = dict[str, typing.Any]
ecg_stats_baseline = dict[str, typing.Any]
emg_stats_baseline = dict[str, typing.Any]

filter_eda_stats_baseline = []
filter_ecg_stats_base = []
filter_emg_stats_baseline = []

ecg_bpm_base = 0




#channels = [emg,ecg,eda]
def analyze_baseline(channel,samplingRate):
    graphs_list = []    #graph list for save function
    #raw_data, error = proc.import_matrix_full_from_text('baseline_sequence.txt') #new based on partial to full analysis
    emg_raw, ecg_raw, eda_raw, error = proc.import_matrix_from_txt('baseline_sequence.txt') # old based on full analysis

    if error == 1:
        print("Error in baseline recording \n")
        return
    
    #variable for graphing
    # emg_peaks_location = None
    # ecg_peaks_location = None
    # eda_peaks_location = None

    # emg_proced = None
    # ecg_proced = None
    # eda_proced = None

    # filter_emg.n = None #needs an object
    # filter_emg.y = None
    # filter_emg.yHat = None
    # filter_emg.e = None

    # filter_ecg.n = None #needs an object
    # filter_ecg.y = None
    # filter_ecg.yHat = None
    # filter_ecg.e = None

    # filter_eda.n = None #needs an object
    # filter_eda.y = None
    # filter_eda.yHat = None
    # filter_eda.e = None

    
    # if channel[0]:
    #     if channel[1]:
    #         if channel[2]:
    #             #print("All True")
    #             emg_raw, ecg_raw, eda_raw = raw_data
    #         else:
    #             #print("First and Second True, Third False")
    #             emg_raw, ecg_raw = raw_data
    #     else:
    #         if channel[2]:
    #             #print("First True, Second False, Third True")
    #             emg_raw, eda_raw = raw_data
    #         else:
    #             #print("First True, Second and Third False")
    #             emg_raw = raw_data
    # else:
    #     if channel[1]:
    #         if channel[2]:
    #             #print("First False, Second and Third True")
    #             ecg_raw, eda_raw = raw_data
    #         else:
    #             #print("First False, Second True, Third False")
    #             ecg_raw = raw_data
    #     else:
    #         if channel[2]:
    #             #print("First, Second and Third False")
    #             print("Error in baseline recording \n")
    #             return
    #         else:
    #             #print("All False")
    #             print("Error in baseline recording \n")
    #             return

    
    #______________________________Reinterpreting the signals from ADC to intended Precision______________________________
    if channel[2]:
        eda_proced = proc.convert_raw_eda(eda_raw)

    if channel[1]:    
        ecg_proced = proc.convert_raw_ecg(ecg_raw)

    if channel[0]:
        emg_proced = proc.convert_raw_emg(emg_raw)
    

    #_______________________________Running data through DWT class_________________________________________________________
    dwt = proc.DiscreteWaveletTransform(wavelet='db4', level=7)

    if channel[2]:
        eda_proced =  dwt.clean_wave_data(eda_proced)
    
    if channel[1]:
        ecg_proced =  dwt.clean_wave_data(ecg_proced)

    if channel[0]:
        emg_proced =  dwt.clean_wave_data(emg_proced)

    #_______________________________Peak detection on data_________________________________________________________________

    #____EDA____
    if channel[2]:
        eda_threshold = proc.simple_threshold(eda_proced)
        eda_peaks_location = proc.peakLocation(eda_proced,eda_threshold)

        eda_bpm_array = proc.calculate_peak_rate_over_interval(eda_peaks_location, interval=5)

    #____ECG____
    if channel[1]:
        ecg_threshold = proc.simple_threshold(ecg_proced)
        ecg_peaks_location = proc.peakLocation(ecg_proced,ecg_threshold)


        ecg_bpm_array = proc.calculate_peak_rate_over_interval(ecg_peaks_location, interval=5)

        ecg_bpm = proc.calculate_peak_rate(ecg_peaks_location)
        global ecg_bpm_base
        ecg_bpm_base = ecg_bpm

    #____EMG____
    if channel[0]:
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
    ax1_eda.set_title('Baseline EDA')
    #ax1_eda.set_xlabel('Time(mS)')
    ax1_eda.set_ylabel('Conductivity(us)')

    ax2_ecg.plot(ecg_proced, label='ECG Signal')
    ax2_ecg.legend()
    ax2_ecg.scatter([x[0] for x in ecg_peaks_location], [x[1] for x in ecg_peaks_location], color='red', label='Peaks')
    ax2_ecg.set_title('Basline ECG')
    #ax2_ecg.set_xlabel('Time(mS)')
    ax2_ecg.set_ylabel('Heartrate Amplitude(mV)')

    ax3_emg.plot(emg_proced, label='EMG Signal')
    ax3_emg.legend()
    ax3_emg.scatter([x[0] for x in emg_peaks_location], [x[1] for x in emg_peaks_location], color='red', label='Peaks')
    ax3_emg.set_title('Baseline EMG')
    ax3_emg.set_xlabel('Time(mS)')
    ax3_emg.set_ylabel('Muscle Amplitude(mV)')
    

    plt.tight_layout()
    plt.grid(True)
    plt.show()
    graphs_list.append(graph1)
    #_______________________________Error Stats_____________________________________________________________________
    section_size = 2000

    #____EDA____
    if channel[2]:
        eda_stats_obj = proc.error_stats(eda_proced)
        eda_stats = eda_stats_obj.calculate_stats()
        eda_stats_sectioned_result = proc.error_stats.calculate_sectioned_stats(eda_proced, section_size)
        graph2 = proc.error_stats.plot_sectioned_stats(eda_stats_sectioned_result,"EDA Stats Plot")
        graphs_list.append(graph2)

    #____ECG____
    if channel[1]:
        ecg_stats_obj = proc.error_stats(ecg_proced)
        ecg_stats = ecg_stats_obj.calculate_stats()
        ecg_stats_sectioned_result = proc.error_stats.calculate_sectioned_stats(ecg_proced, section_size)
        graph3 = proc.error_stats.plot_sectioned_stats(ecg_stats_sectioned_result,"ECG Stats Plot")
        graphs_list.append(graph3)

    #____EMG____
    if channel[0]:
        emg_stats_obj = proc.error_stats(emg_proced)
        emg_stats = emg_stats_obj.calculate_stats()

        emg_stats_sectioned_result = proc.error_stats.calculate_sectioned_stats(emg_proced, section_size)
        graph4 = proc.error_stats.plot_sectioned_stats(emg_stats_sectioned_result,"EMG Stats Plot")
        graphs_list.append(graph4)

    #____Graphs____


    #_______________________________Least Means Squared Adaptive Filtering__________________________________________
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
    ax3.plot(filter_emg.n, filter_emg.y,'g',label='Original EMG')
    ax3.plot(filter_emg.n, filter_emg.yHat,'b', label='Estimated EMG')
    ax3.plot(filter_emg.n, filter_emg.e, 'r',label='Estimation Error')
    ax3.set_title('EMG Estimation')
    ax3.set_xlabel('Time(mS)')
    ax3.set_ylabel('Muscle Amplitude(mV)')
    ax3.legend()

    plt.tight_layout()
    plt.show()
    graphs_list.append(graph4)
    
    if channel[2]:
        eda_stats_baseline = eda_stats

    if channel[1]:   
        ecg_stats_baseline = ecg_stats
    
    if channel[0]:
        emg_stats_baseline = emg_stats
    
    return graphs_list




def analyze_result(channel,samplingRate):
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
