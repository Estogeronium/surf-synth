// Surf Synth (digital version): sound of waves and surf on a Raspberry Pi Pico 2.
//
//  - sound:    DSP from surf_dsp.h (a port of the web version) -> I2S -> MAX98357A -> speaker
//  - controls: 4 potentiometers (Surf, Tide, Tone, Volume) read through an MCP3008 over SPI
//  - LED:      brightness follows the current wave
//
// Arduino IDE: install the "Raspberry Pi Pico/RP2040/RP2350" core by Earle F. Philhower, III,
// choose the board "Raspberry Pi Pico 2", and put surf_dsp.h next to this file.

#include <Arduino.h>
#include <I2S.h>
#include <SPI.h>
#include "surf_dsp.h"

// ---- pins (GP numbers, not board pin numbers) ------------------------------------------------
constexpr pin_size_t PIN_I2S_DIN  = 9;    // board pin 12 -> MAX98357A DIN
constexpr pin_size_t PIN_I2S_BCLK = 10;   // board pin 14 -> MAX98357A BCLK (LRC must be the next pin: GP11)
constexpr pin_size_t PIN_I2S_LRC  = 11;   // board pin 15 -> MAX98357A LRC (set automatically = BCLK + 1)
constexpr pin_size_t PIN_SPI_MISO = 16;   // board pin 21 <- MCP3008 DOUT
constexpr pin_size_t PIN_ADC_CS   = 17;   // board pin 22 -> MCP3008 CS
constexpr pin_size_t PIN_SPI_SCK  = 18;   // board pin 24 -> MCP3008 CLK
constexpr pin_size_t PIN_SPI_MOSI = 19;   // board pin 25 -> MCP3008 DIN
constexpr pin_size_t PIN_LED      = 15;   // board pin 20 -> LED driver transistor

constexpr int SAMPLE_RATE = 32000;
constexpr float OUT_GAIN = 0.8f;          // keeps an 8 ohm speaker below ~1 W at full scale

// MCP3008 channels of the pots
constexpr int CH_SURF = 0, CH_TIDE = 1, CH_TONE = 2, CH_VOLUME = 3;

I2S i2s(OUTPUT);
surf::Engine engine((float)SAMPLE_RATE, 12345);
surf::Params params;

float potValue[4] = {0.5f, 0.45f, 0.5f, 0.6f};   // smoothed 0..1
bool potSeeded = false;

uint16_t readMcp3008(int channel) {
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
  digitalWrite(PIN_ADC_CS, LOW);
  SPI.transfer(0x01);                                   // start bit
  uint8_t hi = SPI.transfer(0x80 | (channel << 4));     // single-ended, channel
  uint8_t lo = SPI.transfer(0x00);
  digitalWrite(PIN_ADC_CS, HIGH);
  SPI.endTransaction();
  return ((hi & 0x03) << 8) | lo;
}

void readPots() {
  for (int ch = 0; ch < 4; ch++) {
    uint32_t sum = 0;
    for (int i = 0; i < 4; i++) sum += readMcp3008(ch);
    float v = sum / (4.0f * 1023.0f);
    // the top and bottom few counts are noise at the end stops
    v = (v - 0.01f) / 0.98f;
    v = v < 0 ? 0 : (v > 1 ? 1 : v);
    potValue[ch] = potSeeded ? potValue[ch] + 0.25f * (v - potValue[ch]) : v;
  }
  potSeeded = true;
  params.surf = potValue[CH_SURF];
  params.tide = potValue[CH_TIDE];
  params.tone = potValue[CH_TONE];
  params.volume = potValue[CH_VOLUME];
  engine.setParams(params);
}

void setup() {
  pinMode(PIN_LED, OUTPUT);
  analogWriteFreq(20000);
  pinMode(PIN_ADC_CS, OUTPUT);
  digitalWrite(PIN_ADC_CS, HIGH);
  SPI.setRX(PIN_SPI_MISO);
  SPI.setTX(PIN_SPI_MOSI);
  SPI.setSCK(PIN_SPI_SCK);
  SPI.begin(false);                       // chip select is handled by hand

  i2s.setBCLK(PIN_I2S_BCLK);              // LRCLK = BCLK + 1 = GP11
  i2s.setDATA(PIN_I2S_DIN);
  i2s.setBitsPerSample(16);
  i2s.setBuffers(4, 128);
  i2s.begin(SAMPLE_RATE);

  readPots();
  readPots();
}

void loop() {
  static uint32_t blocks = 0;
  static float fade = 0.0f;               // short fade-in after power-up, no click
  static float led = 0.0f;

  for (int i = 0; i < 128; i++) {
    float s = surf::Engine::limit(engine.process() * fade) * OUT_GAIN;
    int16_t v = (int16_t)(s * 32767.0f);
    i2s.write16(v, v);                    // mono: same sample on both channels
    if (fade < 1.0f) fade += 1.0f / (0.5f * SAMPLE_RATE);
  }

  if ((++blocks & 3) == 0) {              // every 16 ms
    readPots();
    float target = 0.12f + 0.88f * engine.level();
    led += 0.35f * (target - led);
    analogWrite(PIN_LED, (int)(led * led * 255.0f));
  }
}
