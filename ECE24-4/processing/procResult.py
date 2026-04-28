# procResult.py
#   • processes baseline + test biosignals
#   • calls detect_anomalies() directly (no localhost server needed)
#   • computes stats, LMS filters, and plots
# _______________________________________________________________________________

import traceback

import numpy as np
import matplotlib.pyplot as plt

import procFuncs as proc
import saveFuncs as sv
import hearingTest as sound

from filtering.app.app_anomalies import load_model, detect_anomalies


# =============================================================================
# GLOBAL STATE
# =============================================================================

analysis_results = {
    'ecg': {'baseline': None, 'test': None, 'diff': None, 'flags': None, 'filter': None},
    'emg': {'baseline': None, 'test': None, 'diff': None, 'flags': None, 'filter': None},
    'eda': {'baseline': None, 'test': None, 'diff': None, 'flags': None, 'filter': None},
}

graphs = {
    'Baseline Stats': [],
    'Test Stats': [],
    'LMS Adaptive Filtering': [],
}

ml_predictions = {'ecg': {}}

ml_graphs = {
    'ecg': {'baseline': None, 'test': None},
    'emg': {'baseline': None, 'test': None},
    'eda': {'baseline': None, 'test': None},
}

ml_data = {
    'ecg': {
        'baseline_data': {},
        'test_data': {},
        'percent_difference': {},
    }
}

_model_cache = None


def _get_model():
    global _model_cache
    if _model_cache is None:
        _model_cache = load_model()
    return _model_cache


# =============================================================================
# HELPERS
# =============================================================================

def _run_ecg_ml(ecg_signal, fs):
    """
    Runs the autoencoder anomaly detection on a 1-D ECG numpy array.
    Returns the detect_anomalies result dict.
    """
    try:
        model, mean, scale, threshold, window_size = _get_model()
        signals = np.asarray(ecg_signal, dtype=np.float64).reshape(-1, 1)
        return detect_anomalies(model, signals, fs, mean, scale, threshold, window_size)

    except Exception as e:
        print(f"[ML ERROR] {e}")
        traceback.print_exc()

        n = len(ecg_signal)
        return {
            "errors": np.zeros((max(n - 100, 0), 1)),
            "anomalies": np.zeros(max(n - 100, 0), dtype=bool),
            "anomaly_indices": np.array([], dtype=np.int64),
            "reconstruction": np.zeros((n, 1)),
            "proc_signals": np.zeros((n, 1)),
        }


def _apply_lms_filter(signal):
    try:
        lms = proc.LMSAdaptiveFilter(signal)
        lms.update()
        lms.error()
        return lms

    except Exception as e:
        print(f"LMS filter failed: {e}")
        traceback.print_exc()
        return None


def _create_stats_plot(signal, title, section_size=2000):
    stats_result = proc.error_stats.calculate_sectioned_stats(signal, section_size)
    return proc.error_stats.plot_sectioned_stats(stats_result, title)


def _percent_difference_dict(baseline_stats, test_stats):
    """
    Safely computes percent differences between two stats dictionaries.
    """
    baseline_stats = baseline_stats or {}
    test_stats = test_stats or {}

    return {
        k: ((test_stats[k] - baseline_stats[k]) / (baseline_stats[k] + 1e-9)) * 100
        for k in baseline_stats
        if k in test_stats
    }


def _plot_ecg_ml(signal, anomaly_indices, fs, reconstruction=None, title="ECG ML Result"):
    """
    Local ECG plotting helper.

    This replaces filtering.app.app_anomalies.plot_anomalies because that function
    expects a 2-D array and indexes proc_signal[:, 0]. This helper accepts either
    1-D or 2-D arrays and always flattens safely for plotting.
    """
    signal = np.asarray(signal, dtype=np.float64).flatten()

    if signal.size == 0:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.set_title(title)
        ax.text(0.5, 0.5, "No ECG data available", ha="center", va="center")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Amplitude")
        fig.tight_layout()
        return fig

    t = np.arange(signal.size) / float(fs)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, signal, label="Processed ECG")

    if reconstruction is not None:
        reconstruction = np.asarray(reconstruction, dtype=np.float64).flatten()
        n = min(signal.size, reconstruction.size)
        if n > 0:
            ax.plot(t[:n], reconstruction[:n], label="Reconstruction", alpha=0.8)

    anomaly_indices = np.asarray(anomaly_indices, dtype=int).flatten()
    anomaly_indices = anomaly_indices[(anomaly_indices >= 0) & (anomaly_indices < signal.size)]

    if anomaly_indices.size > 0:
        ax.scatter(
            t[anomaly_indices],
            signal[anomaly_indices],
            label="Anomalies",
            s=20,
        )

    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.legend(loc="best")
    ax.grid(True)
    fig.tight_layout()
    return fig


