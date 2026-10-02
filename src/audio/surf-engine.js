// Ocean surf synthesizer: pink noise shaped by randomised "wave" envelopes.
//
//   noiseBody -> lowpass --------> bodyAmp(env) -> bodyLevel --\
//                                                               +-> power -> volume -> limiter -> out
//   noiseFoam -> highpass -> foamAmp(foamEnv) -> foamLevel ----/
//
// Each wave is one scheduled curve (rise, then long decay) written to two
// ConstantSourceNodes. The same envelope also opens the lowpass cutoff, so a
// crest sounds bright and the backwash sounds dull.

const PARAM_DEFAULTS = { surf: 0.5, tide: 0.45, tone: 0.5, volume: 0.6 };

const lerp = (a, b, t) => a + (b - a) * t;
const clamp01 = (v) => Math.min(1, Math.max(0, v));

// Pink noise (cascaded one-pole filters over white noise), looped seamlessly with an equal-power crossfade.
function createPinkNoiseBuffer(ctx, seconds, fadeSeconds = 0.5) {
  const rate = ctx.sampleRate;
  const length = Math.floor(seconds * rate);
  const fade = Math.floor(fadeSeconds * rate);
  const raw = new Float32Array(length + fade);
  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  for (let i = 0; i < raw.length; i++) {
    const white = Math.random() * 2 - 1;
    b0 = 0.99886 * b0 + white * 0.0555179;
    b1 = 0.99332 * b1 + white * 0.0750759;
    b2 = 0.969 * b2 + white * 0.153852;
    b3 = 0.8665 * b3 + white * 0.3104856;
    b4 = 0.55 * b4 + white * 0.5329522;
    b5 = -0.7616 * b5 - white * 0.016898;
    raw[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362;
    b6 = white * 0.115926;
  }
  const buffer = ctx.createBuffer(1, length, rate);
  const out = buffer.getChannelData(0);
  let peak = 0;
  for (let i = 0; i < length; i++) {
    out[i] = raw[i];
    if (i < fade) {
      const x = (i / fade) * Math.PI * 0.5;
      out[i] = raw[i] * Math.sin(x) + raw[length + i] * Math.cos(x);
    }
    peak = Math.max(peak, Math.abs(out[i]));
  }
  const norm = 0.5 / peak;
  for (let i = 0; i < length; i++) out[i] *= norm;
  return buffer;
}

// Wave shape on x in [0, 1]: smooth rise to `peakAt`, then exponential decay to exactly 0.
function waveShape(x, peakAt, decay) {
  if (x <= 0 || x >= 1) return 0;
  if (x < peakAt) return Math.sin((x / peakAt) * Math.PI * 0.5) ** 2;
  const u = (x - peakAt) / (1 - peakAt);
  const tail = Math.exp(-decay);
  return (Math.exp(-decay * u) - tail) / (1 - tail);
}

function createCurve(peakAt, decay, peak, steps = 256) {
  const curve = new Float32Array(steps);
  for (let i = 0; i < steps; i++) curve[i] = waveShape(i / (steps - 1), peakAt, decay) * peak;
  return curve;
}

const BODY_SHAPE = { peakAt: 0.3, decay: 3.2 };
const FOAM_SHAPE = { peakAt: 0.42, decay: 2.2 };

export class SurfEngine {
  constructor(ctx = null) {
    this.ctx = ctx;
    this.params = { ...PARAM_DEFAULTS };
    this.running = false;
    this._built = false;
    this._timer = null;
    this._nextStart = 0;
    this._waves = [];
    this._stopTimeout = null;
  }

  _build() {
    if (this._built) return;
    if (!this.ctx) this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    const ctx = this.ctx;

    const bufferA = createPinkNoiseBuffer(ctx, 12);
    const bufferB = createPinkNoiseBuffer(ctx, 15);
    const loop = (buffer, offset) => {
      const src = ctx.createBufferSource();
      src.buffer = buffer;
      src.loop = true;
      src.start(0, offset);
      return src;
    };

    // Envelope sources (0..1), written by scheduled curves.
    this.env = ctx.createConstantSource();
    this.env.offset.value = 0;
    this.foamEnv = ctx.createConstantSource();
    this.foamEnv.offset.value = 0;
    this.env.start();
    this.foamEnv.start();

    // Body: lowpassed noise, volume and brightness follow the wave.
    this.bodyFilter = ctx.createBiquadFilter();
    this.bodyFilter.type = 'lowpass';
    this.bodyFilter.Q.value = 0.6;
    this.bodyAmp = ctx.createGain();
    this.bodyAmp.gain.value = 0.12; // quiet bed between waves
    const bodyEnvScale = ctx.createGain();
    bodyEnvScale.gain.value = 0.88;
    this.bodyLevel = ctx.createGain();
    this.filterDepth = ctx.createGain(); // Hz added to the cutoff by the envelope

    loop(bufferA, 0).connect(this.bodyFilter);
    this.bodyFilter.connect(this.bodyAmp).connect(this.bodyLevel);
    this.env.connect(bodyEnvScale).connect(this.bodyAmp.gain);
    this.env.connect(this.filterDepth).connect(this.bodyFilter.frequency);

    // Foam: bright hiss that peaks slightly after the crest.
    this.foamFilter = ctx.createBiquadFilter();
    this.foamFilter.type = 'highpass';
    this.foamFilter.Q.value = 0.5;
    this.foamAmp = ctx.createGain();
    this.foamAmp.gain.value = 0;
    this.foamLevel = ctx.createGain();

    loop(bufferB, 4.3).connect(this.foamFilter);
    this.foamFilter.connect(this.foamAmp).connect(this.foamLevel);
    this.foamEnv.connect(this.foamAmp.gain);

    // Output.
    this.power = ctx.createGain();
    this.power.gain.value = 0;
    this.volume = ctx.createGain();
    this.limiter = ctx.createDynamicsCompressor();
    this.limiter.threshold.value = -10;
    this.limiter.knee.value = 6;
    this.limiter.ratio.value = 12;
    this.limiter.attack.value = 0.005;
    this.limiter.release.value = 0.25;

    this.bodyLevel.connect(this.power);
    this.foamLevel.connect(this.power);
    this.power.connect(this.volume).connect(this.limiter).connect(ctx.destination);

    this._built = true;
    this._applyParams(true);
  }

  _applyParams(immediate = false) {
    if (!this._built) return;
    const { surf, tone, volume } = this.params;
    const t = this.ctx.currentTime;
    const set = (param, value) => {
      if (immediate) param.setValueAtTime(value, t);
      else param.setTargetAtTime(value, t, 0.06);
    };
    set(this.bodyLevel.gain, 0.12 + 0.88 * surf ** 1.2);
    set(this.foamLevel.gain, 0.04 + 0.5 * surf ** 1.6);
    set(this.filterDepth.gain, (900 + tone * 3600) * (0.35 + 0.65 * surf));
    set(this.bodyFilter.frequency, 160 + tone * 520);
    set(this.foamFilter.frequency, 1400 + tone * 2800);
    set(this.volume.gain, 0.4 + 2.6 * volume ** 2);
  }

  setParam(name, value) {
    if (!(name in this.params)) return;
    this.params[name] = clamp01(value);
    this._applyParams();
  }

  // Seconds between wave starts: 14 s at tide=0 down to 3 s at tide=1 (exponential).
  _wavePeriod() {
    return 14 * (3 / 14) ** this.params.tide * lerp(0.8, 1.25, Math.random());
  }

  // Schedule every wave that starts within the next `seconds`.
  scheduleAhead(seconds) {
    const ctx = this.ctx;
    while (this._nextStart < ctx.currentTime + seconds) {
      const start = this._nextStart;
      const duration = this._wavePeriod();
      const peak = 0.55 + 0.45 * Math.random() ** 0.7;
      const foamPeak = 0.6 + 0.4 * Math.random();
      this.env.offset.setValueCurveAtTime(
        createCurve(BODY_SHAPE.peakAt, BODY_SHAPE.decay, peak), start, duration);
      this.foamEnv.offset.setValueCurveAtTime(
        createCurve(FOAM_SHAPE.peakAt, FOAM_SHAPE.decay, foamPeak), start, duration);
      this._waves.push({ start, duration, peak });
      if (this._waves.length > 3) this._waves.shift();
      this._nextStart = start + duration;
    }
  }

  async start() {
    if (this.running) return;
    this._build();
    const ctx = this.ctx;
    clearTimeout(this._stopTimeout);
    if (ctx.state !== 'running') await ctx.resume();
    const now = ctx.currentTime;
    this.env.offset.cancelScheduledValues(now);
    this.foamEnv.offset.cancelScheduledValues(now);
    this.env.offset.setValueAtTime(0, now);
    this.foamEnv.offset.setValueAtTime(0, now);
    this._waves = [];
    this._nextStart = now + 0.2;
    this.scheduleAhead(0.3);
    this._timer = setInterval(() => this.scheduleAhead(0.4), 100);
    this.power.gain.cancelScheduledValues(now);
    this.power.gain.setValueAtTime(this.power.gain.value, now);
    this.power.gain.linearRampToValueAtTime(1, now + 1.5);
    this.running = true;
  }

  async stop() {
    if (!this.running) return;
    this.running = false;
    clearInterval(this._timer);
    const now = this.ctx.currentTime;
    this.power.gain.cancelScheduledValues(now);
    this.power.gain.setValueAtTime(this.power.gain.value, now);
    this.power.gain.linearRampToValueAtTime(0, now + 1);
    this._stopTimeout = setTimeout(() => {
      if (!this.running) this.ctx.suspend();
    }, 1200);
  }

  // Current wave envelope 0..1, for the indicator light.
  getLevel() {
    if (!this.running) return 0;
    const t = this.ctx.currentTime;
    for (const wave of this._waves) {
      if (t >= wave.start && t < wave.start + wave.duration) {
        const x = (t - wave.start) / wave.duration;
        return waveShape(x, BODY_SHAPE.peakAt, BODY_SHAPE.decay) * wave.peak;
      }
    }
    return 0;
  }
}

export { PARAM_DEFAULTS };
