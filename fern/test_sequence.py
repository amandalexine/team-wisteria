# test_sequence.py

# Main control script for running baseline collection and hearing test sequences.
# It manages:
# - BITalino device connection (bioelectric signal collection)
# - Audio playback synchronization (using pygame)
# - Real-time graphing (via matplotlib animation)
# - Concurrent data acquisition, sound playback, and live visualization
# - Data persistence to .txt and Excel files
#_______________________________________________________________________________#

import threading
import pygame
import time
from bitalino import BITalino
import os
import multiprocessing as multi
import sys
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import hearing_test as sound   # Custom module (Kyle’s code) for sound playback and text-to-speech
import openpyxl
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import procResult


# -------------------------- GLOBAL VARIABLES --------------------------
device = 0  # Global BITalino device handle used by acquisition functions


# -------------------------- FILE SAVING FUNCTIONS --------------------------
def save_to_txt_file(txt_name, emg, ecg, eda):
    """
    Save raw EMG, ECG, and EDA data to a CSV-formatted text file.
    Each line = one timestamp’s readings for all three channels.
    """
    data1, data2, data3 = 0, 0, 0

    with open(txt_name, 'w') as file:
        for data in range(len(ecg)):
            if len(emg) > 0:
                data1 = emg[data]
            if len(ecg) > 0:
                data2 = ecg[data]
            if len(eda) > 0:
                data3 = eda[data]
            file.write(f'{data1},{data2},{data3}\n')


def save_to_patients_excel_file(baseline: bool, filename: str, emg, ecg, eda):
    """
    Write acquired data into the patient’s Excel record.
    Appends data to either the “Baseline Data” or “Test Data” worksheet.
    """
    workbook = openpyxl.load_workbook(filename)
    data = [emg, ecg, eda]

    # Determine which sheet to write to
    sheet_name = 'Baseline Data' if baseline else 'Test Data'
    sheet = workbook[sheet_name]

    # Write EMG, ECG, and EDA values column-wise
    for column in range(3):
        for row_num, value in enumerate(data[column], start=2):
            sheet.cell(row=row_num, column=column + 1).value = value

    workbook.save(filename)


# -------------------------- AUDIO FUNCTIONS --------------------------
def set_computer_volume(percentage):
    """
    Set system volume to a specified percentage using the Pycaw COM interface.
    """
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = interface.QueryInterface(IAudioEndpointVolume)
    volume.SetMasterVolumeLevelScalar(percentage / 100, None)


def play_wavefile(sound, duration):
    """
    Play a preloaded .wav sound repeatedly for a fixed duration.
    Stops playback after the given duration.
    """
    start_time = time.time()

    while True:
        sound.play()
        time.sleep(1)
        sound.stop()
        if time.time() - start_time > duration:
            sound.stop()
            break


def play_sound(duration, frequency, interval, di, final_volume_db=-30):
    """
    Play sound stimuli for a hearing test sequence.
    If `frequency` is a string, it loads and plays a .wav file.
    Otherwise, it uses a generated tone from hearing_test.py.
    Volume increases gradually by `di` dB after every `interval` seconds.
    """
    number_of_db_increases = int(duration / interval)

    # Case 1: Pre-recorded .wav file
    if isinstance(frequency, str):
        pygame.init()
        pygame.mixer.init()
        wav_sound = pygame.mixer.Sound('audio_files/' + frequency)
        for _ in range(number_of_db_increases):
            play_wavefile(wav_sound, interval)
            final_volume_db += di  # Increment dB level

    # Case 2: Synthetic tone generated dynamically
    else:
        for _ in range(number_of_db_increases):
            sound.play_for_time(interval, final_volume_db, frequency)
            final_volume_db += di


