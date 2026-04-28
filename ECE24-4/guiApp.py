"""
guiApp.py

SoundSense — combined desktop application.
Supports two workflows from a single entry point:

    Live Test path:
        StartPage → ModeSelectPage → DeviceConnectionPage → ParameterPage
            → InstructionsPage → VolumePage → TestPrepPage → LoadingPage
            → StartTestPage → ResultsPage → ShapPage → StatsResultsPage → GraphPage

    Load & Analyze path:
        StartPage → ModeSelectPage → LoadDataPage → LoadingPage
            → ResultsPage → ShapPage → StatsResultsPage → GraphPage
"""

import tkinter as tk
from tkinter import ttk, filedialog
from ttkbootstrap import Style
import os
import json
import shutil
import threading
import numpy as np
import customtkinter as ctk
import platform
from itertools import cycle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from PIL import Image, ImageTk
import pandas as pd

from recFuncs import (
    check_utilities,
    save_input,
    save_recording_info,
    find_bluetooth_devices,
    get_existing_BITalino_bluetooth_devices,
    save_to_existing_BITalino_bluetooth_devices,
    clear_saved_list,
    next_baseline_function,
    next_test_sequence_function,
    play_beep_sound,
    device_list,
    mac_options,
)
import procResult

# DPI awareness for Windows high-DPI displays
if platform.system() == "Windows":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print(f"Warning: could not set DPI awareness: {e}")

import matplotlib
matplotlib.use("Agg")


# ============================================================================
# HELPERS
# ============================================================================

def _make_banner(parent, title, back_cmd=None, next_cmd=None,
                 back_label="⇦  Back", next_label="Next  ⇨"):
    """
    Build a standard lightblue banner with optional back/next buttons.
    """
    banner = tk.Frame(parent, bg="lightblue")
    banner.grid(row=0, column=0, columnspan=10, sticky="nsew", pady=(0, 20))

    if back_cmd:
        ctk.CTkButton(banner, text=back_label, width=150, height=30,
                      command=back_cmd).pack(side=tk.LEFT, padx=30, pady=10)

    tk.Label(banner, text=title, font=("Calibri Light", 24, "bold"),
             bg="lightblue", justify="center").pack(
        side=tk.LEFT, expand=True, fill="x", padx=30, pady=30)

    if next_cmd:
        ctk.CTkButton(banner, text=next_label, width=150, height=30,
                      command=next_cmd).pack(side=tk.RIGHT, padx=30, pady=10)

    return banner


# ── SD card / CSV conversion helpers ────────────────────────────────────────

# Canonical column names the SD card might use (case-insensitive)
_ECG_NAMES = {"ecg", "ecg_mv", "ecg_raw"}
_EDA_NAMES = {"eda", "eda_us", "eda_raw"}
_EMG_NAMES = {"emg", "emg_mv", "emg_raw"}

def _detect_signal_columns(df):
    """
    Locate ECG, EDA, EMG columns regardless of order or case.
    Also handles a leading 'timestamp' column gracefully.

    Returns:
        (ecg_col, eda_col, emg_col) — column name strings, or None if absent.

    Raises:
        ValueError if none of the three signals can be found at all.
    """
    cols_lower = {c.lower(): c for c in df.columns}

    ecg_col = next((cols_lower[k] for k in cols_lower if k in _ECG_NAMES), None)
    eda_col = next((cols_lower[k] for k in cols_lower if k in _EDA_NAMES), None)
    emg_col = next((cols_lower[k] for k in cols_lower if k in _EMG_NAMES), None)

    # Fallback: if the file has no recognizable headers, assume positional order
    # after dropping any timestamp column.
    if ecg_col is None and eda_col is None and emg_col is None:
        non_ts = [c for c in df.columns
                  if "time" not in c.lower() and "stamp" not in c.lower()]
        if len(non_ts) >= 3:
            # We don't know the exact order — document says "idk what the order is"
            # so we map by position: col0→ECG, col1→EDA, col2→EMG as a safe default.
            ecg_col, eda_col, emg_col = non_ts[0], non_ts[1], non_ts[2]
            print(f"[WARNING] Could not detect signal columns by name. "
                  f"Assuming positional order: ECG={ecg_col}, EDA={eda_col}, EMG={emg_col}")
        else:
            raise ValueError(
                f"Cannot find ECG/EDA/EMG columns. Found: {list(df.columns)}"
            )

    return ecg_col, eda_col, emg_col


def convert_csv_in_folder(folder, baseline_seconds=30):
    """
    Finds the first CSV in *folder*, splits it into baseline and test halves,
    writes baseline_sequence.txt and test_sequence.txt (space-separated,
    columns: ECG EMG EDA — the order procFuncs.import_matrix_from_txt expects).

    Returns True if conversion succeeded, False if no CSV was found.
    Raises ValueError on malformed data.
    """
    csv_files = [f for f in os.listdir(folder) if f.endswith(".csv")]
    if not csv_files:
        return False

    csv_path = os.path.join(folder, csv_files[0])
    df = pd.read_csv(csv_path)

    # Determine sampling rate (look for 'fs' column or fall back to 100 Hz)
    if "fs" in df.columns:
        fs = int(df["fs"].iloc[0])
    else:
        fs = 100
        print(f"[WARNING] No 'fs' column found in {csv_files[0]}. Assuming {fs} Hz.")

    ecg_col, eda_col, emg_col = _detect_signal_columns(df)

    split_idx = baseline_seconds * fs
    if split_idx >= len(df):
        raise ValueError(
            f"Baseline duration ({baseline_seconds}s × {fs}Hz = {split_idx} samples) "
            f"exceeds recording length ({len(df)} samples)."
        )

    # procFuncs.import_matrix_from_txt reads columns as: EMG, ECG, EDA
    col_order = [
        ecg_col if emg_col is None else emg_col,  # col 0 → EMG
        eda_col if ecg_col is None else ecg_col,  # col 1 → ECG
        emg_col if eda_col is None else eda_col,  # col 2 → EDA
    ]
    # Compact rewrite: always use the detected names in the right slot
    col_order = [emg_col or ecg_col, ecg_col or emg_col, eda_col or emg_col]

    baseline_df = df.iloc[:split_idx][col_order]
    test_df     = df.iloc[split_idx:][col_order]

    baseline_df.to_csv(os.path.join(folder, "baseline_sequence.txt"),
                       index=False, header=False, sep=" ")
    test_df.to_csv(os.path.join(folder, "test_sequence.txt"),
                   index=False, header=False, sep=" ")

    return True


# ============================================================================
# MAIN APPLICATION CONTROLLER
# ============================================================================

