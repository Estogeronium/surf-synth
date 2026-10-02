// Renders audio with the firmware DSP on a PC: host_test <seconds> <rate> <surf> <tide> <tone> <volume> <seed> > out.f32
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "../surf_synth/surf_dsp.h"

int main(int argc, char** argv) {
  if (argc < 8) { fprintf(stderr, "usage: host_test seconds rate surf tide tone volume seed\n"); return 1; }
  double secs = atof(argv[1]); float rate = (float)atof(argv[2]);
  surf::Params p; p.surf = atof(argv[3]); p.tide = atof(argv[4]); p.tone = atof(argv[5]); p.volume = atof(argv[6]);
  surf::Engine e(rate, (uint32_t)atoi(argv[7]));
  e.setParams(p);
  long n = (long)(secs * rate);
  std::vector<float> out(n);
  for (long i = 0; i < n; i++) out[i] = e.process();
  fwrite(out.data(), sizeof(float), n, stdout);
  return 0;
}
