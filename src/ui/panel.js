import hw from '../hardware-data/hardware.json';
import { guideHtml } from './guide.js';

const svgs = import.meta.glob('../hardware-data/*.svg', { query: '?raw', import: 'default', eager: true });
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const byRef = Object.fromEntries(hw.parts.map((p) => [p.ref, p]));

const pinLabel = {
  Q: { E: 'эмиттер', B: 'база', C: 'коллектор' },
  D: { A: 'анод', K: 'катод' },
  LED: { A: 'анод', K: 'катод' },
  POT: { 1: 'крайний 1', W: 'движок', 3: 'крайний 3' },
  J: { TIP: 'центр «+»', SLV: 'корпус «−»' },
};

function partCard(ref) {
  const p = byRef[ref];
  if (!p) return '';
  const rows = [];
  const pins = p.pins || {};
  const order = Object.keys(pins).sort((a, b) => (isNaN(a) || isNaN(b) ? a.localeCompare(b) : a - b));
  for (const pin of order) {
    const net = pins[pin];
    if (!net || !hw.nets[net]) { rows.push(`<tr><td>${esc(pin)}</td><td class="nc">не подключён</td><td></td></tr>`); continue; }
    const others = (hw.nets[net] || []).filter((x) => !x.startsWith(p.ref + '.')).slice(0, 5);
    const lab = (pinLabel[p.type] || {})[pin];
    rows.push(`<tr><td>${esc(lab ? `${pin} ${lab}` : pin)}</td><td><b>${esc(net)}</b></td><td class="to">${others.map(esc).join(', ')}${(hw.nets[net] || []).length > 6 ? '…' : ''}</td></tr>`);
  }
  return `
<div class="part-card">
  <div class="part-head"><b>${esc(p.ref === 'RV6A' ? 'RV6' : p.ref)}</b><span>${esc(p.vtxt || p.value)}</span></div>
  <p>${esc(p.desc)}</p>
  <p class="meta">${esc(p.pkg)} · ${esc(p.block || '')}</p>
  ${p.url ? `<p class="meta"><a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title || 'Страница на chipdip.ru')}</a></p>` : ''}
  ${p.note ? `<p class="meta">${esc(p.note)}</p>` : ''}
  ${rows.length ? `<table class="pins"><thead><tr><th>Вывод</th><th>Цепь</th><th>Идёт к</th></tr></thead><tbody>${rows.join('')}</tbody></table>` : ''}
</div>`;
}

