import sys, os, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import circuit, spice
import tempfile
WD = os.environ.get('SURF_SIM_DIR', os.path.join(tempfile.gettempdir(), 'surf-sim'))
os.makedirs(WD, exist_ok=True)

def pwl_noise(T, dt, sigma, seed=1):
    rng = np.random.default_rng(seed); n = int(T / dt) + 2
    x = rng.standard_normal(n) * sigma
    return 'PWL(\n' + '\n'.join(f'+ {i*dt:.7g} {x[i]:.5g}' for i in range(n)) + '\n+ )'

def run(tag, T, step, probes, pots=None, sigma=2.3e-3, noise_dt=2e-3, seed=1, extra='', tmax=None, noise=True, force=None):
    src = pwl_noise(T, noise_dt, sigma, seed) if noise else 'DC 0'
    ctl = f""".options reltol=1e-3 abstol=1e-9 vntol=1e-5
.control
tran {step} {T} {('0 ' + str(tmax)) if tmax else ''}
wrdata {WD}/{tag}.dat {' '.join(probes)}
.endc
.end"""
    nl = spice.export(circuit.D, pots=pots, noise_src=src, extra=extra + '\n' + ctl, force=force)
    open(f'{WD}/{tag}.cir', 'w').write(nl)
    r = subprocess.run(['ngspice', '-b', f'{WD}/{tag}.cir'], capture_output=True, text=True, cwd=WD)
    if not os.path.exists(f'{WD}/{tag}.dat'):
        raise RuntimeError(r.stdout[-3000:])
    d = np.loadtxt(f'{WD}/{tag}.dat')
    t = d[:, 0]
    return t, {p: d[:, 2 * i + 1] for i, p in enumerate(probes)}

if __name__ == '__main__':
    import time
    t0 = time.time()
    t, c = run('ctrl1', 90, '10m', ['v(vw)', 'v(ck1)', 'v(ck2)', 'v(q1)', 'v(q2)', 'v(w)', 'v(cmp)'], pots=dict(RV5=0.5, RV6A=0.5, RV6B=0.5), tmax=5e-3, sigma=3.5e-3, extra='.ic v(t1)=0 v(t2)=0')
    print('elapsed', time.time() - t0, 'points', len(t))
    w = c['v(w)']; print('W rms(ac) %.1f mV' % (np.std(w[t > 5]) * 1000))
    for k in ('v(ck1)', 'v(ck2)'):
        y = c[k]; hi = y > 5.8
        edges = t[1:][(hi[1:]) & (~hi[:-1])]
        print(k, 'rising edges', len(edges), 'period %.2f s' % np.mean(np.diff(edges)), 'pulse width %.2f s' % (np.mean([ (t[1:][(~hi[1:]) & (hi[:-1])][t[1:][(~hi[1:]) & (hi[:-1])]>e][0]-e) for e in edges[:5] ])))
    vw = c['v(vw)']
    print('VW mean %.2f max %.2f' % (vw[t > 20].mean(), vw.max()))
    print('Q1 high frac %.2f  Q2 high frac %.2f' % (np.mean(c['v(q1)'][t>5] > 6), np.mean(c['v(q2)'][t>5] > 6)))
    np.save(f'{WD}/ctrl1.npy', np.vstack([t] + [c[k] for k in c]))
