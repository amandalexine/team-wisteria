// FOR USE IN ARDUINO IDE

#include "BluetoothSerial.h"
#include <Adafruit_ADS1X15.h>
// Create the ADS1115 object for analog input
Adafruit_ADS1115 ads;

// Name of the Bluetooth device when pairing
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

// setup()
// ---------------------------------------------------------------
// Purpose:
//   Initializes serial communication, Bluetooth, and the ADS1115 ADC.
// Description:
//   - Starts the serial monitor for debugging
//   - Initializes Bluetooth with the given name
//   - Configures the ADS1115 gain and data rate
//   - Prints status messages over the serial monitor

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
   ads.setDataRate(250); //250 samples/second
}

// loop()
// ---------------------------------------------------------------
// Purpose:
//   Continuously reads analog values from the ADS1115 and transmits
//   them as comma-separated voltage readings over Bluetooth.
// Description:
//   - Checks if ADC conversion is complete
//   - Reads from channels 0, 1, and 2
//   - Converts raw ADC counts to voltage
//   - Sends the three values over Bluetooth in CSV format
//   - Example message: "1.23,0.87,2.45"

void loop() {
  // Proceed only if a conversion has completed or it's the first loop iteration
  if (ads.conversionComplete() or starting) {
    // Read from ADS1115 channels 0–2 and convert the values into floats
    int16_t adc0   = ads.readADC_SingleEnded(0);
    float   volts0 = ads.computeVolts(adc0);
    int16_t adc1 = ads.readADC_SingleEnded(1);
    float volts1 = ads.computeVolts(adc1);
    int16_t adc2 = ads.readADC_SingleEnded(2);
    float volts2 = ads.computeVolts(adc2);

    // print one value (probs for debugging)
    Serial.println(adc0);

    // make csv fomat
    String dataPacket = String(volts0) + "," + String(volts1) + "," + String(volts2);
    
    // send data over bluetooth
    SerialBT.println(dataPacket);

    // done with first send, so only read/send data when the adc is done
    starting = false;
  }
}