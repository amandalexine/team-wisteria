#include "FS.h"
#include "SD.h"
#include "SPI.h"
#include "SoundSenseTest.h"

enum DeviceState {
  IDLING = 0,
  INITIALIZING = 1,
  RUNNING = 2
};

enum Event {
  BLUE_PRESSED = 0,
  RED_PRESSED = 1,
  NONE_PRESSED = 2
};

DeviceState current_state = IDLING;
Event event = NONE_PRESSED;
const int red_button = 13;
const int blue_button = 12;

SoundSenseTest test(1, 100, 60, blue_button, red_button);
int test_num = 0;

void setup() {
  current_state = INITIALIZING;
  test.init();
  pinMode(red_button, INPUT_PULLUP);
  pinMode(blue_button, INPUT_PULLUP);
  delay(1000);
}

void loop() {

  read_buttons();

  switch (event) {
    case RED_PRESSED:
      // nothing yet
      break;
    case BLUE_PRESSED:
      // run test
      current_state = RUNNING;
      test.run(test_num);
      test_num = test_num + 1;
      break;
    default:
      // nothing yet
      break;
  }
  current_state = IDLING;

  delay(10);
}

void read_buttons() {
  int blue_button_val = digitalRead(blue_button);
  int red_button_val = digitalRead(red_button);

  // eventually change to account for both pressed or keeping track of edges in case button is pushed before we check
  if (blue_button_val == LOW) {
    event = BLUE_PRESSED;
    Serial.println("Blue pressed");
  } else if (red_button_val == LOW) {
    event = RED_PRESSED;
    Serial.println("red pressed");
  } else {
    event = NONE_PRESSED;
  }
}