# -------------------------- SIGNAL ACQUISITION --------------------------
def grab_signal(samplingRate: int, duration: int, emg_vals, ecg_vals, eda_vals, channel=[True, True, True]):
    """
    Continuously collect EMG, ECG, and EDA data from BITalino for a given duration.
    Uses shared memory lists so multiprocessing can access live data.
    """
    device.start(samplingRate, [0, 1, 2, 3, 4, 5])
    start_time = time.time()

    while (time.time() - start_time) < duration:
        data = device.read(samplingRate)  # Read one second worth of samples
        for i in data:
            # Append data if channel is enabled, else append dummy values
            emg_vals.append(i[5] if channel[0] else 1)
            ecg_vals.append(i[6] if channel[1] else 1)
            eda_vals.append(i[7] if channel[2] else 1)

    print(f"Signal acquisition finished in {time.time() - start_time:.2f} seconds")
    device.stop()
    device.close()


# -------------------------- LIVE GRAPHING --------------------------
def live_graphing(ready_event, samplingRate, emg_vals, ecg_vals, eda_vals, channel, duration):
    """
    Plot live bioelectric data in real time using matplotlib animation.
    Runs in a separate process to prevent blocking.
    """
    plt.style.use('fivethirtyeight')

    # Buffers for plotting
    x_vals, emg_vals_graph, ecg_vals_graph, eda_vals_graph = [], [], [], []
    selected_indices = [i for i, v in enumerate(channel) if v]

    # Wait until signal arrays have accumulated enough data to display
    while True:
        if any(len(arr) > 1000 for arr in [emg_vals, ecg_vals, eda_vals]):
            ready_event.set()
            break

    # Adjust graphing parameters based on sampling rate
    if samplingRate == 10:
        num_data_to_graph, window_size, inter = 10, 15, 1000
    elif samplingRate == 100:
        num_data_to_graph, window_size, inter = 100, 150, 1000
    else:
        num_data_to_graph, window_size, inter = 1000, 1500, 750

    start_time = time.time()
    starting = 0

    # Setup one or multiple subplots depending on channels enabled
    if len(selected_indices) == 1:
        fig, ax = plt.subplots()
        lines = [ax.plot([], [])[0]]
    else:
        fig, axs = plt.subplots(len(selected_indices))
        lines = [ax.plot([], [])[0] for ax in axs]

    def animate(i):
        """Frame update function for FuncAnimation."""
        nonlocal starting

        # Stop animation when duration elapsed
        if time.time() - start_time >= duration:
            print(f"Graphing duration reached {duration}s")
            ani.event_source.stop()
            plt.close()
            sys.exit()

        # Append newest samples for each enabled channel
        for _ in range(num_data_to_graph):
            try:
                if channel[0]:
                    emg_vals_graph.append(emg_vals[starting])
                if channel[1]:
                    ecg_vals_graph.append(ecg_vals[starting])
                if channel[2]:
                    eda_vals_graph.append(eda_vals[starting])
                x_vals.append(starting / samplingRate)
                starting += 1
            except:
                continue

            # Keep a rolling window of data
            if len(x_vals) > window_size:
                x_vals.pop(0)
                if channel[0]: emg_vals_graph.pop(0)
                if channel[1]: ecg_vals_graph.pop(0)
                if channel[2]: eda_vals_graph.pop(0)

        # Update each subplot
        for idx, line in zip(selected_indices, lines):
            y_data = [emg_vals_graph, ecg_vals_graph, eda_vals_graph][idx]
            line.set_data(x_vals, y_data)
            line.axes.relim()
            line.axes.autoscale_view()

    ani = FuncAnimation(fig, animate, frames=60, interval=inter)
    plt.tight_layout()
    plt.show()


