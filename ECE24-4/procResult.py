# procResult2.py
#   • analyzes signals by passing values from baseline and test 
#   • uses ECG_ML.py to compute results
#_______________________________________________________________________________#

#imports
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import procFuncs as proc
import saveFuncs as sv
import hearingTest as sound # Kyle's code
#_______________________________________________________________________________#

from ecgML import *

# Dictionary of the previous team's stats results
analysis_results = {
    'ecg' : {
        'baseline' : None,
        'test' : None,
        'diff' : None,
        'flags' : None,
        'filter': None
    },
    'emg' : {
        'baseline' : None,
        'test' : None,
        'diff' : None,
        'flags' : None,
        'filter': None
    },
    'eda' : {
        'baseline' : None,
        'test' : None,
        'diff' : None,
        'flags' : None,
        'filter': None
    }
}

# Dictionary of all of the previous teams stat and lms graphs
graphs = {
    'Baseline Stats' : [],
    'Test Stats' : [],
    'LMS Adaptive Filtering' : []
}

# Dictionary of the ml predictions (build to be expended with future ml models)
ml_predictions = {
    'ecg': {}
}

# Dictionary of the ml feature data 
ml_data = {
    'ecg': {
        'baseline_data': {},
        'test_data': {},
        'percent_difference': {},
    }
}

# Dictionary of all of the signal graphs 
ml_graphs = {
    'ecg' : {
        'baseline' : None,
        'test' : None
    },
    'emg' : {
        'baseline' : None,
        'test' : None
    },
    'eda' : {
        'baseline' : None,
        'test' : None
    }
}




def analyze_baseline(channels, samplingRate, controller):
    """
    args:
        channels (array of booleans): which biosignal channels are enabled for processing 
        samplingRate (int): rate at which signals were sampled
        controller (object): used to manage and switch between different application frames
    
    loads the raw data from the baseline_sequence.txt to perform initial processing
        cleans the EDA and EMG data using Discrete Wavelet Transform
        Gets ECG features from ECG_ML.py
        LMS (Least Mean Square) adaptive filter is applied and a plot for the baseline data is created and stored in graphs 

    """

    global analysis_results
    global ml_data
    global ml_graphs
    global graphs
    for category in graphs:
        graphs[category] = []
    
    try:
        # Load baseline data
        emg_raw, ecg_raw, eda_raw, error = proc.import_matrix_from_txt('baseline_sequence.txt')
        if error:
            raise ValueError("Error loading baseline data")
        
        # Process EDA if enabled
        if channels[2]:
            eda_proced = proc.DiscreteWaveletTransform(wavelet='db4', level=7).clean_wave_data(eda_raw)

            ml_graphs['eda']['baseline'] = plot_eda(eda_raw, "Baseline EDA Signal", "orchid", 
                                            sampling_rate=samplingRate, neurokit_graph=False)
            
            analysis_results['eda']['baseline'] = proc.error_stats(eda_proced).calculate_stats()
            graphs['Baseline Stats'].append(create_stats_plot(eda_proced, "EDA Baseline Stats"))
            
            # Store filter for LMS
            analysis_results['eda']['filter'] = apply_lms_filter(eda_proced)
        
        # Process ECG if enabled
        if channels[1]:
            ecg_proced = ecg_raw

            ml_data['ecg']['baseline_data'] = get_ecg_features(ecg_raw, sampling_rate=samplingRate)
            
            ml_graphs['ecg']['baseline'] = plot_ecg(ecg_raw, "Baseline ECG Signal", "blueviolet", 
                                            sampling_rate=samplingRate, neurokit_graph=False)
            
            analysis_results['ecg']['baseline'] = proc.error_stats(ecg_proced).calculate_stats()

            graphs['Baseline Stats'].append(create_stats_plot(ecg_proced, "ECG Baseline Stats"))
            
            analysis_results['ecg']['filter'] = apply_lms_filter(ecg_proced)
        
        # Process EMG if enabled
        if channels[0]:
            emg_proced =  proc.DiscreteWaveletTransform(wavelet='db4', level=7).clean_wave_data(emg_raw)

            ml_graphs['emg']['baseline'] = plot_emg(emg_raw, "Baseline EMG Signal", "orange", 
                                            sampling_rate=samplingRate, neurokit_graph=False)
            
            analysis_results['emg']['baseline'] = proc.error_stats(emg_proced).calculate_stats()

            graphs['Baseline Stats'].append(create_stats_plot(emg_proced, "EMG Baseline Stats"))
            
            analysis_results['emg']['filter'] = apply_lms_filter(emg_proced)
            
        # Add LMS filter plot if any channels are enabled
        if any(channels):
            graphs['LMS Adaptive Filtering'].append(
                create_lms_plot(
                    "Baseline LMS Filter",
                    analysis_results['eda']['filter'] if channels[2] else None,
                    analysis_results['ecg']['filter'] if channels[1] else None,
                    analysis_results['emg']['filter'] if channels[0] else None
                )
            )
            
    except Exception as e:
        print(f"Error in baseline analysis: {str(e)}")
        raise  

