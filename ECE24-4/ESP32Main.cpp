// FOR USE IN ARDUINO IDE


#include "BluetoothSerial.h"
#include <Adafruit_ADS1X15.h>
// Create the ADS1115 object
Adafruit_ADS1115 ads;
// Name of the Bluetooth device
String device_name = "ESP32-BT";
// Check Bluetooth availability
#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled! Please enable it in your menuconfig.
#endif
// Check Serial Port Profile
#if !defined(CONFIG_BT_SPP_ENABLED)
#error Serial Port Profile (SPP) for Bluetooth is not enabled on your ESP32.
#endif
//to start reading adc
bool starting = true;
BluetoothSerial SerialBT;
void setup() {
  Serial.begin(115200);
  delay(1000);
  SerialBT.begin(device_name); // Start Bluetooth with given name
  Serial.println("Bluetooth device started. Pair with \"" + device_name + "\".");
//   Initialize ADS1115
   if (!ads.begin()) {
     Serial.println("Failed to initialize ADS1115!");
     while (1) { delay(10); }
   }
   //set ADC gain and data rate
   ads.setGain(GAIN_ONE); //max voltage 4.096 V
   ads.setDataRate(250);
}
void loop() {
  if (ads.conversionComplete() or starting) {
    int16_t adc0   = ads.readADC_SingleEnded(0);
    float   volts0 = ads.computeVolts(adc0);
    int16_t adc1 = ads.readADC_SingleEnded(1);
    float volts1 = ads.computeVolts(adc1);
    int16_t adc2 = ads.readADC_SingleEnded(2);
    float volts2 = ads.computeVolts(adc2);
    Serial.println(adc0);
    String dataPacket = String(volts0) + "," + String(volts1) + "," + String(volts2);
    SerialBT.println(dataPacket);
    starting = false;
  }
}