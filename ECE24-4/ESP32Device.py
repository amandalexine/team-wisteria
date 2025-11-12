import serial
import serial.tools.list_ports
import time
import hearingTest as sound

# Device class for connecting to the ESP32 Hardware over Bluetooth
class Device():
    def __init__(self):
        """
        Initializes the Device object by scanning available COM ports
        and setting up internal state variables.
        """

        self.com_ports = [port.device for port in list(serial.tools.list_ports.comports())]
        self.baud_rate = 115200  # Baud rate for the serial connection
        self.ser = None # Serial object to hold the connection
        self.device_found = False # Flag to check if the device is found
        self.signal_data = [] # List to store captured signal data
        self.port = None 


    def collect_data(self, sampling_rate, duration, emg_vals, ecg_vals, eda_vals, channel, controller, audio_text):
        """
        Connects to the ESP32 device via serial communication and collects
        bioelectric signal data (EMG, ECG, EDA) for a specified duration.

        Args:
            sampling_rate (int): Data collection rate in Hz.
            duration (int): Length of time (in seconds) to record data.
            emg_vals (list): List to store EMG samples.
            ecg_vals (list): List to store ECG samples.
            eda_vals (list): List to store EDA samples.
            channel (list[bool]): Boolean list [EMG, ECG, EDA] specifying
                                  which signals are active.
            controller (object): GUI controller object for managing pages.
            audio_text (str): Audio message to announce at start of collection.

        Returns:
            int: Returns -1 if connection fails, otherwise None.
        """

        # If no port assigned yet, attempt to find the device automatically
        if self.port is None:
            sound.tts("Connecting to device, please wait", 150)
            for port in self.com_ports:
                try:
                    # Attempt to open serial connection to each COM port
                    try:
                        ser = serial.Serial(port, self.baud_rate, timeout=0.1) 
                        ser.setDTR(False) # Helps reduce lag on Arduino plotting
                        print(f"Connected to {port} at {self.baud_rate} baud.")
                    except Exception as e:
                        print(f"Failed to open serial port: {port}")
                        continue

                    start_time = time.time()

                    # Try reading one line to confirm the device identity
                    while True:
                        if ser.in_waiting > 0:
                            data = ser.readline().decode('utf-8').rstrip() # Reads in comma seperated value to check if correct Com Port
                            print(f"Data: {data}")
                            
                            # Device sends 3 comma-separated values (EMG, ECG, EDA)
                            if len(data.split(',')) == 3:
                                self.device_found = True
                                self.ser = ser
                                self.port = port
                            break 

                        # timeout after 1 second
                        if time.time() - start_time > 1:
                            break
                        time.sleep(0.1) 
                    
                    if self.device_found:
                        sound.tts("Connected to device.", 150)
                        break
                    else:
                        print(f"Closing port {port}")
                        ser.close()

                except Exception as e:
                    print("Failed to open serial port:", e)
                    exit(1)
        # If the port was already identified before, reconnect directly
        else:
            self.device_found = True
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=0.1)
            self.ser.setDTR(False)
        
        # send an error if no device was found on any port
        if not self.device_found:
            print("Device not found on any of the specified COM ports.")
            sound.tts("Unable to connect to device.", 150)
            controller.show_frame("ErrorPage")
            return -1

       # Notify the user and start data collection
        sound.tts(audio_text, 150)
        controller.frames["LoadingPage"].set_load_title("Collecting data...")

        start_time = time.time()
        num_samples = sampling_rate * duration
        data_values = []

        # clear out buffer before starting data collection
        self.ser.reset_input_buffer()
        while len(ecg_vals) < num_samples and len(emg_vals) < num_samples and len(eda_vals) < num_samples:
            while self.ser.in_waiting:
                try:
                    data_values = self.ser.readline().decode('utf-8').strip().split(',') # Reads in comma seperated ECG,EMG,EDA

                    # Append data if enabled
                    if channel[0] == True:
                        emg_vals.append(float(data_values[1]))
                    if channel[1] == True:
                        ecg_vals.append(float(data_values[0]))
                    if channel[2] == True:
                        eda_vals.append(float(data_values[2]))

                    # place holders are 1 if the channel is diabled
                    if channel[0] == False:
                        emg_vals.append(1)
                    if channel[1] == False:
                        ecg_vals.append(1)
                    if channel[2] == False:
                        eda_vals.append(1)

                except Exception as e:
                    print("Read error:", e)
                    print(data_values)
                    break

    def stop(self):
        """
        Closes the serial connection and resets device state.
        """
        
        print("Device Stopped")
        self.ser.close()
        self.device_found = False