class MainApp(tk.Tk):
    """
    Root window. Instantiates all pages and manages navigation between them.
    """

    def __init__(self):
        super().__init__()
        self.title("SoundSense — Noise Sensitivity Analyzer")
        self._maximize()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frames = {}

        error_frame = ErrorPage(parent=self, controller=self)
        self.frames["ErrorPage"] = error_frame
        error_frame.grid(row=0, column=0, sticky="nsew")

        if check_utilities() == -1:
            self.frames["ErrorPage"].set_error_message(
                "Check that all utilities are present, including logos and images."
            )
            self.show_frame("ErrorPage")
            return

        for PageClass in (
            StartPage, ModeSelectPage,
            DeviceConnectionPage, ParameterPage, InstructionsPage,
            VolumePage, TestPrepPage, StartTestPage,
            LoadDataPage,
            LoadingPage, ResultsPage, ShapPage, StatsResultsPage, GraphPage,
        ):
            name = PageClass.__name__
            frame = PageClass(parent=self, controller=self)
            self.frames[name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("StartPage")

    def _maximize(self):
        system = platform.system()
        if system == "Windows":
            self.state("zoomed")
        elif system == "Darwin":
            self.update_idletasks()
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        else:
            try:
                self.attributes("-zoomed", True)
            except tk.TclError:
                self.update_idletasks()
                self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.focus_set()
        frame.tkraise()


# ============================================================================
# ERROR PAGE
# ============================================================================

class ErrorPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=7, pady=7)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=0)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ttk.Label(frame, text="An error has occurred, please restart the program.",
                  font=("Calibri Light", 18, "bold"), justify="center"
                  ).grid(row=0, column=0, pady=10, sticky="s")

        self.detailed_message = ttk.Label(frame, text="",
                                          font=("Calibri Light", 12), justify="center")
        self.detailed_message.grid(row=1, column=0, pady=10)

        ctk.CTkButton(frame, text="Exit Program",
                      command=lambda: self.controller.destroy()
                      ).grid(row=2, column=0, pady=10, sticky="n")

    def set_error_message(self, text):
        self.detailed_message.config(text=text)


# ============================================================================
# START PAGE
# ============================================================================

class StartPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=7, pady=7)
        for i in range(7):
            frame.grid_rowconfigure(i, weight=(1 if i in [0, 6] else 0))
        for j in range(3):
            frame.grid_columnconfigure(j, weight=1)

        img = tk.PhotoImage(file="Utilities/sound_sense_logo.png").subsample(2, 2)
        img_label = ttk.Label(frame, image=img, anchor="center")
        img_label.image = img
        img_label.grid(row=0, column=0, columnspan=3, sticky="s")

        ttk.Label(frame, text="*Required Information",
                  font=("Calibri Light", 14)).grid(row=1, column=0, columnspan=3, pady=15)

        for row_idx, label_text in enumerate(
            ["Subject Reference Number *:", "Age:", "Contact Information:"], 2
        ):
            ttk.Label(frame, text=label_text, font=("Calibri Light", 14)).grid(
                row=row_idx, column=0, padx=5, pady=5, sticky="e")

        name_entry    = ttk.Entry(frame); name_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        age_entry     = ttk.Entry(frame); age_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        contact_entry = ttk.Entry(frame); contact_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        status_label = ttk.Label(frame, text="", anchor="center",
                                 font=("Calibri Light", 12), foreground="red")
        status_label.grid(row=5, column=0, columnspan=3, pady=15)

        def validate_and_next():
            if name_entry.get().strip():
                save_input(name_entry, age_entry, contact_entry, status_label)
                self.controller.show_frame("ModeSelectPage")
            else:
                status_label.config(text="Subject Reference Number is required.",
                                    font=("Calibri Light", 14))

        ctk.CTkButton(frame, text="Next", command=validate_and_next).grid(
            row=6, column=0, columnspan=3, pady=30, sticky="n")


# ============================================================================
# MODE SELECT PAGE
# ============================================================================

class ModeSelectPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=0)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        _make_banner(frame, "Select Test Mode",
                     back_cmd=lambda: controller.show_frame("StartPage"))

        live_card = tk.Frame(frame, bg="white", relief="groove", bd=2)
        live_card.grid(row=1, column=0, sticky="nsew", padx=40, pady=40)
        live_card.grid_rowconfigure(3, weight=1)
        live_card.grid_columnconfigure(0, weight=1)

        tk.Label(live_card, text="🎙  Run Live Test",
                 font=("Calibri Light", 20, "bold"), bg="white"
                 ).grid(row=0, column=0, pady=(40, 10), padx=30)
        tk.Label(live_card,
                 text=(
                     "Connect a BITalino or Fern (ESP32) device,\n"
                     "configure test parameters, and run a full\n"
                     "baseline + hearing test session in real time."
                 ),
                 font=("Calibri Light", 13), bg="white", justify="center", wraplength=320,
                 ).grid(row=1, column=0, padx=30, pady=10)
        tk.Label(live_card, text="Requires: BITalino or ESP32 device",
                 font=("Calibri Light", 11, "italic"), bg="white", fg="gray"
                 ).grid(row=2, column=0, padx=30, pady=(0, 20))
        ctk.CTkButton(live_card, text="Run Live Test →", width=200, height=45,
                      font=("Calibri Light", 14),
                      command=lambda: controller.show_frame("DeviceConnectionPage")
                      ).grid(row=3, column=0, pady=(10, 40), sticky="n")

        load_card = tk.Frame(frame, bg="white", relief="groove", bd=2)
        load_card.grid(row=1, column=1, sticky="nsew", padx=40, pady=40)
        load_card.grid_rowconfigure(3, weight=1)
        load_card.grid_columnconfigure(0, weight=1)

        tk.Label(load_card, text="📂  Load & Analyze",
                 font=("Calibri Light", 20, "bold"), bg="white"
                 ).grid(row=0, column=0, pady=(40, 10), padx=30)
        tk.Label(load_card,
                 text=(
                     "Load previously recorded signal data\n"
                     "from an SD card or local folder and run\n"
                     "the full ML analysis pipeline offline."
                 ),
                 font=("Calibri Light", 13), bg="white", justify="center", wraplength=320,
                 ).grid(row=1, column=0, padx=30, pady=10)
        tk.Label(load_card,
                 text="Requires: baseline_sequence.txt + test_sequence.txt\n(or a CSV with ECG/EDA/EMG columns)",
                 font=("Calibri Light", 11, "italic"), bg="white", fg="gray"
                 ).grid(row=2, column=0, padx=30, pady=(0, 20))
        ctk.CTkButton(load_card, text="Load & Analyze →", width=200, height=45,
                      font=("Calibri Light", 14),
                      command=lambda: controller.show_frame("LoadDataPage")
                      ).grid(row=3, column=0, pady=(10, 40), sticky="n")


# ============================================================================
# DEVICE CONNECTION PAGE
# ============================================================================

class DeviceConnectionPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew")
        for i in range(6):
            self.frame.grid_rowconfigure(i, weight=(1 if i == 5 else 0))
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=0)
        self.frame.grid_columnconfigure(2, weight=1)

        _make_banner(self.frame, "Connecting Device Instructions",
                     back_cmd=lambda: controller.show_frame("ModeSelectPage"),
                     next_cmd=self._next)

        ttk.Label(self.frame,
                  text="Select your biosignal recording device. Instructions will update below.",
                  font=("Calibri Light", 14), justify="center"
                  ).grid(row=1, column=0, columnspan=3, pady=5)
        ttk.Label(self.frame, text="Press 'Next' when the device is ready.",
                  font=("Calibri Light", 14)
                  ).grid(row=2, column=0, columnspan=3, pady=5)

        self.device_var = tk.StringVar(value="BITalino")
        sel_frame = ttk.Frame(self.frame)
        sel_frame.grid(row=3, column=1, pady=5)
        sel_frame.grid_columnconfigure(0, weight=1)
        sel_frame.grid_columnconfigure(2, weight=1)

        ttk.Radiobutton(sel_frame, text="BITalino", variable=self.device_var,
                        value="BITalino", command=self._update
                        ).grid(row=0, column=0, padx=10, sticky="e")
        ttk.Label(sel_frame, text="OR", font=("Calibri Light", 14, "bold")
                  ).grid(row=0, column=1, padx=10)
        ttk.Radiobutton(sel_frame, text="Fern Bioelectric Box", variable=self.device_var,
                        value="ESP32", command=self._update
                        ).grid(row=0, column=2, padx=10, sticky="w")

        self.bitalino_frame = self._build_device_frame(
            "BITalino (r)evolution Board",
            (
                "1. Turn on BITalino — confirm power light is solid.\n"
                "   If blinking red, charge before continuing.\n"
                "2. First-time setup: Settings → Bluetooth → Add Device → BITalino.\n"
                "   Enter password '1234' if prompted.\n"
                "3. Connect ECG, EMG, and EDA cables to the side ports."
            ),
            ["Utilities/Bitalino_front.png", "Utilities/Bitalino_back.png"],
        )
        self.bitalino_frame.grid(row=4, column=1, pady=10, padx=30, sticky="nsew")

        self.esp32_frame = self._build_device_frame(
            "Fern Bioelectric Box (ESP32)",
            (
                "1. Turn on the Fern box — confirm power light is on.\n"
                "2. First-time setup: Settings → Bluetooth → Add Device → ESP32-BT.\n"
                "3. Connect ECG, EMG, and EDA cables to the labeled ports.\n"
                "4. Allow device to warm up for 3 minutes before starting."
            ),
            ["Utilities/ESP32_front.png", "Utilities/ESP32_back.png"],
        )
        self.esp32_frame.grid(row=4, column=1, pady=10, padx=30, sticky="nsew")
        self.esp32_frame.grid_remove()

    def _build_device_frame(self, title, instructions, image_paths):
        lf = ttk.LabelFrame(self.frame, text=title)
        lf.grid_columnconfigure(0, weight=1)
        ttk.Label(lf, text=instructions, font=("Calibri Light", 12)
                  ).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        img_frame = ttk.Frame(lf)
        img_frame.grid(row=1, column=0, pady=5)
        for path in image_paths:
            try:
                raw = Image.open(path).resize((480, 320), Image.LANCZOS)
                photo = ImageTk.PhotoImage(raw)
                lbl = ttk.Label(img_frame, image=photo)
                lbl.image = photo
                lbl.pack(side=tk.LEFT, padx=10)
            except Exception:
                ttk.Label(img_frame, text=f"[Image not found: {path}]",
                          font=("Calibri Light", 10), foreground="gray"
                          ).pack(side=tk.LEFT, padx=10)
        return lf

    def _update(self):
        if self.device_var.get() == "BITalino":
            self.bitalino_frame.grid()
            self.esp32_frame.grid_remove()
        else:
            self.esp32_frame.grid()
            self.bitalino_frame.grid_remove()

    def _next(self):
        device = self.device_var.get()
        self.controller.frames["InstructionsPage"].update_device_instructions(device)
        self.controller.frames["ParameterPage"].update_mac_options(device)
        self.controller.show_frame("ParameterPage")


# ============================================================================
# PARAMETER PAGE
# ============================================================================

class ParameterPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._device_option = "BITalino"
        self._recording_info = {}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=0)
        frame.grid_rowconfigure(22, weight=1)
        for col in range(8):
            frame.grid_columnconfigure(col, weight=(1 if col in [0, 1, 5, 6, 7] else 0))

        _make_banner(frame, "Enter Recording Parameters",
                     back_cmd=lambda: controller.show_frame("DeviceConnectionPage"),
                     next_cmd=lambda: self._validate())

        wav_files = [f for f in os.listdir("audio_files") if f.endswith(".wav")] \
            if os.path.isdir("audio_files") else []
        ttk.Label(frame, text="Select a WAV file (leave empty if none):",
                  font=("Calibri Light", 12)).grid(row=1, column=2, padx=5, pady=5, columnspan=4, sticky="ew")
        self.wav_entry = ttk.Combobox(frame, values=wav_files, state="readonly")
        self.wav_entry.grid(row=2, column=2, padx=5, pady=5, columnspan=4, sticky="ew")

        ttk.Label(frame, text="Sound Frequency (Hz):",
                  font=("Calibri Light", 12)).grid(row=3, column=2, padx=5, pady=5, columnspan=4, sticky="ew")
        self.fq_entry = ttk.Entry(frame)
        self.fq_entry.grid(row=4, column=2, padx=5, pady=5, columnspan=4, sticky="ew")

        ttk.Label(frame, text="Sound increment (dB) — default 5:",
                  font=("Calibri Light", 12)).grid(row=5, column=2, padx=5, pady=5, columnspan=4, sticky="ew")
        self.di_entry = ttk.Entry(frame)
        self.di_entry.grid(row=6, column=2, padx=5, pady=5, columnspan=4, sticky="ew")

        ttk.Label(frame, text="Time increment (sec) — default 15:",
                  font=("Calibri Light", 12)).grid(row=7, column=2, padx=5, pady=5, columnspan=4, sticky="ew")
        self.ti_entry = ttk.Entry(frame)
        self.ti_entry.grid(row=8, column=2, padx=5, pady=5, columnspan=4, sticky="ew")

        self.sr_label = ttk.Label(frame, text="Sampling Rate (Hz):", font=("Calibri Light", 12))
        self.sr_label.grid(row=9, column=2, padx=5, pady=5, columnspan=4, sticky="ew")
        self.sr_combobox = ttk.Combobox(frame, values=[100, 1000], state="readonly")
        self.sr_combobox.grid(row=10, column=2, padx=5, pady=5, columnspan=4, sticky="ew")

        ttk.Label(frame, text="Duration (sec):",
                  font=("Calibri Light", 12)).grid(row=11, column=2, padx=5, pady=5, columnspan=4, sticky="ew")
        self.duration_entry = ttk.Combobox(
            frame, values=[15, 30, 45, 60, 75, 90, 105, 120], state="readonly")
        self.duration_entry.grid(row=12, column=2, padx=5, pady=5, columnspan=4, sticky="ew")

        ttk.Label(frame, text="Signals to record:",
                  font=("Calibri Light", 12)).grid(row=13, column=2, padx=5, pady=5, columnspan=4, sticky="ew")
        ch_frame = ttk.Frame(frame)
        ch_frame.grid(row=14, column=2, columnspan=4)
        self.emg_var = tk.IntVar()
        self.ecg_var = tk.IntVar()
        self.eda_var = tk.IntVar()
        for text, var in [("EMG", self.emg_var), ("ECG", self.ecg_var), ("EDA", self.eda_var)]:
            ttk.Checkbutton(ch_frame, text=text, variable=var,
                            onvalue=1, offvalue=0).pack(side=tk.LEFT, padx=15, pady=10)

        self.mac_label = ttk.Label(frame, text="Select a BITalino:", font=("Calibri Light", 12))
        self.mac_label.grid(row=17, column=2, padx=5, pady=5, columnspan=4, sticky="ew")
        self.mac_combobox = ttk.Combobox(frame, state="normal", takefocus=False)
        self.mac_combobox.grid(row=18, column=2, padx=5, pady=5, columnspan=4, sticky="ew")
        get_existing_BITalino_bluetooth_devices(self.mac_combobox)

        self.message_box = tk.Message(frame, text="", anchor="center", width=500,
                                      font=("Calibri Light", 10), foreground="red", bg="white")
        self.message_box.grid(row=19, column=2, padx=5, pady=5, columnspan=4, sticky="ew")

        ctk.CTkButton(frame, text="Scan for Bluetooth devices",
                      fg_color="darkred", hover_color="red",
                      command=lambda: find_bluetooth_devices(self.mac_combobox, self.message_box)
                      ).grid(row=20, column=2, padx=5, pady=5, columnspan=2, sticky="ew")
        ctk.CTkButton(frame, text="Clear list",
                      fg_color="darkred", hover_color="red",
                      command=lambda: clear_saved_list(self.mac_combobox, self.message_box, 1)
                      ).grid(row=20, column=4, padx=5, pady=5, sticky="ew")

    def update_mac_options(self, device_option):
        self._device_option = device_option
        show = device_option == "BITalino"
        for widget in (self.mac_label, self.mac_combobox, self.sr_label, self.sr_combobox):
            widget.grid() if show else widget.grid_remove()

    def _validate(self):
        msg = self.message_box
        try:
            duration = int(self.duration_entry.get())
        except ValueError:
            msg.config(text="Please select a duration.")
            return

        sample_rate = 130 if self._device_option == "ESP32" else \
            (int(self.sr_combobox.get()) if self.sr_combobox.get() else None)
        if sample_rate is None:
            msg.config(text="Please select a sampling rate.")
            return

        try:
            di_option = int(self.di_entry.get()) if self.di_entry.get() else 5
        except ValueError:
            msg.config(text="dB increment must be an integer.")
            return

        try:
            time_option = int(self.ti_entry.get()) if self.ti_entry.get() else 15
        except ValueError:
            msg.config(text="Time increment must be an integer.")
            return

        if time_option > duration:
            msg.config(text="Time increment cannot exceed duration.")
            return

        signals = [bool(self.emg_var.get()), bool(self.ecg_var.get()), bool(self.eda_var.get())]
        if not any(signals):
            msg.config(text="Select at least one signal to record.")
            return

        if self.wav_entry.get():
            audio_option = self.wav_entry.get()
        elif self.fq_entry.get():
            try:
                audio_option = int(self.fq_entry.get())
            except ValueError:
                msg.config(text="Frequency must be a valid integer.")
                return
        else:
            msg.config(text="Enter a frequency (Hz) or select a WAV file.")
            return

        mac_address = ""
        if self._device_option == "BITalino":
            mac_option = self.mac_combobox.get()
            if not mac_option:
                msg.config(text="Select a BITalino device before continuing.")
                return
            save_to_existing_BITalino_bluetooth_devices(mac_option)
            for d in device_list:
                if d[1] == mac_option:
                    mac_address = d[0]

        self._recording_info = {
            "sample_rate":   sample_rate,
            "duration":      duration,
            "macAddress":    mac_address,
            "audio_option":  audio_option,
            "time_option":   time_option,
            "di_option":     di_option,
            "signals":       signals,
            "device_option": self._device_option,
        }
        self.controller.frames["InstructionsPage"].update_device_instructions(self._device_option)
        self.controller.show_frame("InstructionsPage")

    def get_recording_info(self):
        return self._recording_info


