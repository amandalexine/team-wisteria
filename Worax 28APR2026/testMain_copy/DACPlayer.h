#ifndef DACPlayer_h
#define DACPlayer_h

#include <Arduino.h>
#include <Adafruit_TLV320DAC3100.h>
#include <driver/i2s.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <math.h>

#define DAC_RESET_PIN  4
#define I2S_BCLK       26
#define I2S_LRCLK      25
#define I2S_DOUT       27 //23 used by SPI

#define SAMPLE_RATE     44100
#define I2S_PORT        I2S_NUM_0
#define SINE_FREQ       440
#define AMPLITUDE       1000
#define BUFFER_SAMPLES  256
#define VOL_DEFAULT     80
#define VOL_STEP        4
#define VOL_REG_MIN     0
#define VOL_REG_MAX     254
#define DEBOUNCE_MS     200

#define PLL_P 1
#define PLL_R 1
#define PLL_J 7
#define PLL_D 5264
#define NDAC_VAL 2
#define MDAC_VAL 8

class DACPlayer {
  private:
    Adafruit_TLV320DAC3100 codec;
    TaskHandle_t audioTaskHandle;
    volatile bool audioRunning;
    float sinePhase;
    int currentVolReg;

    static void audioTaskWrapper(void* param);
    void audioTaskLoop();

  public:
    DACPlayer();
    void init();               // call after Wire.begin()
    void play();
    void stop();
    void setVolume(int reg);
    void handleButtons(int bluePin, int redPin);
    bool isPlaying();
};

#endif