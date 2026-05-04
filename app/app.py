# app.py
# Author: Anna Lee / Team Wisteria
#   • Streamlit web application for ECG anomaly detection
#   • allows user to upload Excel file (ECE24-4 format)
#   • integrates:
#       • ECG filtering pipeline
#       • autoencoder-based anomaly detection
#   • loads pretrained model and normalization parameters
#   • processes uploaded data in real-time
#   • displays:
#       • ECG signal visualization
#       • detected anomaly indices
#       • reconstructed vs original signal comparison
#   • serves as front-end interface for full ML pipeline
#_______________________________________________________________________________#

# last updated: 4/15/26

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from app_ecg_filtering import run_ecg_filtering
from app_anomalies import detect_anomalies, load_model, plot_anomalies

# load trained model
model, mean, scale, threshold, window_size = load_model()

#streamlit UI title
st.title("ECG Anomaly Detection")

# ask user to upload Excel file
#uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "txt", "csv"])
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])


if uploaded_file:

    # Save temporarily 
    #streamlit provides the file as bytes, so we need to temp save this to disk
    temp_path = "temp.xlsx"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())

    # run the ecg_filtering to output the .csv file
    # return filtered signal and sampling freq
    signals, fs = run_ecg_filtering(temp_path)

    #write back the sampling frequency so user knows if it will get scaled down
    st.write(f"Sampling rate: {fs}")

    # perform anomaly detection using trained autoencoder 
    results = detect_anomalies(
        model=model,
        signals=signals,
        fs=fs,
        mean=mean,
        scale=scale,
        threshold=threshold,
        window_size=window_size
    )

    # display the anomaly count
    st.write("Anomaly count:", len(results["anomaly_indices"]))

    #plot the ecg signal 
    chart_data = pd.DataFrame({
        "ECG": signals.flatten()
    })

    #interactive line chart for the ECG signal post-fiiltering
    st.line_chart(chart_data)

    #extract results 
    anomaly_idx = results["anomaly_indices"]
    processed_signals = results["proc_signals"]

    #plot ecg with anomoalies highlighted 
    fig1 = plot_anomalies(processed_signals, results["anomaly_indices"], fs)
    #plot ecg with original, reconstruction, and anomalies
    fig2 = plot_anomalies(processed_signals, results["anomaly_indices"], fs, results["reconstruction"])

    #render plots on Streamlit
    st.pyplot(fig1)
    st.pyplot(fig2)