# ============================================================================
# INSTRUCTIONS PAGE
# ============================================================================

class InstructionsPage(ttk.Frame):
    _BITALINO_IMAGES = [
        "Utilities/BITalino_front.png", "Utilities/BITalino_back.png",
        "Utilities/BITalino_ECG_pads.png", "Utilities/BITalino_EDA_pads.png",
        "Utilities/BITalino_EMG_pads.png", "Utilities/BITalino_all_pads.png",
        "Utilities/Wires_all_pads.png",
    ]
    _ESP32_IMAGES = [
        "Utilities/ESP32_front.png", "Utilities/ESP32_back.png",
        "Utilities/ESP32_ECG_pads.png", "Utilities/ESP32_EDA_pads.png",
        "Utilities/ESP32_EMG_pads.png", "Utilities/ESP32_all_pads.png",
        "Utilities/Wires_all_pads.png",
    ]
    _BITALINO_TEXT = (
        "1. Turn on headphones and connect via Bluetooth.\n"
        "2. Connect ECG/EDA/EMG cables to BITalino side ports (flip upside down).\n"
        "3. Attach electrode pads per the images on the right.\n"
        "   Note: the red ECG reference pad can be placed on the ankle.\n"
        "4. Connect colored wires to the correct pads."
    )
    _ESP32_TEXT = (
        "1. Turn on headphones and connect via Bluetooth.\n"
        "2. Attach electrode pads per the images on the right.\n"
        "   Note: the black ECG reference pad can be placed on the ankle.\n"
        "3. Connect the labeled and colored wires from the Fern box to the pads."
    )

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew")
        for i in range(6):
            self.frame.grid_rowconfigure(i, weight=(1 if i == 5 else 0))
        for j, w in enumerate([1, 0, 0, 1]):
            self.frame.grid_columnconfigure(j, weight=w)

        _make_banner(self.frame, "Setup Instructions",
                     back_cmd=lambda: controller.show_frame("ParameterPage"),
                     next_cmd=lambda: (
                         controller.frames["VolumePage"].bind_arrows(),
                         controller.show_frame("VolumePage"),
                     ))

        ttk.Label(self.frame,
                  text="Follow the instructions below. Use the image thumbnails for pad placement guidance.\nPress 'Next' when complete.",
                  font=("Calibri Light", 14), justify="center"
                  ).grid(row=1, column=0, columnspan=4, pady=10)

        self.instruction_label = ttk.Label(self.frame, text="", font=("Calibri Light", 13))
        self.instruction_label.grid(row=3, column=1, padx=40, pady=5, sticky="nw", rowspan=2)

        self._build_image_viewer()
        self.update_device_instructions("BITalino")

    def _load_photos(self, paths, full_w=560, full_h=420, thumb_w=70, thumb_h=52):
        full, thumbs = [], []
        for path in paths:
            try:
                raw = Image.open(path)
                full.append(ImageTk.PhotoImage(raw.resize((full_w, full_h), Image.LANCZOS)))
                thumbs.append(ImageTk.PhotoImage(raw.resize((thumb_w, thumb_h), Image.LANCZOS)))
            except Exception:
                placeholder = Image.new("RGB", (full_w, full_h), "#e0e0e0")
                full.append(ImageTk.PhotoImage(placeholder))
                placeholder_t = Image.new("RGB", (thumb_w, thumb_h), "#e0e0e0")
                thumbs.append(ImageTk.PhotoImage(placeholder_t))
        return full, thumbs

    def _build_image_viewer(self):
        self.selected_index = 0
        self.bt_full,  self.bt_thumbs  = self._load_photos(self._BITALINO_IMAGES)
        self.esp_full, self.esp_thumbs = self._load_photos(self._ESP32_IMAGES)

        self.bt_img_label = tk.Label(self.frame, bg="white")
        self.bt_img_label.grid(row=3, column=2, pady=10, padx=10, sticky="s")
        self.bt_thumb_frame = tk.Frame(self.frame)
        self.bt_thumb_frame.grid(row=4, column=2, pady=5, padx=10, sticky="n")
        self._populate_thumbs(self.bt_thumb_frame, self.bt_thumbs, self.bt_full, self.bt_img_label)

        self.esp_img_label = tk.Label(self.frame, bg="white")
        self.esp_img_label.grid(row=3, column=2, pady=10, padx=10, sticky="s")
        self.esp_thumb_frame = tk.Frame(self.frame)
        self.esp_thumb_frame.grid(row=4, column=2, pady=5, padx=10, sticky="n")
        self._populate_thumbs(self.esp_thumb_frame, self.esp_thumbs, self.esp_full, self.esp_img_label)

    def _populate_thumbs(self, thumb_frame, thumbs, full_photos, img_label):
        img_label.config(image=full_photos[0])
        for idx, thumb in enumerate(thumbs):
            lbl = tk.Label(thumb_frame, image=thumb, cursor="hand2")
            lbl.pack(side=tk.LEFT, padx=3)
            lbl.bind("<Button-1>",
                     lambda e, i=idx, lbl=img_label, ph=full_photos: lbl.config(image=ph[i]))

    def update_device_instructions(self, device_option):
        if device_option == "ESP32":
            self.instruction_label.config(text=self._ESP32_TEXT)
            self.bt_img_label.grid_remove()
            self.bt_thumb_frame.grid_remove()
            self.esp_img_label.grid()
            self.esp_thumb_frame.grid()
        else:
            self.instruction_label.config(text=self._BITALINO_TEXT)
            self.esp_img_label.grid_remove()
            self.esp_thumb_frame.grid_remove()
            self.bt_img_label.grid()
            self.bt_thumb_frame.grid()


