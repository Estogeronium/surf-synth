"""Run the full set of checks against the drawn schematic and write out/sim-summary.json.

Uses ngspice with behavioural models. It checks bias points, levels, filter shapes and the
timing of the wave generator; it does not replace measuring the real board.
"""
import sys, os, json, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import circuit, spice
from ac_check import ac
from audio_check import job as audio_job, spectrum
from simrun import WD, run
import concurrent.futures as cf

OUT = os.path.join(os.path.dirname(__file__), '..', 'out')
DOCS = os.path.join(os.path.dirname(__file__), '..', 'docs')
os.makedirs(DOCS, exist_ok=True)
S = {}

# 1. DC operating point
nl = spice.export(circuit.D, pots=dict(RV3=0.5), extra='.options reltol=1e-3 abstol=1e-9 vntol=1e-5\n.control\nop\nprint v(V12) v(A12) v(VB) v(QE) v(SURFW) v(OUTA) v(TONW)\n.endc\n.end', force={'VW': 0.02, 'FW': 0.02})
open(f'{WD}/op.cir', 'w').write(nl)
r = subprocess.run(['ngspice', '-b', f'{WD}/op.cir'], capture_output=True, text=True, cwd=WD).stdout
dc = {}
for line in r.splitlines():
    if line.startswith('v('):
        k, v = line.split('=')
        dc[k.strip()[2:-1].upper()] = round(float(v), 2)
S['dc'] = dc
print('DC', dc)

# 2. pink slope + VCF
f, (w, pn, vcfo, mo) = ac('v_ac0', {'VW': 0.02, 'FW': 0.02})
h = 20 * np.log10(np.abs(pn / w)); sel = (f >= 30) & (f <= 16000)
x = np.log2(f[sel]); A = np.polyfit(x, h[sel], 1)
S['pink'] = dict(slope_db_oct=round(float(A[0]), 2), max_dev_db=round(float(np.max(np.abs(h[sel] - np.polyval(A, x)))), 2), band='30 Гц – 16 кГц')
fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
ax[0].semilogx(f, h, color='#00a79b'); ax[0].semilogx(f[sel], np.polyval(A, x), '--', color='#999')
ax[0].set_title('Розовый шум: W → PN (с усилителем), наклон %.2f дБ/окт' % A[0], fontsize=9); ax[0].set_xlabel('Гц'); ax[0].set_ylabel('дБ'); ax[0].grid(alpha=.3)
vcf = []
for vw in (0.02, 2.5, 3.5, 4.5, 5.5):
    f2, (w2, pn2, vo2, mo2) = ac(f'v_ac_{vw}', {'VW': vw, 'FW': vw}, pots=dict(RV3=0.5))
    hv = 20 * np.log10(np.abs(vo2 / pn2)); ref = hv[np.argmin(abs(f2 - 20))]
    below = np.where(hv < ref - 3)[0]; fc = float(f2[below[0]]) if len(below) else None
    vcf.append((vw, fc)); ax[1].semilogx(f2, hv, label=f'VW={vw} В, срез ≈ {fc:.0f} Гц')
ax[1].set_ylim(-30, 3); ax[1].set_title('Фильтр U6A при разных напряжениях волны', fontsize=9); ax[1].legend(fontsize=7); ax[1].grid(alpha=.3); ax[1].set_xlabel('Гц')
plt.tight_layout(); plt.savefig(os.path.join(DOCS, 'sim-filters.png'), dpi=80); plt.close()
S['vcf'] = [dict(vw=a, fc_hz=round(b)) for a, b in vcf]
fcs = {}
for pos in (0.05, 1.0):
    f3, (w3, pn3, vo3, mo3) = ac(f'v_act_{pos}', {'VW': 0.02, 'FW': 0.02}, pots=dict(RV3=pos))
    hv = 20 * np.log10(np.abs(vo3 / pn3)); ref = hv[np.argmin(abs(f3 - 10))]
    below = np.where(hv < ref - 3)[0]; fcs[pos] = float(f3[below[0]]) if len(below) else None
S['tone'] = dict(min_hz=round(fcs[0.05]) if fcs[0.05] else None, max_hz=round(fcs[1.0]) if fcs[1.0] else None)
print('pink', S['pink'], 'vcf', S['vcf'], 'tone', S['tone'])

# 3. levels
lv = []
with cf.ThreadPoolExecutor(max_workers=4) as ex:
    for vw, t, c in ex.map(audio_job, [(0.02,), (2.5,), (4.0,), (5.5,)]):
        m = t > 0.4
        lv.append(dict(vw=vw, w_mv=round(float(np.std(c['v(w)'][m]) * 1000)), mix_mv=round(float(np.std(c['v(mo)'][m]) * 1000), 1), spk_v=round(float(np.std(c['v(outa)'][m])), 2)))
S['levels'] = lv
print('levels', lv)

# 4. wave generator (from cached sweep runs)
names = ['vw', 'fw', 'ck1', 'ck2', 'q1', 'q2', 'cmp']
rows = []
fig, ax = plt.subplots(3, 2, figsize=(11, 6), sharex=True, sharey=True)
for j, tide in enumerate(('t5', 't95')):
    for i, surf in enumerate(('s15', 's50', 's85')):
        p = f'{WD}/sw_{surf}_{tide}.npy'
        if not os.path.exists(p): continue
        d = np.load(p); t = d[0]; c = dict(zip(names, d[1:]))
        m = t > 10; v = c['vw'][m]; tt = t[m]
        up = int(np.sum((v[1:] > 2.5) & (v[:-1] <= 2.5)))
        pr = []
        for k in ('ck1', 'ck2'):
            hi = c[k][m] > 5.8; pr.append(round((tt[-1] - tt[0]) / max(int(np.sum(hi[1:] & ~hi[:-1])), 1), 1))
        rows.append(dict(surf=int(surf[1:]), tide=int(tide[1:]), waves_per_min=round(up / (tt[-1] - tt[0]) * 60, 1), mean_vw=round(float(v.mean()), 2), max_vw=round(float(v.max()), 2), periods_s=pr))
        ax[i, j].plot(t, c['vw'], color='#00a79b', lw=1); ax[i, j].plot(t, c['fw'], color='#e08a00', lw=.7); ax[i, j].axhline(1.8, color='#c33', lw=.5)
        ax[i, j].set_title('Surf %s%%, Tide %s%%' % (surf[1:], tide[1:]), fontsize=9)
ax[2, 0].set_xlabel('с'); ax[2, 1].set_xlabel('с'); ax[1, 0].set_ylabel('VW, В (бирюз.) / FW (оранж.)')
plt.tight_layout(); plt.savefig(os.path.join(DOCS, 'sim-waves.png'), dpi=80); plt.close()
S['waves'] = rows
json.dump(S, open(os.path.join(OUT, 'sim-summary.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(S, ensure_ascii=False)[:1500])
