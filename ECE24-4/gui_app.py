import tkinter as tk
from tkinter import ttk
from ttkbootstrap import Style
import os
import numpy as np
import customtkinter as ctk
import ctypes
from itertools import cycle
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from PIL import Image, ImageTk

from RecordingFuncs import *

device_option = "BITalino"
recording_info = {}
 
ctypes.windll.shcore.SetProcessDpiAwareness(1)

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Noise Sensitivity Test")
        self.state('zoomed')
        self.iconbitmap('Utilities/ss_logo.ico')

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frames = {} 

        page_name = ErrorPage.__name__
        frame = ErrorPage(parent=self, controller=self)
        self.frames[page_name] = frame
        frame.grid(row=0, column=0, sticky="nsew")

        if check_utilities() == -1:
            self.frames['ErrorPage'].set_error_message("Check that all utilities are present, including logos and images")
            self.show_frame("ErrorPage")
        else:
            # Create all of the pages
            for F in (StartPage, DeviceConnectionPage, VolumePage, ParameterPage, InstructionsPage, TestPrepPage, LoadingPage, StartTestPage, ResultsPage, ShapPage, GraphPage, StatsResultsPage):
                page_name = F.__name__
                frame = F(parent=self, controller=self)
                self.frames[page_name] = frame
                frame.grid(row=0, column=0, sticky="nsew")

            self.show_frame("StartPage")

    def show_frame(self, page_name):

        frame = self.frames[page_name]
        frame.focus_set()
        frame.tkraise()

# Class for the error page
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

        message_label = ttk.Label(frame, text="An error has occurred, please restart the program.", font=("Calibri Light", 18, 'bold'), justify="center")
        message_label.grid(row=0, column=0, pady=10, sticky="s") 

        self.detailed_message = ttk.Label(frame, text="", font=("Calibri Light", 12), justify="center")
        self.detailed_message.grid(row=1, column=0, pady=10) 

        restart_button = ctk.CTkButton(frame, text="Exit Program", command=lambda: self.controller.destroy())
        restart_button.grid(row=2, column=0, pady=10, sticky="n") 

    # Set a detailed error message
    def set_error_message(self, title):
       self.detailed_message.config(text=title)


# Start page class
class StartPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=7, pady=7)


        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=0)
        frame.grid_rowconfigure(2, weight=0)
        frame.grid_rowconfigure(3, weight=0)
        frame.grid_rowconfigure(4, weight=0)
        frame.grid_rowconfigure(5, weight=0)
        frame.grid_rowconfigure(6, weight=1)
        frame.grid_columnconfigure(0, weight=1) 
        frame.grid_columnconfigure(1, weight=1) 
        frame.grid_columnconfigure(2, weight=1) 

        img_path = "Utilities/sound_sense_logo.png"
        img = tk.PhotoImage(file=img_path)
        img = img.subsample(2, 2)
                            
        img_label = ttk.Label(frame, image=img, anchor="center")
        img_label.image = img
        img_label.grid(row=0, column=0, columnspan=3, sticky="s") 

        
        required_label = ttk.Label(frame, text="*Required Information", font=("Calibri Light", 14))
        required_label.grid(row=1, column=0, columnspan=3, pady=15)

        name_label = ttk.Label(frame, text="Subject Reference Number *:", font=("Calibri Light", 14))
        name_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        name_entry = ttk.Entry(frame)
        name_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        age_label = ttk.Label(frame, text="Age:", font=("Calibri Light", 14))
        age_label.grid(row=3, column=0, padx=5, pady=5, sticky="e")
        age_entry = ttk.Entry(frame)
        age_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        contact_info_label = ttk.Label(frame, text="Contact Information:", font=("Calibri Light", 14))
        contact_info_label.grid(row=4, column=0, padx=5, pady=5, sticky="e")
        contact_info_entry = ttk.Entry(frame)
        contact_info_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        status_label = ttk.Label(frame, text="", anchor="center", font=("Calibri Light", 12) , foreground="red")
        status_label.grid(row=5, column=0, columnspan=3, pady=15)
    
        # Ensure user input is valid
        def validate_entries():
            if name_entry.get().strip():
                save_input(name_entry,age_entry,contact_info_entry,status_label)
                self.next_page()
            else:
                status_label.config(text="Subject Reference Number is required.", font=("Calibri Light", 14))
    
        next_button = ctk.CTkButton(frame, text="Next", command=lambda:validate_entries())
        next_button.grid(row=6, column=0, columnspan=3, pady=30, sticky="n")


    def next_page(self):
        self.controller.show_frame("DeviceConnectionPage")


