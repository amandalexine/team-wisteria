import pyttsx3
import numpy as np
import pygame
import time
import keyboard
 
def tts(text, rate):
    engine = pyttsx3.init()
    engine.setProperty('rate', rate)

    engine.say(text)
    engine.runAndWait()
 
# Initialize pygame mixer
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
 
# Function to create a sine wave
def create_sine_wave(freq, db_volume, duration=1):
    linear_volume = db_to_linear(db_volume)
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.sin(freq * 2 * np.pi * t) * (2**15 - 1) * linear_volume
    wave = wave.astype(np.int16)
    contiguous_wave = np.ascontiguousarray(np.array([wave, wave]).T, dtype=np.int16)
    sound = pygame.sndarray.make_sound(contiguous_wave)
    return sound
 
# Function to convert dB to linear scale
def db_to_linear(db):
    return 10 ** (db / 20)
 
# Function to play a quieter beep and adjust volume
def play_quieter_beep():
    global final_volume_db
    db_volume = -30  # Start at -30 dB
    while True:
        if keyboard.is_pressed('h'):
            db_volume -= 3
            beep = create_sine_wave(1000, db_volume, duration=1)
            beep.play()
            print(f"Volume: {db_volume} dB")
            time.sleep(1)
        elif keyboard.is_pressed('k'):
            db_volume += 3
            beep = create_sine_wave(1000, db_volume, duration=1)
            beep.play()
            print(f"Volume: {db_volume} dB")
            time.sleep(1)
        elif keyboard.is_pressed('t'):
            final_volume_db = db_volume
            print(f"Final volume saved at {final_volume_db} dB")
            break
        elif keyboard.is_pressed('r'):
            db_volume = -30
            print("Restarting test to -30 dB")
            time.sleep(1)
        time.sleep(0.1)  # Prevents too rapid execution
    return final_volume_db
 
# Function to play the sine wave for a specified time in minutes
def play_for_time(secs, final_volume_db ,freq=1000):
    beep = create_sine_wave(freq, final_volume_db, duration=secs)
    beep.play()  # Play indefinitely
    time.sleep(secs)
    beep.stop()