# ============================================================================
# VOLUME PAGE
# ============================================================================

class VolumePage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.final_volume_db = -30

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew")
        for i, w in enumerate([0, 0, 0, 1]):
            frame.grid_rowconfigure(i, weight=w)
        frame.grid_columnconfigure(0, weight=1)

        _make_banner(frame, "Volume Adjustment",
                     back_cmd=lambda: (self.unbind_arrows(),
                                       controller.show_frame("InstructionsPage")),
                     next_cmd=lambda: (self.unbind_arrows(),
                                       controller.show_frame("TestPrepPage")))

        ttk.Label(frame,
                  text="Use the ↑ and ↓ arrow keys to adjust the beep volume.\nPress 'Next' when the volume feels comfortable.",
                  font=("Calibri Light", 14), justify="center"
                  ).grid(row=1, column=0, pady=10, sticky="s")

        self.volume_label = ttk.Label(frame, text=f"Current Volume: {self.final_volume_db} dB",
                                      font=("Calibri Light", 16))
        self.volume_label.grid(row=2, column=0, pady=10)

    def bind_arrows(self):
        self.controller.bind_all("<KeyPress-Up>",  self._adjust)
        self.controller.bind_all("<KeyPress-Down>", self._adjust)

    def unbind_arrows(self):
        self.controller.unbind_all("<KeyPress-Up>")
        self.controller.unbind_all("<KeyPress-Down>")

    def _adjust(self, event):
        if event.keysym == "Up":
            self.final_volume_db = min(self.final_volume_db + 3, 0)
        else:
            self.final_volume_db = max(self.final_volume_db - 3, -60)
        play_beep_sound(self.final_volume_db)
        self.volume_label.config(text=f"Current Volume: {self.final_volume_db} dB")


# ============================================================================
# TEST PREP PAGE
# ============================================================================

class TestPrepPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(7, weight=1)
        for j, w in enumerate([1, 0, 1]):
            self.frame.grid_columnconfigure(j, weight=w)

        _make_banner(self.frame, "Test Preparation",
                     back_cmd=lambda: controller.show_frame("VolumePage"))

        ttk.Label(self.frame, text="Please Read Carefully Before Beginning",
                  font=("Calibri Light", 14)).grid(row=2, column=1, pady=10)

        for row_idx, (heading, body) in enumerate([
            (
                "How the Test Works:",
                "The system captures two sessions of biosignals.\n"
                "First, a baseline recording captures your resting state.\n"
                "Then a second recording runs while a sound stimulus is played.\n"
                "Do not close the application during recording.",
            ),
            (
                "Before You Begin:",
                "Remain as still as possible throughout both sessions.\n"
                "Stay calm and avoid distractions — close your eyes if it helps.\n"
                "Consistent behavior is essential for reliable results.",
            ),
        ], 3):
            f = ttk.Frame(self.frame)
            f.grid(row=row_idx, column=1, sticky="ns", padx=10, pady=15)
            ttk.Label(f, text=heading, font=("Calibri Light", 15, "bold")).grid(row=0, column=0)
            ttk.Label(f, text=body, font=("Calibri Light", 13), justify="center").grid(row=1, column=0)

        ttk.Label(self.frame, text="When you are ready, click 'Begin'",
                  font=("Calibri Light", 14, "bold")).grid(row=6, column=1, pady=20)
        ctk.CTkButton(self.frame, text="Begin", command=self._begin).grid(
            row=7, column=1, pady=20, sticky="n")

    def _begin(self):
        info = self.controller.frames["ParameterPage"].get_recording_info()
        next_baseline_function(info, self.controller)
        self.controller.frames["LoadingPage"].set_load_title("Please Wait…")
        self.controller.show_frame("LoadingPage")


# ============================================================================
# LOAD DATA PAGE
# ============================================================================

