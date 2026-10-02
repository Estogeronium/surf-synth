import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import hw from '../hardware-data/hardware.json';

const MM = 1 / hw.unit_mm;                       // millimetres -> scene units
const T_PANEL = 0.1, T_LID = 0.1, T_WALL = 0.11;
const B = hw.board;
const PCB_T = B.thickness;                       // mm

const COL = {
  board: 0x2a7b57, boardSilk: '#f4f6f2', gold: 0xd7b44a, black: 0x1d2022, socket: 0x2a2e31, pin: 0xb9bec2,
  pico: 0x1f7a4a, red: 0xb3262a, resistor: 0xd9c38e, ceramic: 0xd6a84c, glass: 0xd9873a, alu: 0xc9ced1, brass: 0xc2a24a,
  el16: 0x20406f, stripe: 0xe8e8e8,
};
const BAND = { black: 0x111111, brown: 0x6b3a1e, red: 0xc02a1d, orange: 0xe5782a, yellow: 0xe8c534, green: 0x2e8b4a, blue: 0x2a52b8, violet: 0x7a3fa0, grey: 0x8a8d90, white: 0xf2f2f2, gold: 0xc9a43c, silver: 0xb8bcc0 };

const mats = {};
const mat = (color, o = {}) => (mats[color + JSON.stringify(o)] ||= new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness: 0, ...o }));
const metal = () => mat(COL.pin, { metalness: 0.6, roughness: 0.35 });
const unitCyl = new THREE.CylinderGeometry(1, 1, 1, 18).rotateX(Math.PI / 2);   // axis = z
const unitBox = new THREE.BoxGeometry(1, 1, 1);
const cyl = (r, len, m, x, y, z0) => { const o = new THREE.Mesh(unitCyl, m); o.scale.set(r, r, len); o.position.set(x, y, z0 + len / 2); return o; };
const box = (w, d, h, m, x, y, z0) => { const o = new THREE.Mesh(unitBox, m); o.scale.set(w, d, h); o.position.set(x, y, z0 + h / 2); return o; };
const bCyl = (r, len, x, y, z0) => unitCyl.clone().scale(r, r, len).translate(x, y, z0 + len / 2);
const bBox = (w, d, h, x, y, z0) => unitBox.clone().scale(w, d, h).translate(x, y, z0 + h / 2);
const cache = {};
const once = (k, f) => (cache[k] ||= f());
const legs = (key, mk) => new THREE.Mesh(once('g' + key, () => mergeGeometries(mk())), metal());

function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

