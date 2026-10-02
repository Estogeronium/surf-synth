// Surf Synth DSP: a float port of src/audio/surf-engine.js (the web version).
// No Arduino dependencies, so the same file is compiled on a PC for testing.
#pragma once
#include <math.h>
#include <stdint.h>

namespace surf {

constexpr float kPi = 3.14159265358979f;

// Small, fast PRNG (xorshift32).
struct Rng {
  uint32_t s;
  explicit Rng(uint32_t seed = 2463534242u) : s(seed ? seed : 1u) {}
  inline uint32_t next() { s ^= s << 13; s ^= s >> 17; s ^= s << 5; return s; }
  inline float white() { return (int32_t)next() * (1.0f / 2147483648.0f); }   // -1 .. 1
  inline float uni() { return (next() >> 8) * (1.0f / 16777216.0f); }        // 0 .. 1
};

// Pink noise: Paul Kellet's filter, the same coefficients as the web version.
struct Pink {
  float b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  inline float next(float white) {
    b0 = 0.99886f * b0 + white * 0.0555179f;
    b1 = 0.99332f * b1 + white * 0.0750759f;
    b2 = 0.96900f * b2 + white * 0.1538520f;
    b3 = 0.86650f * b3 + white * 0.3104856f;
    b4 = 0.55000f * b4 + white * 0.5329522f;
    b5 = -0.7616f * b5 - white * 0.0168980f;
    float out = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362f;
    b6 = white * 0.115926f;
    return out;
  }
};

// RBJ biquad. Like the Web Audio API, Q of low/high-pass filters is given in dB.
struct Biquad {
  float b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0, x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  inline float process(float x) {
    float y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
    x2 = x1; x1 = x; y2 = y1; y1 = y;
    return y;
  }
  void set(bool highpass, float fs, float f, float qDb) {
    if (f > 0.45f * fs) f = 0.45f * fs;
    float q = powf(10.0f, qDb / 20.0f);
    float w0 = 2.0f * kPi * f / fs, c = cosf(w0), alpha = sinf(w0) / (2.0f * q);
    float a0 = 1.0f + alpha;
    a1 = -2.0f * c / a0; a2 = (1.0f - alpha) / a0;
    if (highpass) { b0 = (1.0f + c) * 0.5f / a0; b1 = -(1.0f + c) / a0; b2 = b0; }
    else          { b0 = (1.0f - c) * 0.5f / a0; b1 = (1.0f - c) / a0;  b2 = b0; }
  }
};

// Wave shape on x in [0,1]: smooth rise to peakAt, then exponential decay to exactly 0.
inline float waveShape(float x, float peakAt, float decay) {
  if (x <= 0.0f || x >= 1.0f) return 0.0f;
  if (x < peakAt) { float s = sinf((x / peakAt) * kPi * 0.5f); return s * s; }
  float u = (x - peakAt) / (1.0f - peakAt);
  float tail = expf(-decay);
  return (expf(-decay * u) - tail) / (1.0f - tail);
}

struct Params { float surf = 0.5f, tide = 0.45f, tone = 0.5f, volume = 0.6f; };

class Engine {
 public:
  explicit Engine(float sampleRate, uint32_t seed = 1) : fs_(sampleRate), rng_(seed * 2654435761u + 1u) {
    nextWave(0.0f);
    updateControl();
  }

  void setParams(const Params& p) { p_ = p; }
  Params params() const { return p_; }

  // One mono output sample in about -1..1 (before the output soft limiter).
  inline float process() {
    if (ctl_ == 0) { advanceControl(); }
    if (--ctl_ < 0) ctl_ = kControlEvery - 1;
    float body = bodyLp_.process(pinkA_.next(rng_.white()) * kPinkScale) * bodyGain_;
    float foam = foamHp_.process(pinkB_.next(rng_.white()) * kPinkScale) * foamGain_;
    return (body + foam) * volGain_;
  }

  // Soft limiter that stays close to linear below 0.5.
  static inline float limit(float x) {
    if (x > 3.0f) return 1.0f;
    if (x < -3.0f) return -1.0f;
    float x2 = x * x;
    return x * (27.0f + x2) / (27.0f + 9.0f * x2);
  }

  float level() const { return envBody_; }          // 0..1, for the LED

 private:
  static constexpr int kControlEvery = 16;
  // Scales the Kellet output to the loudness of the web version's normalised noise buffer.
  static constexpr float kPinkScale = 0.1030f;

  void nextWave(float start) {
    float period = 14.0f * powf(3.0f / 14.0f, p_.tide) * (0.8f + 0.45f * rng_.uni());
    waveStart_ = start;
    waveLen_ = period;
    bodyPeak_ = 0.55f + 0.45f * powf(rng_.uni(), 0.7f);
    foamPeak_ = 0.6f + 0.4f * rng_.uni();
  }

  void advanceControl() {
    t_ += kControlEvery / fs_;
    if (t_ >= waveStart_ + waveLen_) nextWave(waveStart_ + waveLen_);
    updateControl();
  }

  void updateControl() {
    float x = (t_ - waveStart_) / waveLen_;
    envBody_ = waveShape(x, 0.30f, 3.2f) * bodyPeak_;
    float envFoam = waveShape(x, 0.42f, 2.2f) * foamPeak_;
    float surf = p_.surf, tone = p_.tone;
    float base = 160.0f + tone * 520.0f;
    float depth = (900.0f + tone * 3600.0f) * (0.35f + 0.65f * surf);
    bodyLp_.set(false, fs_, base + envBody_ * depth, 0.6f);
    foamHp_.set(true, fs_, 1400.0f + tone * 2800.0f, 0.5f);
    bodyGain_ = (0.12f + 0.88f * envBody_) * (0.12f + 0.88f * powf(surf, 1.2f));
    foamGain_ = envFoam * (0.04f + 0.5f * powf(surf, 1.6f));
    volGain_ = 0.4f + 2.6f * p_.volume * p_.volume;
  }

  float fs_;
  Rng rng_;
  Params p_;
  Pink pinkA_, pinkB_;
  Biquad bodyLp_, foamHp_;
  float t_ = 0, waveStart_ = 0, waveLen_ = 5, bodyPeak_ = 1, foamPeak_ = 1;
  float envBody_ = 0, bodyGain_ = 0, foamGain_ = 0, volGain_ = 1;
  int ctl_ = 0;
};

}  // namespace surf
