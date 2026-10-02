import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import circuit, spice
nl = spice.export(circuit.D, extra='''
.options reltol=1e-3 abstol=1e-9 vntol=1e-5
.control
op
print v(V12) v(A12) v(VB) v(QE) v(W) v(PN) v(CMP) v(SURFW) v(ACT) v(CK1) v(CK2) v(VW) v(FW) v(IC1) v(IC2) v(IC3) v(MIX) v(MO) v(VCFO) v(OUTA) v(TONW) v(T1) v(T2) v(E)
.endc
.end''')
p = os.path.join(__import__('simrun').WD, 'op.cir')
open(p, 'w').write(nl)
print(subprocess.run(['ngspice', '-b', p], capture_output=True, text=True, cwd=__import__('simrun').WD).stdout[-3500:])
