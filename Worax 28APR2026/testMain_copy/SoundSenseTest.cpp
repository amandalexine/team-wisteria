// SoundSenseTest.cpp
#include "SoundSenseTest.h"

// for adc
Adafruit_ADS1115 ads;
HardwareSerial BITalino(2);

#define ADS1115_ADDRESS 0x48
#define I2C_SDA 21
#define I2C_SCL 22

#define CS_PIN 5
// these are default, but here for reference
// #define DI_PIN 23
// #define DO_PIN 19
// #define CLK_PIN 18

// for rgb led
#define RED_PIN   32 //25
#define GREEN_PIN 33 //26
#define BLUE_PIN  14 //27
#define PWM_FREQ 5000
#define PWM_RES  8   // 0–255

#define FLATLINE_THRESHOLD 0.01f  // volts

SoundSenseTest::SoundSenseTest(int patient_id, int rate, int duration, int blueButtonPin, int redButtonPin) {
  patient_num = patient_id;
  sampling_rate_hz = rate;
  duration_s = duration;
  redPin = redButtonPin;
  bluePin = blueButtonPin;
  ledState = 0;
}

void SoundSenseTest::init() {
  pinMode(redPin,  INPUT_PULLUP);
  pinMode(bluePin, INPUT_PULLUP);

  initRGB(); //rgb led
  delay(500);
  setColor(INITIALIZE);
  Serial.begin(115200);
  delay(1000);
  initSDCard(); // spi sd card
  delay(1000); 
  initADC(); // wire begin for i2c/i2s
  delay(1000);
  dac.init(); //assumes wiree has started
  delay(500);

  // BITalino connection on UART2 (RX2=GPIO16, TX2=GPIO17)
  BITalino.begin(115200, SERIAL_8N1, 16, 17); // RX=16, TX=17
  
  delay(1000);
  
  // Test communication - get firmware version
  Serial.println("Requesting BITalino version...");
  BITalino.write(0x07);
  delay(500);
  
  // Read version response (if any)
  while (BITalino.available()) {
    char c = BITalino.read();
    Serial.print(c);
  }
  Serial.println();

  delay(2000); // extra delay so it's obvious everything has initialized
  Serial.println("Ready. Press blue to adjust audio.");
  setColor(IDLE);
}

void SoundSenseTest::run(int test_num) {
  
  int num_samples = sampling_rate_hz * duration_s;
  //String folder = "/SoundSenseTest" + String(patient_num);
  int test_count = 1;
  String folder;

  // Find the next available session folder
  while (true) {
    folder = "/SoundSenseTest_" + String(test_count);
    if (!SD.exists(folder)) {
      break;
    }
    test_count++;
  }

    // Create the new folder
  if (SD.mkdir(folder)) {
    Serial.println("Created: " + folder);
  } else {
    Serial.println("Folder creation failed");
  }

  // if (!SD.exists(folder)) {
  //   delay(500);
  //   // if the folder doesn't exist make a new one
  //   if (SD.mkdir(folder)) {
  //     Serial.println("Folder created successfully");
  //   } else {
  //     Serial.println("Folder creation failed");
  //   }
  // }

  // adjust volume
  adjustVolume();
  delay(1000);

  //setColor(PRETEST);
  while (!signalPretest()) {
    Serial.println("Fix sensors and press blue to retry. Red to ignore");
    // Wait until either button is pressed
    while (digitalRead(bluePin) == HIGH && digitalRead(redPin) == HIGH) {
        delay(10); 
    }

    // If Red was pressed, break out of the loop and move on
    if (digitalRead(redPin) == LOW) {
        Serial.println("Skipping pretest");
        break; 
    }
    delay(200);
  }

  //baseline
  Serial.println("Doing Baseline");
  String filename = folder + "/baseline_sequence.txt";
  dac.stop(); // make quiet
  readData(num_samples);
  delay(1500);
  writeFile(num_samples, filename);
  delay(1000);

  //response
  Serial.println("Doing Response");
  filename = folder + "/test_sequence.txt";
  dac.play(); //start audio
  readData(num_samples);
  dac.stop(); //stop audio
  delay(1500);
  writeFile(num_samples, filename);

  Serial.println("Ended Test  ٩(ˊᗜˋ*)و ♡");
  setColor(IDLE);
}

void SoundSenseTest::initSDCard() {
  // Initialize SD card, CS connected to pin 5
  if (!SD.begin(CS_PIN)) {
    Serial.println("Card Mount Failed");
    return;
  }

  uint8_t cardType = SD.cardType();

  if (cardType == CARD_NONE) {
    Serial.println("No SD card attached");
    return;
  }

  Serial.println("SD Card Initialized ✧｡٩(ˊᗜˋ )و✧*｡");
}

void SoundSenseTest::initRGB() {
  ledcAttach(RED_PIN, PWM_FREQ, PWM_RES);
  ledcAttach(GREEN_PIN, PWM_FREQ, PWM_RES);
  ledcAttach(BLUE_PIN, PWM_FREQ, PWM_RES);
}

void SoundSenseTest::initADC() {
  Wire.begin(I2C_SDA, I2C_SCL);

  delay(1000);
  // Initialize ADS1115
  if (!ads.begin(ADS1115_ADDRESS)) {
    Serial.println("Failed to initialize ADS1115");
    while (1) { delay(10); }
  }else{
    Serial.println("ADS1115 has begun");
  }

  ads.setGain(GAIN_ONE); // range should be ~1.4-2.1 V based on what i see on the oscilloscope
  ads.setDataRate(RATE_ADS1115_860SPS); // roughly 860 samples/second Hz, picked the fastest bc extra delays in executing code

  Serial.println("Done initializing ADS1115 ദ്ദി( • ᴗ - ) ✧");
}