export function createPanel({ onSelect, onHighlight, onXray, onNet }) {
  const el = document.createElement('aside');
  el.className = 'panel'; el.hidden = true; el.setAttribute('aria-label', 'Состав устройства');
  el.innerHTML = `
  <div class="tabs" role="tablist">
    <button role="tab" data-tab="parts" aria-selected="true">Детали</button>
    <button role="tab" data-tab="schem" aria-selected="false">Схема</button>
    <button role="tab" data-tab="nets" aria-selected="false">Цепи</button>
    <button role="tab" data-tab="guide" aria-selected="false">Сборка</button>
    <label class="xray"><input type="checkbox" id="xray"> Просвет</label>
  </div>
  <div class="tabpane" data-pane="parts">
    <div class="summary"><b>${hw.totals.items}</b> деталей, <b>${hw.totals.lines}</b> позиций. Нажмите на обозначение — деталь и её провода подсветятся на плате.</div>
    <div id="card" class="card-slot"></div>
    <div class="bom"></div>
    <h4>Кроме деталей на схеме</h4>
    <ul class="extra">${hw.extra.map((e) => `<li><b>${esc(e.name)}</b> ×${esc(e.qty)}${e.url ? ` · <a href="${esc(e.url)}" target="_blank" rel="noopener">chipdip.ru</a>` : ''}<br><span>${esc(e.note)}</span>${e.title ? `<br><small>${esc(e.title)}</small>` : ''}</li>`).join('')}</ul>
    <p class="meta">Названия и ссылки взяты из поиска по chipdip.ru. Страницы товаров я открыть не мог, поэтому наличие и цены проверьте на сайте.</p>
  </div>
  <div class="tabpane" data-pane="schem" hidden>
    <div class="sheetbar">
      ${hw.sheets.map((s, i) => `<button data-sheet="${i}" aria-pressed="${i === 0}">Лист ${i + 1}</button>`).join('')}
      <span class="zoom"><button data-zoom="-1" aria-label="Уменьшить">−</button><button data-zoom="1" aria-label="Увеличить">+</button></span>
    </div>
    <p class="meta sheettitle"></p>
    <div class="sheetview"></div>
  </div>
  <div class="tabpane" data-pane="nets" hidden>
    <p class="summary">Нажмите на название цепи — её провода подсветятся на плате.</p>
    ${Object.entries(hw.nets).sort().map(([n, pins]) => `<div class="net"><button class="netname" data-net="${esc(n)}">${esc(n)}</button><span>${pins.map((x) => esc(x)).join(' · ')}</span></div>`).join('')}
  </div>
  <div class="tabpane guide" data-pane="guide" hidden>${guideHtml()}</div>`;

  const bom = el.querySelector('.bom');
  let lastGroup = '';
  for (const b of hw.bom) {
    if (b.group !== lastGroup) { bom.insertAdjacentHTML('beforeend', `<h4>${esc(b.group)}</h4>`); lastGroup = b.group; }
    bom.insertAdjacentHTML('beforeend', `
<div class="line" data-refs="${esc(b.refs.join(' '))}">
  <span class="qty">${b.qty}</span>
  <div class="d"><span>${esc(b.name)}</span><small>${esc(b.pkg)}</small>
  ${b.url ? `<small><a href="${esc(b.url)}" target="_blank" rel="noopener">${esc(b.title || 'chipdip.ru')}</a></small>` : ''}
  ${b.note ? `<small>${esc(b.note)}</small>` : ''}
  <small class="chk">${esc(b.check)}</small>
  <div class="refs">${b.refs.map((r) => `<button class="chip" data-ref="${esc(r)}">${esc(r)}</button>`).join('')}</div></div>
</div>`);
  }

  const tabs = el.querySelectorAll('.tabs [data-tab]');
  tabs.forEach((t) => t.addEventListener('click', () => show(t.dataset.tab)));
  function show(name) {
    tabs.forEach((t) => t.setAttribute('aria-selected', String(t.dataset.tab === name)));
    el.querySelectorAll('.tabpane').forEach((p) => { p.hidden = p.dataset.pane !== name; });
    if (name === 'schem' && !sheetShown) showSheet(0);
  }

  let sheetShown = false, zoom = 1, cur = 0;
  const view = el.querySelector('.sheetview'), title = el.querySelector('.sheettitle');
  function showSheet(i) {
    sheetShown = true; cur = i;
    const s = hw.sheets[i];
    const raw = svgs[`../hardware-data/${s.file}`];
    view.innerHTML = raw; title.textContent = s.title;
    const svg = view.querySelector('svg'); svg.removeAttribute('width'); svg.removeAttribute('height');
    applyZoom();
    el.querySelectorAll('[data-sheet]').forEach((b) => b.setAttribute('aria-pressed', String(Number(b.dataset.sheet) === i)));
  }
  function applyZoom() {
    const s = hw.sheets[cur]; const svg = view.querySelector('svg'); if (!svg) return;
    svg.style.width = `${Math.round(s.w * zoom * 0.8)}px`; svg.style.height = 'auto';
  }
  el.querySelectorAll('[data-sheet]').forEach((b) => b.addEventListener('click', () => showSheet(Number(b.dataset.sheet))));
  el.querySelectorAll('[data-zoom]').forEach((b) => b.addEventListener('click', () => { zoom = Math.min(2.4, Math.max(0.5, zoom * (b.dataset.zoom > 0 ? 1.25 : 0.8))); applyZoom(); }));

  el.querySelector('#xray').addEventListener('change', (e) => onXray(e.target.checked));

  const card = el.querySelector('#card');
  function setSelected(ref) {
    el.querySelectorAll('.chip').forEach((c) => c.classList.toggle('on', c.dataset.ref === ref));
    card.innerHTML = ref ? partCard(ref) : '';
    if (ref) {
      show('parts');
      const chip = el.querySelector(`.chip[data-ref="${CSS.escape(ref)}"]`);
      chip?.closest('.line')?.classList.add('flash');
      setTimeout(() => chip?.closest('.line')?.classList.remove('flash'), 900);
      chip?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }
  el.addEventListener('click', (e) => {
    const net = e.target.closest('.netname');
    if (net) { onNet(net.dataset.net); return; }
    const chip = e.target.closest('.chip');
    if (chip) { onSelect(chip.dataset.ref); return; }
    const line = e.target.closest('.line');
    if (line) { onHighlight(line.dataset.refs.split(' ')); }
  });

  return { el, setSelected, show };
}
