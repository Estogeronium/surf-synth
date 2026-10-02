import { SurfEngine, PARAM_DEFAULTS } from './audio/surf-engine.js';
import { createInstrument } from './ui/scene.js';

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
try {
  instrument = createInstrument({
    canvas: document.getElementById('stage'),
    values,
    onChange: (id, value) => { sliders[id].value = value; setValue(id, value); },
    onPower: setPower,
  });
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