# -------------------------- SEQUENCE RUNNERS --------------------------
def run_baseline_sequence(samplingRate: int, duration: int, macAddress: str, filename: str, channel=[True, True, True]):
    """
    Run baseline sequence:
    - Connects to BITalino
    - Collects EMG/ECG/EDA data
    - Displays live graph
    - Saves results to both text and Excel files
    """
    global device
    filename = 'Patient Records/' + filename

    # Attempt Bluetooth connection with retries
    for i in range(5):
        try:
            device = BITalino(macAddress)
            break
        except Exception as e:
            print("Connection failed, retrying:", e)
            if i == 4:
                print("Failed to connect after 5 attempts.")
                return -1

    with multi.Manager() as manager:
        emg_vals, ecg_vals, eda_vals = manager.list(), manager.list(), manager.list()
        ready_event = multi.Event()

        try:
            set_computer_volume(50)
            sound.tts("Baseline Collection sequence starts in. 3, 2, 1 ", 150)

            # Create data collection thread and graphing process
            signal_thread = threading.Thread(target=grab_signal, args=(samplingRate, duration, emg_vals, ecg_vals, eda_vals, channel))
            graphing_process = multi.Process(target=live_graphing, args=(ready_event, samplingRate, emg_vals, ecg_vals, eda_vals, channel, duration))

            graphing_process.start()
            signal_thread.start()
            ready_event.wait()  # Wait until graph is ready
            graphing_process.join()
            signal_thread.join()
        except Exception as e:
            print("Error during baseline:", e)
            return -1

        sound.tts("Baseline Collection sequence complete. Saving Results Now. Please wait", 150)
        save_to_txt_file('baseline_sequence.txt', emg_vals, ecg_vals, eda_vals)
        save_to_patients_excel_file(True, filename, emg_vals, ecg_vals, eda_vals)
        sound.tts("Results have been saved", 150)


def run_test_sequence(samplingRate: int, duration: int, macAddress: str, db_volume: int,
                      audio_frequency, filename: str, time_interval, di, channel=[True, True, True]):
    """
    Run hearing test sequence:
    - Plays sound stimuli while collecting BITalino signals
    - Displays live biofeedback
    - Saves test data and runs analysis (procResult)
    """
    global device
    filename = 'Patient Records/' + filename

    # Retry connection with BITalino up to 5 times
    for i in range(5):
        try:
            device = BITalino(macAddress)
            break
        except Exception as e:
            print("Connection attempt failed:", e)
            if i == 4:
                print("Could not connect after 5 tries")
                return -1

    with multi.Manager() as manager:
        emg_vals, ecg_vals, eda_vals = manager.list(), manager.list(), manager.list()
        ready_event = multi.Event()

        try:
            set_computer_volume(50)
            sound.tts("Sounds Sense hearing test starts in. 3, 2, 1 ", 150)

            # Create threads for sound + signal, process for graph
            sound_thread = threading.Thread(target=play_sound, args=(duration, audio_frequency, time_interval, di, db_volume))
            signal_thread = threading.Thread(target=grab_signal, args=(samplingRate, duration, emg_vals, ecg_vals, eda_vals, channel))
            graphing_process = multi.Process(target=live_graphing, args=(ready_event, samplingRate, emg_vals, ecg_vals, eda_vals, channel, duration))

            graphing_process.start()
            signal_thread.start()
            ready_event.wait()
            sound_thread.start()

            graphing_process.join()
            sound_thread.join()
            signal_thread.join()
        except:
            return -1

        sound.tts("Sound Sense hearing test complete. Saving Results Now. Please wait", 150)
        save_to_txt_file('test_sequence.txt', emg_vals, ecg_vals, eda_vals)
        save_to_patients_excel_file(False, filename, emg_vals, ecg_vals, eda_vals)
        sound.tts("Results have been saved", 150)

    # Run post-processing analysis
    procResult.main(filename, channel, samplingRate)

    # Clean up temporary files
    os.remove('test_sequence.txt')
    os.remove('baseline_sequence.txt')


# -------------------------- TESTING BLOCK --------------------------
if __name__ == "__main__":
    """
    Example run configuration for debugging or standalone testing.
    """
    samplingRate = 1000     # Samples per second (Hz)
    duration = 15           # Duration of test (s)
    mac_address = "98:D3:61:FD:6D:36"
    db_volume = -30
    audio_frequency = 1000  # Hz or filename if str
    filename = ""
    time_interval = 15
    di = 5
    channels = [True, True, False]

    run_test_sequence(samplingRate, duration, mac_address, db_volume, audio_frequency, filename, time_interval, di, channels)
