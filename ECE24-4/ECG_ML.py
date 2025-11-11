# ECG_ML.py
#   • Holds a K-Nearest Neighbor ML model
#   • End-to-end Machine Learning module to analyze, quantify, and classify ECG data
#   • Takes an ECG raw signal, transforms it into quantifiable biomarkers and compares them across different measurements
#   • Then uses a trained model to draw a conclusion about the observed change
#_______________________________________________________________________________#

#imports
import numpy as np
import matplotli
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import neurokit2 as nk
import joblib
import shap
#_______________________________________________________________________________#

# ------------------------------------------------ECG PREPROCESSING FUNCS-----------------------------------------------------------
def calculate_bpm_hrv(signals, r_info, sampling_rate=100):
    """
    Args:
        signals (array of values?): data values brought in by sensors
        r_info (array): information about the r-wave in ecg signal
        sampling_rate: samples acquired per second
        
    Returns:
        bpm: beats per minute
        mean_rr: average rr ratio
        r_peaks: the peaks that are within the r information
        hrv: heart rate variability
        hr_sd: heart rate standard deviation
    
    calculates common heart rate variability and heart rate metrics from a list of R-peak locations obtained from an ECG signal

    """
    r_peaks = r_info['ECG_R_Peaks']

    rr_intervals = np.diff(r_peaks) / sampling_rate

    if len(rr_intervals) == 0:
        return None, r_peaks

    hrv = np.std(rr_intervals)

    bpm_values = 60 / rr_intervals
    bpm = np.mean(bpm_values)
    hr_sd = np.std(bpm_values)
    mean_rr = np.mean(rr_intervals)

    return bpm, mean_rr, r_peaks, hrv, hr_sd


def calculate_qrs_duration(signals, r_info, sampling_rate=100):
    """
    args:
        signals (array): ecg signal
        r_info (array): R wave on signal
        sampling_rate (int): rate of samples (default 100)
        
    returns:
        mean of QRS duration for the entire signal as long as it isn’t 0
        
    Calculates the QRS Duration in an ECG
        time interal between the onset of the Q wave and the end of the S wave
        QRS: series of waves on the ECG that represent the electrical depolarization (contraction) of the ventricles
    
    """
    q_peaks = np.where(signals['ECG_Q_Peaks'] == 1)[0]  # indices of Q-peaks
    s_peaks = np.where(signals['ECG_S_Peaks'] == 1)[0]  # indices of S-peaks

    qrs_durations = []
    for r in r_info['ECG_R_Peaks']:
        # find the closest Q-peak before the R-peak
        q_candidates = q_peaks[q_peaks < r]
        if len(q_candidates) > 0:
            q_peak = q_candidates[-1]  # last Q-peak before the R-peak
        else:
            q_peak = None

        # find the closest S-peak after the R-peak
        s_candidates = s_peaks[s_peaks > r]
        if len(s_candidates) > 0:
            s_peak = s_candidates[0]  # first S-peak after the R-peak
        else:
            s_peak = None

        # calculate QRS duration if both Q and S peaks are found
        if q_peak is not None and s_peak is not None:
            qrs_duration = (s_peak - q_peak) / sampling_rate * 1000  # (milliseconds)
            qrs_durations.append(qrs_duration)
    
    return np.mean(qrs_durations) if qrs_durations else 0


def calculate_r_wave_amplitude(ecg_signal, r_peaks):
    """
    args:
        ecg_signal (array): array containing the ecg signal
        r_peaks (array): where the r-peaks are in the signal based upon the r-info
        
    return: mean amplitude of the r-peaks if there are any
    
    calculates the mean amplitude of the R-waves in the ECG signal

    """
    return np.mean([ecg_signal[r] for r in r_peaks]) if r_peaks.any() else 0