# =============================================================================
# BASELINE ANALYSIS
# =============================================================================

def analyze_baseline(channels, samplingRate, controller):
    global analysis_results, ml_graphs, graphs

    for k in graphs:
        graphs[k] = []

    emg_raw, ecg_raw, eda_raw, error = proc.import_matrix_from_txt('baseline_sequence.txt')
    if error:
        raise ValueError("Error loading baseline_sequence.txt")

    # ── EDA ──────────────────────────────────────────────────────────────────
    if channels[2] and eda_raw is not None:
        eda_clean = proc.DiscreteWaveletTransform('db4', 7).clean_wave_data(eda_raw)

        analysis_results['eda']['baseline'] = proc.error_stats(eda_clean).calculate_stats()
        analysis_results['eda']['filter'] = _apply_lms_filter(eda_clean)

        graphs['Baseline Stats'].append(
            _create_stats_plot(eda_clean, "EDA Baseline Stats")
        )

    # ── ECG ──────────────────────────────────────────────────────────────────
    if channels[1] and ecg_raw is not None:
        ecg_arr = np.asarray(ecg_raw, dtype=np.float64)
        result = _run_ecg_ml(ecg_arr, samplingRate)

        print("DEBUG baseline proc_signals shape:", np.asarray(result["proc_signals"]).shape)
        print("DEBUG baseline proc_signals min/max:", np.min(result["proc_signals"]), np.max(result["proc_signals"]))
        print("DEBUG baseline reconstruction shape:", np.asarray(result["reconstruction"]).shape)
        print("DEBUG baseline anomaly count:", len(result["anomaly_indices"]))

        analysis_results['ecg']['baseline'] = {
            "mean_error": float(np.mean(result["errors"])),
            "num_anomalies": int(len(result["anomaly_indices"])),
        }

        analysis_results['ecg']['reconstruction'] = result["reconstruction"]
        analysis_results['ecg']['anomalies'] = result["anomaly_indices"]
        analysis_results['ecg']['filter'] = None

        ml_graphs['ecg']['baseline'] = _plot_ecg_ml(
            result["proc_signals"],
            result["anomaly_indices"],
            100,
            reconstruction=result["reconstruction"],
            title="ECG Baseline Anomaly Detection",
        )

    # ── EMG ──────────────────────────────────────────────────────────────────
    if channels[0] and emg_raw is not None:
        emg_clean = proc.DiscreteWaveletTransform('db4', 7).clean_wave_data(emg_raw)

        analysis_results['emg']['baseline'] = proc.error_stats(emg_clean).calculate_stats()
        analysis_results['emg']['filter'] = _apply_lms_filter(emg_clean)


# =============================================================================
# TEST ANALYSIS
# =============================================================================

