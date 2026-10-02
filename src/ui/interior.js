import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import hw from '../hardware-data/hardware.json';

const MM = 1 / hw.unit_mm;            // millimetres -> scene units
const T_PANEL = 0.1, T_LID = 0.1, T_WALL = 0.11, PCB_T = 1.6 * MM, GAP = 7 * MM;

const COL = {
  pcb: 0xeef0ec, silk: '#0b8f86', resistor: 0xd9c38e, film: 0xc0392b, ceramic: 0xd6a84c,
  alu: 0xc9ced1, black: 0x1d2022, socket: 0x34393c, pin: 0xb9bec2, glass: 0xd9873a,
  trim: 0x2f5fa8, brass: 0xc2a24a, el16: 0x20406f, el25: 0x23272a, stripe: 0xe8e8e8,
};
const BAND = { black: 0x111111, brown: 0x6b3a1e, red: 0xc02a1d, orange: 0xe5782a, yellow: 0xe8c534, green: 0x2e8b4a, blue: 0x2a52b8, violet: 0x7a3fa0, grey: 0x8a8d90, white: 0xf2f2f2, gold: 0xc9a43c, silver: 0xb8bcc0 };

const mats = {};
function mat(color, opts = {}) {
  const key = color + JSON.stringify(opts);
  return (mats[key] ||= new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness: 0, ...opts }));
}
const unitCyl = new THREE.CylinderGeometry(1, 1, 1, 18).rotateX(Math.PI / 2);   // axis = z
const unitBox = new THREE.BoxGeometry(1, 1, 1);
function cyl(r, len, material, x, y, z0) {
  const m = new THREE.Mesh(unitCyl, material);
  m.scale.set(r, r, len); m.position.set(x, y, z0 + len / 2); return m;
}
function box(w, d, h, material, x, y, z0) {
  const m = new THREE.Mesh(unitBox, material);
  m.scale.set(w, d, h); m.position.set(x, y, z0 + h / 2); return m;
}
// baked geometries (position/scale applied) so that many thin pieces become one mesh
function bCyl(r, len, x, y, z0) { return unitCyl.clone().scale(r, r, len).translate(x, y, z0 + len / 2); }
function bBox(w, d, h, x, y, z0) { return unitBox.clone().scale(w, d, h).translate(x, y, z0 + h / 2); }
const metal = () => mat(COL.pin, { metalness: 0.6, roughness: 0.35 });
const cache = {};
function once(key, make) { return (cache[key] ||= make()); }
function legsMesh(key, makeGeoms) {
  const geo = once('g' + key, () => mergeGeometries(makeGeoms()));
  return new THREE.Mesh(geo, metal());
}

function resistorTexture(bands) {
  const key = 'rt' + bands.join();
  return once(key, () => {
    const c = document.createElement('canvas'); c.width = 4; c.height = 128;
    const x = c.getContext('2d');
    x.fillStyle = '#' + COL.resistor.toString(16); x.fillRect(0, 0, 4, 128);
    const L = 6.3, at = [0.9, 1.8, 2.7, 3.6, 5.3];
    bands.forEach((b, i) => { x.fillStyle = '#' + BAND[b].toString(16).padStart(6, '0'); x.fillRect(0, (1 - (at[i] + 0.3) / L) * 128, 4, (0.6 / L) * 128); });
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
  });
}