# Device Connection Instruction Page Class
class DeviceConnectionPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(1, weight=0)
        self.frame.grid_rowconfigure(2, weight=0)
        self.frame.grid_rowconfigure(3, weight=0)
        self.frame.grid_rowconfigure(4, weight=0)
        self.frame.grid_rowconfigure(5, weight=1)

        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=0)
        self.frame.grid_columnconfigure(2, weight=1)

        # ---------- BANNER -----------
        banner = tk.Frame(self.frame, height=150)
        banner.config(bg='lightblue')
        banner.grid(row=0, column=0, columnspan=5, sticky='nsew', pady=(0, 20), padx=0)

        back_button = ctk.CTkButton(banner, text="⇦  Back", width=75, height=30, command=self.last_page)
        back_button.pack(side=tk.LEFT, padx=30, pady=10)

        instruction_title_label = tk.Label(banner, text="Connecting Device Instructions", font=("Calibri Light", 24, 'bold'), justify="center")
        instruction_title_label.config(bg='lightblue')
        instruction_title_label.pack(side=tk.LEFT, expand=True, fill="x", padx=30, pady=30)

        next_button = ctk.CTkButton(banner, text="Next  ⇨", width=75, height=30, command=self.next_page)
        next_button.pack(side=tk.RIGHT, padx=30, pady=10)

        instruction_subtitle_label = ttk.Label(self.frame, text="Please select the bioelectric signal recording device you would like to use. \nThe device's instructions will be displayed below.", font=("Calibri Light", 14), justify="center")
        instruction_subtitle_label.grid(row=1, column=0, pady=5, padx=10, sticky="ns", columnspan=3)

        instruction_subtitle_label2 = ttk.Label(self.frame, text="Press 'Next' when complete.", font=("Calibri Light", 14))
        instruction_subtitle_label2.grid(row=2, column=0, pady=5, padx=10, sticky="ns", columnspan=3)

        self.device_var = tk.StringVar(value="BITalino")
        selection_frame = ttk.Frame(self.frame)
        selection_frame.grid_columnconfigure(0, weight=1)
        selection_frame.grid_columnconfigure(2, weight=1)
        selection_frame.grid(row=3, column=1, pady=5, padx=10, sticky="nsew")
        bitalino_radio = ttk.Radiobutton(selection_frame, text="BITalino", variable=self.device_var,
                                         value="BITalino", command=self.update_instructions)
        bitalino_radio.grid(row=0, column=0, pady=5, padx=10, sticky="e")

        or_label = ttk.Label(selection_frame, text="OR", font=("Calibri Light", 14, 'bold'))
        or_label.grid(row=0, column=1, pady=5, padx=10)

        ESP32_radio = ttk.Radiobutton(selection_frame, text="Fern Bioelectric Box", variable=self.device_var,
                                      value="ESP32", command=self.update_instructions)
        ESP32_radio.grid(row=0, column=2, pady=5, padx=10, sticky="w")



        self.bitalino_frame = ttk.LabelFrame(self.frame, text="BITalino (r)evolution Board")
        self.bitalino_frame.grid(row=4, column=1, pady=10, padx=30, sticky="nsew")
        self.bitalino_frame.grid_columnconfigure(1, weight=1)
        self.bitalino_frame.grid_rowconfigure(3, weight=1)

        bitalino_title_label = ttk.Label(self.bitalino_frame, text="If using BITalino for Bioelectric Signal Collection:", font=("Calibri Light", 14))
        bitalino_title_label.grid(row=1, column=1, pady=10, padx=20, sticky="ns")

        bitalino_instruction_text = (
            "   1. Locate the BITalino (r)evolution Board as seen in the images below\n"
            "   2. Turn on BITalino by flipping the on/off switch on the device. Make sure the power light is on.\n"
            "         a. If light is off or blinking red, charge device using the charging port indicated below.\n"
            "   3. If this is your first time using the BITalino device:\n"
            "         a. Navigate to the computer's settings, and select 'Bluetooth & devices' → 'Add Device' → 'Bluetooth'\n"
            "         b. Wait for the BITalino PCB to appear and click 'connect'. Enter password '1234' if prompted.\n"
            "   4. Connect the wires labled 'ECG', 'EMG', and 'EDA' to the appropriate side ports, as seen below."
        )

        bitalino_instruction_label = ttk.Label(self.bitalino_frame, text=bitalino_instruction_text, font=("Calibri Light", 12))
        bitalino_instruction_label.grid(row=2, column=1, pady=10, padx=10, sticky="ns")

        self.bitalino_img_frame = ttk.Frame(self.bitalino_frame)
        self.bitalino_img_frame.grid(row=3, column=1, sticky="n", pady=5, padx=30)

        self.BITalino_front = Image.open("Utilities/Bitalino_front.png")
        self.BITalino_front = self.BITalino_front.resize((540, 360), Image.LANCZOS) 
        self.bitalino_front_img = ImageTk.PhotoImage(self.BITalino_front)
        ttk.Label(self.bitalino_img_frame, image=self.bitalino_front_img, anchor="center").pack(side=tk.LEFT, padx=5, pady=5)

        self.BITalino_back= Image.open("Utilities/Bitalino_back.png")
        self.BITalino_back = self.BITalino_back.resize((540, 360), Image.LANCZOS)
        self.bitalino_back_img = ImageTk.PhotoImage(self.BITalino_back)
        ttk.Label(self.bitalino_img_frame, image=self.bitalino_back_img, anchor="center").pack(side=tk.RIGHT, padx=5, pady=5)

        self.ESP32_frame = ttk.LabelFrame(self.frame, text="Fern Bioelectric Box")
        self.ESP32_frame.grid(row=4, column=1, pady=10, padx=30, sticky="nsew")
        self.ESP32_frame.grid_columnconfigure(1, weight=1)
        self.ESP32_frame.grid_rowconfigure(3, weight=1)

        ESP32_title_label = ttk.Label(self.ESP32_frame, text="If using the Fern Bioelectric Box for Signal Collection:", font=("Calibri Light", 14))
        ESP32_title_label.grid(row=1, column=1, pady=10, padx=20, sticky="ns")

        ESP32_instruction_text = (
            "   1. Locate the Fern Bioelectric Box and turn on by flipping the on/off switch as seen below.\n"
            "   2. If power light is off, charge device using charging cables\n"
            "   3. If this is the first time using the Box:\n"
            "         a. Navigate to the computer's settings, and select 'Bluetooth & devices' → 'Add Device' → 'Bluetooth'\n"
            "         b. Wait for the ESP32-BT to appear and click 'connect'\n"
            "   4. Connect the wires labeled 'ECG,' 'EMG,' and 'EDA' to the appropriate side ports, as seen below.\n"
            "   5. Let device sit on for 3 minutes before starting test."
        )

        ESP32_instruction_label = ttk.Label(self.ESP32_frame, text=ESP32_instruction_text, font=("Calibri Light", 12))
        ESP32_instruction_label.grid(row=2, column=1, pady=10, padx=10, sticky="ns")

        self.ESP32_img_frame = ttk.Frame(self.ESP32_frame)
        self.ESP32_img_frame.grid(row=3, column=1, sticky="n", pady=5, padx=30)

        self.ESP32_front = Image.open("Utilities/ESP32_front.png")
        self.ESP32_front = self.ESP32_front.resize((540, 360), Image.LANCZOS) 
        self.ESP32_front_img = ImageTk.PhotoImage(self.ESP32_front)
        ttk.Label(self.ESP32_img_frame, image=self.ESP32_front_img, anchor="center").pack(side=tk.LEFT, padx=5, pady=5)

        self.ESP32_back= Image.open("Utilities/ESP32_back.png")
        self.ESP32_back = self.ESP32_back.resize((540, 360), Image.LANCZOS)
        self.ESP32_back_img = ImageTk.PhotoImage(self.ESP32_back)
        ttk.Label(self.ESP32_img_frame, image=self.ESP32_back_img, anchor="center").pack(side=tk.RIGHT, padx=5, pady=5)

        self.ESP32_frame.grid_remove()

    # Update instruction page with current device selection
    def update_instructions(self):
        """Called when the device selection changes."""
        device = self.device_var.get()
        if device == "BITalino":
            self.bitalino_frame.grid()
            self.ESP32_frame.grid_remove()  
        else:
            self.ESP32_frame.grid() 
            self.bitalino_frame.grid_remove()

    def next_page(self):
        global device_option

        device_option = self.device_var.get()
        print(f"device option: {device_option}")

        self.controller.frames["InstructionsPage"].update_device_instructions(device_option)
        self.controller.frames["ParameterPage"].update_mac_options()
        self.controller.show_frame("ParameterPage")
    
    def last_page(self):
        self.controller.show_frame("StartPage")



