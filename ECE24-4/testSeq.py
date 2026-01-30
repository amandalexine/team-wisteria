import threading
import pygame
import time
from bitalino import BITalino
import os
import multiprocessing as multi
import sys
# from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
# from comtypes import CLSCTX_ALL
import hearingTest as sound # Kyle's code
import openpyxl
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import procFuncs as proc
import procResult
from esp32Device import Device

# Global variables
device = 0

# Saves the EMG, ECG, EDA signals in a TXT file
def save_to_txt_file(txt_name, emg, ecg, eda):
    """
    Save EMG, ECG, and EDA signal data to a text file.

    Parameters
    ----------
    txt_name : str
        Path or filename of the output text file.
    emg : list
        List of EMG signal values.
    ecg : list
        List of ECG signal values.
    eda : list
        List of EDA signal values.

    Returns
    -------
    None
        Writes data directly to a file. Each line contains comma-separated EMG, ECG, and EDA values.

    Side Effects
    -------------
    Creates or overwrites a text file on disk.
    """

    # init as 0
    data1, data2, data3 = 0,0,0

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
    Save signal data (EMG, ECG, EDA) to a patient's Excel file.

    Parameters
    ----------
    baseline : bool
        True if writing to baseline data sheet; False for test data sheet.
    filename : str
        Path to the Excel file to update.
    emg, ecg, eda : list
        Lists containing EMG, ECG, and EDA samples.

    Returns
    -------
    None
        Writes values into Excel workbook.

    Side Effects
    -------------
    Updates and saves an Excel workbook using openpyxl.
    """

    # Write data to excel file
    print(f'in save_to_patients_excel_file: {filename}')
    workbook = openpyxl.load_workbook(filename)

    data = [emg, ecg, eda]

    if baseline:
        sheet_name = 'Baseline Data'
    else:
        sheet_name = 'Test Data'

    sheet = workbook[sheet_name]

    # write in data (EMG, ECG, EDA) by column
    for column in range(3):
        for row_num, value in enumerate(data[column], start=2):
            sheet.cell(row=row_num, column=column + 1).value = value

    # Save workbook with a new name or overwrite the existing one
    workbook.save(filename)

# def set_computer_volume(percentage):
#     """
#     Adjust system master volume using Windows audio API.

#     Parameters
#     ----------
#     percentage : float
#         Volume level as a percentage (0-100).

#     Returns
#     -------
#     None

#     Side Effects
#     -------------
#     Changes the master output volume of the host computer.
#     """

#     devices = AudioUtilities.GetSpeakers()
#     interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
#     volume = interface.QueryInterface(IAudioEndpointVolume)

#     # Volume is set as a scalar between 0.0 and 1.0 (0% to 100%)
#     volume.SetMasterVolumeLevelScalar(percentage/100, None)  # Set volume to a percentage

# def play_wavefile(sound, duration):
#     """
#     Play a WAV sound file for a fixed duration.

#     Parameters
#     ----------
#     sound : pygame.mixer.Sound
#         Preloaded sound object to play.
#     duration : float
#         Playback duration in seconds.

#     Returns
#     -------
#     None
#     """

#     start_time = time.time()

#     while(1):
#         sound.play()
#         time.sleep(1)
#         sound.stop()

#         # end at the specified duration
#         if time.time() - start_time > duration:
#             sound.stop()
#             break

import platform
import subprocess