def analyze_result(channels, samplingRate, controller):
    """
    args:
        channels (array of booleans): which biosignal channels are enabled for processing 
        samplingRate (int): rate at which signals were sampled
        controller (object): used to manage and switch between different application frames
    
    loads in the raw data from the test_sequence.txt to perform processing (same as analyze_baseline, but on the test data now)
        Data from EDA and EMG are cleaned, ECG is left alone
        test statistics are calculated and stored as graphs
        percentage difference from baseline results are taken
        Diagnostic flags are assigned based on statistical differences from the baseline
        KNN classification is run specifically on the ECG dataset

    """

    global analysis_results
    global graphs
    global ml_data
    global ml_graphs
    global ml_predictions
    
    try:
        # Load test data
        emg_raw, ecg_raw, eda_raw, error = proc.import_matrix_from_txt('test_sequence.txt')
        if error:
            raise ValueError("Error loading test data")
        
        # Process EDA if enabled
        if channels[2]:
            eda_proced = proc.DiscreteWaveletTransform(wavelet='db4', level=7).clean_wave_data(eda_raw)

            ml_graphs['eda']['test'] = plot_eda(eda_raw, "Test EDA Signal", "deeppink", 
                                            sampling_rate=samplingRate, neurokit_graph=False)
            
            # Add to Test Stats
            test_stats = proc.error_stats(eda_proced).calculate_stats()
            analysis_results['eda']['test'] = test_stats
            analysis_results['eda']['diff'] = proc.error_stats.calculate_percent_difference(analysis_results['eda']['baseline'], analysis_results['eda']['test'])
            analysis_results['eda']['flags'] = proc.error_stats.assign_flags(analysis_results['eda']['diff'])
            graphs['Test Stats'].append(create_stats_plot(eda_proced, "EDA Test Stats"))
            
            # Store filter for LMS
            analysis_results['eda']['test_filter'] = apply_lms_filter(eda_proced)

        # Process ECG if enabled
        if channels[1]:
            ecg_proced = ecg_raw
            
            ml_data['ecg']['test_data'] = get_ecg_features(ecg_raw, sampling_rate=samplingRate)
            ml_data['ecg']['percent_difference'] = get_feature_percent_diffs(ml_data['ecg']['baseline_data'], ml_data['ecg']['test_data'])
            ml_graphs['ecg']['test'] = plot_ecg(ecg_raw, "Test ECG Signal", "mediumblue", 
                                            sampling_rate=samplingRate, neurokit_graph=False)
            
            test_stats = proc.error_stats(ecg_proced).calculate_stats()

            analysis_results['ecg']['test'] = test_stats
            analysis_results['ecg']['diff'] = proc.error_stats.calculate_percent_difference(analysis_results['ecg']['baseline'], analysis_results['ecg']['test'])
            analysis_results['ecg']['flags'] = proc.error_stats.assign_flags(analysis_results['ecg']['diff'])

            graphs['Test Stats'].append(create_stats_plot(ecg_proced, "ECG Test Stats"))
            
            analysis_results['ecg']['test_filter'] = apply_lms_filter(ecg_proced)

            ml_predictions['ecg'] = ecg_classification_knn(ml_data['ecg']['percent_difference'])

        # Process EMG if enabled
        if channels[0]:
            emg_proced =  proc.DiscreteWaveletTransform(wavelet='db4', level=7).clean_wave_data(emg_raw)
            
            ml_graphs['emg']['test'] = plot_emg(emg_raw, "Test EMG Signal", "salmon", 
                                            sampling_rate=samplingRate, neurokit_graph=False)
            
            test_stats = proc.error_stats(emg_proced).calculate_stats()
            analysis_results['emg']['test'] = test_stats
            analysis_results['emg']['diff'] = proc.error_stats.calculate_percent_difference(analysis_results['emg']['baseline'], analysis_results['emg']['test'])
            analysis_results['emg']['flags'] = proc.error_stats.assign_flags(analysis_results['emg']['diff'])

            graphs['Test Stats'].append(create_stats_plot(emg_proced, "EMG Test Stats"))
            
            analysis_results['emg']['test_filter'] = apply_lms_filter(emg_proced)
            
        # Add LMS filter plot if any channels are enabled
        if any(channels):
            graphs['LMS Adaptive Filtering'].append(
                create_lms_plot(
                    "Test LMS Filter",
                    analysis_results['eda']['test_filter'] if channels[2] else None,
                    analysis_results['ecg']['test_filter'] if channels[1] else None,
                    analysis_results['emg']['test_filter'] if channels[0] else None
                )
            )
    

    except Exception as e:
        print(f"Error in test analysis: {str(e)}")
        raise   