# Test parameter input page
class ParameterPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        global recording_info
        global device_option
        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        frame.grid_rowconfigure(0, weight=0)
        frame.grid_rowconfigure(22, weight=1)
        frame.grid_columnconfigure(0, weight=1) 
        frame.grid_columnconfigure(1, weight=1)
        
        frame.grid_columnconfigure(2, weight=0)
        frame.grid_columnconfigure(3, weight=1)
        frame.grid_columnconfigure(4, weight=0)

        frame.grid_columnconfigure(5, weight=1)
        frame.grid_columnconfigure(6, weight=1)
        frame.grid_columnconfigure(7, weight=1)

        # ---------- BANNER -----------
        banner = tk.Frame(frame, height=150)
        banner.config(bg='lightblue')
        banner.grid(row=0, column=0, columnspan=8, sticky='nsew', pady=(0, 20), padx=0)

        back_button = ctk.CTkButton(banner, text="⇦  Back", width=75, height=30, command=self.last_page)
        back_button.pack(side=tk.LEFT, padx=30, pady=10)

        title_label = tk.Label(banner, text="Enter Recording Parameters", font=("Calibri Light", 24, 'bold'), justify="center")
        title_label.config(bg='lightblue')
        title_label.pack(side=tk.LEFT, expand=True, fill="x", padx=30, pady=30)

        next_button = ctk.CTkButton(banner, text="Next  ⇨", width=75, height=30, command=lambda:validate_entries())
        next_button.pack(side=tk.RIGHT, padx=30, pady=10)
    
    #-----------------------WAV FILE ---------
        directory = "audio_files"
        wav_files=[file for file in os.listdir(directory) if file.endswith('.wav')]
    
        wav_label = ttk.Label(frame, text=f"Select a Wav File (leave empty if none):", font=("Calibri Light", 12))
        wav_label.grid(row=1, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
    
        wav_entry = ttk.Combobox(frame, values=wav_files, state="readonly")
        wav_entry.grid(row=2, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
    
    #-------------FREQUENCY------------
        fq_label = ttk.Label(frame, text="Sound Frequency (in Hz):", font=("Calibri Light", 12))
        fq_label.grid(row=3, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
        fq_entry = ttk.Entry(master=frame)
        fq_entry.grid(row=4, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
    
    #-----------Sound increment (in dB)-----------------

        di_label=ttk.Label(frame,text="Sound increment (in dB) (leave empty for default value of 5 dB):", font=("Calibri Light", 12))
        di_label.grid(row=5, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
        di_entry=ttk.Entry(master=frame)
        di_entry.grid(row=6, column=2, padx=5, pady=5, sticky="ew", columnspan=4)

    #-----------Time increment----------------
        ti_label=ttk.Label(frame,text="Time increment (in seconds) (leave empty for default value of 15 seconds):", font=("Calibri Light", 12))
        ti_label.grid(row=7, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
        ti_entry=ttk.Entry(master=frame)
        ti_entry.grid(row=8, column=2, padx=5, pady=5, sticky="ew", columnspan=4)

        sample_rate_options = [100, 1000]

        self.sr_label = ttk.Label(frame, text="Sampling Rate (in Hz):", font=("Calibri Light", 12))
        self.sr_label.grid(row=9, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
        self.sr_combobox = ttk.Combobox(frame, values=sample_rate_options, state="readonly")
        self.sr_combobox.grid(row=10, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
    

        duration_options = [15,30,45,60,75,90,105,120]
        duration_label = ttk.Label(frame, text="Duration (in seconds):", font=("Calibri Light", 12))
        duration_label.grid(row=11, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
        duration_entry = ttk.Combobox(frame, values=duration_options, state="readonly")
        duration_entry.grid(row=12, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
    
    
    #------------------------CHECK BOX----------------------------------
        signal_label = ttk.Label(frame, text="Select signals to be recorded for analysis:", font=("Calibri Light", 12))
        signal_label.grid(row=13, column=2, padx=5, pady=5, sticky="ew", columnspan=4)

        options_frame = ttk.Frame(frame)
        options_frame.grid(row=14, column=2, columnspan=2)
        
        emg = tk.IntVar()
        ecg = tk.IntVar()
        eda = tk.IntVar()

        op1 = ttk.Checkbutton(options_frame, text="EMG", variable=emg, onvalue=1, offvalue=0)
        op1.pack(side=tk.LEFT, padx=15, pady=10)
        op2 = ttk.Checkbutton(options_frame, text="ECG", variable=ecg, onvalue=1, offvalue=0)
        op2.pack(side=tk.LEFT, padx=15, pady=10)
        op3 = ttk.Checkbutton(options_frame, text="EDA", variable=eda, onvalue=1, offvalue=0)
        op3.pack(side=tk.LEFT, padx=15, pady=10)
    
    #-------------------
        self.mac_label = ttk.Label(frame, text="Select a BITalino:", font=("Calibri Light", 12))
        self.mac_label.grid(row=17, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
        self.mac_combobox = ttk.Combobox(frame, values=mac_options, state='normal', takefocus=False)
        self.mac_combobox.grid(row=18, column=2, padx=5, pady=5, sticky="ew", columnspan=4)


        get_existing_BITalino_bluetooth_devices(self.mac_combobox)
        self.mac_button = ctk.CTkButton(frame, text="Scan for Bluetooth devices", fg_color="darkred", hover_color="red", text_color="white", corner_radius=0, font=("Calibri Light", 13, "italic"),
                                                                    command=lambda:[find_bluetooth_devices(self.mac_combobox, message_box)])
        self.mac_button.grid(row=19, column=2, padx=5, pady=5, sticky="ew", columnspan=2)
    
        self.clear_button = ctk.CTkButton(frame, text="Clear current list", fg_color="darkred", hover_color="red", text_color="white", corner_radius=0,  font=("Calibri Light", 13, "italic"),
                                                                    command=lambda:clear_saved_list(self.mac_combobox, message_box,1))
        self.clear_button.grid(row=19, column=4, padx=5, pady=5, sticky="ew", columnspan=1)
    
        status_label = ttk.Label(frame, text="", anchor="center")
        status_label.grid(row=20, column=2, padx=5, pady=5, sticky="ew", columnspan=4)
    
        def validate_entries(): 
            try:
                duration = int(duration_entry.get())
                if device_option == "BITalino":
                    sample_rate = int(self.sr_combobox.get())
                else:
                    sample_rate = 130
                
                if not di_entry.get() == '':
                    try:
                        di_option = int(di_entry.get())
                    except:
                        message_box.config(text="Decibel increment entry must be a valid integer")
                        return 
                else:
                    di_option = 5


                if not ti_entry.get() == '':
                    try:
                        time_option = int(ti_entry.get())
                    except:
                        message_box.config(text="Time interval entry must be a valid integer")
                        return
                else: # if the time interval entry is empty, default to a value of 15 seconds
                    time_option = 15

                if time_option > duration:
                    message_box.config(text="The time interval cannot be larger than the duration")
                    return
                

                # Check to see which signals to graph
                signals = []
                if emg.get() == 1:
                    signals.append(True)
                else:
                    signals.append(False)
                if ecg.get() == 1:
                    signals.append(True)
                else:
                    signals.append(False)
                if eda.get() == 1:
                    signals.append(True)
                else:
                    signals.append(False)
                
                if not (signals[0] or signals[1] or signals[2]):
                    message_box.config(text="You must select at least 1 signal type to record")
                    return

                if not wav_entry.get() == "" and fq_entry.get() == "": # if wave field is populated and frequency field is empty, use .wav file
                    audio_option = wav_entry.get()
                elif not fq_entry.get() == "" and wav_entry == "": # if frequency field is populated and wave field is empty, use frequency entry
                    try:
                        audio_option = int(fq_entry.get())
                    except:
                        message_box.config(text="If you did not enter a .wave file, the frequency must be specified as a valid integer")
                        return
                elif not fq_entry.get() == "" and not wav_entry == "": # if both are populated use frequency entry as default
                    try:
                        audio_option = int(fq_entry.get())
                    except:
                        message_box.config(text="If you did not enter a .wave file, the frequency must be specified as a valid integer")
                        return
                else:
                    message_box.config(text="One or more invalid parameters. Fix entries and try again.")
                    print("Invalid Parameters")
                    return
                
                macAddress = ''
                if device_option == "BITalino":
                    # Check to see if a BITalino was selected
                    if not self.mac_combobox.get() == '': # if BITalino field is not empty, continue
                        mac_option = self.mac_combobox.get()
                    else: # if empty, throw error message
                        message_box.config(text="Must choose a BITalino device before continuing")
                        return
                    save_to_existing_BITalino_bluetooth_devices(mac_option)
                    
                    for i in device_list:
                        if i[1] == mac_option:
                            macAddress = i[0]
                
                

                print(f"macAddress = {macAddress}")

                self.recording_info = {
                    "sample_rate": sample_rate,
                    "duration": duration,
                    "macAddress": macAddress,
                    "audio_option": audio_option,
                    "time_option": time_option,
                    "di_option": di_option,
                    "signals": signals,
                    "device_option": device_option
                }

                recording_info = {
                    "sample_rate": sample_rate,
                    "duration": duration,
                    "macAddress": macAddress,
                    "audio_option": audio_option,
                    "time_option": time_option,
                    "di_option": di_option,
                    "signals": signals,
                    "device_option": device_option
                }
                
                self.next_page()
                
            except Exception as e:
                message_box.config(text="One or more invalid parameters. Fix entries and try again.")
                print(e)
            
        message_box = tk.Message(frame, text="", anchor="center", width=500, font=("Calibri Light", 10), foreground="red", background="white")
        message_box.grid(row=21, column=2, padx=5, pady=5, sticky="nsew", columnspan=4)
    

    def next_page(self):
        self.controller.show_frame("InstructionsPage")

    def last_page(self):
        self.controller.show_frame("DeviceConnectionPage")
    
    def get_recording_info(self):
        return self.recording_info

    def update_mac_options(self):
        global device_option

        if device_option == "BITalino":
            self.mac_label.grid()
            self.mac_combobox.grid()
            self.mac_button.grid()
            self.clear_button.grid()
            self.sr_combobox.grid()
            self.sr_label.grid()
        else:
            self.mac_label.grid_remove()
            self.mac_combobox.grid_remove()
            self.mac_button.grid_remove()
            self.clear_button.grid_remove()
            self.sr_combobox.grid_remove()
            self.sr_label.grid_remove()
        

# Instruction page for pad placement and device info
class InstructionsPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.final_volume_db = -30  

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(1, weight=0)
        self.frame.grid_rowconfigure(2, weight=0)
        self.frame.grid_rowconfigure(3, weight=0)
        self.frame.grid_rowconfigure(4, weight=0)
        self.frame.grid_rowconfigure(5, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=0)
        self.frame.grid_columnconfigure(2, weight=0)
        self.frame.grid_columnconfigure(3, weight=1)


        # ---------- BANNER -----------
        banner = tk.Frame(self.frame, height=150)
        banner.config(bg='lightblue')
        banner.grid(row=0, column=0, columnspan=4, sticky='nsew', pady=(0, 20), padx=0)

        back_button = ctk.CTkButton(banner, text="⇦  Back", width=75, height=30, command=self.last_page)
        back_button.pack(side=tk.LEFT, padx=30, pady=10)

        instruction_title_label = tk.Label(banner, text="Setup Instructions", font=("Calibri Light", 24, 'bold'), justify="center")
        instruction_title_label.config(bg='lightblue')
        instruction_title_label.pack(side=tk.LEFT, expand=True, fill="x", padx=30, pady=30)

        next_button = ctk.CTkButton(banner, text="Next  ⇨", width=75, height=30, command=self.next_page)
        next_button.pack(side=tk.RIGHT, padx=30, pady=10)

        instruction_subtitle_label = ttk.Label(self.frame, text="Please follow the instructions listed below. \nCycle through the images to the right for device references and pad placements.", font=("Calibri Light", 14), justify="center")
        instruction_subtitle_label.grid(row=1, column=0, pady=5, padx=10, sticky="ns", columnspan=4)

        instruction_subtitle_label2 = ttk.Label(self.frame, text="Press 'Next' when complete.", font=("Calibri Light", 14), justify="center")
        instruction_subtitle_label2.grid(row=2, column=0, pady=5, padx=10, sticky="ns", columnspan=4)

        self.make_images()


    def update_device_instructions(self, device_option):
        if device_option == "ESP32":
            self.add_ESP32_instructions()
            self.BITalino_image_label.grid_remove()     
            self.BITalino_thumb_frame.grid_remove()  
            self.ESP32_image_label.grid()  
            self.ESP32_thumb_frame.grid() 
        else:
            self.add_bitalino_instructions()
            self.BITalino_image_label.grid()     
            self.BITalino_thumb_frame.grid()  
            self.ESP32_image_label.grid_remove()  
            self.ESP32_thumb_frame.grid_remove()  

    def add_bitalino_instructions(self):
        instruction_text_1 = (
            "   1. Locate and turn on headphones\n"
            "   2. If this is the first time using the headphones:\n"
            "         a. Navigate to the computer's settings\n"
            "         b. Select 'Bluetooth & devices'\n"
            "         c. Select 'Add Device'\n"
            "         d. Select 'Bluetooth'\n"
            "         e. Wait for the headphones to appear and click 'connect'\n"
            "   3. Attach cables provided:\n"
            "         a. Flip BITalino upside down\n"
            "         b. Locate the side ports labeled ECG, EDA, EMG\n"
            "         c. Plug in labeled cables to appropriate ports\n"
            "   4. Attach electrode pads to body:\n"
            "         a. Pad placement depends on selected signals (ECG, EMG, and/or EDA).\n"
            "         b. Use the images to the right for placement guidance.\n"
            "         c. Note that there is an additional ECG pad (red) not pictured that can\n"
            "               be placed anywhere at or below the right knee (preferably ankle)\n"
            "   5. Attach the correctly colored wires to patches according to the images.\n"
            "           Colors can be found near the base of the wires."
        )

        instruction_label_1 = ttk.Label(self.frame, text=instruction_text_1, font=("Calibri Light", 14))
        instruction_label_1.grid(row=3, column=1, pady=5, padx=40, sticky="nsew", rowspan=2)

        
    # Add the ESP32 instructions
    def add_ESP32_instructions(self):
        instruction_text_1 = (
            "   1. Locate and turn on headphones\n"
            "   2. If this is the first time using the headphones:\n"
            "         a. Navigate to the computer's settings\n"
            "         b. Select 'Bluetooth & devices'\n"
            "         c. Select 'Add Device'\n"
            "         d. Select 'Bluetooth'\n"
            "         e. Wait for the headphones to appear and click 'connect'\n"
            "   3. Attach electrode pads to body:\n"
            "         a. Pad placement depends on selected signals (ECG, EMG, and/or EDA).\n"
            "         b. Use the images to the right for placement guidance.\n"
            "         c. Note that there is an additional ECG pad (black) not pictured that can\n"
            "               be placed anywhere at or below the right knee (preferably ankle)\n"
            "   4. Locate labeled and colored wires attached to the Box\n"
            "   5. Attach the correctly colored wires to patches according to the images.\n"
        )


        instruction_label_1 = ttk.Label(self.frame, text=instruction_text_1, font=("Calibri Light", 14))
        instruction_label_1.grid(row=3, column=1, pady=5, padx=40, sticky="nsew", rowspan=2)

          

    def next_page(self):
        self.controller.frames["VolumePage"].bind_arrows()
        self.controller.show_frame("VolumePage")
    
    def last_page(self):
        self.controller.show_frame("ParameterPage")

    # Make image selection widget (similar to amazon image selection with small thumbnail image selections)
    def make_images(self):
        IMG_HEIGHT = 500
        IMG_WIDTH = 600
        THUMB_HEIGHT = 60
        THUMB_WIDTH = 80

        def resize_keep_aspect(img, max_width, max_height):
            w, h = img.size
            ratio = min(max_width / w, max_height / h)
            return img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        
        self.selected_index = 0
        
        self.BITalino_image_paths = [
            f"Utilities/BITalino_front.png",
            f"Utilities/BITalino_back.png",
            f"Utilities/BITalino_ECG_pads.png",
            f"Utilities/BITalino_EDA_pads.png",
            f"Utilities/BITalino_EMG_pads.png",
            f"Utilities/BITalino_all_pads.png",
            f"Utilities/Wires_all_pads.png"
        ]

        self.BITalino_thumb_frame = tk.Frame(self.frame)
        self.BITalino_thumb_frame.grid(row=4, column=2, pady=5, padx=10, sticky="n")

        self.BITalino_full_photos = [ImageTk.PhotoImage(resize_keep_aspect(Image.open(path), IMG_WIDTH, IMG_HEIGHT)) for path in self.BITalino_image_paths]
        self.BITalino_thumbs = [ImageTk.PhotoImage(resize_keep_aspect(Image.open(path), THUMB_WIDTH, THUMB_HEIGHT)) for path in self.BITalino_image_paths]

        for idx, thumb in enumerate(self.BITalino_thumbs):
            label = tk.Label(self.BITalino_thumb_frame, image=thumb)
            label.pack(side=tk.LEFT, padx=5)
            label.bind("<Button-1>", lambda e, i=idx: self.update_main_image(i))

        self.BITalino_image_label = tk.Label(self.frame, width=IMG_WIDTH, height=IMG_HEIGHT, bg="white")
        self.BITalino_image_label.grid(row=3, column=2, pady=10, padx=10, sticky="s")
        self.BITalino_image_label.config(image=self.BITalino_full_photos[self.selected_index])


        self.ESP32_image_paths = [
            f"Utilities/ESP32_front.png",
            f"Utilities/ESP32_back.png",
            f"Utilities/ESP32_ECG_pads.png",
            f"Utilities/ESP32_EDA_pads.png",
            f"Utilities/ESP32_EMG_pads.png",
            f"Utilities/ESP32_all_pads.png",
            f"Utilities/Wires_all_pads.png"
        ]
        
        self.ESP32_thumb_frame = tk.Frame(self.frame)
        self.ESP32_thumb_frame.grid(row=4, column=2, pady=5, padx=10, sticky="n")
        
        self.ESP32_full_photos = [ImageTk.PhotoImage(resize_keep_aspect(Image.open(path), IMG_WIDTH, IMG_HEIGHT)) for path in self.ESP32_image_paths]
        self.ESP32_thumbs = [ImageTk.PhotoImage(resize_keep_aspect(Image.open(path), THUMB_WIDTH, THUMB_HEIGHT)) for path in self.ESP32_image_paths]

        for idx, thumb in enumerate(self.ESP32_thumbs):
            label = tk.Label(self.ESP32_thumb_frame, image=thumb)
            label.pack(side=tk.LEFT, padx=5)
            label.bind("<Button-1>", lambda e, i=idx: self.update_main_image(i))

        self.ESP32_image_label = tk.Label(self.frame, width=IMG_WIDTH, height=IMG_HEIGHT, bg="white")
        self.ESP32_image_label.grid(row=3, column=2, pady=10, padx=10, sticky="s")
        self.ESP32_image_label.config(image=self.ESP32_full_photos[self.selected_index])

    def update_main_image(self, index):
        self.selected_index = index
        self.BITalino_image_label.config(image=self.BITalino_full_photos[index])
        self.ESP32_image_label.config(image=self.ESP32_full_photos[index])

# Volume page class
class VolumePage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.final_volume_db = -30  
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        frame.grid_rowconfigure(0, weight=0)  
        frame.grid_rowconfigure(1, weight=0) 
        frame.grid_rowconfigure(2, weight=0)  
        frame.grid_rowconfigure(3, weight=1) 
        frame.grid_columnconfigure(0, weight=1) 

        # ---------- BANNER -----------
        banner = tk.Frame(frame, height=150)
        banner.config(bg='lightblue')
        banner.grid(row=0, column=0, columnspan=1, sticky='nsew', pady=(0, 20), padx=0)

        back_button = ctk.CTkButton(banner, text="⇦  Back", width=75, height=30, command=self.last_page)
        back_button.pack(side=tk.LEFT, padx=30, pady=10)

        title_label = tk.Label(banner, text="Volume Adjustment", font=("Calibri Light", 24, 'bold'), justify="center")
        title_label.config(bg='lightblue')
        title_label.pack(side=tk.LEFT, expand=True, fill="x", padx=30, pady=30)

        next_button = ctk.CTkButton(banner, text="Next  ⇨", width=75, height=30, command=self.next_page)
        next_button.pack(side=tk.RIGHT, padx=30, pady=10)

        instructions_label = ttk.Label(frame, text="Use the Up and Down arrow keys to adjust the volume to a comfortable level.\nPress 'Next' when finished.", font=("Calibri Light", 14), justify="center")
        instructions_label.grid(row=1, column=0, pady=10, sticky="s") 

        self.volume_label = ttk.Label(frame, text=f"Current Volume: {self.final_volume_db} dB", font=("Calibri Light", 16))
        self.volume_label.grid(row=2, column=0, pady=10) 


        
    def bind_arrows(self):
        self.controller.bind_all('<KeyPress-Up>', self.adjust_volume_arrows)
        self.controller.bind_all('<KeyPress-Down>', self.adjust_volume_arrows)
    
    def unbind_arrows(self):
        self.controller.unbind_all('<KeyPress-Up>')
        self.controller.unbind_all('<KeyPress-Down>')


    def adjust_volume_arrows(self, event):
        if event.keysym == 'Up':
            self.final_volume_db = min(self.final_volume_db + 3, 0)  # Cap at 0 dB
        elif event.keysym == 'Down':
            self.final_volume_db = max(self.final_volume_db - 3, -60)  # Limit to -60 dB

        play_beep_sound(self.final_volume_db)  # Play beep at new volume
        self.volume_label.config(text=f"Current Volume: {self.final_volume_db} dB") 

    def next_page(self):
        self.unbind_arrows()
        self.controller.show_frame("TestPrepPage")
    
    def last_page(self):
        self.unbind_arrows
        self.controller.show_frame("InstructionsPage")
        


# Instructions for before user begins test
class TestPrepPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.final_volume_db = -30  

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(7, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=0)
        self.frame.grid_columnconfigure(2, weight=1)

        # ---------- BANNER -----------
        banner = tk.Frame(self.frame, height=150)
        banner.config(bg='lightblue')
        banner.grid(row=0, column=0, columnspan=3, sticky='nsew', pady=(0, 20), padx=0)

        back_button = ctk.CTkButton(banner, text="⇦  Back", width=75, height=30, command=self.last_page)
        back_button.pack(side=tk.LEFT, padx=30, pady=10)

        title_label = tk.Label(banner, text="Test Preparation", font=("Calibri Light", 24, 'bold'), justify="center")
        title_label.config(bg='lightblue')
        title_label.pack(side=tk.LEFT, expand=True, fill="x", padx=(30, 200), pady=30)

        subtitle_label = ttk.Label(self.frame, text="Please Read Carefully Before Beginning Recording", font=("Calibri Light", 14))
        subtitle_label.grid(row=2, column=1, pady=10, padx=10)

        frame1 = ttk.Frame(self.frame)
        frame1.grid(row=3, column=1, sticky="ns", padx=10, pady=15)

        section1_title = ttk.Label(frame1, text="How the Test Works:", font=("Calibri Light", 15, 'bold'))
        section1_title.grid(row=1, column=0, pady=5, padx=10)

        t1 = ttk.Label(frame1, text="The system will capture two sessions of your bioelectric signals over the duration you specified.", font=("Calibri Light", 13))
        t1.grid(row=2, column=0, pady=5, padx=10)

        t2 = ttk.Label(frame1, text="First, a baseline reading will record your natural state.", font=("Calibri Light", 13))
        t2.grid(row=3, column=0, pady=5, padx=10)

        t3 = ttk.Label(frame1, text="Next, a second reading is taken while your chosen sound frequency or audio file is played.", font=("Calibri Light", 13))
        t3.grid(row=4, column=0, pady=5, padx=10)

        t4 = ttk.Label(frame1, text="Throughout both sessions, a real-time graph will display your recorded signals.", font=("Calibri Light", 13))
        t4.grid(row=5, column=0, pady=5, padx=10)

        t5 = ttk.Label(frame1, text="Please do not close out of the system during signal recording.", font=("Calibri Light", 13))
        t5.grid(row=6, column=0, pady=5, padx=10)

        frame2 = ttk.Frame(self.frame)
        frame2.grid(row=4, column=1, sticky="ns", padx=10, pady=15)

        section2 = ttk.Label(frame2, text="Before You Begin:", font=("Calibri Light", 15, 'bold'))
        section2.grid(row=1, column=0, pady=10, padx=10)

        t1 = ttk.Label(frame2, text="To ensure we capture your most accurate results, please follow these guidelines during the test.", font=("Calibri Light", 13))
        t1.grid(row=2, column=0, pady=5, padx=10)

        t2 = ttk.Label(frame2, text="Remain as still as possible throughout the session, maintain a calm state, and try not to be distracted by your surroundings.", font=("Calibri Light", 13))
        t2.grid(row=3, column=0, pady=5, padx=10)

        t2 = ttk.Label(frame2, text="If you are in a distracting environment, consider closing your eyes to help keep your body relaxed and your physiological responses stable.", font=("Calibri Light", 13))
        t2.grid(row=4, column=0, pady=5, padx=10)

        t3 = ttk.Label(frame2, text="Following these instructions is essential to obtaining reliable data.", font=("Calibri Light", 13, 'italic'))
        t3.grid(row=5, column=0, pady=5, padx=10)

        instruction3 = ttk.Label(self.frame, text="When you are ready, click 'Begin'", font=("Calibri Light", 14, 'bold'))
        instruction3.grid(row=6, column=1, pady=20, padx=10)

        start_button = ctk.CTkButton(self.frame, text="Begin", command=self.next_page)
        start_button.grid(row=7, column=1, padx=10, pady=20, sticky="n")

    def next_page(self):
        global recording_info
        next_baseline_function(self.controller.frames["ParameterPage"].get_recording_info(), self.controller)
        self.controller.frames["LoadingPage"].set_load_title("Please Wait...")
        self.controller.show_frame("LoadingPage")
    
    def last_page(self):
        self.controller.frames["VolumePage"].unbind_arrows()
        self.controller.show_frame("VolumePage")

# Loading page class 
class LoadingPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  

        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=7, pady=7)

        frame.grid_rowconfigure(0, weight=0)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        self.label = ttk.Label(frame, text="Please Wait...", font=("Calibri Light", 16))
        self.label.grid(row=0, column=0, pady=30, padx=10, sticky="e")

        # --- Animated loading logo ----
        self.image_files = ["Utilities/logo_loading_1.png", "Utilities/logo_loading_2.png", "Utilities/logo_loading_3.png"]
        self.images = [tk.PhotoImage(file=img).subsample(4, 4) for img in self.image_files]
        
        self.image_cycle = cycle(self.images)
        
        self.load_symbol = ttk.Label(frame, image=next(self.image_cycle))
        self.load_symbol.grid(row=0, column=1, columnspan=1, pady=30, padx=10, sticky="w") 
        
        self.update_image()
    
    def update_image(self):
        if self.winfo_exists():  
            self.after(1000, self.update_image)
            self.load_symbol.config(image=next(self.image_cycle))

    def set_load_title(self, title):
       self.label.config(text=title)

# Start test page
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

        label = ttk.Label(frame, text="Baseline Collection Complete!", font=("Calibri Light", 16), justify="center")
        label.grid(row=0, column=0, pady=10, sticky="s") 

        start_button = ctk.CTkButton(frame, text="Start Test Sequence", command=self.next_page)
        start_button.grid(row=1, column=0, pady=10, sticky="n") 

    def next_page(self):
        self.controller.frames["LoadingPage"].set_load_title("Please Wait...")
        self.controller.show_frame("LoadingPage")
        next_test_sequence_function(self.controller)


# ML results page
class ResultsPage(ttk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(1, weight=0)
        self.frame.grid_rowconfigure(2, weight=0)
        self.frame.grid_rowconfigure(3, weight=0)
        self.frame.grid_rowconfigure(4, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)  
        self.frame.grid_columnconfigure(1, weight=0)  
        self.frame.grid_columnconfigure(2, weight=1) 


        # ---------- BANNER -----------
        banner = tk.Frame(self.frame, height=150)
        banner.config(bg='lightblue')
        banner.grid(row=0, column=0, columnspan=3, sticky='nsew', pady=(0, 20), padx=0)

        instruction_title_label = tk.Label(banner, text="ML Results Overview", font=("Calibri Light", 24, 'bold'), justify="center")
        instruction_title_label.config(bg='lightblue')
        instruction_title_label.pack(side=tk.LEFT, expand=True, fill="x", padx=(290, 30), pady=30)

        next_button = ctk.CTkButton(banner, text="View Feature Significance  ⇨", width=150, height=30, command=lambda: controller.show_frame("ShapPage"))
        next_button.pack(side=tk.RIGHT, padx=30, pady=10)


        self.exit_button = ctk.CTkButton(self.frame, text="Exit", command=lambda: self.controller.destroy(), width=75, fg_color='red', hover_color='darkred')
        self.exit_button.grid(row=4, column=0, padx=20, pady=10, sticky="se", columnspan=3)

        no_ml_label = tk.Label(self.frame, text="We are unable to generate an ML prediciton for the selected signals.\n\nPlease see the Stats Display Page and Graphs for information on your collected signals.", font=('Calibri Light', 16), justify="center")
        no_ml_label.grid(row=2, column=1, sticky="nsew", pady=40)


    # Displays the ML results, it's confidence, and a table with all of the feature values
    def display_results(self, ml_predictions, results_data):
        prediction_frame = tk.Frame(self.frame, relief="groove")
        prediction_frame.config(bg='#FEE788')
        prediction_frame.grid(row=2, column=1, sticky="nsew", pady=40)

        final_prediction = "Unable to make prediction."
        for signal, prediction_data in ml_predictions.items():
            if prediction_data['classification'] == 1:
                final_prediction = "Your response indicates a potential irregularity.\nWe recommend consulting with a healthcare professional for further evaluation."
                confidence = f"Our system is {(100*prediction_data['confidence']):.2f}% confident an abnormal reaction occured."
            elif prediction_data['classification'] == 0:
                final_prediction = "No abnormal response was detected."
                confidence = f"Our system is {(100*(1-prediction_data['confidence'])):.2f}% confident that no abnormal reaction occured."
        
        prediction_label = tk.Label(prediction_frame, text=final_prediction, font=('Calibri Light', 13, 'bold')).pack(pady=10, padx=15)
        confidence_label = tk.Label(prediction_frame, text=confidence, font=('Calibri Light', 10)).pack(pady=10, padx=15)

        table = ttk.Treeview(self.frame, columns=["Feature", "Baseline", "Test", "Difference"], show="headings", height=12)
        table.grid(row=3, column=1, sticky="nsew", padx=7, pady=7)
        
        table.heading("Feature", text="Feature", anchor="w")
        table.heading("Baseline", text="Baseline", anchor="center")
        table.heading("Test", text="Test", anchor="center")
        table.heading("Difference", text="Difference", anchor="center")

        table.column("Feature", width=80, anchor="w")
        table.column("Baseline", width=100, anchor="center")
        table.column("Test", width=100, anchor="center")
        table.column("Difference", width=100, anchor="center")

        style = ttk.Style()
        style.configure("Treeview", font=("Calibri Light", 10), rowheight=30) 
        style.configure("Treeview.Heading", font=("Calibri Light", 12, "bold")) 

        feature_types = list(results_data['ecg']['baseline_data'].keys())

        table.tag_configure("even", background="#E1EEFF")
        table.tag_configure("odd", background="#E7F7FA")

        # Make feature table
        for i, feature in enumerate(feature_types):
            tag = "even" if i % 2 == 0 else "odd"
            baseline_value = results_data['ecg']['baseline_data'].get(feature, 'N/A')
            test_value = results_data['ecg']['test_data'].get(feature, 'N/A')
            percent_diff = results_data['ecg']['percent_difference'].get(feature, 'N/A')

            baseline_value = f"{baseline_value:.5f}" if baseline_value != 'N/A' else 'N/A'
            test_value = f"{test_value:.5f}" if test_value != 'N/A' else 'N/A'
            percent_diff = f"{percent_diff:.5f}%" if percent_diff != 'N/A' else 'N/A%'

            table.insert("", "end", values=(feature, baseline_value, test_value, percent_diff), tags=(tag,))

# Page to display shap plot
class ShapPage(ttk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(1, weight=0)
        self.frame.grid_rowconfigure(2, weight=1)
        self.frame.grid_rowconfigure(3, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)  
        self.frame.grid_columnconfigure(1, weight=0)  
        self.frame.grid_columnconfigure(2, weight=1)  

        # ---------- BANNER -----------
        banner = tk.Frame(self.frame, height=150)
        banner.config(bg='lightblue')
        banner.grid(row=0, column=0, columnspan=3, sticky='nsew', pady=(0, 20), padx=0)

        back_button = ctk.CTkButton(banner, text="⇦  Back to ML Results", width=150, height=30, command=lambda: controller.show_frame("ResultsPage"))
        back_button.pack(side=tk.LEFT, padx=30, pady=10)

        instruction_title_label = tk.Label(banner, text="Feature Significance", font=("Calibri Light", 24, 'bold'), justify="center")
        instruction_title_label.config(bg='lightblue')
        instruction_title_label.pack(side=tk.LEFT, expand=True, fill="x", padx=30, pady=30)

        next_button = ctk.CTkButton(banner, text="View Stats Results  ⇨", width=150, height=30, command=lambda: controller.show_frame("StatsResultsPage"))
        next_button.pack(side=tk.RIGHT, padx=30, pady=10)


        self.exit_button = ctk.CTkButton(self.frame, text="Exit", command=lambda: self.controller.destroy(), width=75, fg_color='red', hover_color='darkred')
        self.exit_button.grid(row=3, column=0, padx=20, pady=10, sticky="se", columnspan=3)

        no_shap_label = tk.Label(self.frame, text="Because we were unable to generate an ML prediciton, we cannot provide insight on feature importance.\n\nPlease see the Stats Display Page and Graphs for information on your collected signals.", font=('Calibri Light', 16), justify="center")
        no_shap_label.grid(row=2, column=1, sticky="nsew", pady=40)

    # Displays the shap waterfall plot created in the ECG_ML.py file
    def display_results(self, ml_predictions):
        shap_frame = tk.Frame(self.frame)
        shap_frame.grid(row=2, column=1, sticky="nsew", padx=7, pady=20)

        fig = ml_predictions['ecg']['fig']
        fig.set_size_inches(8, 6)
        
        canvas = FigureCanvasTkAgg(fig, master=shap_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

# Signal graph page
class GraphPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.figs = [] 

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(1, weight=0)
        self.frame.grid_rowconfigure(2, weight=0)
        self.frame.grid_rowconfigure(3, weight=0)
        self.frame.grid_rowconfigure(4, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)  
        self.frame.grid_columnconfigure(1, weight=0)  
        self.frame.grid_columnconfigure(2, weight=1)  

        # ---------- BANNER -----------
        banner = tk.Frame(self.frame, height=150)
        banner.config(bg='lightblue')
        banner.grid(row=0, column=0, columnspan=3, sticky='nsew', pady=(0, 20), padx=0)

        back_button = ctk.CTkButton(banner, text="⇦  Back to Stats Results", width=150, height=30, command=self.last_page)
        back_button.pack(side=tk.LEFT, padx=30, pady=10)

        instruction_title_label = tk.Label(banner, text="Analysis Graphs", font=("Calibri Light", 24, 'bold'), justify="center")
        instruction_title_label.config(bg='lightblue')
        instruction_title_label.pack(side=tk.LEFT, expand=True, fill="x", padx=(30, 290), pady=30)

        self.exit_button = ctk.CTkButton(self.frame, text="Exit", command=lambda: self.controller.destroy(), width=75, fg_color='red', hover_color='darkred')
        self.exit_button.grid(row=4, column=0, padx=20, pady=10, sticky="se", columnspan=3)

        self.subtitle_label = tk.Label(self.frame, text="Click between tabs to view all graphs.", font=('Calibri Light', 14))
        self.subtitle_label.grid(row=2, column=0, pady=(0,20), columnspan=3)
        
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.grid(row=3, column=1, sticky="nsew", padx=7, pady=7)
    
    # Load in the graphs from signal collection
    def load_graphs(self, graphs_dict):
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        self.figs.clear()
        
        for category, data_types in graphs_dict.items():
            for data_type, fig in data_types.items():

                if not fig:
                    continue

                title = category.upper() + " " + data_type.capitalize()

                self.figs.append(fig)  
        
                fig.set_size_inches(13, 2)
                
                graph_frame = tk.Frame(self.notebook, padx=20, pady=20)
                graph_frame.pack(fill="x", pady=10)
                
                canvas = FigureCanvasTkAgg(fig, master=graph_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
                
                toolbar = NavigationToolbar2Tk(canvas, graph_frame)
                toolbar.update()
                canvas._tkcanvas.pack(fill="x")

                self.notebook.add(graph_frame, text=title)
            
        self.update_idletasks()
    def last_page(self):
        self.controller.show_frame("StatsResultsPage")




# Page to display previous teams's stats
class StatsResultsPage(ttk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.figs = [] 
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)  

        self.frame = ttk.Frame(self)
        self.frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.frame.grid_rowconfigure(0, weight=0)
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_rowconfigure(2, weight=0)
        self.frame.grid_columnconfigure(0, weight=1)  


        # ---------- BANNER -----------
        banner = tk.Frame(self.frame, height=150)
        banner.config(bg='lightblue')
        banner.grid(row=0, column=0, sticky='nsew', pady=(0, 20), padx=0)

        back_button = ctk.CTkButton(banner, text="⇦  Back to Feature Significance", width=75, height=30, command=self.last_page)
        back_button.pack(side=tk.LEFT, padx=30, pady=10)
        

        instruction_title_label = tk.Label(banner, text="Stats Overview", font=("Calibri Light", 24, 'bold'), justify="center")
        instruction_title_label.config(bg='lightblue')
        instruction_title_label.pack(side=tk.LEFT, expand=True, fill="x", padx=30, pady=30)

        next_button = ctk.CTkButton(banner, text="View Graphs  ⇨", width=150, height=30, command=self.next_page)
        next_button.pack(side=tk.RIGHT, padx=30, pady=10)

        self.exit_button = ctk.CTkButton(self.frame, text="Exit", command=lambda: self.controller.destroy(), width=75, fg_color='red', hover_color='darkred')
        self.exit_button.grid(row=2, column=0, padx=20, pady=10, sticky="se")

        self.notebook = ttk.Notebook(self.frame)
        self.notebook.grid(row=1, column=0, sticky='nsew', pady=10, padx=25)


    # Load in and display stat results
    def display_results(self, stats_data):

        self.stats_tab = tk.Frame(self.notebook)
        self.notebook.add(self.stats_tab, text="Stats")

        self.stats_tab.grid_rowconfigure(0, weight=0)
        self.stats_tab.grid_rowconfigure(1, weight=0)
        self.stats_tab.grid_rowconfigure(2, weight=0)
        self.stats_tab.grid_rowconfigure(3, weight=0)
        self.stats_tab.grid_rowconfigure(7, weight=1)
        self.stats_tab.grid_columnconfigure(0, weight=2)  
        self.stats_tab.grid_columnconfigure(1, weight=0)  
        self.stats_tab.grid_columnconfigure(2, weight=2)  

        row = 1
        for signal, categories in stats_data.items():
            if categories['baseline'] is not None:
                table_label = tk.Label(self.stats_tab, text=f"{signal.upper()} Stats", font=('Calibri Light', 16, 'bold'))
                table_label.grid(row=row, column=1, sticky="nsew", padx=7, pady=7)

                table = ttk.Treeview(self.stats_tab, columns=["Stat Type", "Baseline", "Test", "Difference", "Flag"], show="headings", height=4)
                table.grid(row=row+1, column=1, sticky="nsew", padx=7, pady=7)
                
                table.heading("Stat Type", text="Stat Type", anchor="w")
                table.heading("Baseline", text="Baseline", anchor="center")
                table.heading("Test", text="Test", anchor="center")
                table.heading("Difference", text="Difference", anchor="center")
                table.heading("Flag", text="Flag", anchor="center")
                
                table.column("Stat Type", width=100, anchor="w")
                table.column("Baseline", width=180, anchor="center")
                table.column("Test", width=180, anchor="center")
                table.column("Difference", width=180, anchor="center")
                table.column("Flag", width=180, anchor="center")

                style = ttk.Style()
                style.configure("Treeview", font=("Calibri Light", 10), rowheight=30) 
                style.configure("Treeview.Heading", font=("Calibri Light", 12, "bold")) 

                stat_types = ['max', 'min', 'mean', 'std_dev']

                table.tag_configure("even", background="#E1EEFF")
                table.tag_configure("odd", background="#E7F7FA")

                for i, stat in enumerate(stat_types):
                    tag = "even" if i % 2 == 0 else "odd"
                    baseline_value = categories['baseline'].get(stat, 'N/A')
                    test_value = categories['test'].get(stat, 'N/A')
                    diff_value = categories['diff'].get(stat, 'N/A')
                    flag = categories['flags'].get(stat, 'N/A')

                    baseline_value = f"{baseline_value:.4f}" if baseline_value != 'N/A' and not np.isnan(baseline_value) else 'N/A'
                    test_value = f"{test_value:.4f}" if test_value != 'N/A' and not np.isnan(test_value) else 'N/A'
                    diff_value = f"{diff_value:.4f}%" if diff_value != 'N/A' and not np.isnan(diff_value) else 'N/A'
                
                    table.insert("", "end", values=(stat, baseline_value, test_value, diff_value, flag), tags=(tag,))
                
                row += 2
        
    # Load in and display the other graph results
    def load_graphs(self, graphs_dict):
        
        for category, graphs in graphs_dict.items():
            if not graphs:
                continue
                
            tab_frame = ScrollableFrame(self.notebook)
            self._add_graphs_to_tab(tab_frame.scrollable_frame, category, graphs)
            self.notebook.add(tab_frame, text=category)
        
        self.update_idletasks()
    
    def _add_graphs_to_tab(self, parent_frame, category, graphs):
        tk.Label(parent_frame,
                text=category,
                font=('Calibri Light', 16, 'bold'),
                pady=10).pack(fill="x")
        
        for i, fig in enumerate(graphs, 1):
            self.figs.append(fig) 
            
            graph_frame = tk.Frame(parent_frame, 
                                 bd=1, 
                                 relief="groove",
                                 padx=30, 
                                 pady=40)
            graph_frame.pack(fill="x", pady=10, padx=30)
            
            canvas = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            toolbar = NavigationToolbar2Tk(canvas, graph_frame)
            toolbar.update()
            canvas._tkcanvas.pack(fill="x")
        
    def next_page(self):
        self.controller.show_frame("GraphPage")
    
    def last_page(self):
        self.controller.show_frame("ShapPage")


    
# Class for a scrollable frame 
class ScrollableFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind("<Enter>", self.bind_mousewheel)
        self.scrollable_frame.bind("<Leave>", self.unbind_mousewheel)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="frame")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind("<Configure>", self.on_canvas_configure)
    
    def on_canvas_configure(self, event):
        self.canvas.itemconfigure("frame", width=event.width)

    def bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

    def unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")





# ------- UNUSED CLASSES (the Stats page and graph page were combined to make the StatsResultsPage above) ------ #

# Old stats display page - not used
# class StatsResultsPage(ttk.Frame):
#     def __init__(self, parent, controller):
#         tk.Frame.__init__(self, parent)
#         self.controller = controller
        
#         self.grid_rowconfigure(0, weight=1)
#         self.grid_columnconfigure(0, weight=1)  

#         self.frame = ttk.Frame(self)
#         self.frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

#         self.frame.grid_rowconfigure(0, weight=0)
#         self.frame.grid_rowconfigure(1, weight=0)
#         self.frame.grid_rowconfigure(2, weight=0)
#         self.frame.grid_rowconfigure(3, weight=0)
#         self.frame.grid_rowconfigure(7, weight=1)
#         self.frame.grid_columnconfigure(0, weight=2)  
#         self.frame.grid_columnconfigure(1, weight=0)  
#         self.frame.grid_columnconfigure(2, weight=2)  


#         # ---------- BANNER -----------
#         banner = tk.Frame(self.frame, height=150)
#         banner.config(bg='lightblue')
#         banner.grid(row=0, column=0, columnspan=3, sticky='nsew', pady=(0, 20), padx=0)

#         back_button = ctk.CTkButton(banner, text="⇦  Back to Feature Significance", width=75, height=30, command=self.last_page)
#         back_button.pack(side=tk.LEFT, padx=30, pady=10)
        

#         instruction_title_label = tk.Label(banner, text="Stats Overview", font=("Calibri Light", 24, 'bold'), justify="center")
#         instruction_title_label.config(bg='lightblue')
#         instruction_title_label.pack(side=tk.LEFT, expand=True, fill="x", padx=30, pady=30)

#         next_button = ctk.CTkButton(banner, text="View Graphs  ⇨", width=150, height=30, command=self.next_page)
#         next_button.pack(side=tk.RIGHT, padx=30, pady=10)

#         self.exit_button = ctk.CTkButton(self.frame, text="Exit", command=lambda: self.controller.destroy(), width=75, fg_color='red', hover_color='darkred')
#         self.exit_button.grid(row=7, column=0, padx=20, pady=10, sticky="se", columnspan=3)


#     # Load in and display stat results
#     def display_results(self, stats_data):
#         row = 1
#         for signal, categories in stats_data.items():
#             if categories['baseline'] is not None:
#                 table_label = tk.Label(self.frame, text=f"{signal.upper()} Stats", font=('Calibri Light', 16, 'bold'))
#                 table_label.grid(row=row, column=1, sticky="nsew", padx=7, pady=7)

#                 table = ttk.Treeview(self.frame, columns=["Stat Type", "Baseline", "Test", "Difference", "Flag"], show="headings", height=4)
#                 table.grid(row=row+1, column=1, sticky="nsew", padx=7, pady=7)
                
#                 table.heading("Stat Type", text="Stat Type", anchor="w")
#                 table.heading("Baseline", text="Baseline", anchor="center")
#                 table.heading("Test", text="Test", anchor="center")
#                 table.heading("Difference", text="Difference", anchor="center")
#                 table.heading("Flag", text="Flag", anchor="center")
                
#                 table.column("Stat Type", width=100, anchor="w")
#                 table.column("Baseline", width=180, anchor="center")
#                 table.column("Test", width=180, anchor="center")
#                 table.column("Difference", width=180, anchor="center")
#                 table.column("Flag", width=180, anchor="center")

#                 style = ttk.Style()
#                 style.configure("Treeview", font=("Calibri Light", 10), rowheight=30) 
#                 style.configure("Treeview.Heading", font=("Calibri Light", 12, "bold")) 

#                 stat_types = ['max', 'min', 'mean', 'std_dev']

#                 table.tag_configure("even", background="#E1EEFF")
#                 table.tag_configure("odd", background="#E7F7FA")

#                 for i, stat in enumerate(stat_types):
#                     tag = "even" if i % 2 == 0 else "odd"
#                     baseline_value = categories['baseline'].get(stat, 'N/A')
#                     test_value = categories['test'].get(stat, 'N/A')
#                     diff_value = categories['diff'].get(stat, 'N/A')
#                     flag = categories['flags'].get(stat, 'N/A')

#                     baseline_value = f"{baseline_value:.4f}" if baseline_value != 'N/A' and not np.isnan(baseline_value) else 'N/A'
#                     test_value = f"{test_value:.4f}" if test_value != 'N/A' and not np.isnan(test_value) else 'N/A'
#                     diff_value = f"{diff_value:.4f}%" if diff_value != 'N/A' and not np.isnan(diff_value) else 'N/A'
                
#                     table.insert("", "end", values=(stat, baseline_value, test_value, diff_value, flag), tags=(tag,))
                
#                 row += 2
#     def next_page(self):
#         self.controller.show_frame("GraphPage")
    
#     def last_page(self):
#         self.controller.show_frame("ShapPage")




# Old graph display page - not in use currently
class OldGraphPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.figs = [] 
        
        # Main container
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.title_label = tk.Label(self.main_frame, text="Analysis Graphs", font=('Calibri Light', 16, 'bold'))
        self.title_label.pack(pady=(0, 15))
        
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(self.button_frame, text="Show old results", command=lambda: controller.show_frame("OldResultsPage")).pack(side="right", padx=5)
        ctk.CTkButton(self.button_frame, text="Back to Results", command=lambda: controller.show_frame("ResultsPage")).pack(side="right", padx=5)
    
    def load_graphs(self, graphs_dict):
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        self.figs.clear()
        
        for category, graphs in graphs_dict.items():
            if not graphs:
                continue
                
            tab_frame = ScrollableFrame(self.notebook)
            self._add_graphs_to_tab(tab_frame.scrollable_frame, category, graphs)
            self.notebook.add(tab_frame, text=category)
        
        self.update_idletasks()
    
    def _add_graphs_to_tab(self, parent_frame, category, graphs):
        tk.Label(parent_frame,
                text=category,
                font=('Calibri Light', 14, 'bold'),
                pady=10).pack(fill="x")
        
        for i, fig in enumerate(graphs, 1):
            self.figs.append(fig) 
            
            fig.set_size_inches(8, 4)
            
            graph_frame = tk.Frame(parent_frame, 
                                 bd=1, 
                                 relief="groove",
                                 padx=10, 
                                 pady=10)
            graph_frame.pack(fill="x", pady=10)
            
            tk.Label(graph_frame,
                   text=f"Graph {i}",
                   font=('Calibri Light', 11)).pack()
            
            canvas = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            toolbar = NavigationToolbar2Tk(canvas, graph_frame)
            toolbar.update()
            canvas._tkcanvas.pack(fill="x")






if __name__ == "__main__":
    app = MainApp()
    app.mainloop()