def set_computer_volume(percentage: float) -> bool:
    """
    Cross-platform: set the system master volume.

    Parameters
    ----------
    percentage : float
        Volume level as a percentage (0-100).

    Returns
    -------
    bool
        True if the operation likely succeeded, False if it failed or couldn't be performed.
    """
    # clamp to 0..100
    try:
        pct = max(0.0, min(100.0, float(percentage)))
    except Exception:
        print(f"set_computer_volume: invalid percentage {percentage}")
        return False

    system = platform.system()
    if system == "Windows":
        try:
            # import here to avoid import errors on non-Windows systems
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            # use the pycaw API to set master volume scalar (0.0 - 1.0)
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            volume.SetMasterVolumeLevelScalar(pct / 100.0, None)
            return True
        except Exception as e:
            print("set_computer_volume (Windows): failed to set volume via pycaw:", e)
            print(" - Ensure 'pycaw' and 'comtypes' are installed and you're on Windows.")
            return False

    elif system == "Linux":
        # Try amixer (ALSA). Many distros have it as part of alsa-utils.
        try:
            # Some systems expect 'Master' control; others use 'PCM' or different names.
            # We'll try 'Master' first, fallback to 'PCM' if needed.
            cmd = ["amixer", "sset", "Master", f"{int(round(pct))}%"]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode == 0:
                return True
            # fallback
            cmd2 = ["amixer", "sset", "PCM", f"{int(round(pct))}%"]
            proc2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc2.returncode == 0:
                return True
            print("set_computer_volume (Linux): amixer returned non-zero exit code.")
            print("stdout:", proc.stdout.decode('utf-8', errors='ignore'))
            print("stderr:", proc.stderr.decode('utf-8', errors='ignore'))
            return False
        except FileNotFoundError:
            print("set_computer_volume (Linux): 'amixer' not found. Install alsa-utils or use PulseAudio tools.")
            return False
        except Exception as e:
            print("set_computer_volume (Linux): unexpected error:", e)
            return False

    elif system == "Darwin":  # macOS
        try:
            # macOS 'osascript' sets output volume as integer 0..100
            cmd = ["osascript", "-e", f"set volume output volume {int(round(pct))}"]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode == 0:
                return True
            else:
                print("set_computer_volume (macOS) failed; osascript exit code:", proc.returncode)
                return False
        except FileNotFoundError:
            print("set_computer_volume (macOS): 'osascript' not found (very unusual).")
            return False
        except Exception as e:
            print("set_computer_volume (macOS): unexpected error:", e)
            return False

    else:
        print(f"set_computer_volume: Unsupported OS '{system}'. Cannot set system volume.")
        return False


def play_sound(duration, frequency, interval, di, final_volume_db=-30):
    """
    Generate or play sound with incremental volume changes.

    Parameters
    ----------
    duration : float
        Total duration of playback (s).
    frequency : int or str
        Frequency (Hz) for generated tone or filename for .wav playback.
    interval : float
        Interval between volume increases (s).
    di : float
        dB increment at each step.
    final_volume_db : float, optional
        Starting decibel level (default -30 dB).

    Returns
    -------
    None
    """

    number_of_db_increases = int(duration/interval)

    if type(frequency) == str: # Play .wav file
        pygame.init()
        pygame.mixer.init()
        wav_sound = pygame.mixer.Sound('audio_files/' + frequency)
        for i in range(number_of_db_increases):
            play_wavefile(wav_sound, interval)
            final_volume_db += di # Increases by a certain db

    else:
        # ----------------------START SOUND GENERATION----------------------
        for i in range(number_of_db_increases):
            sound.play_for_time(interval, final_volume_db, frequency)
            final_volume_db += di # Increases by a certain db
        # --------------------------------------------------------------------

def grab_signal(samplingRate:int, duration:int, emg_vals, ecg_vals, eda_vals, channel = [True, True, True]):
    """
    Acquire EMG, ECG, and EDA signals from a connected BITalino or ESP32 device.

    Parameters
    ----------
    samplingRate : int
        Sampling rate in Hz.
    duration : int
        Duration of acquisition in seconds.
    emg_vals, ecg_vals, eda_vals : multiprocessing.Manager().list
        Shared lists to store sampled data.
    channel : list of bool
        Enables or disables each channel [EMG, ECG, EDA].

    Returns
    -------
    None
    """

    device.start(samplingRate, [0,1,2,3,4,5])
    start_time = time.time()
    
    # grad data for specified duration of test
    while (time.time() - start_time) < duration:
        data = device.read(samplingRate) # <--- Returns n samples in one second (n = samplingRate)
        for i in data:
            # if the channel is enabled, add in data, if not use 1 as a placeholder
            if channel[0] == True:
                emg_vals.append(i[5])
            if channel[1] == True:
                ecg_vals.append(i[6])
            if channel[2] == True:
                eda_vals.append(i[7])
            if channel[0] == False:
                emg_vals.append(1)
            if channel[1] == False:
                ecg_vals.append(1)
            if channel[2] == False:
                eda_vals.append(1)            
 

    print(time.time()-start_time)
    # Stop acquisition
    device.stop()

    # Close the connection
    device.close()