// -- builders: local frame in millimetres, +z = away from the board --------------------------
function buildResistor(p) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(unitCyl, once('rm' + (p.bands || []).join(), () => new THREE.MeshStandardMaterial({ map: resistorTexture(p.bands || []), roughness: 0.6 })));
  body.scale.set(1.3, 1.3, 6.3); body.position.set(-1.27, 0, 1.0 + 3.15); g.add(body);
  g.add(legsMesh('res', () => [bCyl(0.28, 1.1, -1.27, 0, 0), bCyl(0.28, 8.4, 1.27, 0, 0), bBox(2.6, 0.55, 0.55, 0, 0, 8.1), bCyl(0.28, 0.9, -1.27, 0, 7.3)]));
  return g;
}
function buildDiode(p) {
  const g = new THREE.Group();
  const big = p.value === '1N5819';
  g.add(cyl(big ? 1.6 : 1.0, big ? 4.8 : 3.6, mat(big ? COL.black : COL.glass), -1.27, 0, 1.0));
  g.add(cyl(big ? 1.66 : 1.06, 0.7, mat(big ? COL.alu : COL.black), -1.27, 0, big ? 5.1 : 3.9));
  const top = big ? 7.2 : 6.0;
  g.add(legsMesh('dio' + big, () => [bCyl(0.28, 1.1, -1.27, 0, 0), bCyl(0.28, top, 1.27, 0, 0), bBox(2.6, 0.55, 0.55, 0, 0, top - 0.3), bCyl(0.28, 0.8, -1.27, 0, big ? 5.8 : 4.6)]));
  return g;
}
function buildCap(p) {
  const g = new THREE.Group(); const fp = p.fp; const d = p.fp_dim;
  if (fp === 'C_disc') {
    const disc = new THREE.Mesh(once('disc', () => new THREE.CylinderGeometry(2.5, 2.5, 2.4, 20)), mat(COL.ceramic)); disc.position.set(0, 0, 4.6);
    g.add(disc); g.add(legsMesh('discl', () => [bCyl(0.28, 4.0, -2.5, 0, 0), bCyl(0.28, 4.0, 2.5, 0, 0)])); return g;
  }
  if (fp.startsWith('C_film')) {
    const pitch = { C_film_s: 5, C_film_m: 7.5, C_film_l: 10, C_film_xl: 22.5 }[fp];
    g.add(box(d.w - 0.8, d.d - 0.6, d.h - 1.2, mat(COL.film), 0, 0, 1.2));
    g.add(legsMesh('film' + pitch, () => [bCyl(0.28, 2, -pitch / 2, 0, 0), bCyl(0.28, 2, pitch / 2, 0, 0)]));
    return g;
  }
  const diam = { C_el5: 5, C_el63: 6.3, C_el8: 8 }[fp];
  const high = d.h; const pitch = { C_el5: 2, C_el63: 2.5, C_el8: 3.5 }[fp];
  const sleeve = /25 В/.test(p.desc) ? COL.el25 : COL.el16;
  g.add(cyl(diam / 2, high - 1.0, mat(sleeve, { roughness: 0.4 }), 0, 0, 0.6));
  g.add(cyl(diam / 2 - 0.1, 0.5, mat(COL.alu, { metalness: 0.7, roughness: 0.3 }), 0, 0, high - 0.4));
  g.add(box(0.8, diam * 0.5, high - 3, mat(COL.stripe), -diam / 2 + 0.05, 0, 1.6));
  g.add(legsMesh('el' + pitch, () => [bCyl(0.28, 1.2, -pitch / 2, 0, 0), bCyl(0.28, 1.2, pitch / 2, 0, 0)]));
  return g;
}
function buildIC(p) {
  const g = new THREE.Group(); const d = p.fp_dim;
  const n = { DIP8: 8, DIP14: 14, DIP16: 16 }[p.fp];
  const bw = (n / 2) * 2.54 - 0.6;
  g.add(box(d.w - 1.2, d.d - 1.6, 3.4, mat(COL.socket), 0, 0, 0.4));
  g.add(box(bw, 6.3, 3.4, mat(COL.black, { roughness: 0.35 }), 0, 0, 3.8));
  const dot = cyl(0.5, 0.15, mat(0x9aa0a3), -bw / 2 + 0.9, -2.2, 7.15); g.add(dot);
  g.add(legsMesh('dip' + n, () => {
    const a = [];
    for (let i = 0; i < n / 2; i++) { const x = -((n / 2 - 1) * 2.54) / 2 + i * 2.54; for (const s of [-1, 1]) a.push(bBox(0.6, 0.5, 2.6, x, s * 3.9, 0.5)); }
    return a;
  }));
  return g;
}
function buildTO92() {
  const g = new THREE.Group();
  const body = new THREE.Mesh(once('to92', () => new THREE.CylinderGeometry(2.4, 2.4, 4.2, 18, 1, false, 0, Math.PI).rotateX(Math.PI / 2).rotateZ(Math.PI / 2)), mat(COL.black));
  body.position.set(0, 0, 3.4); g.add(body);
  g.add(legsMesh('to92l', () => [-1.27, 0, 1.27].map((x) => bCyl(0.28, 3.2, x, 0, 0))));
  return g;
}
function buildTrim(p) {
  const g = new THREE.Group(); const d = p.fp_dim;
  g.add(box(d.w - 1, d.d, 9.6, mat(COL.trim), 0, 0, 0.4));
  g.add(cyl(2.0, 1.0, mat(COL.brass, { metalness: 0.7 }), 2.4, 0, 9.9));
  return g;
}
function buildJack() {
  const g = new THREE.Group();
  g.add(box(14.5, 9.0, 10.8, mat(COL.black), 0, 0, 0.4));
  const hole = new THREE.Mesh(once('jh', () => new THREE.CylinderGeometry(3.2, 3.2, 1, 20)), mat(0x050606)); hole.rotation.z = Math.PI / 2; hole.position.set(7.4, 0, 5.5); g.add(hole);
  return g;
}
function buildPot(p) {   // front side of the board, bodies in the gap towards the panel
  const g = new THREE.Group();
  const dual = p.fp === 'POT9D', big = p.fp === 'POT16';
  const r = big ? 8.0 : 4.75;
  g.add(cyl(r, big ? 5.5 : 5.0, mat(0x2b2f32, { metalness: 0.4 }), 0, 0, 0));
  g.add(cyl(big ? 5.5 : 3.5, 6.8, mat(COL.alu, { metalness: 0.7, roughness: 0.3 }), 0, 0, big ? 5.5 : 5.0));
  if (dual) g.add(cyl(4.75, 5.0, mat(0x2b2f32, { metalness: 0.4 }), 0, 0, -5.0));
  return g;
}
function buildSwitch() {
  const g = new THREE.Group();
  g.add(box(12, 12, 6, mat(0x2b2f32), 0, 0, 0));
  g.add(box(8, 8, 3, mat(COL.alu, { metalness: 0.5 }), 0, 0, 6));
  return g;
}
function buildLED() {
  const g = new THREE.Group();
  g.add(cyl(1.5, 4.5, mat(0x7fe0d8, { transparent: true, opacity: 0.85, emissive: 0x00cfc1, emissiveIntensity: 0.25 }), 0, 0, 0));
  return g;
}

