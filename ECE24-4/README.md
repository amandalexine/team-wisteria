# ECE24-4 — SoundSense Desktop Application

The main software component of **SoundSense**. A Python desktop application for conducting noise sensitivity tests, analyzing biosignals, detecting anomalies, and exporting results.

---

## Features

- Subject intake + automatic patient record management  
- SD card data loader (offline analysis from recorded sessions)  
- Real-time biosignal acquisition (BITalino / ESP32 support)  
- Live signal visualization during acquisition  
- Signal processing:
  - DWT denoising (EDA, EMG)
  - LMS adaptive filtering
  - Sectioned statistical analysis
- **ECG anomaly detection using autoencoder model**
- ECG reconstruction + anomaly visualization plots  
- Statistical comparison (baseline vs test) with percent differences  
- Multi-page GUI workflow with graphs + tables  
- Full Excel export:
  - Patient info
  - Raw signals
  - Stats tables
  - Graphs
  - ML outputs

---

## Page Flow
```
StartPage → LoadDataPage → LoadingPage → ResultsPage → ShapPage → StatsResultsPage → GraphPage
```
---

## Project Structure
```
ECE24-4/
├── guiApp.py                  # main entry point
├── requirements.txt
├── README.md
│
├── app/
│   ├── recFuncs.py
│   ├── hearingTest.py
│   ├── testSeq.py
│   ├── testSettings.py
│   └── saveFuncs.py
│
├── processing/
│   ├── procFuncs.py
│   └── procResult.py
│
├── ml/
│   ├── ecgML.py
│   ├── ML_files/
│   └── ML_Training/
│
├── hardware/
│   ├── esp32Device.py
│   └── esp32Arduino.cpp
│
├── assets/
│   ├── Utilities/
│   └── audio_files/
│
├── data/
│   ├── baseline_sequence.txt
│   └── test_sequence.txt
│
└── patient_records/
```
---

## Setup (Linux Recommended)

### Create virtual environment
```
cd ~/personal/team-wisteria/ECE24-4
python3 -m venv venv
source venv/bin/activate
```
---

### Install dependencies
```
pip install numpy pandas matplotlib pillow
pip install customtkinter ttkbootstrap
pip install PyWavelets neurokit2 scikit-learn shap
pip install openpyxl pygame pyttsx3 keyboard
pip install bitalino
```
---

### Run the application
```
python3 guiApp.py
```
---

## Required Assets
```
Utilities/
├── ss_logo.ico
├── sound_sense_logo.png
├── logo_loading_1.png
├── logo_loading_2.png
└── logo_loading_3.png
```
---

## Data Format (Updated)

baseline_sequence.txt  
test_sequence.txt  

CSV format:
```
Timestamp (ms), ECG (V), EMG (V), EDA (V)
```
---

## Output
```
Patient Records/Patient_<id>/<id>_<N>.xlsx
```
---

## Signal Processing Pipeline

EDA / EMG:
- DWT denoising (db4, level 7)
- LMS adaptive filtering

ECG:
- Autoencoder anomaly detection
- Reconstruction + anomaly visualization

---

## Supported Devices

- BITalino (Bluetooth)
- ESP32 (USB / Wi-Fi)

---

## Notes

- Use a virtual environment
- CSV format replaced old format
- Autoencoder replaced KNN pipeline

---

## Known Issues

- pyttsx3 warnings on Linux (safe to ignore)
- Large datasets may slow graphs

---

## Authors
Team Wisteria:
Karen Bei, Anna Lee, Amanda-Lexine Sunga, Amanda Yan (Tufts ECE '26)