def calculate_rmssd(r_peaks, sampling_rate=100):
    """
    args:
        signals (array): processed signal information
        sampling_rate: the rate, samples per second, at which the ECG signal was acquired (default is 100 Hz)
        
    returns:
        returns the root mean square of successive differences
        
    calculates the Root Mean Square of the Successive Differences of the RR intervals

    """
    rr_intervals = np.diff(r_peaks) / sampling_rate
    return np.sqrt(np.mean(np.square(np.diff(rr_intervals)))) if len(rr_intervals) > 1 else 0


def calculate_pr_mean(signals, r_info, sampling_rate=100):
    """
    args:
        signals (array): processed signal information
        r_info (array): R-wave information
        sampling_rate: the rate at which samples were taken (default is 100)
    
    returns:
        pr_mean: PR interval (time between onset of the P wave adn onset of the QRS complex)
    
    calculates the mean and standard deviation of the PR interval 

    """
    r_peaks = r_info['ECG_R_Peaks']
    p_peaks = np.where(signals['ECG_P_Peaks'] == 1)[0]  # indices of P-peaks

    pr_intervals = []
    for r in r_peaks:
        p_candidates = p_peaks[p_peaks < r]
        if len(p_candidates) > 0:
            p_peak = p_candidates[-1]  # get the last P-peak before the R-peak
            pr_intervals.append((r - p_peak) / sampling_rate)

    pr_mean = np.mean(pr_intervals) if len(pr_intervals) > 0 else 0
    pr_sd = np.std(pr_intervals) if len(pr_intervals) > 0 else 0
    
    return pr_mean, pr_sd, pr_intervals


def calculate_st_mean(signals, r_info, sampling_rate=100):
    """
    args:
        signals (array): processed signal information
        r_info (array): R-wave information
        sampling_rate: rate at which samples were taken (default is 100)
    
    returns:
        st_mean: mean of the ST interval
        st_sd: standard deviation of the ST interval
        st_intervals:  interval between S-peak and T-peak

    calculates the mean and standard deviation of the ST interval
        part of the ECG that represents time between the ventricular depolarization and repolarization

    """
    r_peaks = r_info['ECG_R_Peaks']
    s_peaks = np.where(signals['ECG_S_Peaks'] == 1)[0]  # indices of S-peaks
    t_peaks = np.where(signals['ECG_T_Peaks'] == 1)[0]  # indices of T-peaks

    st_intervals = []
    for r in r_peaks:
        # find S-peak (lowest point after R-peak within 80ms)
        s_peak = s_peaks[np.argmin(np.abs(s_peaks - r))]  # find closest S-peak
        # find T-peak (next peak after S-peak within 200ms)
        t_peak = t_peaks[np.argmin(np.abs(t_peaks - s_peak))]  # find closest T-peak

        if s_peak and t_peak:
            st_intervals.append((t_peak - s_peak) / sampling_rate)

    st_mean = np.mean(st_intervals) if len(st_intervals) > 0 else 0
    st_sd = np.std(st_intervals) if len(st_intervals) > 0 else 0
    return st_mean, st_sd, st_intervals


def calculate_nfd_mean(ecg_signal):
    """
    args:
        ecg_signal (array): ECG voltage signal
    
    returns:
        mean of nfd_values
    
    calculates the NFD (normalized first derivative) of the ECG signal

    """
    if len(ecg_signal) < 2:
        return 0 

    ecg_signal = np.array(ecg_signal, dtype=np.float64) 
    ecg_signal[ecg_signal == 0] = np.nan

    with np.errstate(divide='ignore', invalid='ignore'):
        nfd_values = np.abs(np.diff(ecg_signal) / ecg_signal[:-1]) 

    nfd_values = nfd_values[~np.isnan(nfd_values) & ~np.isinf(nfd_values)]

    return np.mean(nfd_values) if len(nfd_values) > 0 else 0