def live_graphing(ready_event, samplingRate, emg_vals, ecg_vals, eda_vals, channel, duration):
    """
    Display real-time graphing of signals using Matplotlib animation.

    Parameters
    ----------
    ready_event : multiprocessing.Event
        Event flag signaling readiness to start graphing.
    samplingRate : int
        Sampling rate in Hz.
    emg_vals, ecg_vals, eda_vals : multiprocessing.Manager().list
        Shared data arrays for EMG, ECG, and EDA.
    channel : list of bool
        Indicates which channels are enabled.
    duration : float
        Total graphing duration in seconds.

    Returns
    -------
    None
    """

    plt.style.use('fivethirtyeight')

    x_vals = []
    emg_vals_graph = []
    ecg_vals_graph = []
    eda_vals_graph = []
    selected_indices = []

    for index, value in enumerate(channel):
        if value == True:
            selected_indices.append(index)

    # wait until populated with data
    while(1):
        if (len(emg_vals) > 100) or (len(ecg_vals) > 100) or (len(eda_vals) > 100):
            ready_event.set() # Tell other processes that graphing has started
            break  
    
    # THESE ARE SUBJECT TO CHANGE BASED ON COMPUTERS ABILITY
    if samplingRate == 10:
        num_data_to_graph = 10
        window_size = 15
        inter = 1000
    elif samplingRate == 100:
        num_data_to_graph = 100
        window_size = 150
        inter = 1000
    elif samplingRate == 130:
        num_data_to_graph = 130
        window_size = 100
        inter = 1000
    else:
        num_data_to_graph = 1000 # Needs adjusting
        window_size = 1500
        inter = 750
        '''
        num_data_to_graph = 30
        window_size = 1500
        inter = 1
        '''
    
    num_data_to_graph = samplingRate
    start_time = time.time()
    starting = 0
    
    if len(selected_indices) == 1:
        fig, ax = plt.subplots()
        line = ax.plot([], [])[0]  # Create a line for the subplot ax
        lines = [line]  # Create a list containing only the line
    else:
        # Creating subplots based on user's selection
        fig, axs = plt.subplots(len(selected_indices))
        lines = []
        for ax in axs:
            line = ax.plot([], [])[0]  # Create a line for the current subplot ax
            lines.append(line)  # Append the created line to the list of lines

    def animate(i):
        # stop if duration is up
        if(time.time() - start_time) >= duration:
            print(f'Time: {time.time()-start_time}')
            ani.event_source.stop()
            plt.close()
            sys.exit()
            return

        nonlocal starting, ax
        for i in range(starting, starting + num_data_to_graph):
            try: 
                if channel[0] == True:
                    emg_vals_graph.append(emg_vals[i])
                if channel[1] == True:
                    ecg_vals_graph.append(ecg_vals[i])
                if channel[2] == True:
                    eda_vals_graph.append(eda_vals[i])
            except Exception as e:
                # make sure all arrays are the same size before conitnuing to next itteration (some might've been added to before error was thrown)
                if (channel[0] == True) and (len(emg_vals_graph) > len(x_vals)):
                    emg_vals_graph.pop() # pop the last element
                if (channel[1] == True) and (len(ecg_vals_graph) > len(x_vals)):
                    ecg_vals_graph.pop() # pop the last element
                if (channel[2] == True) and (len(eda_vals_graph) > len(x_vals)):
                    eda_vals_graph.pop() # pop the last element
                continue
            
            x_vals.append(starting / samplingRate)
            starting += 1
            
            # Maintain a moving window of values for live plotting
            if len(x_vals) > window_size:
                x_vals.pop(0)
                if channel[0] == True: 
                    emg_vals_graph.pop(0)
                if channel[1] == True:
                    ecg_vals_graph.pop(0)
                if channel[2] == True:
                    eda_vals_graph.pop(0)

        if len(selected_indices) == 1:
            idx = selected_indices[0]
            line = lines[0]
            ax = ax  # Assuming you don't need to update ax in this case

            if idx == 0:
                line.set_data(x_vals, emg_vals_graph)
            elif idx == 1:
                line.set_data(x_vals, ecg_vals_graph)  
            elif idx == 2:
                line.set_data(x_vals, eda_vals_graph) 
                
            ax.relim()
            ax.autoscale_view()
        else:
            for idx, line, ax in zip(selected_indices, lines, axs):
                if idx == 0:
                    line.set_data(x_vals, emg_vals_graph)
                elif idx == 1:
                    line.set_data(x_vals, ecg_vals_graph)  
                elif idx == 2:
                    line.set_data(x_vals, eda_vals_graph) 
                
                try:
                    ax.relim()
                    ax.autoscale_view()
                except:
                    print(len(x_vals), len(emg_vals_graph), len(ecg_vals_graph), len(eda_vals_graph))

    ani = FuncAnimation(fig, animate, frames=60, interval=inter)
    plt.tight_layout()
    plt.show()