// ---- parts that sit on the board: local frame in mm, +z = away from the board (towards the rear) --------------
// Two-pad parts are built between their two pads (a, b in mm, relative to the part centre).
function axial(g, a, b, bodyR, bodyLen, bodyMat, extra) {
  const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy), ang = Math.atan2(dy, dx);
  const holder = new THREE.Group(); holder.rotation.z = ang;
  const h = bodyR + 0.6;
  const body = cyl(bodyR, bodyLen, bodyMat, 0, 0, 0); body.rotation.y = Math.PI / 2; body.position.set(0, 0, h);
  holder.add(body);
  if (extra) extra(holder, bodyR, bodyLen, h);
  holder.add(legsMesh2(len, h));
  g.add(holder);
}
function legsMesh2(len, h) {
  const key = `ax${len.toFixed(1)}_${h.toFixed(1)}`;
  const geo = once('g' + key, () => mergeGeometries([
    bCyl(0.3, h, -len / 2, 0, 0), bCyl(0.3, h, len / 2, 0, 0),
    unitBox.clone().scale(len, 0.6, 0.6).translate(0, 0, h + 0.1),
  ]));
  return new THREE.Mesh(geo, metal());
}
function buildResistor(p, pads) {
  const g = new THREE.Group();
  const a = pads['1'], b = pads['2'];
  const tex = once('rt' + p.bands.join(), () => canvasTex(4, 128, (x) => {
    x.fillStyle = '#d9c38e'; x.fillRect(0, 0, 4, 128);
    [0.9, 1.8, 2.7, 4.6].forEach((at, i) => { x.fillStyle = '#' + BAND[p.bands[i]].toString(16).padStart(6, '0'); x.fillRect(0, (1 - (at + 0.3) / 6.3) * 128, 4, (0.6 / 6.3) * 128); });
  }));
  const bodyMat = once('rm' + p.bands.join(), () => new THREE.MeshStandardMaterial({ map: tex, roughness: 0.6 }));
  const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy), ang = Math.atan2(dy, dx);
  const holder = new THREE.Group(); holder.position.set((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0); holder.rotation.z = ang;
  const body = new THREE.Mesh(unitCyl, bodyMat); body.scale.set(1.2, 1.2, 6.3); body.rotation.y = Math.PI / 2; body.position.set(0, 0, 1.6);
  holder.add(body, legsMesh2(len, 1.6));
  g.add(holder); return g;
}
function buildDiode(p, pads) {
  const g = new THREE.Group(); const a = pads.A, k = pads.K;
  const dx = k[0] - a[0], dy = k[1] - a[1], len = Math.hypot(dx, dy), ang = Math.atan2(dy, dx);
  const holder = new THREE.Group(); holder.position.set((a[0] + k[0]) / 2, (a[1] + k[1]) / 2, 0); holder.rotation.z = ang;
  const bodyL = 4.7;
  const body = new THREE.Mesh(unitCyl, mat(COL.black)); body.scale.set(1.35, 1.35, bodyL); body.rotation.y = Math.PI / 2; body.position.set(0, 0, 2.0);
  const band = new THREE.Mesh(unitCyl, mat(COL.alu)); band.scale.set(1.4, 1.4, 0.8); band.rotation.y = Math.PI / 2; band.position.set(bodyL / 2 - 0.6, 0, 2.0);
  holder.add(body, band, legsMesh2(len, 2.0)); g.add(holder); return g;
}
function buildCap(p, pads) {
  const g = new THREE.Group(); const a = pads['1'], b = pads['2'];
  const cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2;
  const holder = new THREE.Group(); holder.position.set(cx, cy, 0); holder.rotation.z = Math.atan2(b[1] - a[1], b[0] - a[0]);
  if (p.kind === 'CP') {
    const big = /470/.test(p.value);
    const dia = big ? 8 : 5, high = big ? 11.5 : 11;
    holder.add(cyl(dia / 2, high - 1, mat(COL.el16, { roughness: 0.4 }), 0, 0, 0.6));
    holder.add(cyl(dia / 2 - 0.1, 0.5, mat(COL.alu, { metalness: 0.7, roughness: 0.3 }), 0, 0, high - 0.4));
    holder.add(box(0.8, dia * 0.5, high - 3, mat(COL.stripe), -dia / 2 + 0.05, 0, 1.6));
    holder.add(legs(`el${(big ? 3.5 : 2)}`, () => [bCyl(0.3, 1.2, -(big ? 1.75 : 1), 0, 0), bCyl(0.3, 1.2, (big ? 1.75 : 1), 0, 0)]));
  } else {
    const disc = new THREE.Mesh(once('disc', () => new THREE.CylinderGeometry(2.5, 2.5, 2.4, 20)), mat(COL.ceramic)); disc.position.set(0, 0, 4.6);
    holder.add(disc, legs('discl', () => [bCyl(0.3, 4.0, -2.5, 0, 0), bCyl(0.3, 4.0, 2.5, 0, 0)]));
  }
  g.add(holder); return g;
}
function buildTO92(p, pads) {
  const g = new THREE.Group(); const c = pads.B;
  const body = new THREE.Mesh(once('to92', () => new THREE.CylinderGeometry(2.4, 2.4, 4.2, 18, 1, false, 0, Math.PI).rotateX(Math.PI / 2).rotateZ(Math.PI / 2)), mat(COL.black));
  body.position.set(c[0], c[1], 3.4); g.add(body);
  g.add(legs('to92l', () => [-1.27, 0, 1.27].map((x) => bCyl(0.3, 3.2, x, 0, 0))).translateX(c[0]).translateY(c[1]));
  return g;
}