def plot_ecg(ecg, title, color, sampling_rate=100, neurokit_graph=False):
    """
    args:
        ecg (array): signal data
        title (string): plot name
        color (string): color of plot
        sample_rate (int): rate at which sample was taken (default 100)
        neurokit_graph (boolean): if the function should use nk.ecg_process to clean the signal
    
    returns:
        figure of the ecg plot
    
    plots the ECG sigal against time
    plots the cleaned ECG signal and uses scatter points to highlight R-peaks
        if fails, prints back raw input signal

    """
    try:
        signals, r_info = nk.ecg_process(ecg, sampling_rate)

        clean_ecg = signals['ECG_Clean']
        
        r_peaks = r_info['ECG_R_Peaks']
        # p_peaks = np.where(signals['ECG_P_Peaks'] == 1)[0]
        # q_peaks = np.where(signals['ECG_Q_Peaks'] == 1)[0]
        # s_peaks = np.where(signals['ECG_S_Peaks'] == 1)[0]
        # t_peaks = np.where(signals['ECG_T_Peaks'] == 1)[0]
        
        time_axis = np.linspace(0, len(clean_ecg) / sampling_rate, len(clean_ecg))
        
        fig = plt.Figure(figsize=(13, 2))
        ax = fig.add_subplot(111)
        ax.plot(time_axis, clean_ecg, color=color, label="ECG Signal")
        ax.scatter(time_axis[r_peaks], clean_ecg[r_peaks], color="orange", label="R-Peaks", zorder=5)
        
        ax.set_title(title)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude (V)')
        ax.legend()
        ax.grid(True)

        return fig
    except Exception as e:
        print(f"Couldn't plot ECG: {e}")
        time_axis = np.linspace(0, len(ecg) / sampling_rate, len(ecg))
    
        fig = plt.Figure(figsize=(13, 2))
        ax = fig.add_subplot(111)
        ax.plot(time_axis, ecg, color=color, label="ECG Signal")
        
        ax.set_title(title)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude (V)')
        ax.legend()
        ax.grid(True)

        return fig


def plot_eda(eda_signal, title, color, sampling_rate=100, neurokit_graph=False):
    """
    args:
        eda (array): signal data
        title (string): plot name
        color (string): color of plot
        sample_rate (int): rate at which sample was taken (default 100)
        neurokit_graph (boolean): if the function should use nk.ecg_process to clean the signal (always false unless ECG)
    
    returns:
        figure of the eda plot
    
    plots the EDA sigal against time

    """
    time_axis = np.linspace(0, len(eda_signal) / sampling_rate, len(eda_signal))
    
    fig = plt.Figure(figsize=(13, 2))
    ax = fig.add_subplot(111)
    ax.plot(time_axis, eda_signal, color=color, label="EDA Signal")
    
    ax.set_title(title)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Amplitude (V)')
    ax.legend()
    ax.grid(True)

    return fig

def plot_emg(emg_signal, title, color, sampling_rate=100, neurokit_graph=False):
    """
    args:
        emg (array): signal data
        title (string): plot name
        color (string): color of plot
        sample_rate (int): rate at which sample was taken (default 100)
        neurokit_graph (boolean): if the function should use nk.ecg_process to clean the signal (always false unless ECG)
    
    returns:
        figure of the emg plot
    
    plots the EMG sigal against time

    """
    time_axis = np.linspace(0, len(emg_signal) / sampling_rate, len(emg_signal))
    
    fig = plt.Figure(figsize=(13, 2))
    ax = fig.add_subplot(111)
    ax.plot(time_axis, emg_signal, color=color, label="EMG Signal")
    
    ax.set_title(title)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Amplitude (V)')
    ax.legend()
    ax.grid(True)

    return fig


def create_stats_plot(signal, title, section_size=2000):
    """
    args:
        signal (array): signal data
        title (string): plot name
        section_size (int): size of the section (default 2000)
    
    returns:
        Matplotlib figure plot of the section
    
    Calculates statistics over defined sections of a signal and plots the statistics 

    """
    stats_result = proc.error_stats.calculate_sectioned_stats(signal, section_size)
    return proc.error_stats.plot_sectioned_stats(stats_result, title)