def run_baseline_sequence_ESP32(filepath:str, filename:str, recording_info, controller):
    """
    Run the baseline signal collection sequence using an ESP32 device (Fern box).

    Parameters
    ----------
    filepath : str
        Directory path for saving results.
    filename : str
        Patient Excel filename.
    recording_info : dict
        Configuration including sample rate, duration, audio, and channel info.
    controller : object
        GUI controller with page frame references.

    Returns
    -------
    int
        -1 if failure occurs, else None on success.
    """
    
    global device

    filename = filepath + filename

    # get parameters for the test
    macAddress = recording_info["macAddress"]
    sample_rate = recording_info["sample_rate"]
    print(f"Sampling rate: {sample_rate}")
    duration = recording_info["duration"]
    audio_option = recording_info["audio_option"]
    time_option = recording_info["time_option"]
    di_option = recording_info["di_option"]
    signals = recording_info["signals"]

    device = Device()

    # Establish array values for multiprocessing
    with multi.Manager() as manager:
        emg_vals = manager.list()
        ecg_vals = manager.list()
        eda_vals = manager.list()

        ready_event = multi.Event()
    
        # Ensure no errors are thrown during the baseline sequence
        try:
            set_computer_volume(50) # takes in a percentage to change the volume on physical computer

            signal_thread = threading.Thread(target=device.collect_data, args=(sample_rate, duration, emg_vals, ecg_vals, eda_vals, signals,
                                                                                       controller, "Baseline Collection sequence starts in. 3, 2, 1 "))
            graphing_process = multi.Process(target=live_graphing,args=(ready_event, sample_rate, emg_vals, ecg_vals, eda_vals, signals, duration))

            # Starts all threads/proccess
            graphing_process.start()
            signal_thread.start()
            ready_event.wait() # wait till process loads
            
            # Wait for threads/subprocess to finish
            graphing_process.join()
            signal_thread.join()
        except Exception as e:
            print(e)
            return -1

        
        # Notify user baseline collection finished
        sound.tts("Baseline Collection sequence complete. Saving Results Now. Please wait", 150)
        device.stop()

        controller.frames["LoadingPage"].set_load_title("Saving Results...")

        # Save info to text file (needed for Max's code)
        save_to_txt_file('baseline_sequence.txt', emg_vals, ecg_vals, eda_vals)

        # Save results to patients excel file
        save_to_patients_excel_file(True, filename, emg_vals, ecg_vals, eda_vals)
        sound.tts("Results have been saved", 150)


def run_test_sequence_ESP32(filepath, filename, db_volume, recording_info, controller):
    """
    Execute test sequence using ESP32 device (fern box).

    Parameters
    ----------
    filepath, filename : str
        Filepath and patient file for saving results.
    db_volume : float
        Initial playback volume in decibels.
    recording_info : dict
        Test configuration (duration, audio, timing, etc.).
    controller : object
        GUI controller for status display.

    Returns
    -------
    int
        -1 on error, otherwise None.
    """

    global device

    # get test parameters
    macAddress = recording_info["macAddress"]
    sample_rate = recording_info["sample_rate"]
    duration = recording_info["duration"]
    audio_option = recording_info["audio_option"]
    time_option = recording_info["time_option"]
    di_option = recording_info["di_option"]
    signals = recording_info["signals"]


    filename = filepath + filename

    with multi.Manager() as manager:
        emg_vals = manager.list()
        ecg_vals = manager.list()
        eda_vals = manager.list()

        ready_event = multi.Event()
    
        try:
            set_computer_volume(50) # takes in a percentage to change the volume on physical computer

            # Create one thread and one subprocesses
            sound_thread = threading.Thread(target=play_sound, args=(duration, audio_option, time_option, di_option, db_volume))
            signal_thread = threading.Thread(target=device.collect_data, args=(sample_rate, duration, emg_vals, ecg_vals, eda_vals, signals,
                                                                                controller, "Sounds Sense hearing test starts in. 3, 2, 1 "))
            graphing_process = multi.Process(target=live_graphing,args=(ready_event, sample_rate, emg_vals, ecg_vals, eda_vals, signals, duration))

            # Starts all threads/proccess
            graphing_process.start()
            signal_thread.start()
            ready_event.wait() # wait till process loads
            sound_thread.start()
            
            # Wait for threads/subprocess to finish
            graphing_process.join()
            signal_thread.join()
            sound_thread.join()
        except Exception as e:
            print(e)
            return -1

        # Notify user Test Sequnce finished
        sound.tts("Sound Sense hearing test complete. Saving Results Now. Please wait", 150)
        device.stop()

        controller.frames["LoadingPage"].set_load_title("Saving Results...")

        # Save info to text file (needed for Max's code)
        save_to_txt_file('test_sequence.txt', emg_vals, ecg_vals, eda_vals)

        # Save results to patients excel file
        save_to_patients_excel_file(False, filename, emg_vals, ecg_vals, eda_vals)
        # sound.tts("Results have been saved", 150)
        controller.frames["LoadingPage"].set_load_title("Please Wait...")
    
    # Run analysis on code
    procResult2.main(filename,signals,sample_rate, controller)

    # Delete text files
    os.remove('test_sequence.txt')
    os.remove('baseline_sequence.txt')


