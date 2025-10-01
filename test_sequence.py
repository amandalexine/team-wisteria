import threading
import pygame
import time
from bitalino import BITalino
import os
import multiprocessing as multi
import sys
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import hearing_test as sound # Kyle's code
import openpyxl
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import procResult

# Global variables
device = 0


def save_to_txt_file(txt_name, emg, ecg, eda):
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
    # Write data to excel file
    workbook = openpyxl.load_workbook(filename)

    data = [emg, ecg, eda]

    if baseline:
        sheet_name = 'Baseline Data'
    else:
        sheet_name = 'Test Data'

    sheet = workbook[sheet_name]

    for column in range(3):
        for row_num, value in enumerate(data[column], start=2):
            sheet.cell(row=row_num, column=column + 1).value = value

    # Save workbook with a new name or overwrite the existing one
    workbook.save(filename)

def set_computer_volume(percentage):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = interface.QueryInterface(IAudioEndpointVolume)

    # Volume is set as a scalar between 0.0 and 1.0 (0% to 100%)
    volume.SetMasterVolumeLevelScalar(percentage/100, None)  # Set volume to a percentage

def play_wavefile(sound, duration):
    start_time = time.time()

    while(1):
        sound.play()
        time.sleep(1)
        sound.stop()
        if time.time() - start_time > duration:
            sound.stop()
            break

def play_sound(duration, frequency, interval, di, final_volume_db=-30):
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
    device.start(samplingRate, [0,1,2,3,4,5])
    start_time = time.time()
    
    while (time.time() - start_time) < duration:
        data = device.read(samplingRate) # <--- Returns n samples in one second (n = samplingRate)
        for i in data:
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
            # if channel[0] == False:
            #     emg_vals.append(i[5])
            # if channel[1] == False:
            #     ecg_vals.append(i[6])
            # if channel[2] == False:
            #     eda_vals.append(i[7])
            
                

    print(time.time()-start_time)
    # Stop acquisition
    device.stop()

    # Close the connection
    device.close()

def live_graphing(ready_event, samplingRate, emg_vals, ecg_vals, eda_vals, channel, duration):
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
        if (len(emg_vals) > 1000) or (len(ecg_vals) > 1000) or (len(eda_vals) > 1000):
            ready_event.set()
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
    else:
        num_data_to_graph = 1000 # Needs adjusting
        window_size = 1500
        inter = 750
        '''
        num_data_to_graph = 30
        window_size = 1500
        inter = 1
        '''
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

def run_baseline_sequence(samplingRate:int, duration:int, macAddress:str, filename:str, channel = [True, True, True]):
    global device

    filename = 'Patient Records/'+ filename

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
    
        # Ensure no errors are thrown during the baseline sequence
        try:
            set_computer_volume(50) # takes in a percentage to change the volume on physical computer
            # Start the countdown (from Kyle's code)
            sound.tts("Baseline Collection sequence starts in. 3, 2, 1 ", 150)

            # Create one thread and one subprocesses
            signal_thread = threading.Thread(target=grab_signal, args=(samplingRate, duration, emg_vals, ecg_vals, eda_vals, channel))
            graphing_process = multi.Process(target=live_graphing,args=(ready_event, samplingRate, emg_vals, ecg_vals, eda_vals, channel, duration))
            
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

        # Save info to text file (needed for Max's code)
        save_to_txt_file('baseline_sequence.txt', emg_vals, ecg_vals, eda_vals)

        # Save results to patients excel file
        save_to_patients_excel_file(True, filename, emg_vals, ecg_vals, eda_vals)
        sound.tts("Results have been saved", 150)

def run_test_sequence(samplingRate:int, duration:int, macAddress:str, db_volume:int, audio_frequency, filename:str, time_interval, di, channel = [True, True, True]):
    global device

    filename = 'Patient Records/'+ filename

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

            # Create two threads and one subprocesses
            sound_thread = threading.Thread(target=play_sound, args=(duration, audio_frequency, time_interval, di, db_volume))
            signal_thread = threading.Thread(target=grab_signal, args=(samplingRate, duration, emg_vals, ecg_vals, eda_vals, channel))
            graphing_process = multi.Process(target=live_graphing,args=(ready_event, samplingRate, emg_vals, ecg_vals, eda_vals, channel, duration))
            
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

        # Save info to text file (needed for Max's code)
        save_to_txt_file('test_sequence.txt', emg_vals, ecg_vals, eda_vals)

        # Save results to patients excel file
        save_to_patients_excel_file(False, filename, emg_vals, ecg_vals, eda_vals)
        sound.tts("Results have been saved", 150)
    
    # Run analysis on code
    procResult.main(filename,channel,samplingRate)

    # Delete text files
    os.remove('test_sequence.txt')
    os.remove('baseline_sequence.txt')


# TESTING BLOCK
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
    run_test_sequence(samplingRate,duration,mac_address,db_volume,audio_frequency,filename,time_interval,5,channels)

