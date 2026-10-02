import * as THREE from 'three';

export const ACCENT = 0x00cfc1;
export const SWEEP_DEG = 270;

const FONT = '"Helvetica Neue", Helvetica, Arial, sans-serif';
const PLATE_PX = 512;

// Knob angle in radians (rotation.z) for a value in 0..1. Clockwise from 7 o'clock to 5 o'clock.
export const valueToRotation = (v) => -THREE.MathUtils.degToRad(-SWEEP_DEG / 2 + SWEEP_DEG * v);

function knobProfile(r, h) {
  // Lathe profile (x = radius, y = height) with a soft chamfer and two grip grooves.
  const pts = [
    [0, 0], [r, 0], [r, h * 0.22],
    [r * 0.975, h * 0.28], [r * 0.975, h * 0.4], [r, h * 0.46],
    [r, h * 0.56], [r * 0.975, h * 0.62], [r * 0.975, h * 0.74], [r, h * 0.8],
    [r * 0.96, h * 0.97], [r * 0.9, h], [0, h],
  ];
  return pts.map(([x, y]) => new THREE.Vector2(x, y));
}

// A knob whose axis points along +z. Returns { group, body, setHighlight }.
export function createKnob({ radius, height, accentCap = false }) {
  const group = new THREE.Group();

  const geometry = new THREE.LatheGeometry(knobProfile(radius, height), 72);
  geometry.rotateX(Math.PI / 2);
  const bodyMat = new THREE.MeshStandardMaterial({
    color: 0xeeeeea, roughness: 0.45, metalness: 0.0, emissive: ACCENT, emissiveIntensity: 0,
  });
  const body = new THREE.Mesh(geometry, bodyMat);
  body.castShadow = true;
  body.receiveShadow = true;
  group.add(body);

  if (accentCap) {
    const cap = new THREE.Mesh(
      new THREE.CircleGeometry(radius * 0.8, 64),
      new THREE.MeshStandardMaterial({ color: ACCENT, roughness: 0.5 }),
    );
    cap.position.z = height + 0.003;
    group.add(cap);
  }

  const mark = new THREE.Mesh(
    new THREE.BoxGeometry(radius * 0.1, radius * 0.4, 0.008),
    new THREE.MeshStandardMaterial({ color: accentCap ? 0xffffff : ACCENT, roughness: 0.5 }),
  );
  mark.position.set(0, radius * 0.58, height + 0.006);
  group.add(mark);

  const setHighlight = (amount) => { bodyMat.emissiveIntensity = amount * 0.18; };
  return { group, body, setHighlight };
}

function makeTexture(canvas) {
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  return tex;
}

function plane(size, tex) {
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(size, size),
    new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, toneMapped: false }),
  );
  mesh.renderOrder = 2;
  return mesh;
}

// Printed scale around a knob: 11 ticks on the 270° sweep, "0"/"10" at the ends, label in the gap.
export function createDialPlate({ knobRadius, label }) {
  const size = knobRadius * 4.6;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = PLATE_PX;
  const c = canvas.getContext('2d');
  const k = PLATE_PX / size; // px per world unit
  const mid = PLATE_PX / 2;
  c.strokeStyle = '#6d7377';
  c.fillStyle = '#6d7377';
  c.lineCap = 'butt';
  for (let i = 0; i <= 10; i++) {
    const a = THREE.MathUtils.degToRad(-SWEEP_DEG / 2 + (SWEEP_DEG / 10) * i);
    const major = i === 0 || i === 5 || i === 10;
    const r0 = knobRadius * 1.22 * k;
    const r1 = knobRadius * (major ? 1.5 : 1.4) * k;
    c.lineWidth = major ? 3 : 2;
    c.beginPath();
    c.moveTo(mid + Math.sin(a) * r0, mid - Math.cos(a) * r0);
    c.lineTo(mid + Math.sin(a) * r1, mid - Math.cos(a) * r1);
    c.stroke();
  }
  c.font = `500 ${Math.round(knobRadius * 0.34 * k)}px ${FONT}`;
  c.textAlign = 'center';
  c.textBaseline = 'middle';
  for (const [i, text] of [[0, '0'], [10, '10']]) {
    const a = THREE.MathUtils.degToRad(-SWEEP_DEG / 2 + (SWEEP_DEG / 10) * i);
    const rr = knobRadius * 1.78 * k;
    c.fillText(text, mid + Math.sin(a) * rr, mid - Math.cos(a) * rr);
  }
  c.font = `600 ${Math.round(knobRadius * 0.4 * k)}px ${FONT}`;
  c.letterSpacing = `${Math.round(knobRadius * 0.08 * k)}px`;
  c.fillStyle = '#3c4144';
  c.fillText(label, mid, mid + knobRadius * 1.95 * k);
  return plane(size, makeTexture(canvas));
}

// Small standalone text label.
export function createLabel(text, { width = 1, fontUnits = 0.11 } = {}) {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 128;
  const c = canvas.getContext('2d');
  const k = 512 / width;
  c.font = `600 ${Math.round(fontUnits * k)}px ${FONT}`;
  c.letterSpacing = `${Math.round(fontUnits * 0.2 * k)}px`;
  c.fillStyle = '#3c4144';
  c.textAlign = 'center';
  c.textBaseline = 'middle';
  c.fillText(text, 256, 64);
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(width, width / 4),
    new THREE.MeshBasicMaterial({ map: makeTexture(canvas), transparent: true, depthWrite: false, toneMapped: false }),
  );
  mesh.renderOrder = 2;
  return mesh;
}
