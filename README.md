# team-wisteria

Senior design project — software component.

## Overview

**SoundSense** is a noise sensitivity testing and biosignal analysis system designed for clinical use. It presents audio stimuli to a subject while simultaneously recording physiological responses (ECG, EMG, EDA), then applies machine learning to classify whether an abnormal autonomic response occurred.

The system supports two hardware backends: **BITalino** (Bluetooth biosignal device) and a custom **ESP32-based "Fern box"**. Results are exported to a per-patient Excel workbook and visualized in a desktop GUI.

## Repository Structure

```
team-wisteria/
├── ECE24-4/            # Main application — GUI, signal processing, ML pipeline
├── fern/               # ESP32 firmware and embedded acquisition code (Fern box)
├── filtering/          # Signal filtering experiments and notebooks
├── filtered_baseline.csv   # Sample baseline dataset
├── filtered_test.csv       # Sample test dataset
└── README.md
```

## Submodules

| Folder | Description |
|---|---|
| [`ECE24-4/`](ECE24-4/) | Desktop application: GUI, biosignal pipeline, ML classification, Excel export |
| [`fern/`](fern/) | ESP32 firmware for the custom acquisition hardware (Fern box) |

## Hardware

- **BITalino** — Bluetooth biosignal acquisition board (EMG, ECG, EDA channels)
- **ESP32 Fern box** — Custom acquisition device built by the team
- Standard audio output — used to deliver calibrated sound stimuli

## Tech Stack

- Python 3, tkinter / customtkinter, ttkbootstrap
- NumPy, PyWavelets, NeuroKit2, scikit-learn, SHAP, matplotlib
- openpyxl (Excel export), pygame (audio), pyttsx3 (TTS)
- BITalino Python API, ESP32 firmware (C++)