def run_baseline_sequence_bitalino(filepath:str, filename:str, recording_info, controller):
    """
    Collect baseline signals using a BITalino

    Parameters
    ----------
    filepath, filename : str
        Output directory and file for saving data.
    recording_info : dict
        Contains sample rate, duration, and signal enable info.
    controller : object
        GUI controller instance.

    Returns
    -------
    int
        -1 if device connection fails or error occurs.
    """

    global device

    filename = filepath + filename

    # get test parameters
    macAddress = recording_info["macAddress"]
    sample_rate = recording_info["sample_rate"]
    duration = recording_info["duration"]
    audio_option = recording_info["audio_option"]
    time_option = recording_info["time_option"]
    di_option = recording_info["di_option"]
    signals = recording_info["signals"]

    # Attempt to connect with device
    for i in range(5):
        print(i)
        try:
            device = BITalino(macAddress)
            break
        except Exception as e:
            sound.tts("Couldn't connect to device. Trying again.", 150)
            time.sleep(2)
            print("Trying again")
            print(e)
        if i == 4:
            sound.tts("Couldn't connect to device after 5 tries.", 150)
            print("Couldnt connect after 5 tries")
            return -1

    sound.tts("Connected to device.", 150)
    # Establish array values for multiprocessing
    with multi.Manager() as manager:
        emg_vals = manager.list()
        ecg_vals = manager.list()
        eda_vals = manager.list()

        ready_event = multi.Event()
    
        # Ensure no errors are thrown during the baseline sequence
        try:
            set_computer_volume(50) # takes in a percentage to change the volume on physical computer
            # Start the countdown (from Kyle's code)
            sound.tts("Baseline Collection sequence starts in. 3, 2, 1 ", 150)

            controller.frames["LoadingPage"].set_load_title("Collecting data...")
            # Create one thread and one subprocesses
            signal_thread = threading.Thread(target=grab_signal, args=(sample_rate, duration, emg_vals, ecg_vals, eda_vals, signals))
            graphing_process = multi.Process(target=live_graphing,args=(ready_event, sample_rate, emg_vals, ecg_vals, eda_vals, signals, duration))

            # Starts all threads/proccess
            graphing_process.start()
            signal_thread.start()
            ready_event.wait() # wait till process loads
            
            # Wait for threads/subprocess to finish
            graphing_process.join()
            signal_thread.join()
        except Exception as e:
            print(e)
            return -1

        
        # Notify user baseline collection finished
        sound.tts("Baseline Collection sequence complete. Saving Results Now. Please wait", 150)

        controller.frames["LoadingPage"].set_load_title("Saving Results...")

        converted_emg_vals = proc.convert_raw_emg(emg_vals)
        converted_ecg_vals = proc.convert_raw_ecg(ecg_vals)
        converted_eda_vals = proc.convert_raw_eda(eda_vals)     

        # Save info to text file (needed for Max's code)
        # save_to_txt_file('baseline_sequence.txt', emg_vals, ecg_vals, eda_vals)
        save_to_txt_file('baseline_sequence.txt', converted_emg_vals, converted_ecg_vals, converted_eda_vals)
        

        # Save results to patients excel file
        save_to_patients_excel_file(True, filename, converted_emg_vals, converted_ecg_vals, eda_vals)
        sound.tts("Results have been saved", 150)
        
        