// sockets and modules ------------------------------------------------------------------------------------------------------------------------
function picoTexture() {
  const L = ['GP0', 'GP1', 'GND', 'GP2', 'GP3', 'GP4', 'GP5', 'GND', 'GP6', 'GP7', 'GP8', 'GP9', 'GND', 'GP10', 'GP11', 'GP12', 'GP13', 'GND', 'GP14', 'GP15'];
  const R = ['GP16', 'GP17', 'GND', 'GP18', 'GP19', 'GP20', 'GP21', 'GND', 'GP22', 'RUN', 'GP26', 'GP27', 'AGND', 'GP28', 'VREF', '3V3', '3V3_EN', 'GND', 'VSYS', 'VBUS'];
  const used = new Set(['GP9', 'GP10', 'GP11', 'GP15', 'GP16', 'GP17', 'GP18', 'GP19', 'AGND', '3V3', 'GND', 'VSYS']);
  return canvasTex(210, 520, (x, w, h) => {
    x.fillStyle = '#1f7a4a'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#d8efe0'; x.font = '600 13px Helvetica, Arial, sans-serif'; x.textAlign = 'center';
    x.fillText('Raspberry Pi Pico 2', w / 2, h * 0.58); x.font = '11px Helvetica, Arial, sans-serif'; x.fillText('RP2350', w / 2, h * 0.58 + 16);
    x.font = '600 10px Helvetica, Arial, sans-serif';
    for (let i = 0; i < 20; i++) {
      const y = 22 + i * (h - 44) / 19;
      x.textAlign = 'left'; x.fillStyle = used.has(L[i]) ? '#ffe27a' : '#a9d2b8'; x.fillText(L[i], 16, y + 4);
      x.textAlign = 'right'; x.fillStyle = used.has(R[19 - i]) ? '#ffe27a' : '#a9d2b8'; x.fillText(R[19 - i], w - 16, y + 4);
    }
    x.fillStyle = '#e8c534'; for (let i = 0; i < 20; i++) { const y = 22 + i * (h - 44) / 19; x.fillRect(2, y - 3, 7, 7); x.fillRect(w - 9, y - 3, 7, 7); }
  });
}
function buildPico() {
  const g = new THREE.Group();
  const pitch = 2.54, len = 50.8 + 2.6, wid = 17.78 + 3.2;
  // sockets (two PBS-20 strips) and pins
  for (const sx of [-17.78 / 2, 17.78 / 2]) g.add(box(2.54, 50.8, 8.5, mat(COL.socket), sx, 0, 0));
  const top = 8.5;
  const pcb = new THREE.Mesh(new THREE.BoxGeometry(wid, len, 1.0), [mat(COL.pico), mat(COL.pico), mat(COL.pico), mat(COL.pico), new THREE.MeshStandardMaterial({ map: picoTexture(), roughness: 0.6 }), mat(COL.pico)]);
  pcb.position.set(0, 0, top + 0.5); g.add(pcb);
  g.add(box(7.5, 5.5, 2.8, mat(COL.alu, { metalness: 0.7, roughness: 0.3 }), 0, len / 2 - 1.8, top + 1.0));    // USB connector at the top
  g.add(box(7, 7, 0.9, mat(COL.black), 0, -1, top + 1.0));                                                       // RP2350
  g.add(box(5, 4, 0.9, mat(COL.black), 0, -9, top + 1.0));                                                       // flash
  g.add(box(4, 3.5, 1.3, mat(0xf0f0f0), -3.5, len / 2 - 11, top + 1.0));                                         // BOOTSEL
  return g;
}
function buildMCP() {
  const g = new THREE.Group();
  g.add(box(10.16 - 1.8 + 0.4, 20.3, 3.4, mat(COL.socket), 0, 0, 0));
  g.add(box(6.4, 19.2, 3.4, mat(COL.black, { roughness: 0.35 }), 0, 0, 3.4));
  const tex = canvasTex(64, 220, (x, w, h) => { x.fillStyle = '#e8ecee'; x.font = '600 18px Helvetica, Arial, sans-serif'; x.translate(w / 2, h / 2); x.rotate(Math.PI / 2); x.textAlign = 'center'; x.fillText('MCP3008', 0, -4); x.font = '12px Helvetica, Arial, sans-serif'; x.fillText('I/P', 0, 14); });
  const lab = new THREE.Mesh(new THREE.PlaneGeometry(6.2, 19), new THREE.MeshBasicMaterial({ map: tex, transparent: true })); lab.position.set(0, 0, 6.85); g.add(lab);
  g.add(cyl(0.5, 0.15, mat(0x9aa0a3), 2.3, 8.2, 6.8));
  g.add(legs('dip16', () => { const a = []; for (let i = 0; i < 8; i++) for (const s of [-1, 1]) a.push(bBox(0.5, 0.6, 2.6, s * 3.9, -8.89 + i * 2.54, 0.5)); return a; }));
  return g;
}
function buildAmp() {
  const g = new THREE.Group();
  g.add(box(17.8, 2.54, 8.5, mat(COL.socket), 0, 0, 0));                    // 1x7 socket along x
  const tex = canvasTex(356, 420, (x, w, h) => {
    x.fillStyle = '#b3262a'; x.fillRect(0, 0, w, h);
    x.fillStyle = '#fff'; x.font = '600 24px Helvetica, Arial, sans-serif'; x.textAlign = 'center';
    x.fillText('MAX98357A', w / 2, h * 0.55); x.font = '16px Helvetica, Arial, sans-serif'; x.fillText('I2S 3W Amp', w / 2, h * 0.55 + 24);
    x.font = '600 16px Helvetica, Arial, sans-serif'; const names = ['VIN', 'GND', 'SD', 'GAIN', 'DIN', 'BCLK', 'LRC'];
    names.forEach((n, i) => { x.fillText(n, (i + 0.5) * w / 7, 24); });
    x.fillStyle = '#e8c534'; x.fillRect(w * 0.18, h - 36, 26, 26); x.fillRect(w * 0.7, h - 36, 26, 26);
    x.fillStyle = '#fff'; x.fillText('+', w * 0.18 + 13, h - 44); x.fillText('−', w * 0.7 + 13, h - 44);
  });
  const pcb = new THREE.Mesh(new THREE.BoxGeometry(19.5, 21.5, 1.0), [mat(COL.red), mat(COL.red), mat(COL.red), mat(COL.red), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.6 }), mat(COL.red)]);
  pcb.position.set(0, -11.5, 9.0); g.add(pcb);
  g.add(box(3.2, 3.2, 0.8, mat(COL.black), 0, -11, 9.5));
  return g;
}

