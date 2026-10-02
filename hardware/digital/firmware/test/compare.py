"""Compare the firmware DSP (C++) with the web engine (JS) statistically.

The waves are random, so we compare distributions: loudness, spectrum bands, envelope range
and the typical gap between waves. Needs Playwright (Chromium) and a running `vite` dev server.
"""
import base64, json, subprocess, sys, os, numpy as np
from scipy.signal import find_peaks, butter, sosfilt
HERE = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get('HOST_TEST', '/tmp/ap/host_test')
PW = os.environ.get('PLAYWRIGHT_JS', '/opt/node-tools/node_modules/playwright')
FS = 32000
SETS = [dict(surf=.5, tide=.45, tone=.5, volume=.6), dict(surf=.2, tide=.2, tone=.3, volume=.6), dict(surf=.9, tide=.8, tone=.7, volume=.6)]
DUR = 120

def run_js(p):
    js = f"""
const {{ chromium }} = require('{PW}');
(async () => {{
  const b = await chromium.launch(); const pg = await b.newPage();
  await pg.goto('http://localhost:5173/');
  const r = await pg.evaluate(async ([p, DUR, FS]) => {{
    const {{ SurfEngine }} = await import('/src/audio/surf-engine.js');
    const ctx = new OfflineAudioContext(1, FS * DUR, FS);
    const e = new SurfEngine(ctx); e.params = {{ ...p }}; e._build(); e.power.gain.value = 1; e.running = true; e._nextStart = 0.05; e.scheduleAhead(DUR);
    const buf = await ctx.startRendering(); const d = buf.getChannelData(0);
    const u8 = new Uint8Array(d.buffer.slice(0)); let s = ''; for (let i = 0; i < u8.length; i += 32768) s += String.fromCharCode.apply(null, u8.subarray(i, i + 32768));
    return btoa(s);
  }}, [{json.dumps(p)}, {DUR}, {FS}]);
  process.stdout.write(r); await b.close();
}})();"""
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout
    return np.frombuffer(base64.b64decode(out), dtype=np.float32)

def run_cpp(p, seed=1):
    out = subprocess.run([HOST, str(DUR), str(FS), str(p['surf']), str(p['tide']), str(p['tone']), str(p['volume']), str(seed)], capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32)

def metrics(x):
    x = x.astype(np.float64); win = FS // 4
    n = len(x) // win; r = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(1))
    f = np.fft.rfftfreq(len(x), 1 / FS); P = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    def band(a, b): return P[(f >= a) & (f < b)].sum() / P.sum()
    sm = np.convolve(r, np.ones(4) / 4, 'same')
    pk, _ = find_peaks(sm, prominence=0.25 * sm.std() + 1e-9, distance=4)
    return dict(rms=float(np.sqrt((x ** 2).mean())), env_p5=float(np.percentile(r, 5)), env_p50=float(np.percentile(r, 50)), env_p95=float(np.percentile(r, 95)),
                dyn_db=float(20 * np.log10(np.percentile(r, 95) / max(np.percentile(r, 5), 1e-9))),
                b_lt200=float(band(20, 200)), b_200_1k=float(band(200, 1000)), b_1_4k=float(band(1000, 4000)), b_gt4k=float(band(4000, 15000)),
                wave_gap_s=float(np.median(np.diff(pk)) * 0.25) if len(pk) > 2 else float('nan'), peak=float(np.abs(x).max()))

if __name__ == '__main__':
    res = []
    for p in SETS:
        j, c = metrics(run_js(p)), metrics(run_cpp(p))
        res.append(dict(params=p, js=j, cpp=c))
        print(p)
        for k in j: print(f'  {k:12s} js {j[k]:9.4f}   cpp {c[k]:9.4f}')
    json.dump(res, open(os.path.join(HERE, '..', '..', 'out', 'dsp-compare.json'), 'w'), indent=1)
