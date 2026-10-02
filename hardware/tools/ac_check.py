import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import circuit, spice
from simrun import WD

def ac(tag, force, pots=None, probes=('v(w)', 'v(pn)', 'v(vcfo)', 'v(mo)')):
    ctl = f""".options reltol=1e-3
.control
ac dec 30 10 50k
wrdata {WD}/{tag}.dat {' '.join(probes)}
.endc
.end"""
    nl = spice.export(circuit.D, pots=pots, noise_src='DC 0 AC 1m', extra=ctl, force=force)
    open(f'{WD}/{tag}.cir', 'w').write(nl)
    r = subprocess.run(['ngspice', '-b', f'{WD}/{tag}.cir'], capture_output=True, text=True, cwd=WD)
    d = np.loadtxt(f'{WD}/{tag}.dat')
    f = d[:, 0]
    return f, [d[:, 1 + 3 * i] + 1j * d[:, 2 + 3 * i] for i in range(len(probes))]

if __name__ == '__main__':
    # pink slope: W -> PN
    f, (w, pn, vcfo, mo) = ac('ac0', {'VW': 0.02, 'FW': 0.02})
    h = 20 * np.log10(np.abs(pn / w))
    for fq in (30, 100, 300, 1000, 3000, 10000, 16000):
        i = np.argmin(abs(f - fq)); print(f'PN/W at {fq:>6} Hz: {h[i]:6.1f} dB')
    sel = (f >= 30) & (f <= 16000)
    x = np.log2(f[sel]); A = np.polyfit(x, h[sel], 1)
    print('pink filter+amp slope %.2f dB/oct, max dev from line %.2f dB' % (A[0], np.max(np.abs(h[sel] - np.polyval(A, x)))))
    print('VCF cutoff (-3 dB re low-frequency level) vs wave voltage VW:')
    for vw in (0.02, 1.8, 2.5, 3.5, 4.5, 5.5):
        f, (w, pn, vcfo, mo) = ac(f'ac_{vw}', {'VW': vw, 'FW': vw}, pots=dict(RV3=0.5))
        hv = 20 * np.log10(np.abs(vcfo / pn))
        ref = hv[np.argmin(abs(f - 20))]
        below = np.where(hv < ref - 3)[0]
        fc = f[below[0]] if len(below) else float('nan')
        print(f'  VW={vw:4.2f} V: LF gain {ref:5.1f} dB, f(-3dB) = {fc:7.0f} Hz')
    print('Tone knob at VW=0.02:')
    for pos in (0.0, 0.5, 1.0):
        f, (w, pn, vcfo, mo) = ac(f'act_{pos}', {'VW': 0.02, 'FW': 0.02}, pots=dict(RV3=pos))
        hv = 20 * np.log10(np.abs(vcfo / pn)); ref = hv[np.argmin(abs(f - 20))]
        below = np.where(hv < ref - 3)[0]; print(f'  Tone {pos:.1f}: f(-3dB) = {f[below[0]] if len(below) else float("nan"):.0f} Hz')
