// SoundSenseTest.h
#ifndef SoundSenseTest_h
#define SoundSenseTest_h

#include <Arduino.h>
#include "DACPlayer.h"
#include "FS.h"
#include "SD.h"
#include "SPI.h"
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <HardwareSerial.h>

#define IDLE 0 // idle
#define INITIALIZE 1 // init
#define COLLECT 2 // collect data
#define SAVE 3 // save csv to sd card
#define ADJUST 4 //adjust volume
#define ERROR 5
#define PRETEST 6 // check for flatlines

class SoundSenseTest {
  private:
    int patient_num;
    unsigned char ledState;
    int sampling_rate_hz;
    int duration_s;
    int bluePin;
    int redPin;

    DACPlayer dac;

    float ecg_vals[6000];
    float emg_vals[6000];
    float eda_vals[6000];
    unsigned long timestamps[6000];
    
    void initADC();
    void initSDCard();
    void initRGB();
    void readData(int num_samples);
    void writeFile(int num_samples, String filename);
    void adjustVolume();
    bool areBothPressed();
    void setColor(int state);
    bool signalPretest();
    bool isFlatline(float* vals, int n);

  public:
    SoundSenseTest(int patient_id, int rate, int duration, int blueButtonPin, int redButtonPin);
    void init();
    void run(int test_num);
    int getState();
    DACPlayer& getDAC();
};

#endif