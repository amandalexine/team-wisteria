import pyttsx3
import numpy as np
import pygame
import time
import keyboard

# ---------------------------------------------------------------------------
# TEXT-TO-SPEECH FUNCTION
# ---------------------------------------------------------------------------
def tts(text, rate):
    """
    Speak a given text aloud using a text-to-speech engine.

    Args:
        text (str): The text to be spoken.
        rate (int): The speed (words per minute) of the speech.

    Purpose:
        This is used for auditory prompts, such as instructing the user
        during a hearing test (e.g., “Press H to make it quieter”).
    """
    # Initialize the text-to-speech engine
    engine = pyttsx3.init()
    # Set how fast the speech will be spoken
    engine.setProperty('rate', rate)
    # Queue the text to be spoken and then play it
    engine.say(text)
    engine.runAndWait()
 
# ---------------------------------------------------------------------------
# INITIALIZE PYGAME AUDIO SYSTEM
# ---------------------------------------------------------------------------
# Pygame's mixer is what actually plays the audio.
# We set it up with standard audio parameters.

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
 
# ---------------------------------------------------------------------------
# GENERATE A SINE WAVE SOUND
# ---------------------------------------------------------------------------
def create_sine_wave(freq, db_volume, duration=1):
    """
    Generate and return a sine wave sound at a given frequency and volume.

    Args:
        freq (float): Frequency of the sine wave in Hz (e.g., 1000 for 1kHz tone).
        db_volume (float): Desired volume in decibels (dB).
        duration (float): Duration of the tone in seconds. Default is 1 sec.

    Returns:
        pygame.mixer.Sound: A playable sound object containing the sine wave.

    Logic:
        1. Convert dB volume to a linear amplitude scale.
        2. Generate a time array for the desired duration.
        3. Compute sine wave values at each sample.
        4. Format wave into stereo (two channels).
        5. Convert to a Pygame-compatible audio buffer for playback.
    """
    # Convert decibel scale to linear amplitude (0.0 to 1.0)
    linear_volume = db_to_linear(db_volume)
    # Audio parameters
    sample_rate = 44100
    # Generate evenly spaced time values for one duration
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Create the sine wave: A(t) = sin(2πft)
    wave = np.sin(freq * 2 * np.pi * t) * (2**15 - 1) * linear_volume
    # Convert wave from float to 16-bit integer format
    wave = wave.astype(np.int16)
    # Create a stereo version of the signal (duplicate for both channels)
    contiguous_wave = np.ascontiguousarray(np.array([wave, wave]).T, dtype=np.int16)
    # Convert numpy array into a Pygame Sound object
    sound = pygame.sndarray.make_sound(contiguous_wave)
    return sound
 
# ---------------------------------------------------------------------------
# DECIBEL TO LINEAR CONVERSION
# ---------------------------------------------------------------------------
def db_to_linear(db):
    """
    Convert a decibel (dB) value to a linear amplitude ratio.

    Args:
        db (float): Decibel value (negative for attenuation).

    Returns:
        float: Linear amplitude (1.0 = max volume, 0.0 = silence).

    Example:
        -20 dB → 0.1 linear volume
    """
    return 10 ** (db / 20)
 
# ---------------------------------------------------------------------------
# INTERACTIVE VOLUME ADJUSTMENT FUNCTION
# ---------------------------------------------------------------------------
def play_quieter_beep():
    """
    Interactive hearing test where the user adjusts beep volume using keys.

    Controls:
        - Press 'h' → decrease volume by 3 dB (make quieter)
        - Press 'k' → increase volume by 3 dB (make louder)
        - Press 'r' → reset to starting volume (-30 dB)
        - Press 't' → save current volume and end the test

    Returns:
        float: The final volume level (in dB) chosen by the user.

    Logic:
        Starts at -30 dB and plays a 1 kHz tone each time the user adjusts
        volume. The user can fine-tune until the quietest audible level is found.
    """
    global final_volume_db
    db_volume = -30  # Start at -30 dB
    while True:
        if keyboard.is_pressed('h'):
            # Make the beep quieter
            db_volume -= 3
            beep = create_sine_wave(1000, db_volume, duration=1)
            beep.play()
            print(f"Volume: {db_volume} dB")
            time.sleep(1)
        elif keyboard.is_pressed('k'):
            # Make the beep louder
            db_volume += 3
            beep = create_sine_wave(1000, db_volume, duration=1)
            beep.play()
            print(f"Volume: {db_volume} dB")
            time.sleep(1)
        elif keyboard.is_pressed('t'):
             # Save current volume and stop
            final_volume_db = db_volume
            print(f"Final volume saved at {final_volume_db} dB")
            break
        elif keyboard.is_pressed('r'):
            # Restart the test from the initial volume
            db_volume = -30
            print("Restarting test to -30 dB")
            time.sleep(1)
        
        time.sleep(0.1)  # Prevents too rapid execution; short delay between loop checks to avoid CPU overload
    return final_volume_db
 

# ---------------------------------------------------------------------------
# PLAY A CONTINUOUS TONE FOR A SET TIME
# ---------------------------------------------------------------------------
def play_for_time(secs, final_volume_db ,freq=1000):
    """
    Play a continuous sine wave for a specified number of seconds.

    Args:
        secs (float): How long to play the tone, in seconds.
        final_volume_db (float): Volume level in dB for playback.
        freq (float): Frequency of tone in Hz (default = 1000 Hz).

    Purpose:
        Used for sustained tone playback once the hearing threshold
        has been determined from play_quieter_beep().
    """
    beep = create_sine_wave(freq, final_volume_db, duration=secs)
    beep.play()  # Play indefinitely
    time.sleep(secs)
    # Start playing the sound
    beep.stop()