const BUILDERS = { R: buildResistor, D: buildDiode, LED: buildLED, C: buildCap, IC: buildIC, Q: buildTO92, POT: (p) => (p.fp === 'TRIM' ? buildTrim(p) : buildPot(p)), J: buildJack, SW: buildSwitch };

function labelTexture(text, w = 128, h = 40, fg = '#e8ecee') {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const x = c.getContext('2d'); x.fillStyle = fg; x.font = `600 ${h * 0.5}px Helvetica, Arial, sans-serif`;
  x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(text, w / 2, h / 2);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}

function silkTexture() {
  const B = hw.board, S = 10;               // px per mm
  const W = Math.round((B.x1 - B.x0) * S), H = Math.round((B.y1 - B.y0) * S);
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const x = c.getContext('2d');
  x.fillStyle = '#eef0ec'; x.fillRect(0, 0, W, H);
  // viewed from the rear: device x is mirrored on screen
  const px = (X) => (B.x1 - X) * S, py = (Y) => (B.y1 - Y) * S;
  x.strokeStyle = COL.silk; x.fillStyle = COL.silk; x.lineWidth = 3;
  x.font = '600 38px Helvetica, Arial, sans-serif'; x.textBaseline = 'top';
  x.fillText('SURF SYNTH · rev A', 40, 36);
  x.font = '400 26px Helvetica, Arial, sans-serif';
  x.fillText('12 V DC, centre +   ·   вид со стороны деталей', 40, 82);
  x.lineWidth = 2.5;
  for (const p of hw.parts) {
    if (p.side !== 'rear') continue;
    const w = p.fp_dim.w * S, d = p.fp_dim.d * S;
    x.strokeRect(px(p.x) - w / 2 + 6, py(p.y) - d / 2 + 6, w - 12, d - 12);
    x.font = `600 ${p.type === 'IC' ? 26 : 20}px Helvetica, Arial, sans-serif`;
    x.textAlign = 'center'; x.textBaseline = 'middle';
    if (p.type !== 'IC') x.fillText(p.ref, px(p.x), py(p.y) + d / 2 + 14);
    else x.fillText(p.ref, px(p.x), py(p.y) - d / 2 - 16);
  }
  // mounting holes
  x.fillStyle = '#9aa0a3';
  for (const sx of [B.x0 + 4, B.x1 - 4]) for (const sy of [B.y0 + 4, B.y1 - 4]) { x.beginPath(); x.arc(px(sx), py(sy), 16, 0, 7); x.fill(); x.fillStyle = '#fff'; x.beginPath(); x.arc(px(sx), py(sy), 8, 0, 7); x.fill(); x.fillStyle = '#9aa0a3'; }
  // solder pads of the panel-mounted parts (soldered from the rear)
  x.fillStyle = '#c9a43c';
  const pads = (cx, cy, offs) => offs.forEach(([dx, dy]) => { x.beginPath(); x.arc(px(cx + dx), py(cy + dy), 8, 0, 7); x.fill(); });
  for (const p of hw.parts) {
    if (p.side !== 'front') continue;
    if (p.ref === 'RV5') pads(p.x, p.y - 9.5, [[-5, 0], [0, 0], [5, 0]]);
    else if (p.ref === 'RV3' || p.ref === 'RV4') pads(p.x, p.y - 7.5, [[-2.5, 0], [0, 0], [2.5, 0]]);
    else if (p.ref === 'RV6A') pads(p.x, p.y - 9, [[-2.5, 0], [0, 0], [2.5, 0], [-2.5, 4.5], [0, 4.5], [2.5, 4.5]]);
    else if (p.ref === 'SW1') pads(p.x, p.y, [[-4.5, -4.5], [4.5, -4.5], [-4.5, 4.5], [4.5, 4.5]]);
    else if (p.ref === 'D10') pads(p.x, p.y, [[-1.27, 0], [1.27, 0]]);
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

export function createInterior(housingMat) {
  const root = new THREE.Group();
  const B = hw.board;
  const bw = (B.x1 - B.x0) * MM, bh = (B.y1 - B.y0) * MM, bcx = ((B.x0 + B.x1) / 2) * MM, bcy = ((B.y0 + B.y1) / 2) * MM;
  const D = 1.5, W = 7.4, H = 3.9;
  const zPanelBack = D / 2 - T_PANEL, zPcbFront = zPanelBack - GAP, zPcbRear = zPcbFront - PCB_T;

  // --- case shell and lid ------------------------------------------------------------------------
  const shape = new THREE.Shape(); const rr = (s, w, h, r) => {
    s.moveTo(-w / 2 + r, -h / 2); s.lineTo(w / 2 - r, -h / 2); s.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r);
    s.lineTo(w / 2, h / 2 - r); s.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2); s.lineTo(-w / 2 + r, h / 2);
    s.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r); s.lineTo(-w / 2, -h / 2 + r); s.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
  };
  rr(shape, W, H, 0.2);
  const hole = new THREE.Path(); rr(hole, W - 2 * T_WALL, H - 2 * T_WALL, 0.08); shape.holes.push(hole);
  const ringDepth = D - T_PANEL - T_LID;
  const ring = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: ringDepth, bevelEnabled: false, curveSegments: 10 }), housingMat);
  ring.position.z = -D / 2 + T_LID; ring.castShadow = true; ring.receiveShadow = true;
  const panel = new THREE.Mesh(new RoundedBoxGeometry(W, H, T_PANEL, 6, 0.04), housingMat);
  panel.position.z = D / 2 - T_PANEL / 2; panel.castShadow = true; panel.receiveShadow = true;
  const lid = new THREE.Mesh(new RoundedBoxGeometry(W, H, T_LID, 6, 0.04), housingMat);
  lid.position.z = -D / 2 + T_LID / 2; lid.castShadow = true;
  const shell = new THREE.Group(); shell.add(ring, panel);
  root.add(shell, lid);

  // --- PCB -----------------------------------------------------------------------------------------
  const pcbMat = new THREE.MeshStandardMaterial({ color: COL.pcb, roughness: 0.6 });
  const pcb = new THREE.Mesh(new THREE.BoxGeometry(bw, bh, PCB_T), [pcbMat, pcbMat, pcbMat, pcbMat, pcbMat, pcbMat]);
  pcb.position.set(bcx, bcy, zPcbFront - PCB_T / 2); pcb.castShadow = true; pcb.receiveShadow = true;
  const silk = new THREE.Mesh(new THREE.PlaneGeometry(bw, bh), new THREE.MeshStandardMaterial({ map: silkTexture(), roughness: 0.7, transparent: true }));
  silk.rotation.y = Math.PI; silk.position.set(bcx, bcy, zPcbRear - 0.002);
  root.add(pcb, silk);
  // standoffs
  for (const sx of [B.x0 + 4, B.x1 - 4]) for (const sy of [B.y0 + 4, B.y1 - 4]) {
    const s = new THREE.Mesh(new THREE.CylinderGeometry(3 * MM, 3 * MM, GAP + 0.03, 6).rotateX(Math.PI / 2), mat(COL.brass, { metalness: 0.7, roughness: 0.4 }));
    s.position.set(sx * MM, sy * MM, zPanelBack - (GAP + 0.03) / 2); root.add(s);
  }

  // --- speaker ------------------------------------------------------------------------------------
  const spk = new THREE.Group();
  const spkR = 33 * MM;
  const ring2 = new THREE.Mesh(new THREE.TorusGeometry(spkR - 3 * MM, 3 * MM, 10, 40), mat(0x24282b));
  const cone = new THREE.Mesh(new THREE.CylinderGeometry(spkR - 5 * MM, 12 * MM, 12 * MM, 36, 1, true).rotateX(Math.PI / 2), mat(0x3b4145, { side: THREE.DoubleSide }));
  cone.position.z = -6 * MM;
  const dust = new THREE.Mesh(new THREE.SphereGeometry(10 * MM, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(-Math.PI / 2), mat(0x2b3033));
  dust.position.z = -11 * MM;
  const magnet = new THREE.Mesh(new THREE.CylinderGeometry(19 * MM, 19 * MM, 14 * MM, 28).rotateX(Math.PI / 2), mat(0x16191b, { roughness: 0.4 }));
  magnet.position.z = -20 * MM;
  const frame = new THREE.Mesh(new THREE.CylinderGeometry(spkR - 3 * MM, 22 * MM, 14 * MM, 32, 1, true).rotateX(Math.PI / 2), mat(0x7a8084, { side: THREE.DoubleSide, metalness: 0.5, roughness: 0.4 }));
  frame.position.z = -9 * MM;
  spk.add(ring2, cone, dust, magnet, frame);
  spk.position.set(-2.15 * hw.unit_mm * MM, -0.05 * hw.unit_mm * MM, zPanelBack);
  spk.userData.ref = 'SPK1';
  root.add(spk);
  const spkPos = spk.position.clone();
  // wires speaker -> board
  const mkWire = (pts, color) => {
    const curve = new THREE.CatmullRomCurve3(pts.map((p) => new THREE.Vector3(...p)));
    const m = new THREE.Mesh(new THREE.TubeGeometry(curve, 24, 0.012, 6, false), mat(color, { roughness: 0.5 }));
    root.add(m);
  };
  const u8 = hw.parts.find((p) => p.ref === 'U8');
  const wx = (B.x0 + 2) * MM;
  mkWire([[spkPos.x + 0.05, spkPos.y - 0.2, spkPos.z - 0.65], [spkPos.x + 0.6, spkPos.y - 0.7, zPcbRear - 0.25], [wx - 0.2, u8.y * MM, zPcbRear - 0.16], [wx, u8.y * MM + 0.1, zPcbRear - 0.02]], 0xc0392b);
  mkWire([[spkPos.x + 0.12, spkPos.y - 0.22, spkPos.z - 0.65], [spkPos.x + 0.65, spkPos.y - 0.75, zPcbRear - 0.3], [wx - 0.25, u8.y * MM - 0.1, zPcbRear - 0.2], [wx, u8.y * MM, zPcbRear - 0.02]], 0x1d2022);

  // --- parts -------------------------------------------------------------------------------------------------------------
  const rear = new THREE.Group(); rear.position.z = zPcbRear; rear.scale.z = -1; root.add(rear);
  const front = new THREE.Group(); front.position.z = zPcbFront; root.add(front);
  const labelGroup = new THREE.Group(); root.add(labelGroup);
  const byRef = {}, proxies = [];
  const proxyMat = new THREE.MeshBasicMaterial({ visible: false });
  for (const p of hw.parts) {
    const type = p.type === 'POT' && p.fp === 'TRIM' ? 'POT' : p.type;
    const build = BUILDERS[type];
    if (!build) continue;
    let g = build(p);
    g.scale.setScalar(MM);
    // pots: the dual one has two gangs in one body — only build once
    if (p.ref === 'RV6B') continue;
    const holder = new THREE.Group(); holder.add(g);
    holder.position.set(p.x * MM, p.y * MM, 0);
    holder.userData.ref = p.ref;
    (p.side === 'rear' ? rear : front).add(holder);
    byRef[p.ref] = holder;
    // pick proxy (device space)
    const d = p.fp_dim; const hgt = (type === 'POT' && p.side === 'front' ? 12 : d.h) * MM;
    const proxy = new THREE.Mesh(unitBox, proxyMat);
    proxy.scale.set(d.w * MM, d.d * MM, hgt);
    const zc = p.side === 'rear' ? zPcbRear - hgt / 2 : zPcbFront + hgt / 2;
    proxy.position.set(p.x * MM, p.y * MM, zc);
    proxy.userData.ref = p.ref; proxy.userData.box = [d.w * MM, d.d * MM, hgt];
    root.add(proxy); proxies.push(proxy);
    if (p.type === 'IC') {
      const tex = labelTexture(p.value, 160, 40);
      const lab = new THREE.Mesh(new THREE.PlaneGeometry(((p.fp === 'DIP8' ? 8 : p.fp === 'DIP14' ? 14 : 16) / 2) * 2.54 * MM - 0.12, 0.17), new THREE.MeshBasicMaterial({ map: tex, transparent: true }));
      lab.rotation.y = Math.PI; lab.position.set(p.x * MM, p.y * MM, zPcbRear - 7.3 * MM); labelGroup.add(lab);
    }
  }
  // resistor / generic highlight outlines
  const outlineMat = new THREE.MeshBasicMaterial({ color: 0x00cfc1, transparent: true, opacity: 0.38, depthTest: false });
  const outlines = [];
  const outlineBox = new THREE.BoxGeometry(1, 1, 1);
  function highlight(refs) {
    outlines.forEach((o) => { o.visible = false; });
    let i = 0;
    for (const ref of refs) {
      const prox = proxies.find((p) => p.userData.ref === ref) || (ref === 'RV6' ? proxies.find((p) => p.userData.ref === 'RV6A') : null);
      if (!prox && ref !== 'SPK1') continue;
      const o = (outlines[i] ||= (() => { const m = new THREE.Mesh(outlineBox, outlineMat); m.renderOrder = 10; root.add(m); return m; })());
      if (ref === 'SPK1') { o.scale.set(spkR * 2, spkR * 2, 0.5); o.position.set(spkPos.x, spkPos.y, spkPos.z - 0.25); }
      else { o.scale.set(prox.scale.x + 0.05, prox.scale.y + 0.05, prox.scale.z + 0.03); o.position.copy(prox.position); }
      o.visible = true; i++;
    }
  }

  return {
    root, lid, shell, pcbMat, proxies, highlight, byRef, labelGroup,
    set xray(on) { pcbMat.transparent = on; pcbMat.opacity = on ? 0.28 : 1; silk.visible = !on || true; },
    lidClosedZ: lid.position.z,
  };
}