def calculate_nsd_mean(ecg_signal):
    """
    args:
        ecg_signal (array): ECG voltage signal
    
    returns:
        mean of the nsd_values
    
    calculates the NSD (normalized second derivative) of the ECG signal
    
    """
    if len(ecg_signal) < 3: 
        return 0  

    ecg_signal = np.array(ecg_signal, dtype=np.float64) 
    ecg_signal[ecg_signal == 0] = np.nan  

    with np.errstate(divide='ignore', invalid='ignore'): 
        nsd_values = np.abs(np.diff(ecg_signal, n=2) / ecg_signal[:-2])  

    nsd_values = nsd_values[~np.isnan(nsd_values) & ~np.isinf(nsd_values)]  

    return np.mean(nsd_values) if len(nsd_values) > 0 else 0


def calculate_change(old, new, percent=True):
    """
    args:
        old (float): old percentage
        new (float): new percentage
        percent (boolean): percent change (true) or absolute difference in percentages (false)

    returns:
        returns percentage change or absolute difference in percentages
        
    calculates the difference between an old value and a new value 
    default to returning the percentage change
    
    """
    if percent:
        return ((new - old) / abs(old)) * 100 if old != 0 else 0  
    else:
        return new - old


def get_ecg_features(ecg, sampling_rate=100):
    """
    args:
        ecg (array): ECG signal
        sampling_rate: rate of samples taken (default of 100)
    
    returns:
        dictionary containing extracted features from ecg signal such as BPM, HRV, HRSD, QRS, AMP, RMSSD, mean RR, mean PR, PR standard deviation, mean ST, mean NFD, mean NSD
    
    Main feature extraction using neurokit2 to identify peaks and segments
    then uses previous fucntiosn to compile 12 features into one library labeled “ecg”

    """
    signals, r_info = nk.ecg_process(ecg, sampling_rate=sampling_rate)

    bpm, mean_RR, r_peaks, hrv, hrsd = calculate_bpm_hrv(signals, r_info, sampling_rate)
    qrs = calculate_qrs_duration(signals, r_info, sampling_rate)
    amp = calculate_r_wave_amplitude(signals['ECG_Clean'], r_peaks)
    rmssd = calculate_rmssd(r_peaks)
    mean_PR, PRsd, _ = calculate_pr_mean(signals, r_info, sampling_rate)
    mean_ST, STsd, _ = calculate_st_mean(signals, r_info, sampling_rate)
    mean_nfd = calculate_nfd_mean(ecg)
    mean_nsd = calculate_nsd_mean(ecg)

    if bpm is None or r_peaks is None:
        raise ValueError("Unable to calculate ECG features, most likely due to too few R peaks. Try either a higher sampling rate or longer duration.")

    ecg_features = { # Extracted ecg features in order
        "bpm": bpm,
        "hrv": hrv,
        "hrsd": hrsd,
        "qrs": qrs,
        "amp": amp,
        "rmssd": rmssd,
        "mean_RR": mean_RR,
        "mean_PR": mean_PR,
        "PRsd": PRsd,
        "mean_ST": mean_ST,
        "mean_nfd": mean_nfd,
        "mean_nsd": mean_nsd
    }

    return ecg_features

def get_feature_percent_diffs(baseline, test):
    """
    args:
        baseline (ecg features): dictionary of ecg features from baseline signal
        test (ecg features): dictionary of ecg features from test signal

    returns:
        dictionary containing percentage differences between baseline and test ecg signals 
        such as PM, HRV, HRSD, QRS, AMP, RMSSD, mean RR, mean PR, PR standard deviation, mean ST, mean NFD, mean NSD
    
    calculates the percentage difference for each feature between the baseline set of features and the test set of features

    """
    percent_diffs =  {
        "bpm": calculate_change(baseline['bpm'], test['bpm']),
        "hrv": calculate_change(baseline['hrv'], test['hrv']),
        "hrsd": calculate_change(baseline['hrsd'], test['hrsd']),
        "qrs": calculate_change(baseline['qrs'], test['qrs']),
        "amp": calculate_change(baseline['amp'], test['amp']),
        "rmssd": calculate_change(baseline['rmssd'], test['rmssd']),
        "mean_RR": calculate_change(baseline['mean_RR'], test['mean_RR']),
        "mean_PR": calculate_change(baseline['mean_PR'], test['mean_PR']),
        "PRsd": calculate_change(baseline['PRsd'], test['PRsd']),
        "mean_ST": calculate_change(baseline['mean_ST'], test['mean_ST']),
        "mean_nfd": calculate_change(baseline['mean_nfd'], test['mean_nfd']),
        "mean_nsd": calculate_change(baseline['mean_nsd'], test['mean_nsd'])
    }

    return percent_diffs