def run_test_sequence_bitalino(filepath, filename, db_volume, recording_info, controller):
    """
    Run test sequence with BITalino device and audio/ frequency playing.

    Parameters
    ----------
    filepath, filename : str
        Output directory and file for saving results.
    db_volume : float
        Starting playback volume in dB.
    recording_info : dict
        Test configuration parameters.
    controller : object
        GUI controller reference.

    Returns
    -------
    int
        -1 on failure; None on success.
    """

    global device

    # get test parameters
    macAddress = recording_info["macAddress"]
    sample_rate = recording_info["sample_rate"]
    duration = recording_info["duration"]
    audio_option = recording_info["audio_option"]
    time_option = recording_info["time_option"]
    di_option = recording_info["di_option"]
    signals = recording_info["signals"]

    filename = filepath + filename
    # Attempt to connect with device
    for i in range(5):
        try:
            device = BITalino(macAddress)
            break
        except Exception as e:
            print("Trying again")
            print(e)
            
        if i == 4:
            print("Couldnt connect after 5 tries")
            return -1
    

    # Establish array values for multiprocessing
    with multi.Manager() as manager:
        emg_vals = manager.list()
        ecg_vals = manager.list()
        eda_vals = manager.list()

        ready_event = multi.Event()

        # Ensure no errors are thrown during the test sequence
        try:
            set_computer_volume(50) # takes in a percentage to change the volume on physical computer
            # Start the countdown (from Kyle's code)
            sound.tts("Sounds Sense hearing test starts in. 3, 2, 1 ", 150)
            controller.frames["LoadingPage"].set_load_title("Collecting data...")

            # Create two threads and one subprocesses
            sound_thread = threading.Thread(target=play_sound, args=(duration, audio_option, time_option, di_option, db_volume))
            signal_thread = threading.Thread(target=grab_signal, args=(sample_rate, duration, emg_vals, ecg_vals, eda_vals, signals))
            graphing_process = multi.Process(target=live_graphing,args=(ready_event, sample_rate, emg_vals, ecg_vals, eda_vals, signals, duration))
            
            # Starts all threads/proccess
            graphing_process.start()
            signal_thread.start()
            ready_event.wait() # wait till process loads
            sound_thread.start()
                
            # Wait for threads/subprocess to finish
            graphing_process.join()
            sound_thread.join()
            signal_thread.join()
        except:
            return -1

        # Notify user Test Sequnce finished
        sound.tts("Sound Sense hearing test complete. Saving Results Now. Please wait", 150)

        controller.frames["LoadingPage"].set_load_title("Saving Results...")

        converted_emg_vals = proc.convert_raw_emg(emg_vals)
        converted_ecg_vals = proc.convert_raw_ecg(ecg_vals)
        converted_eda_vals = proc.convert_raw_eda(eda_vals)     

        # Save info to text file (needed for Max's code)
        # save_to_txt_file('test_sequence.txt', emg_vals, ecg_vals, eda_vals)
        save_to_txt_file('test_sequence.txt', converted_emg_vals, converted_ecg_vals, converted_eda_vals)

        # Save results to patients excel file
        save_to_patients_excel_file(False, filename, converted_emg_vals, converted_ecg_vals, converted_eda_vals)
        # sound.tts("Results have been saved", 150)
        controller.frames["LoadingPage"].set_load_title("Please Wait...")
    
    # Run analysis on code
    procResult2.main(filename,signals,sample_rate, controller)

    # Delete text files
    os.remove('test_sequence.txt')
    os.remove('baseline_sequence.txt')



# TESTING BLOCK
# this isn't an actual main, it's just for testing this script by itslef
if __name__ == "__main__":
    # TEST SIGNAL GRAB FUNCTION.
    # code here runs only when the file is executed directly, not when imported
    samplingRate = 1000 # <--- Amount of samples collected per seconed (Hz)
    duration = 15 # <--- How long the test will be ran for 
    mac_address = "98:D3:61:FD:6D:36"
    # mac_address = "98:D3:A1:FD:67:36"
    db_volume = -30
    audio_frequency = 1000
    filename = ""
    time_interval = 15
    di = 5
    channels = [True, True, False]


    run_test_sequence_bitalino(samplingRate,duration,mac_address,db_volume,audio_frequency,filename,time_interval,5,channels)