def create_lms_plot(title, eda_filter=None, ecg_filter=None, emg_filter=None):
    """
    args: 
        title (string): name of plot
        eda_filter (object): LMS figure object provided (default none)
        ecg_filter (object): LMS figure object provided (default none)
        emg_filter (object): LMS figure object provided (default none)
    returns:
        Matplotlib figure plot 
    
    for each provided filter (ECG, EDA, EMG) it creates a subplot showing the original signal, the estimated signal, and the estimation error

    """
    num_signals = sum(f is not None for f in [eda_filter, ecg_filter, emg_filter])
    fig = plt.Figure(figsize=(7, (3 * num_signals)))
    fig.suptitle(title, fontsize=14)
    
    plot_index = 1
    if eda_filter:
        # ax1 = fig.add_subplot(311)
        ax1 = fig.add_subplot(num_signals, 1, plot_index)
        ax1.plot(eda_filter.n, eda_filter.y, 'g', label='Original EDA')
        ax1.plot(eda_filter.n, eda_filter.yHat, 'b', label='Estimated EDA')
        ax1.plot(eda_filter.n, eda_filter.e, 'r', label='Estimation Error')
        ax1.set_title('EDA Estimation')
        ax1.set_ylabel('Conductivity (µS)')
        ax1.legend()

        plot_index += 1
    
    if ecg_filter:
        # ax2 = fig.add_subplot(312)
        ax2 = fig.add_subplot(num_signals, 1, plot_index)
        ax2.plot(ecg_filter.n, ecg_filter.y, 'g', label='Original ECG')
        ax2.plot(ecg_filter.n, ecg_filter.yHat, 'b', label='Estimated ECG')
        ax2.plot(ecg_filter.n, ecg_filter.e, 'r', label='Estimation Error')
        ax2.set_title('ECG Estimation')
        ax2.set_ylabel('Amplitude (V)')
        ax2.legend()

        plot_index += 1
    
    if emg_filter:
        # ax3 = fig.add_subplot(313)
        ax3 = fig.add_subplot(num_signals, 1, plot_index)
        ax3.plot(emg_filter.n, emg_filter.y, 'g', label='Original EMG')
        ax3.plot(emg_filter.n, emg_filter.yHat, 'b', label='Estimated EMG')
        ax3.plot(emg_filter.n, emg_filter.e, 'r', label='Estimation Error')
        ax3.set_title('EMG Estimation')
        ax3.set_xlabel('Time (ms)')
        ax3.set_ylabel('Amplitude (V)')
        ax3.legend()
    
    fig.tight_layout(pad=2.0)
    
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    return fig

def apply_lms_filter(signal):
    """
    args:
        signal (array): data signal
        
    return:
        lms_filter (object): object for plotting signal
    
    applies the LMS (Least Mean Squares) adaptive filter to a biosignal
        Instantiates the filter object, calls update method and calculates error 

    """
    lms_filter = proc.LMSAdaptiveFilter(signal)
    lms_filter.update()
    lms_filter.error()
    return lms_filter



# --------------------------------MAIN FUNCTION-----------------------------------------
def main(file_path, channels, samplingRate, controller):
    """
    args:
        file_path (string): name of file to save results
        channels (boolean list): enabling channels
        samplingRate (int): rate at which signal is sampled
        controller (object): GUI management object
    
    returns:
        returns true upon completion
        
    controls entire analysis pipeline
        calls baseline and test analysis
        handles errors
        saves graphs and stat results
        if ECG was selected (by controller), save ML results and display
        load results and graphs to different page
        tell user results have been saved and show results


    """
    global graphs
    global ml_data
    global analysis_results
    try:
        analyze_baseline(channels, samplingRate, controller)
        analyze_result(channels, samplingRate, controller)
    except Exception as e:
        controller.frames['ErrorPage'].set_error_message(f"Error occured during signal analysis. See error message below: \n {str(e)}")
        controller.show_frame("ErrorPage")
        raise

    # Save graphs and stats results
    sv.save_graphs_to_excel(file_path, graphs)
    sv.save_stats_results_to_excel(file_path, analysis_results)

    # If ECG was selected, save ML results and display them
    if channels[1]:
        sv.save_ml_graphs_to_excel(file_path, ml_graphs)
        sv.save_ml_results_to_excel(file_path, ml_predictions, ml_data)
        
        controller.frames["ResultsPage"].display_results(ml_predictions, ml_data)
        controller.frames["ShapPage"].display_results(ml_predictions)
    
    
    # Load results and graphs to different pages
    controller.frames["GraphPage"].load_graphs(ml_graphs)
    controller.frames["StatsResultsPage"].display_results(analysis_results)
    controller.frames["StatsResultsPage"].load_graphs(graphs)

    # Tell user that the results have been saved and show the results
    sound.tts("Results have been saved", 150)
    controller.show_frame("ResultsPage")


    return True