def ecg_classification_knn(diff_features):
    """
    args:
        diff_features: dictionary of feature differences (expected to be percentage differences)
    
    returns:
        dictionary containing model classification, classification confidence, and the SHAP plot figure
    
    performs the final classification using the K-Nearest Neighbors (KNN)
        KNN - supervised learning algorithm used for both classification and regression tasks
        loads trained model and scaler
        scales the input features
        makes a prediction
        calculates the probability/confidence and generates a SHAP waterfall plot for model interpretability

    """
    knn_model = joblib.load("ML_files/knn_model.joblib") # Load in the knn model (94.5% f1 accuracy)
    scaler = joblib.load("ML_files/scaler_1.joblib") # Load in scaler
    background = np.load("ML_files/shap_background.npy", allow_pickle=True) # Load in background for shap graph

    if isinstance(background, np.ndarray) and background.ndim == 0:
        background = background.item()

    FEATURE_ORDER = [
        "bpm",
        "hrv",
        "hrsd",
        "qrs",
        "amp",
        "rmssd",
        "mean_RR",
        "mean_PR",
        "PRsd",
        "mean_ST",
        "mean_nfd",
        "mean_nsd"
    ]

    feature_array = np.array([diff_features[key] for key in FEATURE_ORDER])
    if (len(feature_array) == 0 or np.isnan(feature_array).any() or np.isinf(feature_array).any()):
        raise ValueError("One or more features are missing or invalid (most likely due to poor ECG signal).")
    
    
    feature_array_scaled = scaler.transform(feature_array.reshape(1, -1)) # Scale new features

    model_prediction = knn_model.predict(feature_array_scaled)[0] # Get model prediction

    proba = knn_model.predict_proba(feature_array_scaled)[0,1] # get the probability / confidence


    distances, neighbor_indexes = knn_model.kneighbors(feature_array_scaled) # Get nearest neighbors (for testing)
    neighbor_votes = knn_model._y[neighbor_indexes[0]] # Get neighbors votes (for testing)

    print(f'ML Prediction: {model_prediction}')
    print(f'Reaction Strength: {proba}')
    print(f'Neighbor Votes: {neighbor_votes.tolist()}')

    # Create the shap explainer
    explainer = shap.KernelExplainer(knn_model.predict_proba, background)
    shap_values = explainer.shap_values(feature_array_scaled)

    print("shap_values type:", type(shap_values))
    if isinstance(shap_values, (list, tuple)):
        print("list length:", len(shap_values))
        for i, arr in enumerate(shap_values):
            print(f" element {i} shape:", np.array(arr).shape)
    elif isinstance(shap_values, np.ndarray):
        print("array shape:", shap_values.shape)
    else:
        print("unexpected structure:", shap_values)


    sv_class1 = shap_values[0, :, 1]

    sample = feature_array_scaled[0] 
    exp = shap.Explanation(
        values = sv_class1,              
        base_values = explainer.expected_value[1],  
        data = sample,                 
        feature_names = FEATURE_ORDER           
    )
    
    matplotlib.use("Agg", force=True)

    plt.figure(figsize=(2,2))

    ax = shap.plots.waterfall(exp, max_display=12, show=False)

    fig = ax.figure

    plt.tight_layout() 
    fig.savefig("shap_waterfall.png", dpi=100, bbox_inches="tight")

    plt.close(fig)

    return {'classification': model_prediction, 
            'confidence': proba, 
            'fig': fig}

    
