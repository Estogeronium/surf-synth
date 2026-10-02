import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, concurrent.futures as cf
from simrun import run

def job(a):
    vw, = a
    t, c = run(f'au_{vw}', 1.0, '20u', ['v(w)', 'v(pn)', 'v(vcfo)', 'v(mo)', 'v(outa)'], pots=dict(RV1=0.5, RV2=0.0, RV3=0.5, RV4=0.8),
               sigma=3.0e-3, noise_dt=10e-6, force={'VW': vw, 'FW': vw}, tmax=20e-6, extra='.ic v(t1)=0 v(t2)=0')
    return vw, t, c

def spectrum(sig, t):
    dt = np.median(np.diff(t)); tt = np.arange(t[0] + 0.4, t[-1], dt)
    y = np.interp(tt, t, sig); y = y - y.mean()
    f = np.fft.rfftfreq(len(y), dt); P = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
    return f, P

if __name__ == '__main__':
    res = {}
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for vw, t, c in ex.map(job, [(0.16,), (2.5,), (4.0,), (5.5,)]):
            m = t > 0.4
            f, P = spectrum(c['v(mo)'], t)
            tot = P.sum()
            cen = (f * P).sum() / tot
            def band(a, b): return 10 * np.log10(P[(f >= a) & (f < b)].sum() / tot + 1e-18)
            print(f"VW={vw}: W rms {np.std(c['v(w)'][m])*1000:.0f} mV | pink {np.std(c['v(pn)'][m])*1000:.0f} mV | MO {np.std(c['v(mo)'][m])*1000:.1f} mV | OUTA {np.std(c['v(outa)'][m]):.2f} V | centroid {cen:.0f} Hz | bands dB <200Hz {band(20,200):.1f}, 200-1k {band(200,1000):.1f}, 1-4k {band(1000,4000):.1f}, >4k {band(4000,20000):.1f}")
