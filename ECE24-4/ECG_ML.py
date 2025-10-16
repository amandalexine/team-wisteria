import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import neurokit2 as nk
import joblib
import shap

# ------------------------------------------------ECG PREPROCESSING FUNCS-----------------------------------------------------------
def calculate_bpm_hrv(signals, r_info, sampling_rate=100):
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
    return np.mean([ecg_signal[r] for r in r_peaks]) if r_peaks.any() else 0


def calculate_rmssd(r_peaks, sampling_rate=100):
    rr_intervals = np.diff(r_peaks) / sampling_rate
    return np.sqrt(np.mean(np.square(np.diff(rr_intervals)))) if len(rr_intervals) > 1 else 0


def calculate_pr_mean(signals, r_info, sampling_rate=100):
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
    if len(ecg_signal) < 2:
        return 0 

    ecg_signal = np.array(ecg_signal, dtype=np.float64) 
    ecg_signal[ecg_signal == 0] = np.nan

    with np.errstate(divide='ignore', invalid='ignore'):
        nfd_values = np.abs(np.diff(ecg_signal) / ecg_signal[:-1]) 

    nfd_values = nfd_values[~np.isnan(nfd_values) & ~np.isinf(nfd_values)]

    return np.mean(nfd_values) if len(nfd_values) > 0 else 0


def calculate_nsd_mean(ecg_signal):
    if len(ecg_signal) < 3: 
        return 0  

    ecg_signal = np.array(ecg_signal, dtype=np.float64) 
    ecg_signal[ecg_signal == 0] = np.nan  

    with np.errstate(divide='ignore', invalid='ignore'): 
        nsd_values = np.abs(np.diff(ecg_signal, n=2) / ecg_signal[:-2])  

    nsd_values = nsd_values[~np.isnan(nsd_values) & ~np.isinf(nsd_values)]  

    return np.mean(nsd_values) if len(nsd_values) > 0 else 0


def calculate_change(old, new, percent=True):
    if percent:
        return ((new - old) / abs(old)) * 100 if old != 0 else 0  
    else:
        return new - old


def get_ecg_features(ecg, sampling_rate=100):
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
    