class LoadDataPage(ttk.Frame):
    """
    Loads pre-recorded biosignal data from an SD card or local folder.

    Accepted folder contents:
        baseline_sequence.txt + test_sequence.txt  (space-separated, columns: EMG ECG EDA)
        OR a single CSV with columns: timestamp, ECG, EDA, EMG (any order/case)

    Optional:
        session_info.json — auto-populates sample rate and channel settings.
    """

    REQUIRED_FILES = ("baseline_sequence.txt", "test_sequence.txt")

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        outer = ttk.Frame(self)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        _make_banner(outer, "Load Patient Data",
                     back_cmd=lambda: controller.show_frame("ModeSelectPage"))

        content = ttk.Frame(outer)
        content.grid(row=1, column=0, sticky="nsew", padx=60, pady=20)
        content.grid_columnconfigure(1, weight=1)

        ttk.Label(content,
                  text="Select the folder containing the recording files from the patient's SD card.",
                  font=("Calibri Light", 14), justify="center", wraplength=700
                  ).grid(row=0, column=0, columnspan=3, pady=(0, 25))

        ttk.Label(content, text="Data folder:", font=("Calibri Light", 13)).grid(
            row=1, column=0, sticky="e", padx=(0, 10), pady=8)
        self.folder_var = tk.StringVar()
        ttk.Entry(content, textvariable=self.folder_var, width=55).grid(
            row=1, column=1, sticky="ew", pady=8)
        ctk.CTkButton(content, text="Browse…", width=90, command=self._browse).grid(
            row=1, column=2, padx=(10, 0), pady=8)

        override = ttk.LabelFrame(
            content, text="Recording parameters  (override if no session_info.json)")
        override.grid(row=2, column=0, columnspan=3, sticky="ew", pady=15)
        override.grid_columnconfigure(1, weight=1)

        ttk.Label(override, text="Sample rate (Hz):", font=("Calibri Light", 13)).grid(
            row=0, column=0, sticky="e", padx=10, pady=8)
        self.sr_var = tk.StringVar(value="100")
        ttk.Entry(override, textvariable=self.sr_var, width=10).grid(
            row=0, column=1, sticky="w", pady=8)

        ttk.Label(override, text="Baseline duration (sec):", font=("Calibri Light", 13)).grid(
            row=1, column=0, sticky="e", padx=10, pady=8)
        self.baseline_sec_var = tk.StringVar(value="30")
        ttk.Entry(override, textvariable=self.baseline_sec_var, width=10).grid(
            row=1, column=1, sticky="w", pady=8)

        ttk.Label(override, text="Channels recorded:", font=("Calibri Light", 13)).grid(
            row=2, column=0, sticky="e", padx=10, pady=8)
        ch_frame = ttk.Frame(override)
        ch_frame.grid(row=2, column=1, columnspan=3, sticky="w", pady=8)
        self.emg_var = tk.BooleanVar(value=True)
        self.ecg_var = tk.BooleanVar(value=True)
        self.eda_var = tk.BooleanVar(value=True)
        for text, var in [("EMG", self.emg_var), ("ECG", self.ecg_var), ("EDA", self.eda_var)]:
            ttk.Checkbutton(ch_frame, text=text, variable=var).pack(side=tk.LEFT, padx=12)

        self.status_label = ttk.Label(content, text="", font=("Calibri Light", 12),
                                      foreground="red", justify="center", wraplength=700)
        self.status_label.grid(row=3, column=0, columnspan=3, pady=10)

        self.file_status_frame = ttk.Frame(content)
        self.file_status_frame.grid(row=4, column=0, columnspan=3, pady=5)

        ctk.CTkButton(content, text="Analyze", width=160, height=40,
                      command=self._start_analysis).grid(row=5, column=0, columnspan=3, pady=30)

    def _browse(self):
        folder = filedialog.askdirectory(title="Select SD card data folder")
        if folder:
            self.folder_var.set(folder)
            self._check_folder(folder)

    def _check_folder(self, folder):
        for w in self.file_status_frame.winfo_children():
            w.destroy()

        # Try CSV conversion if sequence files are absent
        txt_missing = [f for f in self.REQUIRED_FILES
                       if not os.path.isfile(os.path.join(folder, f))]

        if txt_missing:
            try:
                baseline_sec = int(float(self.baseline_sec_var.get()))
            except ValueError:
                baseline_sec = 30

            try:
                converted = convert_csv_in_folder(folder, baseline_seconds=baseline_sec)
                if converted:
                    ttk.Label(self.file_status_frame,
                              text="  ✓  CSV detected → converted to sequence files",
                              font=("Calibri Light", 12), foreground="green").pack(anchor="w")
            except Exception as e:
                ttk.Label(self.file_status_frame,
                          text=f"  ⚠  CSV conversion failed: {e}",
                          font=("Calibri Light", 12), foreground="orange").pack(anchor="w")

        missing = []
        for fname in self.REQUIRED_FILES:
            present = os.path.isfile(os.path.join(folder, fname))
            ttk.Label(self.file_status_frame,
                      text=f"  {'✓' if present else '✗'}  {fname}",
                      font=("Calibri Light", 12),
                      foreground="green" if present else "red"
                      ).pack(anchor="w")
            if not present:
                missing.append(fname)

        info_path = os.path.join(folder, "session_info.json")
        if os.path.isfile(info_path):
            try:
                with open(info_path) as f:
                    info = json.load(f)
                self.sr_var.set(str(info.get("sample_rate", 100)))
                ch = info.get("channels", {})
                self.emg_var.set(bool(ch.get("emg", True)))
                self.ecg_var.set(bool(ch.get("ecg", True)))
                self.eda_var.set(bool(ch.get("eda", True)))
                ttk.Label(self.file_status_frame,
                          text="  ✓  session_info.json  (parameters loaded)",
                          font=("Calibri Light", 12), foreground="green").pack(anchor="w")
            except Exception as e:
                ttk.Label(self.file_status_frame,
                          text=f"  ⚠  session_info.json could not be parsed: {e}",
                          font=("Calibri Light", 12), foreground="orange").pack(anchor="w")
        else:
            ttk.Label(self.file_status_frame,
                      text="  —  session_info.json not found (using manual parameters)",
                      font=("Calibri Light", 12), foreground="gray").pack(anchor="w")

        self.status_label.config(
            text=f"Missing required files: {', '.join(missing)}" if missing
            else "All required files found.",
            foreground="red" if missing else "green",
        )

    def _start_analysis(self):
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            self.status_label.config(text="Please select a valid data folder.", foreground="red")
            return

        missing = [f for f in self.REQUIRED_FILES
                   if not os.path.isfile(os.path.join(folder, f))]
        if missing:
            self.status_label.config(
                text=f"Missing required files: {', '.join(missing)}", foreground="red")
            return

        try:
            sample_rate = int(float(self.sr_var.get().strip()))
            if sample_rate <= 0:
                raise ValueError
        except Exception:
            self.status_label.config(
                text=f"Invalid sample rate: '{self.sr_var.get()}' (must be a positive integer)",
                foreground="red")
            return

        channels = [self.emg_var.get(), self.ecg_var.get(), self.eda_var.get()]
        if not any(channels):
            self.status_label.config(
                text="At least one channel must be selected.", foreground="red")
            return

        try:
            for fname in self.REQUIRED_FILES:
                shutil.copy(os.path.join(folder, fname), os.path.join(os.getcwd(), fname))
        except Exception as e:
            self.status_label.config(text=f"Could not copy data files: {e}", foreground="red")
            return

        from recFuncs import filepath, filename
        output_excel = os.path.join(os.getcwd(), filepath, filename)

        self.controller.frames["LoadingPage"].set_load_title("Analyzing data…")
        self.controller.show_frame("LoadingPage")

        threading.Thread(
            target=self._run_analysis,
            args=(output_excel, channels, sample_rate),
            daemon=True,
        ).start()

    def _run_analysis(self, output_excel, channels, sample_rate):
        try:
            procResult.main(output_excel, channels, sample_rate, self.controller)
        except Exception as e:
            error_msg = str(e)
            self.controller.after(0, lambda: (
                self.controller.frames["ErrorPage"].set_error_message(
                    f"Analysis failed:\n{error_msg}"),
                self.controller.show_frame("ErrorPage"),
            ))


# ============================================================================
# LOADING PAGE
# ============================================================================

class LoadingPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=7, pady=7)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        self.label = ttk.Label(frame, text="Please Wait…", font=("Calibri Light", 16))
        self.label.grid(row=0, column=0, pady=30, padx=10, sticky="e")

        self.images = [
            tk.PhotoImage(file=f"Utilities/logo_loading_{i}.png").subsample(4, 4)
            for i in range(1, 4)
        ]
        self.image_cycle = cycle(self.images)
        self.load_symbol = ttk.Label(frame, image=next(self.image_cycle))
        self.load_symbol.grid(row=0, column=1, pady=30, padx=10, sticky="w")

        self.running   = True
        self._after_id = None
        self._animate()

    def _animate(self):
        if not self.winfo_exists() or not self.running:
            return
        self.load_symbol.config(image=next(self.image_cycle))
        self._after_id = self.after(1000, self._animate)

    def set_load_title(self, title, infinite=False):
        self.label.config(text=title)
        self.running = True
        if self._after_id is None:
            self._animate()

    def stop_loading(self):
        self.running = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def reset(self):
        self.stop_loading()
        self.label.config(text="Please Wait…")
        self.image_cycle = cycle(self.images)
        self.load_symbol.config(image=next(self.image_cycle))


