import { SurfEngine, PARAM_DEFAULTS } from './audio/surf-engine.js';
import { createInstrument } from './ui/scene.js';
import { createPanel } from './ui/panel.js';
import hw from './hardware-data/hardware.json';

const STORAGE_KEY = 'surf-synth:v1';
const IDS = ['surf', 'tide', 'tone', 'volume'];

function loadValues() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    return Object.fromEntries(IDS.map((id) => [id, Number.isFinite(saved[id]) ? saved[id] : PARAM_DEFAULTS[id]]));
  } catch {
    return { ...PARAM_DEFAULTS };
  }
}
function saveValues(values) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(values)); } catch { /* storage unavailable */ }
}

const values = loadValues();
const engine = new SurfEngine();
const power = document.getElementById('power');
const sliders = Object.fromEntries(IDS.map((id) => [id, document.getElementById(id)]));
for (const id of IDS) {
  sliders[id].value = values[id];
  engine.setParam(id, values[id]);
}

function setValue(id, value) {
  values[id] = value;
  engine.setParam(id, value);
  saveValues(values);
}

async function setPower(on) {
  power.checked = on;
  instrument?.setPower(on);
  if (on) await engine.start();
  else await engine.stop();
}

let instrument = null;
const tip = document.querySelector('.tip');
const partInfo = Object.fromEntries(hw.parts.map((p) => [p.ref, p]));
function selectPart(ref) {
  if (!ref) { instrument.highlight([]); panel.setSelected(null); return; }
  instrument.highlight([ref]);
  panel.setSelected(ref);
}
let panel = null;
try {
  instrument = createInstrument({
    canvas: document.getElementById('stage'),
    values,
    onChange: (id, value) => { sliders[id].value = value; setValue(id, value); },
    onPower: setPower,
    onPartSelect: (ref) => selectPart(ref),
    onPartHover: (ref, x, y) => {
      const p = ref && partInfo[ref];
      if (!p) { tip.hidden = true; return; }
      tip.innerHTML = `<b>${ref}</b> · ${p.vtxt || p.value}<small>${p.block || ''}</small>`;
      tip.style.left = `${Math.min(x + 14, window.innerWidth - 270)}px`; tip.style.top = `${y + 14}px`; tip.hidden = false;
    },
  });
  panel = createPanel({
    onSelect: (ref) => selectPart(ref),
    onHighlight: (refs) => instrument.highlight(refs),
    onXray: (on) => instrument.setXray(on),
    onNet: (net) => { instrument.highlightNet(net); panel.setSelected(null); },
  });
  document.body.insertBefore(panel.el, document.querySelector('.bar'));
  document.querySelectorAll('.view-toggle [data-view]').forEach((b) => b.addEventListener('click', () => {
    const inside = b.dataset.view === 'inside';
    document.querySelectorAll('.view-toggle [data-view]').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    document.body.classList.toggle('is-inside', inside);
    panel.el.hidden = !inside;
    if (!inside) { instrument.highlight([]); panel.setSelected(null); tip.hidden = true; }
    instrument.setView(inside ? 'inside' : 'front');
  }));
  instrument.setLevelSource(() => engine.getLevel());
} catch (err) {
  console.warn('WebGL unavailable, falling back to plain controls.', err);
  document.body.classList.add('no-webgl');
}

power.addEventListener('change', () => setPower(power.checked));
for (const id of IDS) {
  sliders[id].addEventListener('input', () => {
    const value = Number(sliders[id].value);
    instrument?.setValue(id, value);
    setValue(id, value);
  });
  sliders[id].addEventListener('focus', () => instrument?.setFocus(id));
  sliders[id].addEventListener('blur', () => instrument?.setFocus(null));
}
