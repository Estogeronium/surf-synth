#pragma once
#include "Arduino.h"
struct SPIClass {
  bool setRX(pin_size_t) { return true; }
  bool setTX(pin_size_t) { return true; }
  bool setSCK(pin_size_t) { return true; }
  void begin(bool = true) {}
  void beginTransaction(SPISettings) {}
  void endTransaction() {}
  uint8_t transfer(uint8_t v) { return v; }
};
extern SPIClass SPI;