// panel side -------------------------------------------------------------------------------------------------------------------------------------------
function buildPot() {
  const g = new THREE.Group();   // z: 0 at the back of the panel, negative = rearwards (device frame)
  g.add(cyl(4.75, 5.0, mat(0x2b2f32, { metalness: 0.4 }), 0, 0, -5.0));
  g.add(cyl(3.0, 5.0, mat(COL.alu, { metalness: 0.7, roughness: 0.3 }), 0, 0, 0));
  g.add(new THREE.Mesh(once('lug', () => mergeGeometries([-5, 0, 5].map((x) => bCyl(0.4, 3.5, x, -7.5, -8.5)))), metal()));
  return g;
}
function buildSwitch() {
  const g = new THREE.Group();
  g.add(cyl(6.5, 6.0, mat(0x2b2f32), 0, 0, -6.0));
  g.add(new THREE.Mesh(once('swl', () => mergeGeometries([-3, 3].map((x) => bCyl(0.4, 3.0, x, -6.5, -9)))), metal()));
  return g;
}
function buildLED() {
  const g = new THREE.Group();
  g.add(cyl(1.5, 5.0, mat(0x7fe0d8, { transparent: true, opacity: 0.85, emissive: 0x00cfc1, emissiveIntensity: 0.3 }), 0, 0, -5.0));
  g.add(new THREE.Mesh(once('ledl', () => mergeGeometries([-1.27, 1.27].map((x) => bCyl(0.3, 4.5, x, -4, -9.5)))), metal()));
  return g;
}
function buildJack() {
  const g = new THREE.Group();   // x axis = into the case, jack on the right wall
  g.add(box(14, 9, 11, mat(COL.black), -11, 0, -5.5));
  g.add(new THREE.Mesh(once('jh', () => new THREE.CylinderGeometry(3.2, 3.2, 1, 20).rotateZ(Math.PI / 2)), mat(0x050606)));
  g.children[1].position.set(-4.2, 0, 0);
  g.add(new THREE.Mesh(once('jl', () => mergeGeometries([bCyl(0.4, 3, -16, 3, -7), bCyl(0.4, 3, -16, -3, -7)])), metal()));
  return g;
}