# ============================================================================
# START TEST PAGE
# ============================================================================

class StartTestPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=7, pady=7)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ttk.Label(frame, text="Baseline Collection Complete!",
                  font=("Calibri Light", 16), justify="center"
                  ).grid(row=0, column=0, pady=10, sticky="s")
        ctk.CTkButton(frame, text="Start Test Sequence", command=self._start).grid(
            row=1, column=0, pady=10, sticky="n")

    def _start(self):
        self.controller.frames["LoadingPage"].set_load_title("Please Wait…")
        self.controller.show_frame("LoadingPage")
        next_test_sequence_function(self.controller)


# ============================================================================
# RESULTS PAGE
# ============================================================================

class ResultsPage(ttk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew")
        for i in range(5):
            self.frame.grid_rowconfigure(i, weight=(1 if i == 4 else 0))
        for j, w in enumerate([1, 0, 1]):
            self.frame.grid_columnconfigure(j, weight=w)

        _make_banner(self.frame, "ML Results Overview",
                     next_cmd=lambda: controller.show_frame("ShapPage"),
                     next_label="View Feature Significance  ⇨")

        ctk.CTkButton(self.frame, text="Exit", command=lambda: self.controller.destroy(),
                      width=75, fg_color="red", hover_color="darkred"
                      ).grid(row=4, column=0, padx=20, pady=10, sticky="se", columnspan=3)

        self.no_ml_label = tk.Label(
            self.frame,
            text=("We are unable to generate an ML prediction for the selected signals.\n\n"
                  "Please see the Stats Display Page and Graphs for information on your collected signals."),
            font=("Calibri Light", 16), justify="center",
        )
        self.no_ml_label.grid(row=2, column=1, sticky="nsew", pady=40)

    def display_results(self, ml_predictions, results_data):
        self.no_ml_label.grid_remove()

        print("DEBUG ml_predictions:", ml_predictions)
        print("DEBUG results_data:", results_data)

        # ─────────────────────────────────────────────
        # Normalize inputs (prevents NoneType errors)
        # ─────────────────────────────────────────────
        ml_predictions = ml_predictions or {}
        results_data = results_data or {}

        ecg_data = results_data.get("ecg") or {}
        baseline_data = ecg_data.get("baseline_data") or {}
        test_data = ecg_data.get("test_data") or {}
        percent_diff = ecg_data.get("percent_difference") or {}

        # ─────────────────────────────────────────────
        # Prediction summary
        # ─────────────────────────────────────────────
        pred_frame = tk.Frame(self.frame, relief="groove", bg="#FEE788")
        pred_frame.grid(row=2, column=1, sticky="nsew", pady=40)

        final_prediction = ""
        confidence_text = ""

        for _, pred in ml_predictions.items():
            pred = pred or {}

            if pred.get("classification") == 1:
                final_prediction = (
                    "Your response indicates a potential irregularity.\n"
                    "We recommend consulting a healthcare professional."
                )
                confidence_text = (
                    f"Our system is {100 * pred.get('confidence', 0):.2f}% "
                    "confident an abnormal reaction occurred."
                )

            elif pred.get("classification") == 0:
                final_prediction = "No abnormal response was detected."
                confidence_text = (
                    f"Our system is {100 * (1 - pred.get('confidence', 0)):.2f}% "
                    "confident that no abnormal reaction occurred."
                )

        for text, font in [
            (final_prediction, ("Calibri Light", 13, "bold")),
            (confidence_text, ("Calibri Light", 10)),
        ]:
            tk.Label(pred_frame, text=text, font=font, bg="#FEE788").pack(pady=10, padx=15)

        # ─────────────────────────────────────────────
        # Table setup
        # ─────────────────────────────────────────────
        table = ttk.Treeview(
            self.frame,
            columns=["Feature", "Baseline", "Test", "Difference"],
            show="headings",
            height=12,
        )
        table.grid(row=3, column=1, sticky="nsew", padx=7, pady=7)

        for col, anchor in [
            ("Feature", "w"),
            ("Baseline", "center"),
            ("Test", "center"),
            ("Difference", "center"),
        ]:
            table.heading(col, text=col, anchor=anchor)
            table.column(col, width=100, anchor=anchor)

        style = ttk.Style()
        style.configure("Treeview", font=("Calibri Light", 10), rowheight=30)
        style.configure("Treeview.Heading", font=("Calibri Light", 12, "bold"))

        table.tag_configure("even", background="#E1EEFF")
        table.tag_configure("odd", background="#E7F7FA")

        # ─────────────────────────────────────────────
        # Populate table safely
        # ─────────────────────────────────────────────
        if not baseline_data:
            print("WARNING: No ECG baseline data available")
            table.insert("", "end", values=("No data available", "-", "-", "-"))
            return

        for i, feature in enumerate(baseline_data):
            tag = "even" if i % 2 == 0 else "odd"

            b = baseline_data.get(feature, "N/A")
            t = test_data.get(feature, "N/A")
            d = percent_diff.get(feature, "N/A")

            table.insert(
                "",
                "end",
                values=(
                    feature,
                    f"{b:.5f}" if isinstance(b, (int, float)) else "N/A",
                    f"{t:.5f}" if isinstance(t, (int, float)) else "N/A",
                    f"{d:.5f}%" if isinstance(d, (int, float)) else "N/A%",
                ),
                tags=(tag,),
            )

# ============================================================================
# SHAP PAGE  (repurposed: shows ECG anomaly plot instead of SHAP waterfall)
# ============================================================================

class ShapPage(ttk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew")
        for i in range(4):
            self.frame.grid_rowconfigure(i, weight=(1 if i >= 2 else 0))
        for j, w in enumerate([1, 0, 1]):
            self.frame.grid_columnconfigure(j, weight=w)

        _make_banner(self.frame, "ECG Anomaly Detection",
                     back_cmd=lambda: controller.show_frame("ResultsPage"),
                     back_label="⇦  Back to ML Results",
                     next_cmd=lambda: controller.show_frame("StatsResultsPage"),
                     next_label="View Stats Results  ⇨")

        ctk.CTkButton(self.frame, text="Exit", command=lambda: self.controller.destroy(),
                      width=75, fg_color="red", hover_color="darkred"
                      ).grid(row=3, column=0, padx=20, pady=10, sticky="se", columnspan=3)

        self.no_shap_label = tk.Label(
            self.frame,
            text=("Because we were unable to generate an ML prediction, "
                  "we cannot provide anomaly detection insight.\n\n"
                  "Please see the Stats Display Page and Graphs for signal information."),
            font=("Calibri Light", 16), justify="center",
        )
        self.no_shap_label.grid(row=2, column=1, sticky="nsew", pady=40)

    def display_results(self, ml_predictions):
        """Render the ECG anomaly figure stored in ml_predictions['ecg']['fig']."""    
        print("DEBUG: ShapPage display_results called")

        fig = (ml_predictions or {}).get("ecg", {}).get("fig")

        if fig is None:
            print("WARNING: No ECG anomaly figure available")
            return

        self.no_shap_label.grid_remove()

        shap_frame = tk.Frame(self.frame)
        shap_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=30, pady=20)
        fig.set_size_inches(12, 5)

        canvas = FigureCanvasTkAgg(fig, master=shap_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        tb = NavigationToolbar2Tk(canvas, shap_frame)
        tb.update()
        canvas._tkcanvas.pack(fill="both", expand=True)

# ============================================================================
# STATS RESULTS PAGE
# ============================================================================

class StatsResultsPage(ttk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.figs = []
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_rowconfigure(2, weight=0)
        self.frame.grid_columnconfigure(0, weight=1)

        _make_banner(self.frame, "Stats Overview",
                     back_cmd=lambda: controller.show_frame("ShapPage"),
                     back_label="⇦  Back to Feature Significance",
                     next_cmd=lambda: controller.show_frame("GraphPage"),
                     next_label="View Graphs  ⇨")

        ctk.CTkButton(self.frame, text="Exit", command=lambda: self.controller.destroy(),
                      width=75, fg_color="red", hover_color="darkred"
                      ).grid(row=2, column=0, padx=20, pady=10, sticky="se")

        self.notebook = ttk.Notebook(self.frame)
        self.notebook.grid(row=1, column=0, sticky="nsew", pady=10, padx=25)

    def display_results(self, stats_data):
        print("DEBUG: StatsResultsPage display_results called")

        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Stats")

        for i in range(12):
            tab.grid_rowconfigure(i, weight=(1 if i == 11 else 0))
        for j, w in enumerate([2, 0, 2]):
            tab.grid_columnconfigure(j, weight=w)

        style = ttk.Style()
        style.configure("Treeview", font=("Calibri Light", 10), rowheight=30)
        style.configure("Treeview.Heading", font=("Calibri Light", 12, "bold"))

        row = 1

        for signal, cats in stats_data.items():
            cats = cats or {}

            baseline_data = cats.get("baseline") or {}
            test_data = cats.get("test") or {}
            diff_data = cats.get("diff") or {}
            flags_data = cats.get("flags") or {}

            if not baseline_data:
                continue

            tk.Label(
                tab,
                text=f"{signal.upper()} Stats",
                font=("Calibri Light", 16, "bold")
            ).grid(row=row, column=1, sticky="nsew", padx=7, pady=7)

            table = ttk.Treeview(
                tab,
                columns=["Stat Type", "Baseline", "Test", "Difference", "Flag"],
                show="headings",
                height=max(4, len(baseline_data)),
            )
            table.grid(row=row + 1, column=0, columnspan=3, sticky="nsew", padx=40, pady=7)
            for col, width in [
                ("Stat Type", 140),
                ("Baseline", 180),
                ("Test", 180),
                ("Difference", 180),
                ("Flag", 180),
            ]:
                anchor = "w" if col == "Stat Type" else "center"
                table.heading(col, text=col, anchor=anchor)
                table.column(col, width=width, anchor=anchor)

            table.tag_configure("even", background="#E1EEFF")
            table.tag_configure("odd", background="#E7F7FA")

            def fmt(value, suffix=""):
                if isinstance(value, (int, float, np.integer, np.floating)) and not np.isnan(value):
                    return f"{value:.5f}{suffix}"
                return "N/A"

            for i, stat in enumerate(baseline_data.keys()):
                tag = "even" if i % 2 == 0 else "odd"

                b = baseline_data.get(stat, "N/A")
                t = test_data.get(stat, "N/A")
                d = diff_data.get(stat, "N/A")
                flag = flags_data.get(stat, "N/A") if isinstance(flags_data, dict) else "N/A"

                table.insert(
                    "",
                    "end",
                    values=(
                        stat,
                        fmt(b),
                        fmt(t),
                        fmt(d, "%"),
                        flag,
                    ),
                    tags=(tag,),
                )

            row += 2

    def load_graphs(self, graphs_dict):
        for category, graphs in graphs_dict.items():
            if not graphs:
                continue
            tab_frame = ScrollableFrame(self.notebook)
            tk.Label(tab_frame.scrollable_frame, text=category,
                     font=("Calibri Light", 16, "bold"), pady=10).pack(fill="x")
            for fig in graphs:
                self.figs.append(fig)
                gf = tk.Frame(tab_frame.scrollable_frame, bd=1, relief="groove",
                              padx=30, pady=40)
                gf.pack(fill="x", pady=10, padx=30)
                canvas = FigureCanvasTkAgg(fig, master=gf)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
                tb = NavigationToolbar2Tk(canvas, gf)
                tb.update()
                canvas._tkcanvas.pack(fill="x")
            self.notebook.add(tab_frame, text=category)
        self.update_idletasks()


# ============================================================================
# GRAPH PAGE
# ============================================================================

class GraphPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.figs = []

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew")

        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(1, weight=0)
        self.frame.grid_rowconfigure(2, weight=1)
        self.frame.grid_rowconfigure(3, weight=0)

        for j in range(3):
            self.frame.grid_columnconfigure(j, weight=1)

        _make_banner(
            self.frame,
            "Analysis Graphs",
            back_cmd=lambda: controller.show_frame("StatsResultsPage"),
            back_label="⇦  Back to Stats Results",
        )

        tk.Label(
            self.frame,
            text="Click between tabs to view all graphs.",
            font=("Calibri Light", 14),
        ).grid(row=1, column=0, columnspan=3, pady=(0, 20))

        self.notebook = ttk.Notebook(self.frame)
        self.notebook.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=30, pady=10)

        ctk.CTkButton(
            self.frame,
            text="Exit",
            command=lambda: self.controller.destroy(),
            width=75,
            fg_color="red",
            hover_color="darkred",
        ).grid(row=3, column=0, columnspan=3, padx=20, pady=10, sticky="se")

    def load_graphs(self, graphs_dict):
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)

        self.figs.clear()

        for category, data_types in graphs_dict.items():
            for data_type, fig in data_types.items():
                if fig is None:
                    continue

                title = f"{category.upper()} {data_type.capitalize()}"
                self.figs.append(fig)

                fig.set_size_inches(14, 6)
                fig.tight_layout()

                gf = tk.Frame(self.notebook)
                gf.grid_rowconfigure(0, weight=1)
                gf.grid_rowconfigure(1, weight=0)
                gf.grid_columnconfigure(0, weight=1)

                canvas = FigureCanvasTkAgg(fig, master=gf)
                canvas.draw()
                canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

                tb = NavigationToolbar2Tk(canvas, gf, pack_toolbar=False)
                tb.update()
                tb.grid(row=1, column=0, sticky="ew")

                self.notebook.add(gf, text=title)

        self.update_idletasks()


# ============================================================================
# SCROLLABLE FRAME
# ============================================================================

class ScrollableFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._scroll))
        self.scrollable_frame.bind(
            "<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="frame")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure("frame", width=e.width))

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _scroll(self, event):
        if platform.system() == "Darwin":
            self.canvas.yview_scroll(-1 * event.delta, "units")
        else:
            self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
