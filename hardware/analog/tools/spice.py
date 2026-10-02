"""Export the drawn schematic to a SPICE netlist for ngspice.

Op-amps, the OTA, the flip-flop and the amplifier use behavioural models: they
check levels, bias points and timing, not manufacturer-exact distortion or noise.
"""
import re, collections

MODELS = r'''
* ---- behavioural models (not manufacturer models) ----
.subckt TL072 inp inn out vcc vee
Rin inp inn 1e10
Eg n1 0 value={2e5*(V(inp)-V(inn))}
R1 n1 n2 1k
C1 n2 0 {1/(6.283*1k*15)}
Eo n3 0 value={ (V(vcc)+V(vee))/2 + (V(vcc)-V(vee)-3)/2*tanh((V(n2)-(V(vcc)+V(vee))/2)/((V(vcc)-V(vee)-3)/2)) }
Ro n3 out 100
.ends
.subckt LM358 inp inn out vcc vee
Rin inp inn 1e9
Eg n1 0 value={1e5*(V(inp)-V(inn))}
R1 n1 n2 1k
C1 n2 0 {1/(6.283*1k*10)}
Eo n3 0 value={ (V(vcc)+V(vee)-1.48)/2 + (V(vcc)-V(vee)-1.52)/2*tanh((V(n2)-(V(vcc)+V(vee)-1.48)/2)/((V(vcc)-V(vee)-1.52)/2)) }
Ro n3 out 50
.ends
* OTA: gm = 19.2*Iabc, Iout = Iabc*tanh(Vd/(2Vt)); Iabc pin sits ~1.2 V above V-; buffer drops 1.2 V
.subckt OTA inp inn iabc out bi bo vcc vee
Vs iabc ia 0
Dm ia n1 DI
Vp n1 vee DC 0.6
.model DI D(IS=1e-14 N=1)
Rinp inp 0 1e9
Rinn inn 0 1e9
Gout 0 out value={ I(Vs)*tanh((V(inp)-V(inn))/0.0517) }
Rbi bi 0 1e9
Ebuf bx 0 value={V(bi)-1.2}
Rbo bx bo 300
.ends
.model D4148 D(IS=2.5n N=1.8 RS=0.6 CJO=4p TT=12n)
.model D5819 D(IS=1u N=1.1 RS=0.05 CJO=100p)
.model DLED D(IS=1e-18 N=1.8 RS=5)
.model DZQ D(IS=1e-14 BV=7.3 IBV=1m)
.model Q2N3904 NPN(IS=6.7f BF=200 VAF=100 CJE=4p CJC=3p)
.model adc1 adc_bridge(in_low=4.2 in_high=7.8)
.model dff1 d_dff(clk_delay=100n set_delay=100n reset_delay=100n ic=0)
.model dac1 dac_bridge(out_low=0 out_high=11.9)
.model and2 d_and(rise_delay=100n fall_delay=100n)
'''

def val(v):
    v = str(v).split()[0]
    if v.endswith('M'): v = v[:-1] + 'Meg'
    return v

def num(v):
    m = re.match(r'^([0-9.]+)([pnumkM]?)', str(v).split()[0])
    mult = {'': 1, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3, 'k': 1e3, 'M': 1e6}[m.group(2)]
    return float(m.group(1)) * mult