// ---- the whole interior ---------------------------------------------------------------------------------------------------------------
export function createInterior(housingMat) {
  const root = new THREE.Group();
  const D = 1.5, W = 7.4, H = 3.9;
  const zPB = D / 2 - T_PANEL;                  // back face of the panel (scene units)

  // case shell, panel and lid
  const shape = new THREE.Shape();
  const rr = (s, w, h, r) => {
    s.moveTo(-w / 2 + r, -h / 2); s.lineTo(w / 2 - r, -h / 2); s.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r);
    s.lineTo(w / 2, h / 2 - r); s.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2); s.lineTo(-w / 2 + r, h / 2);
    s.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r); s.lineTo(-w / 2, -h / 2 + r); s.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
  };
  rr(shape, W, H, 0.2);
  const inner = new THREE.Path(); rr(inner, W - 2 * T_WALL, H - 2 * T_WALL, 0.08); shape.holes.push(inner);
  const ring = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: D - T_PANEL - T_LID, bevelEnabled: false, curveSegments: 10 }), housingMat);
  ring.position.z = -D / 2 + T_LID; ring.castShadow = true; ring.receiveShadow = true;
  const panel = new THREE.Mesh(new RoundedBoxGeometry(W, H, T_PANEL, 6, 0.04), housingMat);
  panel.position.z = D / 2 - T_PANEL / 2; panel.castShadow = true; panel.receiveShadow = true;
  const lid = new THREE.Mesh(new RoundedBoxGeometry(W, H, T_LID, 6, 0.04), housingMat);
  lid.position.z = -D / 2 + T_LID / 2; lid.castShadow = true;
  root.add(ring, panel, lid);

  // frame helpers: everything below is placed in device mm and converted
  const toU = (g) => { g.scale.multiplyScalar(MM); return g; };
  const panelFrame = new THREE.Group(); panelFrame.position.z = zPB; root.add(panelFrame);   // z in mm, negative = rear
  panelFrame.scale.setScalar(MM);

  // perfboard
  const zTop = -(B.standoff + PCB_T);                               // component side, mm from panel back
  const sx = B.w, sy = B.h;
  const pcbTex = canvasTex(Math.round(sx * 12), Math.round(sy * 12), (x, w, h) => {
    const S = 12; x.fillStyle = '#2a7b57'; x.fillRect(0, 0, w, h);
    for (let c = 0; c < B.cols; c++) for (let r = 0; r < B.rows; r++) {
      const px = (sx / 2 + (c - (B.cols - 1) / 2) * B.pitch) * S, py = (sy / 2 + (r - (B.rows - 1) / 2) * B.pitch) * S;
      x.fillStyle = '#d7b44a'; x.beginPath(); x.arc(px, py, 3.4, 0, 7); x.fill();
      x.fillStyle = '#143d2b'; x.beginPath(); x.arc(px, py, 1.5, 0, 7); x.fill();
    }
    // silkscreen frames of the big parts
    x.strokeStyle = '#f4f6f2'; x.lineWidth = 2; x.fillStyle = '#f4f6f2'; x.font = '600 14px Helvetica, Arial, sans-serif'; x.textAlign = 'center';
    const hp = (c, r) => [(sx / 2 + (c - (B.cols - 1) / 2) * B.pitch) * S, (sy / 2 + (r - (B.rows - 1) / 2) * B.pitch) * S];
    const rect = (c0, r0, c1, r1, label) => { const a = hp(c0, r0), b = hp(c1, r1); x.strokeRect(a[0] - 12, a[1] - 12, b[0] - a[0] + 24, b[1] - a[1] + 24); x.fillText(label, (a[0] + b[0]) / 2, b[1] + 28); };
    rect(3, 3, 10, 22, 'U1 Pico 2'); rect(16, 5, 19, 12, 'U2 MCP3008'); rect(3, 25, 9, 25, 'U3 MAX98357A');
    x.font = '600 12px Helvetica, Arial, sans-serif';
    for (const p of hw.parts) {
      if (p.side !== 'rear' || !p.pads) continue;
      const q = Object.values(p.pads); const cx = q.reduce((s2, v) => s2 + v[0], 0) / q.length, cy = q.reduce((s2, v) => s2 + v[1], 0) / q.length;
      // pad coordinates are device mm: convert to canvas (rear view: x mirrored)
      const X = (B.cx + sx / 2 - cx) * S, Y = (B.cy + sy / 2 - cy) * S;
      x.fillText(p.ref, X, Y - 22);
    }
    x.font = '600 20px Helvetica, Arial, sans-serif'; x.textAlign = 'left'; x.fillText('SURF SYNTH · цифровая версия', 20, 30);
  });
  const boardMats = [mat(COL.board), mat(COL.board), mat(COL.board), mat(COL.board), mat(COL.board), mat(COL.board)];
  const pcb = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, PCB_T), boardMats);
  pcb.position.set(B.cx, B.cy, -B.standoff - PCB_T / 2);
  const face = new THREE.Mesh(new THREE.PlaneGeometry(sx, sy), new THREE.MeshStandardMaterial({ map: pcbTex, roughness: 0.6 }));
  face.rotation.y = Math.PI; face.position.set(B.cx, B.cy, zTop - 0.01);
  panelFrame.add(pcb, face);
  // standoffs
  for (const dx of [-1, 1]) for (const dy of [-1, 1]) {
    const x = B.cx + dx * (sx / 2 - 3.8), y = B.cy + dy * (sy / 2 - 3.8);
    panelFrame.add(cyl(2.75, B.standoff, mat(COL.brass, { metalness: 0.7, roughness: 0.4 }), x, y, -B.standoff));
  }

  // components on the rear side of the board
  const rear = new THREE.Group(); rear.position.z = zTop; rear.scale.z = -1; panelFrame.add(rear);
  const padsOf = (p, absolute) => Object.fromEntries(Object.entries(p.pads || {}).map(([k, v]) => [k, [v[0], v[1]]]));
  const holders = {};
  const hole = (c, r) => [B.cx - (c - (B.cols - 1) / 2) * B.pitch, B.cy + ((B.rows - 1) / 2 - r) * B.pitch];
  for (const p of hw.parts) {
    let g = null, host = rear, pos = [p.x, p.y, 0];
    if (p.side === 'rear') {
      if (p.type === 'R') g = buildResistor(p, padsOf(p));
      else if (p.type === 'D') g = buildDiode(p, padsOf(p));
      else if (p.type === 'C') g = buildCap(p, padsOf(p));
      else if (p.type === 'Q') g = buildTO92(p, padsOf(p));
      else if (p.type === 'PICO') { g = buildPico(); pos = [p.x, p.y, 0]; }
      else if (p.type === 'MCP') { g = buildMCP(); pos = [p.x, p.y, 0]; }
      else if (p.type === 'AMP') { g = buildAmp(); pos = [p.x, hole(0, 25)[1], 0]; }
      if (!g) continue;
      const holder = new THREE.Group();
      holder.add(g);
      if (['R', 'D', 'C', 'Q'].includes(p.type)) holder.position.set(0, 0, 0);   // these are built in absolute mm
      else holder.position.set(pos[0], pos[1], 0);
      host.add(holder); holders[p.ref] = holder;
    } else if (p.side === 'panel') {
      if (p.type === 'POT') g = buildPot();
      else if (p.type === 'SW') g = buildSwitch();
      else if (p.type === 'LED') g = buildLED();
      if (!g) continue;
      const holder = new THREE.Group(); holder.add(g); holder.position.set(p.x, p.y, 0);
      panelFrame.add(holder); holders[p.ref] = holder;
    } else if (p.side === 'wall') {
      const holder = new THREE.Group(); holder.add(buildJack()); holder.position.set(p.x, p.y, -14);
      panelFrame.add(holder); holders[p.ref] = holder;
    }
  }
  // the amplifier module sits with its header along a board row
  if (holders.U3) { holders.U3.position.set(hole(6, 25)[0], hole(6, 25)[1], 0); holders.U3.rotation.z = 0; }
  if (holders.U1) holders.U1.position.set((hole(3, 12)[0] + hole(10, 12)[0]) / 2, (hole(3, 3)[1] + hole(3, 22)[1]) / 2, 0);
  if (holders.U2) holders.U2.position.set((hole(16, 5)[0] + hole(19, 5)[0]) / 2, (hole(16, 5)[1] + hole(16, 12)[1]) / 2, 0);

  // speaker on the panel (left)
  const spk = new THREE.Group();
  const spkR = 32;
  spk.add(new THREE.Mesh(new THREE.TorusGeometry(spkR - 3, 3, 10, 40), mat(0x24282b)));
  const cone = new THREE.Mesh(new THREE.CylinderGeometry(spkR - 5, 12, 12, 36, 1, true).rotateX(Math.PI / 2), mat(0x3b4145, { side: THREE.DoubleSide })); cone.position.z = -6;
  const dust = new THREE.Mesh(new THREE.SphereGeometry(10, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(-Math.PI / 2), mat(0x2b3033)); dust.position.z = -11;
  const magnet = new THREE.Mesh(new THREE.CylinderGeometry(18, 18, 12, 28).rotateX(Math.PI / 2), mat(0x16191b, { roughness: 0.4 })); magnet.position.z = -19;
  const frame = new THREE.Mesh(new THREE.CylinderGeometry(spkR - 3, 21, 13, 32, 1, true).rotateX(Math.PI / 2), mat(0x7a8084, { side: THREE.DoubleSide, metalness: 0.5, roughness: 0.4 })); frame.position.z = -9;
  spk.add(cone, dust, magnet, frame);
  const spkP = hw.parts.find((p) => p.ref === 'SPK1');
  spk.position.set(spkP.x, spkP.y, 0); panelFrame.add(spk); holders.SPK1 = spk;

  // wires -----------------------------------------------------------------------------------------------------------------------------------------------------
  const wireGroup = new THREE.Group(); panelFrame.add(wireGroup);
  const wires = [];
  const bx0 = B.cx - sx / 2, bx1 = B.cx + sx / 2, by0 = B.cy - sy / 2, by1 = B.cy + sy / 2;
  function route(w) {
    const P = new THREE.Vector3(...w.p), Q = new THREE.Vector3(...w.q);
    const onBoard = (v) => Math.abs(v.z - zTop) < 0.5;
    const pts = [];
    const lift = (v) => new THREE.Vector3(v.x, v.y, v.z - 1.2);
    const around = (v) => {
      // go from a point in front of the board around its nearest edge to the rear side
      const dxl = v.x - bx0, dxr = bx1 - v.x, dyb = v.y - by0, dyt = by1 - v.y, m = Math.min(dxl, dxr, dyb, dyt);
      let ex = v.x, ey = v.y;
      if (m === dxl) ex = bx0 - 1.5; else if (m === dxr) ex = bx1 + 1.5; else if (m === dyb) ey = by0 - 1.5; else ey = by1 + 1.5;
      return [new THREE.Vector3(v.x, v.y, v.z), new THREE.Vector3(ex, ey, v.z), new THREE.Vector3(ex, ey, zTop - 3)];
    };
    if (onBoard(P) && onBoard(Q)) {
      const len = P.distanceTo(Q), h = Math.min(2.5 + len * 0.1, 11);
      pts.push(P, lift(P), new THREE.Vector3((P.x + Q.x) / 2, (P.y + Q.y) / 2, zTop - h), lift(Q), Q);
    } else {
      const panelPt = onBoard(P) ? Q : P, boardPt = onBoard(P) ? P : Q;
      const a = around(panelPt);
      pts.push(...a, new THREE.Vector3(boardPt.x, boardPt.y, zTop - 5), boardPt);
      if (!onBoard(P)) { /* order is panel -> board already */ } else pts.reverse();
    }
    return pts;
  }
  const wireMatCache = {};
  for (const w of hw.wires) {
    const curve = new THREE.CatmullRomCurve3(route(w), false, 'catmullrom', 0.4);
    const col = w.color;
    const m = (wireMatCache[col] ||= new THREE.MeshStandardMaterial({ color: col, roughness: 0.5, emissive: 0x000000 }));
    const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 28, w.kind === 'harness' ? 0.55 : 0.4, 6, false), m);
    mesh.userData = { net: w.net, a: w.a.split('.')[0], b: w.b.split('.')[0] };
    wireGroup.add(mesh); wires.push(mesh);
  }

  // pick proxies from bounding boxes, in scene space ----------------------------------------------------------------------------------------
  root.updateMatrixWorld(true);
  const proxies = [];
  const proxyMat = new THREE.MeshBasicMaterial({ visible: false });
  const proxyHost = new THREE.Group(); root.add(proxyHost);
  for (const [ref, holder] of Object.entries(holders)) {
    const bb = new THREE.Box3().setFromObject(holder);
    if (bb.isEmpty()) continue;
    const size = bb.getSize(new THREE.Vector3()), ctr = bb.getCenter(new THREE.Vector3());
    const m = new THREE.Mesh(unitBox, proxyMat);
    // root is positioned at the origin of its parent (device); compute in root space
    const inv = new THREE.Matrix4().copy(root.matrixWorld).invert();
    const c2 = ctr.clone().applyMatrix4(inv);
    m.scale.copy(size); m.position.copy(c2); m.userData.ref = ref;
    proxyHost.add(m); proxies.push(m);
  }

  const outlineMat = new THREE.MeshBasicMaterial({ color: 0x00cfc1, transparent: true, opacity: 0.4, depthTest: false });
  const outlines = [];
  const hotMat = new THREE.MeshStandardMaterial({ color: 0x35ffe8, emissive: 0x00cfc1, emissiveIntensity: 1.0, roughness: 0.4 });
  const dimMats = {};
  wires.forEach((w) => { w.userData.base = w.material; });
  const dimOf = (w) => (dimMats[w.userData.base.color.getHex()] ||= new THREE.MeshStandardMaterial({ color: w.userData.base.color, transparent: true, opacity: 0.16, roughness: 0.6, depthWrite: false }));
  function paintWires(isHot) {
    const any = wires.some(isHot);
    for (const w of wires) w.material = !any ? w.userData.base : (isHot(w) ? hotMat : dimOf(w));
  }
  function highlight(refs) {
    outlines.forEach((o) => { o.visible = false; });
    const set = new Set(refs);
    let i = 0;
    for (const ref of set) {
      const prox = proxies.find((p) => p.userData.ref === ref);
      if (!prox) continue;
      const o = (outlines[i] ||= (() => { const mm = new THREE.Mesh(unitBox, outlineMat); mm.renderOrder = 10; root.add(mm); return mm; })());
      o.scale.copy(prox.scale).addScalar(0.04); o.position.copy(prox.position); o.visible = true; i++;
    }
    paintWires((w) => set.has(w.userData.a) || set.has(w.userData.b));
  }
  function highlightNet(net) {
    outlines.forEach((o) => { o.visible = false; });
    paintWires((w) => w.userData.net === net);
  }
  function clear() { highlight([]); }

  return {
    root, lid, proxies, highlight, highlightNet, clear, holders,
    set xray(on) { pcb.material.forEach((m) => { m.transparent = on; m.opacity = on ? 0.3 : 1; }); face.visible = !on; },
    lidClosedZ: lid.position.z,
  };
}
