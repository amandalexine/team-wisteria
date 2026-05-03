#include "DACPlayer.h"

DACPlayer::DACPlayer() {
  audioRunning = false;
  audioTaskHandle = NULL;
  sinePhase = 0.0f;
  currentVolReg = VOL_DEFAULT;
}

void DACPlayer::init() {
  // Hardware reset
  pinMode(DAC_RESET_PIN, OUTPUT);
  digitalWrite(DAC_RESET_PIN, LOW); delay(100);
  digitalWrite(DAC_RESET_PIN, HIGH); delay(10);

  // Wire.begin() already called by SoundSenseTest
  if (!codec.begin()) { Serial.println("Codec init failed!"); return; }

  codec.setCodecInterface(TLV320DAC3100_FORMAT_I2S, TLV320DAC3100_DATA_LEN_16);
  codec.setCodecClockInput(TLV320DAC3100_CODEC_CLKIN_PLL);
  codec.setPLLClockInput(TLV320DAC3100_PLL_CLKIN_BCLK);
  codec.setPLLValues(PLL_P, PLL_R, PLL_J, PLL_D);
  codec.setNDAC(true, NDAC_VAL);
  codec.setMDAC(true, MDAC_VAL);
  codec.powerPLL(true);
  codec.setDACDataPath(true, true, TLV320_DAC_PATH_NORMAL,
                       TLV320_DAC_PATH_NORMAL, TLV320_VOLUME_STEP_1SAMPLE);
  codec.configureAnalogInputs(TLV320_DAC_ROUTE_MIXER, TLV320_DAC_ROUTE_MIXER,
                              false, false, false, false);
  codec.setDACVolumeControl(false, false, TLV320_VOL_INDEPENDENT);
  codec.setChannelVolume(false, 0);
  codec.setChannelVolume(true,  0);
  codec.configureHeadphoneDriver(true, true, TLV320_HP_COMMON_1_35V, false);
  codec.configureHPL_PGA(0, true);
  codec.configureHPR_PGA(0, true);
  codec.setHPLVolume(true, VOL_DEFAULT);
  codec.setHPRVolume(true, VOL_DEFAULT);
  codec.enableSpeaker(false);

  // I2S
  i2s_config_t i2s_config = {
    .mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate          = SAMPLE_RATE,
    .bits_per_sample      = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format       = I2S_CHANNEL_FMT_RIGHT_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count        = 8,
    .dma_buf_len          = BUFFER_SAMPLES,
    .use_apll             = false,
    .tx_desc_auto_clear   = true,
    .fixed_mclk           = 0
  };
  i2s_pin_config_t pin_config = {
    .bck_io_num   = I2S_BCLK,
    .ws_io_num    = I2S_LRCLK,
    .data_out_num = I2S_DOUT,
    .data_in_num  = I2S_PIN_NO_CHANGE
  };
  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
  i2s_zero_dma_buffer(I2S_PORT);

  // Start audio task on core 0
  xTaskCreatePinnedToCore(
    audioTaskWrapper,
    "AudioTask",
    4096,
    this,
    1,
    &audioTaskHandle,
    0
  );

  Serial.println("DACPlayer initialized");
}

void DACPlayer::play() {
  audioRunning = true;
}

void DACPlayer::stop() {
  audioRunning = false;
  i2s_zero_dma_buffer(I2S_PORT);
}

void DACPlayer::setVolume(int reg) {
  currentVolReg = constrain(reg, VOL_REG_MIN, VOL_REG_MAX);
  codec.setChannelVolume(false, currentVolReg);
  codec.setChannelVolume(true,  currentVolReg);

  codec.setHPLVolume(true, currentVolReg);
  codec.setHPRVolume(true, currentVolReg);

  Serial.printf("Volume: %.1f dB\n", currentVolReg * -0.5f);
}

void DACPlayer::handleButtons(int bluePin, int redPin) {
  static unsigned long lastPress = 0;
  unsigned long now = millis();
  if (now - lastPress < DEBOUNCE_MS) return;

  if (digitalRead(bluePin) == LOW) {
    setVolume(currentVolReg + VOL_STEP);
    lastPress = now;
  } else if (digitalRead(redPin) == LOW) {
    setVolume(currentVolReg - VOL_STEP);
    lastPress = now;
  }
}

bool DACPlayer::isPlaying() {
  return audioRunning;
}

void DACPlayer::audioTaskWrapper(void* param) {
  static_cast<DACPlayer*>(param)->audioTaskLoop();
}

void DACPlayer::audioTaskLoop() {
  static int16_t buf[BUFFER_SAMPLES * 2];
  const float inc = 2.0f * M_PI * SINE_FREQ / SAMPLE_RATE;

  while (true) {
    if (audioRunning) {
      for (int i = 0; i < BUFFER_SAMPLES; i++) {
        int16_t s = (int16_t)(AMPLITUDE * sinf(sinePhase));
        buf[i * 2]     = s;
        buf[i * 2 + 1] = s;
        sinePhase += inc;
        if (sinePhase >= 2.0f * M_PI) sinePhase -= 2.0f * M_PI;
      }
      size_t written;
      i2s_write(I2S_PORT, buf, sizeof(buf), &written, portMAX_DELAY);
    } else {
      vTaskDelay(pdMS_TO_TICKS(10));
    }
  }
}