void SoundSenseTest::adjustVolume() {
  setColor(ADJUST);
  Serial.println("adjusting volume");

  dac.play();
  while(!areBothPressed()){
    dac.handleButtons(bluePin, redPin);
  }
  dac.stop();
}

bool SoundSenseTest::signalPretest() {
  int num_pretest_samples = min(sampling_rate_hz * 10, 6000);
  readData(num_pretest_samples);

  // Check each channel's peak-to-peak range
  bool ecg_ok = !isFlatline(ecg_vals, num_pretest_samples);
  bool emg_ok = !isFlatline(emg_vals, num_pretest_samples);
  bool eda_ok = !isFlatline(eda_vals, num_pretest_samples);

  if (!ecg_ok) Serial.println("WARNING: ECG appears to be a flat line!");
  if (!emg_ok) Serial.println("WARNING: EMG appears to be a flat line!");
  if (!eda_ok) Serial.println("WARNING: EDA appears to be a flat line!");

  if (ecg_ok && emg_ok && eda_ok) {
    Serial.println("Signal pretest passed — all channels look good");
    //setColor(IDLE);
    return true;
  }

  // red to indicate bad signal
  setColor(ERROR);
  return false;
}

bool SoundSenseTest::isFlatline(float* vals, int n) {
  float minVal = vals[0];
  float maxVal = vals[0];

  for (int i = 1; i < n; i++) {
    if (vals[i] < minVal) minVal = vals[i];
    if (vals[i] > maxVal) maxVal = vals[i];
  }

  float range = maxVal - minVal;
  Serial.printf("  Signal range: %.4f V (threshold: %.4f V)\n",
                range, FLATLINE_THRESHOLD);

  return (range < FLATLINE_THRESHOLD);
}

bool SoundSenseTest::areBothPressed() {
  return (digitalRead(bluePin) == LOW && digitalRead(redPin) == LOW);
}

int SoundSenseTest::getState() {
  return ledState;
}

void SoundSenseTest::readData(int num_samples) {
  setColor(COLLECT);

  BITalino.write((byte)0x00); 
  delay(200);

  while (BITalino.available()) BITalino.read();

  // set sampling rate
  BITalino.write((byte)0xC3); 
  delay(100);

  //Serial.println("Starting BITalino acquisition...");
  BITalino.write((byte)0x1D); // 1000 Hz, channels A1, A2, A3
  unsigned long startWait = millis();
  while (millis() - startWait < 50) {
      if (BITalino.available()) BITalino.read();
  }

  Serial.println("Reading in Data");

  int16_t adc0, adc1, adc2;
  unsigned long start_time, sample_time;
  start_time = millis();

  for (int i = 0; i < num_samples; i++) {
    sample_time = millis();
    while (BITalino.available()) BITalino.read();

    adc0 = ads.readADC_SingleEnded(0);
    adc1 = ads.readADC_SingleEnded(1);
    adc2 = ads.readADC_SingleEnded(2);
    ecg_vals[i] = ads.computeVolts(adc0) - 1.65;
    emg_vals[i] = ads.computeVolts(adc1) - 1.65;
    eda_vals[i] = ads.computeVolts(adc2) - 1.65;
    timestamps[i] = sample_time - start_time;
    delay(2); //adjust to get 100Hz
  }

  Serial.println("Done Reading in Data");
  // Stop BITalino
  BITalino.write((byte)0xFF);

  //setColor(IDLE);
  delay(1000);
}

void SoundSenseTest::writeFile(int num_samples, String filename) {
  setColor(SAVE);
  Serial.println("Writing File");

  delay(1000);

   // Create and write to a file
  File file = SD.open(filename, FILE_WRITE);

  if (!file) {
    Serial.println("Failed to open file");
    return;
  }

  file.println("Timestamp (ms), ECG (V), EMG (V), EDA(V)");

  for (int i = 0; i < num_samples; i++) {
    file.print(timestamps[i]);
    file.print(", ");
    file.print(ecg_vals[i], 6);
    file.print(", ");
    file.print(emg_vals[i], 6);
    file.print(", ");
    file.println(eda_vals[i], 6);
  }

  file.close();
  Serial.println("File written successfully");
  delay(1000);
  //setColor(IDLE);
}

void SoundSenseTest::setColor(int state) {

  int r = 0, g = 0, b = 0;

  switch(state) {
    case IDLE:        // green
      r = 0; g = 50; b = 0;
      break;

    case INITIALIZE:  // yellow
      r = 50; g = 50; b = 0;
      break;

    case COLLECT:     // blue
      r = 0; g = 0; b = 50;
      break;

    case SAVE:        // purple
      r = 50; g = 0; b = 50;
      break;

    case ADJUST:    // cyan
      r = 0; g = 50; b = 50;
      break;

    case ERROR:   // red
      r = 50; g = 0; b = 0;
      break;

    case PRETEST:   // pink?
      r = 50; g = 0; b = 20;
      break;

    default:
      r = 0; g = 0; b = 0;
  }

  // Invert for common anode
  ledcWrite(RED_PIN,   255 - r);
  ledcWrite(GREEN_PIN, 255 - g);
  ledcWrite(BLUE_PIN,  255 - b);

  ledState = state;
}
