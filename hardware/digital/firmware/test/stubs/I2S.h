#pragma once
#include "Arduino.h"
class I2S {
 public:
  I2S(PinMode) {}
  bool setBCLK(pin_size_t) { return true; }
  bool setDATA(pin_size_t) { return true; }
  bool setBitsPerSample(int) { return true; }
  bool setBuffers(size_t, size_t, int32_t = 0) { return true; }
  bool begin(long) { return true; }
  size_t write16(int16_t, int16_t) { return 4; }
};
