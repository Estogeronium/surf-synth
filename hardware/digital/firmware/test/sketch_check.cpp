#include "stubs/Arduino.h"
#include "stubs/I2S.h"
#include "stubs/SPI.h"
SPIClass SPI;
#include "../surf_synth/surf_synth.ino"
int main() { setup(); for (int i = 0; i < 400; i++) loop(); return 0; }
