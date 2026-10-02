import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, concurrent.futures as cf, json
from simrun import run

def job(args):
    tag, surf, tide, seed = args
    t, c = run(f'sw_{tag}', 100, '10m', ['v(vw)', 'v(fw)', 'v(ck1)', 'v(ck2)', 'v(q1)', 'v(q2)', 'v(cmp)'],
               pots=dict(RV2=0.0, RV5=surf, RV6A=tide, RV6B=tide), tmax=5e-3, sigma=3.5e-3, seed=seed,
               extra='.ic v(t1)=0 v(t2)=0')
    np.save(f'{__import__("simrun").WD}/sw_{tag}.npy', np.vstack([t] + [c[k] for k in c]))
    return tag

if __name__ == '__main__':
    jobs = []
    for surf in (0.15, 0.5, 0.85):
        for tide in (0.05, 0.95):
            jobs.append((f's{int(surf*100)}_t{int(tide*100)}', surf, tide, 7))
    with cf.ThreadPoolExecutor(max_workers=int(os.cpu_count() or 2)) as ex:
        for tag in ex.map(job, jobs): print('done', tag, flush=True)