def export(design, pots=None, noise_src='DC 0', extra='', vsupply=12.0, force=None):
    """pots: wiper positions 0..1 (0 at pin 1) per pot ref."""
    pos = dict(RV1=0.5, RV2=0.7, RV3=0.5, RV4=0.8, RV5=0.5, RV6A=0.5, RV6B=0.5)
    pos.update(pots or {})
    nets = design.nets()
    parts = design.parts()
    pn = {}
    for n, pins in nets.items():
        for r, p in pins: pn[(r, p)] = n
    def net(ref, pin, default=None):
        n = pn.get((ref, str(pin)))
        if n is None: n = default or f'NC_{ref}_{pin}'
        return '0' if n == 'GND' else n
    L = ['* Surf Synth (generated from the schematic)', MODELS]
    ic_power = {}
    for ref, p in parts.items():
        if p.kind == 'PWR':
            ic_power[p.meta['ic']] = (net(ref, 'VP'), net(ref, 'VM'))
    for ref, p in parts.items():
        k = p.kind
        if k == 'R':
            L.append(f'R{ref} {net(ref,"1")} {net(ref,"2")} {val(p.value)}')
        elif k in ('C', 'CP'):
            L.append(f'C{ref} {net(ref,"1")} {net(ref,"2")} {val(p.value)}')
        elif k == 'POT':
            tot = num(p.value); x = pos[ref]
            a, w, b = net(ref, '1'), net(ref, 'W'), net(ref, '3')
            L.append(f'R{ref}a {a} {w} {max(tot*x, 1):.6g}')
            L.append(f'R{ref}b {w} {b} {max(tot*(1-x), 1):.6g}')
        elif k == 'D':
            mdl = 'D5819' if p.value == '1N5819' else 'D4148'
            L.append(f'D{ref} {net(ref,"A")} {net(ref,"K")} {mdl}')
        elif k == 'LED':
            L.append(f'D{ref} {net(ref,"A")} {net(ref,"K")} DLED')
        elif k == 'NPN':
            if ref == 'Q1':   # avalanche noise source: breakdown diode + series noise voltage
                e = net(ref, 'E')
                L.append(f'DQ1 0 qz DZQ')
                L.append(f'Vnoise qz {e} {noise_src}')
            else:
                L.append(f'Q{ref} {net(ref,"C")} {net(ref,"B")} {net(ref,"E")} Q2N3904')
        elif k == 'OP':
            ic = p.meta['ic']; pm = p.meta['pinmap']
            vcc, vee = ic_power[ic]
            model = 'TL072' if 'TL07' in p.value else 'LM358'
            L.append(f'X{ref} {net(ref,"+")} {net(ref,"-")} {net(ref,"O")} {vcc} {vee} {model}')
        elif k == 'IC':
            if p.value == 'LM13700':
                vcc, vee = net(ref, '11'), net(ref, '6')
                L.append(f'X{ref}A {net(ref,3)} {net(ref,4)} {net(ref,1)} {net(ref,5)} {net(ref,7)} {net(ref,8)} {vcc} {vee} OTA')
                L.append(f'X{ref}B {net(ref,14)} {net(ref,13)} {net(ref,16)} {net(ref,12)} {net(ref,10)} {net(ref,9)} {vcc} {vee} OTA')
            elif p.value == 'CD4013':
                lo = f'lo_{ref}'
                L.append(f'A{ref}lo [0] [{lo}] adc1')
                for i, (d, c, q) in enumerate([(5, 3, 1), (9, 11, 13)]):
                    L.append(f'A{ref}d{i} [{net(ref,d)}] [{ref}_d{i}] adc1')
                    L.append(f'A{ref}c{i} [{net(ref,c)}] [{ref}_c{i}] adc1')
                    L.append(f'A{ref}f{i} {ref}_d{i} {ref}_c{i} {lo} {lo} {ref}_q{i} {ref}_qb{i} dff1')
                    L.append(f'A{ref}q{i} [{ref}_q{i}] [{net(ref,q)}] dac1')
                    L.append(f'R{ref}q{i} {net(ref,q)} 0 1Meg')
            elif p.value == 'CD4081':
                for i, (a, b, y) in enumerate([(1, 2, 3), (5, 6, 4)]):
                    L.append(f'A{ref}a{i} [{net(ref,a)}] [{ref}_a{i}] adc1')
                    L.append(f'A{ref}b{i} [{net(ref,b)}] [{ref}_b{i}] adc1')
                    L.append(f'A{ref}g{i} [{ref}_a{i} {ref}_b{i}] {ref}_y{i} and2')
                    L.append(f'A{ref}y{i} [{ref}_y{i}] [{net(ref,y)}] dac1')
                    L.append(f'R{ref}y{i} {net(ref,y)} 0 1Meg')
            elif p.value == 'LM386':
                vs = net(ref, '6')
                L.append(f'B{ref} {ref}_o 0 V = V({vs})/2 + 5*tanh(20*(V({net(ref,3)})-V({net(ref,2)}))/5)')
                L.append(f'R{ref}o {ref}_o {net(ref,5)} 1')
                L.append(f'R{ref}i {net(ref,3)} {net(ref,2)} 50k')
                L.append(f'R{ref}b1 {net(ref,6)} {net(ref,7)} 15k')
                L.append(f'R{ref}b2 {net(ref,7)} 0 15k')
        elif k == 'JACK':
            L.append(f'V{ref} {net(ref,"TIP")} {net(ref,"SLV")} {vsupply}')
        elif k == 'SW':
            L.append(f'R{ref} {net(ref,"1")} {net(ref,"2")} 0.02')
        elif k == 'SPK':
            L.append(f'R{ref} {net(ref,"1")} {net(ref,"2")} 8')
    for n, pins in nets.items():
        if len(pins) == 1 and n not in ('GND',):
            L.append(f'Rnc_{n} {n} 0 1G')
    for n, v in (force or {}).items():
        L.append(f'Vforce_{n} {n} 0 {v}')
    L.append(extra)
    return '\n'.join(L)
