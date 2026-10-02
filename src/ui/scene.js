import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  ACCENT, createKnob, createDialPlate, createLabel, valueToRotation,
} from './knob.js';
import { createInterior } from './interior.js';

const W = 7.4, H = 3.9, D = 1.5;
const FACE = D / 2;
const CAMERA_FOV = 26;

const KNOBS = [
  { id: 'surf', label: 'SURF', x: 1.5, y: 0.75, radius: 0.62, accentCap: true },
  { id: 'tide', label: 'TIDE', x: 0.5, y: -1.1, radius: 0.3 },
  { id: 'tone', label: 'TONE', x: 1.5, y: -1.1, radius: 0.3 },
  { id: 'volume', label: 'VOLUME', x: 2.5, y: -1.1, radius: 0.3 },
];

export function createInstrument({ canvas, values, onChange, onPower, onPartSelect, onPartHover }) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.VSMShadowMap;
  renderer.toneMapping = THREE.NeutralToneMapping;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.6;

  const camera = new THREE.PerspectiveCamera(CAMERA_FOV, 1, 0.1, 100);
  const sun = new THREE.DirectionalLight(0xffffff, 1.15);
  sun.position.set(-3.5, 6, 6);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.left = -8; sun.shadow.camera.right = 8;
  sun.shadow.camera.top = 8; sun.shadow.camera.bottom = -8;
  sun.shadow.radius = 7;
  sun.shadow.blurSamples = 16;
  sun.shadow.bias = -0.0004;
  scene.add(sun);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(40, 40),
    new THREE.ShadowMaterial({ opacity: 0.16 }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -H / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  const device = new THREE.Group();
  scene.add(device);

  // Housing.
  const housingMat = new THREE.MeshStandardMaterial({ color: 0xf6f6f3, roughness: 0.55 });
  const housing = new THREE.Mesh(new RoundedBoxGeometry(W, H, D, 8, 0.2), housingMat);
  housing.castShadow = true;
  housing.receiveShadow = true;
  device.add(housing);

  // Speaker grille: hex-packed dots inside a circle.
  const grille = { x: -2.15, y: -0.05, radius: 1.3, pitch: 0.155 };
  const dots = [];
  const rowH = grille.pitch * Math.sqrt(3) / 2;
  for (let row = -12; row <= 12; row++) {
    for (let col = -12; col <= 12; col++) {
      const x = col * grille.pitch + (row & 1 ? grille.pitch / 2 : 0);
      const y = row * rowH;
      if (Math.hypot(x, y) < grille.radius - 0.04) dots.push([x, y]);
    }
  }
  const dotMesh = new THREE.InstancedMesh(
    new THREE.CylinderGeometry(0.043, 0.043, 0.014, 16).rotateX(Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0x4b5256, roughness: 0.9 }),
    dots.length,
  );
  const m = new THREE.Matrix4();
  dots.forEach(([x, y], i) => {
    m.makeTranslation(grille.x + x, grille.y + y, FACE + 0.002);
    dotMesh.setMatrixAt(i, m);
  });
  device.add(dotMesh);

  // Knobs.
  const knobs = {};
  const pickables = [];
  for (const spec of KNOBS) {
    const knob = createKnob({ radius: spec.radius, height: spec.radius * 0.62, accentCap: spec.accentCap });
    knob.group.position.set(spec.x, spec.y, FACE);
    knob.body.userData.id = spec.id;
    device.add(knob.group);
    const plate = createDialPlate({ knobRadius: spec.radius, label: spec.label });
    plate.position.set(spec.x, spec.y, FACE + 0.003);
    device.add(plate);
    knobs[spec.id] = { ...spec, ...knob, value: values[spec.id], highlight: 0, target: 0 };
    knobs[spec.id].group.rotation.z = valueToRotation(values[spec.id]);
    pickables.push(knob.body);
  }

  // Power key + status LED.
  const keyMat = new THREE.MeshStandardMaterial({ color: 0xeeeeea, roughness: 0.45 });
  const key = new THREE.Mesh(new RoundedBoxGeometry(0.46, 0.3, 0.14, 4, 0.04), keyMat);
  key.position.set(3.1, 1.55, FACE + 0.05);
  key.castShadow = true;
  key.userData.id = 'power';
  device.add(key);
  pickables.push(key);
  const keyStripe = new THREE.Mesh(
    new THREE.BoxGeometry(0.28, 0.03, 0.006),
    new THREE.MeshStandardMaterial({ color: 0x9aa0a3, roughness: 0.5, emissive: ACCENT, emissiveIntensity: 0 }),
  );
  keyStripe.position.set(3.1, 1.55, FACE + 0.123);
  device.add(keyStripe);
  const powerLabel = createLabel('POWER', { width: 0.9, fontUnits: 0.11 });
  powerLabel.position.set(3.1, 1.25, FACE + 0.003);
  device.add(powerLabel);

  const ledMat = new THREE.MeshStandardMaterial({ color: 0x777d80, roughness: 0.3, emissive: ACCENT, emissiveIntensity: 0 });
  const led = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.03, 24).rotateX(Math.PI / 2), ledMat);
  led.position.set(2.65, 1.55, FACE + 0.012);
  device.add(led);

  let powered = false;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Interaction.
  const raycaster = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  let drag = null;
  let hover = null;
  let focused = null;

  function pick(e) {
    const r = canvas.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(ndc, camera);
    const hit = raycaster.intersectObjects(pickables, false)[0];
    return hit ? hit.object.userData.id : null;
  }

  function setKnob(id, value, notify = true) {
    const k = knobs[id];
    k.value = Math.min(1, Math.max(0, value));
    k.group.rotation.z = valueToRotation(k.value);
    if (notify) onChange(id, k.value);
  }

  // ---- inside view -------------------------------------------------------------------------------
  let interior = null;
  let wantInside = false, flip = 0, lidT = 0;
  const controls = new OrbitControls(camera, canvas);
  controls.enabled = false; controls.enableDamping = true; controls.dampingFactor = 0.12;
  controls.minDistance = 4; controls.maxDistance = 22; controls.enablePan = false;
  let downAt = null;
  function pickPart(e) {
    if (!interior) return null;
    const r = canvas.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(ndc, camera);
    scene.updateMatrixWorld(true);
    const hit = raycaster.intersectObjects(interior.proxies, false)[0];
    return hit ? hit.object.userData.ref : null;
  }
  const insideNow = () => flip > 0.98 && wantInside;

  canvas.addEventListener('pointerdown', (e) => {
    if (flip > 0.02) { downAt = { x: e.clientX, y: e.clientY }; return; }
    const id = pick(e);
    if (!id) return;
    if (id === 'power') { onPower(!powered); return; }
    drag = { id, x: e.clientX, y: e.clientY, v0: knobs[id].value };
    canvas.setPointerCapture(e.pointerId);
    canvas.style.cursor = 'grabbing';
  });
  canvas.addEventListener('pointermove', (e) => {
    if (flip > 0.02) {
      if (insideNow() && !(e.buttons & 1)) {
        const ref = pickPart(e);
        canvas.style.cursor = ref ? 'pointer' : 'grab';
        onPartHover?.(ref, e.clientX, e.clientY);
      } else onPartHover?.(null);
      return;
    }
    pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
    pointer.y = (e.clientY / window.innerHeight) * 2 - 1;
    if (drag) {
      const slow = e.shiftKey ? 600 : 200;
      setKnob(drag.id, drag.v0 + ((e.clientX - drag.x) - (e.clientY - drag.y)) / slow);
    } else {
      hover = pick(e);
      canvas.style.cursor = hover ? (hover === 'power' ? 'pointer' : 'grab') : 'default';
    }
  });
  const endDrag = () => { drag = null; canvas.style.cursor = hover ? 'grab' : 'default'; };
  canvas.addEventListener('pointerup', (e) => {
    if (downAt && insideNow() && Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) < 5) onPartSelect?.(pickPart(e));
    downAt = null;
    endDrag();
  });
  canvas.addEventListener('pointercancel', endDrag);
  canvas.addEventListener('pointerleave', () => { hover = null; });
  canvas.addEventListener('wheel', (e) => {
    if (flip > 0.02) return;
    const id = pick(e);
    if (!id || id === 'power') return;
    e.preventDefault();
    setKnob(id, knobs[id].value - e.deltaY * 0.0008);
  }, { passive: false });

  // Parallax tilt toward the pointer.
  const pointer = { x: 0, y: 0 };
  const tilt = { x: 0, y: 0 };

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    const t = Math.tan(THREE.MathUtils.degToRad(CAMERA_FOV / 2));
    const dist = Math.max((H * 1.5) / 2 / t, (W * 1.18) / 2 / t / camera.aspect);
    camera.position.set(0, 1.1, dist);
    camera.lookAt(0, -0.15, 0);
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(canvas);
  resize();

  let ledLevel = 0;
  let getLevel = () => 0;
  let last = performance.now();
  function frame() {
    const now = performance.now();
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    const ease = 1 - Math.exp(-dt * 6);

    // flip between the outside and the inside; the lid comes off after the turn
    const flipTarget = wantInside ? 1 : (lidT < 0.02 ? 0 : 1);
    const lidTarget = wantInside && flip > 0.98 ? 1 : 0;
    const step = reducedMotion ? 1 : dt * 1.15;
    flip += Math.sign(flipTarget - flip) * Math.min(Math.abs(flipTarget - flip), step);
    lidT += Math.sign(lidTarget - lidT) * Math.min(Math.abs(lidTarget - lidT), reducedMotion ? 1 : dt * 1.4);
    const e = flip * flip * (3 - 2 * flip);
    const inter = interior && flip > 0.5;
    housing.visible = !inter;
    if (interior) {
      interior.root.visible = inter;
      const l = lidT * lidT * (3 - 2 * lidT);
      interior.lid.visible = lidT < 0.92;
      interior.lid.position.set(0, l * 9, interior.lidClosedZ - l * 0.3);
      interior.lid.rotation.x = -l * 0.35;
    }
    if (flip > 0.001) {
      tilt.x += (0 - tilt.x) * ease; tilt.y += (0 - tilt.y) * ease;
      device.rotation.y = Math.PI * e; device.rotation.x = 0;
    } else {
      tilt.x += ((reducedMotion ? 0 : pointer.x * 0.1) - tilt.x) * ease;
      tilt.y += ((reducedMotion ? 0 : pointer.y * 0.05) - tilt.y) * ease;
      device.rotation.y = tilt.x;
      device.rotation.x = tilt.y;
    }
    const orbit = insideNow() && lidT > 0.9;
    if (controls.enabled !== orbit) {
      controls.enabled = orbit;
      if (orbit) { controls.target.set(0, -0.15, 0); controls.update(); }
    }
    if (orbit) controls.update();

    for (const id in knobs) {
      const k = knobs[id];
      k.target = drag?.id === id || hover === id || focused === id ? 1 : 0;
      k.highlight += (k.target - k.highlight) * ease;
      k.setHighlight(k.highlight);
    }

    key.position.z += ((powered ? FACE + 0.025 : FACE + 0.05) - key.position.z) * ease * 1.5;
    keyStripe.position.z = key.position.z + 0.073;
    keyStripe.material.emissiveIntensity += ((powered ? 1.4 : 0) - keyStripe.material.emissiveIntensity) * ease;

    const target = powered ? 0.25 + 2.2 * getLevel() : 0;
    ledLevel += (target - ledLevel) * (1 - Math.exp(-dt * 10));
    ledMat.emissiveIntensity = ledLevel;
    ledMat.color.setHex(powered ? 0x00cfc1 : 0x777d80);

    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  if (import.meta.env.DEV || location.search.includes('debug')) window.__dbg = { camera, controls, renderer, canvas, state: () => ({ flip, lidT, wantInside }) };
  function setView(mode) {
    wantInside = mode === 'inside';
    if (wantInside && !interior) {
      interior = createInterior(housingMat);
      interior.root.visible = false;
      device.add(interior.root);
    }
    if (!wantInside) {
      controls.enabled = false;
      onPartHover?.(null);
      resize();   // restore the camera of the outside view
    }
    canvas.style.cursor = 'default';
  }

  return {
    setView,
    getView: () => (wantInside ? 'inside' : 'front'),
    highlight: (refs) => interior?.highlight(refs || []),
    highlightNet: (n) => interior?.highlightNet(n),
    setXray: (on) => { if (interior) interior.xray = on; },
    setValue: (id, v) => setKnob(id, v, false),
    setPower: (on) => { powered = on; },
    setFocus: (id) => { focused = id; },
    setLevelSource: (fn) => { getLevel = fn; },
  };
}