def analyze_result(channels, samplingRate, controller):
    global analysis_results, ml_predictions, graphs, ml_graphs, ml_data

    emg_raw, ecg_raw, eda_raw, error = proc.import_matrix_from_txt('test_sequence.txt')
    if error:
        raise ValueError("Error loading test_sequence.txt")

    print("DEBUG: loaded test_sequence")

    # ── EDA ──────────────────────────────────────────────────────────────────
    if channels[2] and eda_raw is not None:
        eda_clean = proc.DiscreteWaveletTransform('db4', 7).clean_wave_data(eda_raw)

        analysis_results['eda']['test'] = proc.error_stats(eda_clean).calculate_stats()
        analysis_results['eda']['diff'] = proc.error_stats.calculate_percent_difference(
            analysis_results['eda']['baseline'],
            analysis_results['eda']['test'],
        )
        analysis_results['eda']['flags'] = proc.error_stats.assign_flags(
            analysis_results['eda']['diff']
        )
        analysis_results['eda']['test_filter'] = _apply_lms_filter(eda_clean)

        graphs['Test Stats'].append(
            _create_stats_plot(eda_clean, "EDA Test Stats")
        )

    print("DEBUG channels:", channels)
    print("DEBUG ecg_raw is None?", ecg_raw is None)

    # ── ECG ──────────────────────────────────────────────────────────────────
    if channels[1] and ecg_raw is not None:
        print("DEBUG: entering ECG test block")

        ecg_arr = np.asarray(ecg_raw, dtype=np.float64)
        result = _run_ecg_ml(ecg_arr, samplingRate)

        print("DEBUG: finished _run_ecg_ml")
        print("DEBUG test proc_signals shape:", np.asarray(result["proc_signals"]).shape)
        print("DEBUG test proc_signals min/max:", np.min(result["proc_signals"]), np.max(result["proc_signals"]))
        print("DEBUG test reconstruction shape:", np.asarray(result["reconstruction"]).shape)
        print("DEBUG test anomaly count:", len(result["anomaly_indices"]))

        analysis_results['ecg']['test'] = {
            "mean_error": float(np.mean(result["errors"])),
            "num_anomalies": int(len(result["anomaly_indices"])),
        }

        baseline_stats = analysis_results['ecg']['baseline'] or {}
        test_stats = analysis_results['ecg']['test'] or {}

        analysis_results['ecg']['diff'] = _percent_difference_dict(
            baseline_stats,
            test_stats,
        )

        # analysis_results['ecg']['flags'] = result["anomaly_indices"].tolist()

      
        print("DEBUG baseline:", analysis_results['ecg']['baseline'])

        base_anom = baseline_stats.get("num_anomalies", 0)
        test_anom = int(len(result["anomaly_indices"]))
        anomaly_increase = test_anom - base_anom

        analysis_results['ecg']['flags'] = {
            "mean_error": "N/A",
            "num_anomalies": "Abnormal" if test_anom > base_anom else "Normal",
        }

        print("DEBUG result keys:", result.keys())

        ml_predictions['ecg'] = {
            "classification": 1 if anomaly_increase > 5 else 0,
            "confidence": min(0.5 + anomaly_increase * 0.05, 0.99),
            "anomaly_count": test_anom,
            "fig": None,
        }

        ml_graphs['ecg']['test'] = _plot_ecg_ml(
            result["proc_signals"],
            result["anomaly_indices"],
            100,
            reconstruction=result["reconstruction"],
            title="ECG Test Anomaly Detection",
        )

        print("DEBUG: finished local ECG plot")

        ml_predictions['ecg']['fig'] = ml_graphs['ecg']['test']

        ml_data['ecg']['baseline_data'] = baseline_stats
        ml_data['ecg']['test_data'] = test_stats
        ml_data['ecg']['percent_difference'] = analysis_results['ecg']['diff']

    # ── EMG ──────────────────────────────────────────────────────────────────
    if channels[0] and emg_raw is not None:
        emg_clean = proc.DiscreteWaveletTransform('db4', 7).clean_wave_data(emg_raw)

        analysis_results['emg']['test'] = proc.error_stats(emg_clean).calculate_stats()
        analysis_results['emg']['diff'] = proc.error_stats.calculate_percent_difference(
            analysis_results['emg']['baseline'],
            analysis_results['emg']['test'],
        )
        analysis_results['emg']['flags'] = proc.error_stats.assign_flags(
            analysis_results['emg']['diff']
        )
        analysis_results['emg']['test_filter'] = _apply_lms_filter(emg_clean)

        graphs['Test Stats'].append(
            _create_stats_plot(emg_clean, "EMG Test Stats")
        )


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def main(file_path, channels, samplingRate, controller):
    try:
        print("DEBUG: starting baseline")
        analyze_baseline(channels, samplingRate, controller)

        print("DEBUG: starting test")
        analyze_result(channels, samplingRate, controller)

        print("DEBUG: finished analyze_result")

        print("DEBUG: saving graphs")
        sv.save_graphs_to_excel(file_path, graphs)

        print("DEBUG: saving stats")
        sv.save_stats_results_to_excel(file_path, analysis_results)

        if channels[1]:
            print("DEBUG: saving ML")
            sv.save_ml_results_to_excel(file_path, ml_predictions, ml_data)

            print("DEBUG: saving ML graphs")
            sv.save_ml_graphs_to_excel(file_path, ml_graphs)

            print("DEBUG: scheduling ResultsPage display")
            controller.after(
                0,
                lambda: controller.frames["ResultsPage"].display_results(
                    ml_predictions,
                    ml_data,
                ),
            )

        print("DEBUG: scheduling StatsResultsPage display")
        controller.after(
            0,
            lambda: (
                controller.frames["StatsResultsPage"].display_results(analysis_results),
                controller.frames["StatsResultsPage"].load_graphs(graphs),
            ),
        )

        # Temporarily disabled because pyttsx3/espeak was throwing:
        # ReferenceError: weakly-referenced object no longer exists
        # sound.tts("Results have been saved", 150)

        print("DEBUG: scheduling page switch")
        controller.after(0, lambda: controller.show_frame("ResultsPage"))
        controller.after(0, lambda: controller.frames["ShapPage"].display_results(ml_predictions))
        controller.after(0, lambda: controller.frames["GraphPage"].load_graphs(ml_graphs))
        print("DEBUG: main finished")
        return True

    except Exception as e:
        print("\n===== REAL ERROR TRACEBACK =====")
        traceback.print_exc()
        print("================================\n")

        def handle_error(e=e):
            controller.frames['ErrorPage'].set_error_message(str(e))
            controller.show_frame("ErrorPage")

        controller.after(0, handle_error)
        return False
