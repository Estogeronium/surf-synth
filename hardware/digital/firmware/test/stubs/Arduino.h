// Minimal stand-ins so the sketch can be compiled on a PC (syntax and type check only).
#pragma once
#include <stdint.h>
#include <stddef.h>
typedef uint8_t pin_size_t;
enum PinMode { INPUT, OUTPUT };
enum { LOW = 0, HIGH = 1, MSBFIRST = 1, SPI_MODE0 = 0 };
inline void pinMode(pin_size_t, PinMode) {}
inline void digitalWrite(pin_size_t, int) {}
inline void analogWrite(pin_size_t, int) {}
inline void analogWriteFreq(uint32_t) {}
struct SPISettings { SPISettings(uint32_t, int, int) {} };
