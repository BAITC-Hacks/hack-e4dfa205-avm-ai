/* Аким на 5 часов: логика интерфейса. Расчёт делает сервер, здесь только выбор мер, проверка правил и отрисовка. */
'use strict';
(() => {

const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = (v, d = 2) => (v == null || isNaN(v)) ? '—' : Number(v).toFixed(d).replace('.', ',');
const sgn = (v, d = 2) => (v > 0 ? '+' : v < 0 ? '−' : '') + fmt(Math.abs(v), d);
const ptsWord = v => { const a = Math.abs(Number(v)); if (!Number.isInteger(a)) return 'балла'; const r = a % 10, t = a % 100; return (t >= 11 && t <= 19) ? 'баллов' : r === 1 ? 'балл' : (r >= 2 && r <= 4) ? 'балла' : 'баллов'; };
const pts = (v, d = 2) => fmt(v, d) + ' ' + ptsWord(Number(Number(v).toFixed(d)));
const spts = (v, d = 2) => sgn(v, d) + ' ' + ptsWord(Number(Math.abs(Number(v)).toFixed(d)));

/* ---------- карта: контуры и точки в системе viewBox 2000×1493 ---------- */
const MAP = {
  poly: {
    esil: '0,0 750,0 1000,220 1100,330 1300,420 1420,480 1450,540 1300,640 1000,690 760,650 600,560 300,380 0,290',
    nura: '750,0 2000,0 2000,300 1850,320 1700,400 1520,470 1450,540 1420,480 1300,420 1100,330 1000,220',
    almaty: '2000,300 2000,1116 1560,1116 1540,900 1500,760 1420,700 1250,650 1400,560 1520,470 1700,400 1850,320',
    saryarka: '0,290 300,380 600,560 760,650 950,720 930,850 880,1116 0,1116',
    baikonur: '950,720 1000,690 1250,650 1420,700 1500,760 1540,900 1560,1116 880,1116 930,850',
  },
  anchor: { esil: [34, 30], nura: [73, 20], almaty: [84, 62], saryarka: [22, 66], baikonur: [60, 80] },
  spots: {
    esil: [[11.2, 22.4, 7.2], [38.5, 50.7, 7.2], [52.1, 55.6, 7.2], [55.4, 42.2, 5.8], [44.0, 39.2, 5.8], [55.0, 32.8, 6.1], [18.3, 27.6, 6.5]],
    nura: [[94.6, 18.7, 7.2], [84.6, 19.8, 7.2], [84.8, 34.0, 7.2], [51.5, 20.5, 7.2], [87.5, 8.2, 6.1], [90.4, 28.4, 4.3]],
    almaty: [[87.5, 61.9, 7.2], [94.6, 97.0, 7.2], [86.9, 42.2, 5.0], [97.1, 73.5, 5.0], [81.7, 83.0, 5.8]],
    saryarka: [[27.5, 64.9, 7.2], [19.6, 72.4, 7.2], [42.7, 75.4, 7.2], [5.0, 97.0, 7.2], [11.2, 73.5, 5.8], [32.1, 96.3, 5.0], [21.0, 81.9, 5.8]],
    baikonur: [[47.9, 70.9, 6.5], [73.8, 94.0, 7.2], [62.1, 76.9, 4.7], [66.9, 86.2, 4.7], [48.1, 81.0, 4.7], [53.5, 70.5, 4.3]],
    city: [[45.6, 57.1, 5.4], [31.7, 48.5, 5.4], [61.7, 50.7, 5.4], [36.7, 67.8, 5.4]],
  },
  scale: {"M1": 1.0, "M2": 0.9, "M3": 1.1, "M4": 1.05, "M5": 1.0, "M6": 1.0, "M7": 1.0, "M8": 1.0, "M9": 1.0, "M10": 0.7, "M11": 0.85, "M12": 0.85, "M13": 1.0, "M14": 1.0},
};

const DIR_NAMES = { transport: 'Транспорт', ecology: 'Экология', social: 'Соцсфера', safety: 'Безопасность', services: 'Сервисы' };
const ICONS = { M1: 'buslane', M2: 'lights', M3: 'lrt', M4: 'park', M5: 'cleanfuel', M6: 'greening', M7: 'school', M8: 'clinic', M9: 'sport', M10: 'safecity', M11: 'crossing', M12: 'digital', M13: 'pipes', M14: 'brigade' };
const iconSrc = id => `/static/img/ic-${ICONS[id] || 'park'}.png`;

/* ---------- данные задачи на случай, если сервер недоступен ---------- */
const FALLBACK_CITY = {
  version: 'hackalem-12-v1', budget: 100, horizon: 8, critical_threshold: 40, max_per_direction: 2, decisions_required: 5,
  directions: Object.entries(DIR_NAMES).map(([id, name]) => ({ id, name })),
  indicators: [
    ['T1', 'transport', 'Разгрузка дорог', .10], ['T2', 'transport', 'Доступность общественного транспорта', .10],
    ['E1', 'ecology', 'Озеленение', .09], ['E2', 'ecology', 'Качество воздуха', .11],
    ['S1', 'social', 'Школы и детсады', .11], ['S2', 'social', 'Поликлиники и первичная медпомощь', .11],
    ['B1', 'safety', 'Безопасность улиц', .09], ['B2', 'safety', 'Безопасность дорожного движения', .09],
    ['C1', 'services', 'Надёжность ЖКХ', .10], ['C2', 'services', 'Скорость решения обращений жителей', .10],
  ].map(([code, direction, name, weight]) => ({ code, direction, name, weight })),
  districts: [
    ['esil', 'Есиль', .27, [45, 62, 68, 72, 48, 55, 78, 60, 75, 70]],
    ['almaty', 'Алматы', .24, [40, 75, 50, 55, 60, 65, 62, 52, 50, 60]],
    ['saryarka', 'Сарыарка', .20, [50, 70, 42, 40, 62, 68, 58, 55, 45, 55]],
    ['baikonur', 'Байконур', .13, [52, 68, 55, 50, 58, 60, 52, 58, 55, 58]],
    ['nura', 'Нура', .16, [55, 40, 45, 65, 38, 35, 55, 50, 60, 50]],
  ].map(([id, name, population, v]) => ({ id, name, population, indicators: Object.fromEntries(['T1','T2','E1','E2','S1','S2','B1','B2','C1','C2'].map((k, i) => [k, v[i]])) })),
  measures: [
    ['M1', 'transport', 'Выделенные полосы для автобусов', 'district', 18, 2, { T1: 6, T2: 9 }],
    ['M2', 'transport', 'Умные светофоры (адаптивное управление)', 'city', 22, 2, { T1: 4, B2: 3 }],
    ['M3', 'transport', 'Линия ЛРТ / расширение', 'district', 30, 4, { T1: 16, T2: 20, E2: 4 }],
    ['M4', 'ecology', 'Парк / сквер', 'district', 15, 2, { E1: 12, E2: 3, B1: 2 }],
    ['M5', 'ecology', 'Перевод частного сектора на чистое топливо', 'district', 25, 3, { E2: 14, C1: 4 }],
    ['M6', 'ecology', 'Городская программа озеленения и ветрозащитных полос', 'city', 20, 4, { E1: 5, E2: 3 }],
    ['M7', 'social', 'Школа + детсад (модульное строительство)', 'district', 24, 3, { S1: 16 }],
    ['M8', 'social', 'Центр семейного здоровья / поликлиника', 'district', 20, 3, { S2: 14 }],
    ['M9', 'social', 'Дворовые спорт-хабы', 'district', 10, 1, { S1: 3, S2: 3, B1: 3 }],
    ['M10', 'safety', 'Освещение и камеры (расширение Safe City)', 'district', 12, 1, { B1: 12, B2: 2 }],
    ['M11', 'safety', 'Безопасные переходы и школьные зоны', 'district', 10, 1, { B2: 12, T1: -2 }],
    ['M12', 'services', 'Единая цифровая платформа обращений', 'city', 14, 1, { C2: 5 }],
    ['M13', 'services', 'Модернизация тепло- и водосетей', 'district', 28, 4, { C1: 18, E2: 2 }],
    ['M14', 'services', 'Аварийные бригады ЖКХ + раннее оповещение', 'city', 16, 1, { C1: 5, C2: 2 }],
  ].map(([id, direction, name, type, cost, lag, effects]) => ({ id, direction, name, type, cost, lag, effects })),
  synergies: [
    { measures: ['M1', 'M2'], indicator: 'T1', bonus: 2, district_of: 'M1' },
    { measures: ['M10', 'M12'], indicator: 'B1', bonus: 2, district_of: 'M10' },
    { measures: ['M5', 'M6'], indicator: 'E2', bonus: 2, district_of: 'M5' },
  ],
  incompatibilities: [
    { measures: ['M1', 'M3'], scope: 'any' },
    { measures: ['M4', 'M7'], scope: 'same_district' },
    { measures: ['M5', 'M13'], scope: 'same_district' },
  ],
};

/* ---------- звук: пока отключён, вызовы остаются точками расширения ---------- */
function sfx() {}

/* ---------- полотно: карта заливает весь экран, как фон игры ---------- */
const WORLD = { w: 2000, h: 1116 };
function fitView() {
  const st = $('#stage-map'), w = $('#world');
  const W = st.clientWidth, H = st.clientHeight;
  const s = Math.min(W / WORLD.w, H / WORLD.h);   // весь кадр целиком, поля закрывает размытый фон
  const x = (W - WORLD.w * s) / 2, y = (H - WORLD.h * s) / 2;
  w.style.transform = `translate(${x}px, ${y}px) scale(${s})`;
  w.style.setProperty('--inv', (1 / s).toFixed(4));
}
function initView() {
  let t; window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(fitView, 80); });
  fitView();
}

/* ---------- состояние ---------- */
const state = {
  city: null,
  offline: false,
  decisions: [],          // [{measure_id, district_id?}]
  result: null,           // ответ /api/evaluate для текущего набора
  detail: null,           // id раскрытого района
  tab: 'transport',
  modal: null,            // { measure, district }
  shown: {},              // отображаемые оценки районов (для анимации чисел)
  pending: false,         // идёт запрос evaluate
  gen: 0,                 // поколение запроса, чтобы не показать устаревший ответ
  explain: null,          // ответ /api/explain для текущего scenario_key
  explainBusy: false,
  candidates: null,       // ответ /api/improvements
  candidatesError: null,  // текст ошибки поиска замен (сеть, сервер), null если ошибки нет
  improveBusy: false,     // идёт запрос improvements
  chat: [],               // [{role, content}]
  chatBusy: false,
  advisorOpen: false,     // окно советника открыто
  key: '',                // ключ OpenAI из интерфейса, только sessionStorage
  keyStatus: null,        // { ok, model, error, key_source }
};
try { state.key = sessionStorage.getItem('akim.key') || ''; } catch (e) {}
const API = '';
const headers = () => { const h = { 'Content-Type': 'application/json' }; if (state.key) h['X-OpenAI-Key'] = state.key; return h; };
const body = () => JSON.stringify({ decisions: state.decisions.map(d => d.district_id ? { measure_id: d.measure_id, district_id: d.district_id } : { measure_id: d.measure_id }) });

/* ---------- базовые оценки районов из данных (взвешенная сумма, как D_d в ТЗ) ---------- */
function districtBase(d) {
  return state.city.indicators.reduce((s, ind) => s + ind.weight * d.indicators[ind.code], 0);
}
function baseCritical(d) {
  return state.city.indicators.filter(ind => d.indicators[ind.code] < state.city.critical_threshold).length;
}

/* ---------- отрисовка карты ---------- */
function renderMapStatic() {
  const hot = $('#map-hot'), stage = $('#stage');
  hot.innerHTML = state.city.districts.map(d =>
    `<polygon id="poly-${d.id}" data-d="${d.id}" points="${MAP.poly[d.id]}" tabindex="0" role="button" aria-label="${esc(d.name)}"><title>${esc(d.name)}</title></polygon>`
  ).join('');
  $('#map-labels').innerHTML = state.city.districts.map(d => {
    const [x, y] = MAP.anchor[d.id];
    return `<div class="lbl" id="lbl-${d.id}" style="left:${x}%;top:${y}%">${esc(d.name)}</div>`;
  }).join('');
  const hover = id => {
    stage.classList.toggle('hovering', !!id);
    hot.querySelectorAll('polygon').forEach(p => p.classList.toggle('is-hot', p.dataset.d === id));
    document.querySelectorAll('.lbl').forEach(l => l.classList.toggle('is-hot', l.id === 'lbl-' + id));
  };
  $('#stage-map').addEventListener('mouseleave', () => hover(null));
  hot.querySelectorAll('polygon').forEach(p => {
    p.addEventListener('mouseenter', () => hover(p.dataset.d));
    p.addEventListener('mouseleave', () => hover(null));
    p.addEventListener('focus', () => hover(p.dataset.d));
    p.addEventListener('blur', () => hover(null));
  });
}

function districtView(id) {
  const d = state.city.districts.find(x => x.id === id);
  const r = state.result?.valid ? state.result.district_results.find(x => x.id === id) : null;
  const before = districtBase(d);
  return {
    d, before,
    after: r ? r.score_after : null,
    crit: r ? r.indicators.filter(i => i.critical).length : baseCritical(d),
    pins: state.decisions.filter(x => x.district_id === id).map(x => x.measure_id),
  };
}

function renderPlaques() {
  const box = $('#map-plaques');
  const weakest = state.city.districts.reduce((m, d) => (districtView(d.id).after ?? districtView(d.id).before) < (districtView(m.id).after ?? districtView(m.id).before) ? d : m);
  box.innerHTML = state.city.districts.map((d, i) => {
    const v = districtView(d.id);
    const [x, y] = MAP.anchor[d.id];
    const val = v.after ?? v.before;
    const delta = v.after != null ? v.after - v.before : null;
    const tone = delta == null ? '' : delta > 0 ? ' plq--up' : delta < 0 ? ' plq--down' : '';
    return `<button type="button" class="plq${tone}${state.detail === d.id ? ' is-open' : ''}${d.id === weakest.id ? ' is-weak' : ''}" id="plq-${d.id}" data-d="${d.id}" style="left:${x}%;top:${y}%;animation-delay:${i * 70}ms" aria-label="${esc(d.name)}: ${fmt(val)}">
      <div class="plq__n"><span class="plq__name">${esc(d.name)}</span><span class="plq__pop" title="доля населения">${Math.round(d.population * 100)}%</span></div>
      <div class="plq__vrow"><span class="plq__v" data-v="${val}">${fmt(state.shown[d.id] ?? val)}</span><small class="plq__unit">балла</small></div>
      <div class="plq__bar"><i style="width:${Math.max(0, Math.min(100, val))}%"></i></div>
      ${delta != null ? `<div class="plq__d ${delta > 0 ? 'up' : delta < 0 ? 'down' : ''}"><b>${delta > 0 ? '▲' : delta < 0 ? '▼' : '•'}</b>${spts(delta)} к старту</div>` : ''}
      ${d.id === weakest.id ? '<span class="plq__weak" title="Оценка этого района сейчас минимальна: она входит в Score с весом 0,3">слабейший район</span>' : ''}
      ${v.crit ? `<span class="plq__bad" title="Показателей ниже ${state.city.critical_threshold}: ${v.crit}">${v.crit}</span>` : ''}
    </button>`;
  }).join('');
  box.querySelectorAll('.plq').forEach(b => b.addEventListener('click', () => toggleDetail(b.dataset.d)));
  box.querySelectorAll('.plq__v').forEach(el => {
    const to = parseFloat(el.dataset.v), from = parseFloat(el.textContent.replace(',', '.'));
    if (!isNaN(from) && !isNaN(to) && Math.abs(to - from) > 0.004) countUp(el, from, to, 800);
    else el.textContent = fmt(to);
  });
  state.city.districts.forEach(d => { state.shown[d.id] = districtView(d.id).after ?? districtView(d.id).before; });
}
function countUp(el, from, to, ms) {
  const t0 = performance.now();
  (function step(t) {
    const k = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - k, 3);
    el.textContent = fmt(from + (to - from) * e);
    if (k < 1) requestAnimationFrame(step);
  })(t0);
}

function toggleDetail(id) {
  state.detail = state.detail === id ? null : id;
  sfx(state.detail ? 'open' : 'close');
  document.querySelectorAll('#map-hot polygon').forEach(p => p.classList.toggle('is-open', p.dataset.d === state.detail));
  document.querySelectorAll('.plq').forEach(p => p.classList.toggle('is-open', p.dataset.d === state.detail));
  renderDetail();
}

function renderDetail() {
  const box = $('#modal');
  if (!state.detail) { if (state.modal && state.modal.detail) closeModal(); return; }
  if (!state.modal || !state.modal.detail) { modalOpener = document.activeElement; document.querySelectorAll('.top, .stage').forEach(el => el.setAttribute('inert', '')); }
  state.modal = { detail: state.detail };
  box.hidden = false;
  const v = districtView(state.detail);
  const r = state.result?.valid ? state.result.district_results.find(x => x.id === state.detail) : null;
  const thr = state.city.critical_threshold;
  const rows = state.city.indicators.map(ind => {
    const before = v.d.indicators[ind.code];
    const after = r ? r.indicators.find(i => i.code === ind.code).after : null;
    const cur = after ?? before;
    const delta = after != null ? after - before : 0;
    const crit = cur < thr;
    const lo = Math.min(before, cur), hi = Math.max(before, cur);
    return `<div class="irow${crit ? ' irow--crit' : ''}">
      <span class="irow__code" data-dir="${ind.direction || ''}">${ind.code}</span>
      <span class="irow__name">${esc(ind.name)}</span>
      <span class="irow__nums">${after != null && delta ? `<em class="${delta > 0 ? 'up' : 'down'}">${sgn(delta, 1)}</em>` : ''}<b>${after != null ? fmt(after, 1) : fmt(before, 0)}</b>${after != null ? `<small>было ${fmt(before, 0)}</small>` : ''}</span>
      <span class="irow__bar"><i style="width:${lo}%"></i>${delta ? `<b class="${delta < 0 ? 'neg' : ''}" style="left:${lo}%;width:${hi - lo}%"></b>` : ''}<s style="left:${thr}%"></s></span>
    </div>`;
  }).join('');
  box.innerHTML = `<div class="dlg dlg--district" role="dialog" aria-modal="true" aria-label="${esc(v.d.name)}">
    <div class="dlg__head"><div><div class="dlg__kicker">Район · доля населения ${Math.round(v.d.population * 100)}%</div><h3>${esc(v.d.name)}</h3>
      <div class="dlg__meta"><span>оценка района <b>${fmt(v.before)}</b>${v.after != null ? ` → <b>${fmt(v.after)}</b>` : ''}</span>${v.crit ? `<span>критических показателей: <b>${v.crit}</b></span>` : ''}</div></div>
      <button type="button" class="dlg__x" data-close aria-label="Закрыть">×</button></div>
    <div class="dlg__sec"><h4>${v.after != null ? 'Показатели после пяти решений, горизонт 8 кварталов' : 'Исходные показатели, итог появится после пятого решения'}</h4>
      <div class="irows">${rows}</div>
      <div class="legend legend--keys"><span><i class="lg lg--base"></i>исходное значение</span><span><i class="lg lg--up"></i>прирост после мер</span><span><i class="lg lg--down"></i>снижение</span><span><i class="lg lg--thr"></i>порог ${thr}: ниже него показатель критический и отнимает балл</span><span class="legend__note">Шкала 0–100, больше значит лучше</span></div></div>
    <div class="dlg__foot"><button type="button" class="btn" data-close>Закрыть</button></div>
  </div>`;
  box.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', () => toggleDetail(state.detail)));
  box.onclick = e => { if (e.target === box) toggleDetail(state.detail); };
}

/* ---------- панель Score на карте ---------- */
function baseline() {
  const c = state.city;
  if (c.baseline) return c.baseline;
  const avg = c.districts.reduce((s, d) => s + d.population * districtBase(d), 0);
  const min = Math.min(...c.districts.map(districtBase));
  const crit = c.districts.reduce((s, d) => s + baseCritical(d), 0);
  return { score: 0.7 * avg + 0.3 * min - crit, average: avg, minimum: min, critical_count: crit };
}
function renderScore() {
  const box = $('#score'); box.hidden = false;
  const c = state.city, r = state.result, b = baseline();
  const left = c.decisions_required - state.decisions.length;
  if (state.pending) {
    box.innerHTML = `<div class="score__l">Quality of Life Score</div><div class="score__v">${fmt(b.score)} <small>считаем…</small></div><div class="score__hint"><span class="spinner"></span>Сервер пересчитывает пять решений</div>`;
    return;
  }
  if (r && !r.valid) {
    box.innerHTML = `<div class="score__l">Quality of Life Score</div><div class="score__v">—</div>
      <div class="score__hint">Набор не принят сервером</div><ul class="score__err">${r.errors.map(e => `<li>${esc(e.message)}</li>`).join('')}</ul>`;
    return;
  }
  if (!r) {
    box.innerHTML = `<div class="score__l">Quality of Life Score</div>
      <div class="score__v">${fmt(b.score)} <small>до решений</small></div>
      <div class="score__hint">${state.offline ? 'Сервер недоступен, итог посчитать нельзя' : left > 0 ? `Осталось выбрать ${left} ${left === 1 ? 'меру' : left < 5 ? 'меры' : 'мер'}` : 'Нажмите «Рассчитать»'}</div>
      <div class="score__terms">
        <span>0,7 × средний по городу</span><b>${fmt(b.average)}</b>
        <span>0,3 × слабейший район</span><b>${fmt(b.minimum)}</b>
        <span>− критических показателей</span><b class="down">${b.critical_count}</b>
      </div>`;
    return;
  }
  const d = r.decomposition, rk = r.rank;
  const rankLine = rk ? (rk.top_position ? `${rk.top_position}-е место из ${rk.total.toLocaleString('ru-RU')} планов` : `лучше ${fmt(Math.min(rk.percentile, 99.9), 1)}% из ${rk.total.toLocaleString('ru-RU')} планов`) : '';
  box.innerHTML = `<div class="score__l">Quality of Life Score</div>
    <div class="score__v">${fmt(r.score)} <small>было ${fmt(r.baseline_score)} до решений</small></div>
    <div class="score__d ${r.delta > 0 ? 'up' : r.delta < 0 ? 'down' : ''}">${spts(r.delta)} к старту${rankLine ? ' · ' + rankLine : ''}</div>
    <div class="score__hint">Слабейший район: ${fmt(r.minimum)} · критических: ${r.critical_count} · бюджет ${r.cost} из ${c.budget}</div>
    <div class="score__terms">
      <span>средний по городу</span><b class="${d.avg > 0 ? 'up' : d.avg < 0 ? 'down' : ''}">${spts(d.avg)}</b>
      <span>слабейший район</span><b class="${d.min > 0 ? 'up' : d.min < 0 ? 'down' : ''}">${spts(d.min)}</b>
      <span>штраф за провалы</span><b class="${d.crit > 0 ? 'up' : d.crit < 0 ? 'down' : ''}">${spts(d.crit)}</b>
    </div>`;
}

/* ---------- правила набора (проверка на клиенте, сервер перепроверяет) ---------- */
const dirName = id => (state.city.directions.find(d => d.id === id) || {}).name || DIR_NAMES[id] || id;
const measureById = id => state.city.measures.find(m => m.id === id);
const districtById = id => state.city.districts.find(d => d.id === id);
const planCost = () => state.decisions.reduce((s, d) => s + measureById(d.measure_id).cost, 0);
const realized = m => (state.city.horizon - m.lag) / state.city.horizon;

function checkAdd(m, districtId) {
  const c = state.city;
  if (state.decisions.length >= c.decisions_required) return `Уже выбрано ${c.decisions_required} решений. Уберите одну меру, чтобы добавить другую`;
  if (state.decisions.some(d => d.measure_id === m.id)) return 'Эта мера уже в плане';
  const rem = c.budget - planCost();
  if (m.cost > rem) return `Не хватает бюджета: нужно ${m.cost}, осталось ${rem}`;
  const same = state.decisions.filter(d => measureById(d.measure_id).direction === m.direction);
  if (same.length >= c.max_per_direction) return `Уже ${c.max_per_direction} меры направления «${dirName(m.direction)}»`;
  for (const inc of c.incompatibilities) {
    if (!inc.measures.includes(m.id)) continue;
    const other = inc.measures.find(x => x !== m.id);
    const hit = state.decisions.find(d => d.measure_id === other);
    if (!hit) continue;
    if (inc.scope === 'any') return `Несовместимо с ${other} «${measureById(other).name}»: ${inc.reason || 'либо одно, либо другое'}`;
    if (districtId && hit.district_id === districtId) return `Нельзя вместе с ${other} в одном районе${inc.reason ? ': ' + inc.reason : ''}`;
  }
  if (m.type === 'district' && !districtId) return 'Выберите район';
  return null;
}

/* ---------- шапка: бюджет и счётчик ---------- */
function renderHeader() {
  const c = state.city, cost = planCost();
  $('#budget').innerHTML = `<div class="budget__row"><span>Бюджет</span><span class="budget__num">${c.budget - cost} <small>из ${c.budget} ед.</small></span></div>
    <div class="strip">${state.decisions.map(d => { const m = measureById(d.measure_id); return `<div class="strip__seg" data-dir="${m.direction}" style="width:${m.cost / c.budget * 100}%" title="${esc(m.name)}: ${m.cost}">${m.id}</div>`; }).join('')}</div>`;
  $('#counter').innerHTML = `<div class="counter__num">${state.decisions.length} / ${c.decisions_required}</div><div class="counter__lbl">решений</div>`;
}

/* ---------- каталог мер ---------- */
function renderTabs() {}

function effectChips(m) {
  return Object.entries(m.effects).map(([k, v]) => {
    const ind = state.city.indicators.find(i => i.code === k);
    return `<span class="chip${v < 0 ? ' chip--neg' : ''}" title="${esc(ind ? ind.name : k)}: ${v > 0 ? '+' : ''}${v} полный эффект, ${sgn(v * realized(m), 1)} за два года с учётом задержки">${k}${v > 0 ? '+' : ''}${v}</span>`;
  }).join('');
}

function renderCards() {
  const c = state.city;
  $('#cards').innerHTML = c.directions.map((dir, di) => {
    const list = c.measures.filter(m => m.direction === dir.id);
    const n = state.decisions.filter(x => measureById(x.measure_id).direction === dir.id).length;
    const rows = list.map(m => {
      const inPlan = state.decisions.find(d => d.measure_id === m.id);
      const why = inPlan ? null : checkAdd(m, m.type === 'district' ? '__any__' : null);
      const blocked = !!(why && why !== 'Выберите район');
      const full = state.decisions.length >= c.decisions_required;
      const cls = 'row' + (inPlan ? ' row--in' : '') + (blocked ? ' row--off' : '');
      const attrs = inPlan || blocked ? '' : `data-build="${m.id}" tabindex="0" role="button"`;
      return `<div class="${cls}" ${attrs}>
        <div class="row__tile" data-dir="${m.direction}"><img class="row__icon" src="${iconSrc(m.id)}" alt=""></div>
        <div class="row__body">
          <div class="row__name">${esc(m.name)}</div>
          <div class="row__meta">${m.type === 'district' ? 'Один район' : 'Весь город'} · эффект через ${m.lag} кв.</div>
          ${inPlan ? `<div class="row__state">В плане${inPlan.district_id ? ' · ' + esc(districtById(inPlan.district_id).name) : ''}</div>` : blocked && !full ? `<div class="row__why">${esc(why)}</div>` : ''}
        </div>
        <div class="row__side">
          <div class="row__cost">${m.cost}</div>
          ${inPlan ? `<button type="button" class="row__act row__act--rm" data-remove="${m.id}">убрать</button>` : blocked ? '' : `<span class="row__act">построить →</span>`}
        </div>
      </div>`;
    }).join('');
    return `<section class="ledger__sec"><h3 class="ledger__h"><i data-dir="${dir.id}"></i>${esc(dir.name)}<span class="ledger__cnt">${n ? `${n} из ${c.max_per_direction}` : ''}</span></h3>${rows}</section>`;
  }).join('');
  const note = $('#catalog-h span');
  if (note) note.textContent = state.decisions.length >= c.decisions_required ? 'план полон: уберите меру, чтобы заменить её' : 'не более двух из одного направления';
  $('#cards').querySelectorAll('[data-build]').forEach(b => {
    b.addEventListener('click', () => openBuild(b.dataset.build));
    b.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openBuild(b.dataset.build); } });
  });
  $('#cards').querySelectorAll('[data-remove]').forEach(b => b.addEventListener('click', e => { e.stopPropagation(); removeDecision(b.dataset.remove); }));
}

/* ---------- окно «Построить» ---------- */
function openBuild(id) {
  modalOpener = document.activeElement;
  document.querySelectorAll('.top, .stage').forEach(el => el.setAttribute('inert', ''));
  const m = measureById(id);
  const weakest = state.city.districts.reduce((a, b) => districtBase(a) <= districtBase(b) ? a : b);
  state.modal = { measure: m, district: m.type === 'district' ? weakest.id : null };
  renderModal();
}
let modalOpener = null;
function closeModal() {
  if (state.modal && state.modal.detail) { state.detail = null; document.querySelectorAll('#map-hot polygon, .plq').forEach(p => p.classList.remove('is-open')); }
  state.advisorOpen = false;   // любое закрытие (Escape, фон, крестик, кнопка) снимает флаг советника
  state.modal = null; $('#modal').hidden = true; $('#modal').innerHTML = '';
  document.querySelectorAll('.top, .stage').forEach(el => el.removeAttribute('inert'));
  if (modalOpener && document.contains(modalOpener)) modalOpener.focus();
  modalOpener = null;
}
document.addEventListener('keydown', e => {
  if (e.key !== 'Tab' || !state.modal) return;
  const els = Array.from($('#modal').querySelectorAll('button:not([disabled]), [href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'));
  if (!els.length) return;
  const first = els[0], last = els[els.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
});
function renderModal() {
  const box = $('#modal'); const { measure: m, district } = state.modal;
  const why = checkAdd(m, district);
  const eff = Object.entries(m.effects).map(([k, v]) => {
    const ind = state.city.indicators.find(i => i.code === k);
    return `<code>${k}</code><span>${esc(ind ? ind.name : k)}</span><b class="${v < 0 ? 'neg' : ''}">${v > 0 ? '+' : ''}${v} <small>→ ${sgn(v * realized(m), 1)} за ${state.city.horizon} кв.</small></b>`;
  }).join('');
  const keyInd = Object.keys(m.effects)[0];
  const dsel = m.type === 'district' ? `<div class="dlg__sec"><h4>Район</h4><div class="dsel">${state.city.districts.map(d => {
      const cur = d.indicators[keyInd];
      return `<button type="button" data-d="${d.id}" aria-pressed="${district === d.id}">${esc(d.name)}<small class="${cur < state.city.critical_threshold ? 'low' : ''}">${cur}</small></button>`;
    }).join('')}</div><div class="dlg__note">Под названием: текущее значение показателя «${esc((state.city.indicators.find(i => i.code === keyInd) || {}).name || keyInd).toLowerCase()}», на который мера влияет сильнее всего. Эффект достанется только выбранному району.</div></div>`
    : `<div class="dlg__sec"><div class="dlg__note">Городская мера: эффект получат все пять районов.</div></div>`;
  const syn = state.city.synergies.filter(x => x.measures.includes(m.id)).map(x => {
    const other = x.measures.find(y => y !== m.id); const has = state.decisions.some(d => d.measure_id === other);
    return `<div class="dlg__note${has ? ' good' : ''}">${has ? 'Синергия сработает' : 'Синергия'} с ${other} «${esc(measureById(other).name)}»: ${x.indicator} +${x.bonus}${x.district_of === m.id ? ' в этом районе' : ''}</div>`;
  }).join('');
  box.hidden = false;
  box.innerHTML = `<div class="dlg" role="dialog" aria-modal="true" aria-label="${esc(m.name)}">
    <div class="dlg__head"><img class="dlg__icon" src="${iconSrc(m.id)}" alt=""><div><div class="dlg__kicker">Городское улучшение · ${esc(dirName(m.direction))}</div><h3>${esc(m.name)}</h3>
      <div class="dlg__meta"><span><b>${m.cost}</b> ед. из ${state.city.budget - planCost()} доступных</span><span>заработает через ${m.lag} кв. · за 2 года даст ${Math.round(realized(m) * 100)}% эффекта</span></div></div></div>
    <div class="dlg__sec"><h4>Эффекты</h4><div class="eff">${eff}</div>${syn}</div>
    ${dsel}
    ${why ? `<div class="dlg__why">${esc(why)}</div>` : ''}
    <div class="dlg__foot"><button type="button" class="btn btn--ghost" data-close>Отмена</button><button type="button" class="btn btn--good" data-confirm ${why ? 'disabled' : ''}>Построить</button></div>
  </div>`;
  box.querySelectorAll('.dsel button').forEach(b => b.addEventListener('click', () => { state.modal.district = b.dataset.d; renderModal(); }));
  box.querySelector('[data-close]').addEventListener('click', closeModal);
  box.querySelector('[data-confirm]').addEventListener('click', () => { const d = { measure_id: m.id }; if (district) d.district_id = district; closeModal(); addDecision(d); });
  box.onclick = e => { if (e.target === box) closeModal(); };
  const ok = box.querySelector('[data-confirm]:not([disabled])'); if (ok) ok.focus();
}
document.addEventListener('keydown', e => { if (e.key === 'Escape' && state.modal) closeModal(); });

/* ---------- план и постройки на карте ---------- */
function addDecision(d) {
  state.decisions.push(d);
  afterChange();
  dropMarker(d, true);
  sfx('build');
}
function removeDecision(id) {
  const i = state.decisions.findIndex(d => d.measure_id === id);
  if (i < 0) return;
  const mk = document.querySelector(`.mk[data-m="${id}"]`);
  if (mk) { mk.classList.add('leave'); setTimeout(() => mk.remove(), 350); }
  state.decisions.splice(i, 1);
  afterChange();
}
function spotFor(d) {
  const key = d.district_id || 'city';
  const idx = state.decisions.filter(x => (x.district_id || 'city') === key).indexOf(d);
  const list = MAP.spots[key]; return list[Math.max(0, idx) % list.length];
}
function dropMarker(d, animate) {
  const [x, y, w] = spotFor(d);
  const mk = document.createElement('img');
  mk.className = 'mk' + (d.district_id ? '' : ' mk--city') + (animate ? ' drop' : '');
  mk.src = iconSrc(d.measure_id); mk.alt = ''; mk.dataset.m = d.measure_id;
  mk.style.left = x + '%'; mk.style.top = y + '%';
  mk.style.width = ((w || 7.2) * (MAP.scale[d.measure_id] || 1)).toFixed(2) + '%';
  $('#map-marks').appendChild(mk);
  if (!animate) return;
  const dust = document.createElement('div'); dust.className = 'dust'; dust.style.left = x + '%'; dust.style.top = y + '%';
  $('#map-marks').appendChild(dust); setTimeout(() => dust.remove(), 1600);
  const targets = d.district_id ? [d.district_id] : state.city.districts.map(x => x.id);
  targets.forEach(id => { const p = $('#poly-' + id); if (p) { p.classList.remove('flash'); void p.getBBox(); p.classList.add('flash'); } });
}
function renderMarks() { $('#map-marks').innerHTML = ''; state.decisions.forEach(d => dropMarker(d, false)); }

function renderPlan() {
  const c = state.city;
  $('#plan').innerHTML = Array.from({ length: c.decisions_required }, (_, i) => {
    const d = state.decisions[i];
    if (!d) return `<div class="slot slot--empty" title="Решение ${i + 1}"><span>+</span></div>`;
    const m = measureById(d.measure_id);
    return `<div class="slot" title="${esc(m.name)}${d.district_id ? ' · ' + esc(districtById(d.district_id).name) : ' · весь город'}, ${m.cost} ед.">
      <img src="${iconSrc(m.id)}" alt=""><div class="slot__cap">${m.id}<small>${d.district_id ? esc(districtById(d.district_id).name) : 'город'}</small></div>
      <button type="button" class="slot__x" data-remove="${m.id}" aria-label="Убрать ${m.id}">×</button></div>`;
  }).join('');
  $('#plan').querySelectorAll('[data-remove]').forEach(b => b.addEventListener('click', () => removeDecision(b.dataset.remove)));
  $('#plan-sum').innerHTML = `<b>${state.decisions.length}</b> из ${c.decisions_required} решений · <b>${planCost()}</b> из ${c.budget} ед.`;
}

function saveDraft() { try { localStorage.setItem('akim.draft', JSON.stringify({ version: state.city.version, decisions: state.decisions })); } catch (e) {} }
function loadDraft() {
  try { const d = JSON.parse(localStorage.getItem('akim.draft') || 'null'); if (d && d.version === state.city.version && Array.isArray(d.decisions)) state.decisions = d.decisions.filter(x => measureById(x.measure_id)); } catch (e) {}
}
function afterChange() { saveDraft(); renderHeader(); renderTabs(); renderCards(); renderPlan(); refreshResult(); }

/* ---------- загрузка ---------- */
function normalizeCity(c) {
  const codes = c.indicator_order || (c.indicators || []).map(i => i.code);
  const indicators = codes.map(code => {
    const src = (c.indicators || []).find(i => i.code === code) || {};
    return { code, name: src.name || (c.indicator_names || {})[code] || code, direction: src.direction || (c.indicator_directions || {})[code], weight: src.weight ?? (c.indicator_weights || {})[code] };
  });
  const directions = c.directions || Object.entries(c.direction_names || DIR_NAMES).map(([id, name]) => ({ id, name }));
  const measures = (c.measures || []).map(m => ({ ...m, type: m.type || m.scope }));
  const synergies = (c.synergies || []).map(x => ({ ...x, measures: x.measures || x.pair }));
  const incompatibilities = (c.incompatibilities || c.conflicts || []).map(x => ({ ...x, measures: x.measures || x.pair, scope: x.scope === 'global' ? 'any' : x.scope }));
  return { ...c, indicators, directions, measures, synergies, incompatibilities,
    horizon: c.horizon ?? c.horizon_quarters ?? 8, budget: c.budget ?? 100, critical_threshold: c.critical_threshold ?? 40,
    max_per_direction: c.max_per_direction ?? 2, decisions_required: c.decisions_required ?? 5 };
}
async function loadCity() {
  try {
    const r = await fetch('/api/city', { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    state.city = normalizeCity(await r.json());
  } catch (e) {
    state.city = normalizeCity(FALLBACK_CITY); state.offline = true;
    const n = $('#notice'); n.hidden = false; n.textContent = 'Сервер расчёта недоступен: показаны исходные данные, итог набора посчитать нельзя.';
  }
}

/* ---------- запросы к серверу ---------- */
async function post(url, payload, extraHeaders) {
  const r = await fetch(API + url, { method: 'POST', headers: { ...headers(), ...(extraHeaders || {}) }, body: payload });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) { const err = new Error(r.status); err.detail = j.detail; err.status = r.status; throw err; }
  return j;
}

async function refreshResult() {
  // новое поколение: ответы советника прошлого набора игнорируются, их флаги загрузки снимаются здесь
  state.explain = null; state.candidates = null; state.candidatesError = null; state.chat = [];
  state.explainBusy = false; state.improveBusy = false; state.chatBusy = false;
  const gen = ++state.gen;
  if (state.offline || state.decisions.length !== state.city.decisions_required) {
    state.result = null; state.pending = false;
    renderScore(); renderPlaques(); renderDetail(); renderActions(); renderAdvisor();
    return;
  }
  state.pending = true; renderScore(); renderActions(); renderAdvisor();
  try {
    const r = await post('/api/evaluate', body());
    if (gen !== state.gen) return;
    state.result = r;
  } catch (e) {
    if (gen !== state.gen) return;
    state.result = { valid: false, errors: [{ message: 'Сервер не ответил на расчёт. Проверьте, что он запущен.' }] };
  }
  state.pending = false;
  renderScore(); renderPlaques(); renderDetail(); renderActions(); renderAdvisor();
}

function renderActions() {
  const box = $('#plan-actions'), st = $('#plan-status');
  const ready = !!(state.result && state.result.valid) && !state.pending;
  box.innerHTML = `<button type="button" class="btn" id="btn-explain" ${ready ? '' : 'disabled'}>Объяснить</button>
    <button type="button" class="btn btn--ghost" id="btn-improve" ${ready ? '' : 'disabled'}>Найти улучшение</button>
    ${state.explain || state.candidates || state.candidatesError || state.chat.length ? `<button type="button" class="btn btn--ghost plan__reopen" id="btn-advisor">Открыть советника</button>` : ''}`;
  st.textContent = state.pending ? 'Считаем…' : ready ? 'Пять решений приняты. Советник готов.' : state.result && !state.result.valid ? 'Исправьте набор, чтобы получить советы.' : `Выберите ${state.city.decisions_required} мер, и советник разберёт план.`;
  $('#btn-explain').addEventListener('click', () => { openAdvisor(); explainPlan(); });
  $('#btn-improve').addEventListener('click', () => { openAdvisor(); findImprovements(); });
  const ba = $('#btn-advisor'); if (ba) ba.addEventListener('click', openAdvisor);
}

/* текст ошибки запроса для пользователя: сообщение сервера, иначе код ответа, иначе сеть */
function errText(e) {
  const m = e?.detail?.errors?.[0]?.message || (typeof e?.detail === 'string' ? e.detail : null);
  if (m) return String(m);
  if (e?.status) return `сервер ответил кодом ${e.status}`;
  return 'сервер недоступен или нет сети';
}

async function explainPlan() {
  if (!state.result?.valid || state.explainBusy) return;
  const gen = state.gen, key = state.result.scenario_key;
  state.explainBusy = true; renderAdvisor();
  let x = null, err = null;
  try { x = await post('/api/explain', body()); } catch (e) { err = e; }
  // ответ устаревшего набора не записываем: его флаги уже снял refreshResult
  if (gen !== state.gen || state.result?.scenario_key !== key) return;
  if (err) state.explain = { mode: 'error', reason: errText(err) };
  else { state.explain = x; if (x.candidates) { state.candidates = x.candidates; state.candidatesError = null; } }
  state.explainBusy = false;
  renderAdvisor();   // окно открывает только пользователь; если оно открыто, содержимое обновится
}

async function findImprovements() {
  if (!state.result?.valid || state.improveBusy) return;
  const gen = state.gen, key = state.result.scenario_key;
  state.improveBusy = true; state.candidatesError = null; renderAdvisor();
  let j = null, err = null;
  try { j = await post('/api/improvements', body()); } catch (e) { err = e; }
  if (gen !== state.gen || state.result?.scenario_key !== key) return;
  if (err) { state.candidatesError = errText(err); state.candidates = null; }
  else { state.candidates = j.candidates || []; }   // пустой список от сервера означает «не найдено»
  state.improveBusy = false;
  renderAdvisor();
}

function applyCandidate(id) {
  const c = (state.candidates || []).find(x => x.id === id);
  if (!c) return;
  const before = state.decisions.map(d => d.measure_id + ':' + (d.district_id || ''));
  state.decisions = c.decisions.map(d => ({ ...d }));
  if (state.advisorOpen) closeAdvisor();
  afterChange();
  $('#map-marks').innerHTML = '';
  state.decisions.forEach(d => { const key = d.measure_id + ':' + (d.district_id || ''); dropMarker(d, !before.includes(key)); });
  sfx('build');
}

async function sendChat(text) {
  if (!state.result?.valid || state.chatBusy || !text.trim()) return;
  const gen = state.gen, key = state.result.scenario_key;
  state.chat.push({ role: 'user', content: text.trim() });
  state.chatBusy = true; renderAdvisor();
  let j = null, err = null;
  try {
    const payload = JSON.parse(body()); payload.messages = state.chat.slice(-20).map(m => ({ role: m.role, content: m.content }));
    j = await post('/api/chat', JSON.stringify(payload));
  } catch (e) { err = e; }
  // набор сменился, пока ждали ответ: история уже очищена, ответ прошлого набора в неё не попадает
  if (gen !== state.gen || state.result?.scenario_key !== key) return;
  if (err) state.chat.push({ role: 'assistant', content: 'Не удалось получить ответ: ' + errText(err), mode: 'error' });
  else state.chat.push({ role: 'assistant', content: j.reply, mode: j.mode, checked: j.numbers_checked });
  state.chatBusy = false; renderAdvisor();
  const log = $('#chat-log'); if (log) log.scrollTop = log.scrollHeight;
}

async function checkKey() {
  try { state.keyStatus = await post('/api/ai/check', ''); } catch (e) { state.keyStatus = { ok: false, error: e.message }; }
  renderAdvisor();
}

function factText(ids) {
  const facts = state.explain?.facts || [];
  return ids.map(id => facts.find(f => f.id === id)?.text).filter(Boolean).join('\n');
}

function openAdvisor() {
  if (state.advisorOpen) return;
  state.advisorOpen = true;
  modalOpener = document.activeElement;
  document.querySelectorAll('.top, .stage').forEach(el => el.setAttribute('inert', ''));
  state.modal = { advisor: true };
  const box = $('#modal'); box.hidden = false;
  box.innerHTML = `<div class="dlg dlg--advisor" role="dialog" aria-modal="true" aria-label="Советник акима">
    <div class="dlg__head"><img class="dlg__face" src="/static/img/advisor.png" alt=""><div><div class="dlg__kicker">AI-советник</div><h3>Советник акима</h3><div class="dlg__meta" id="advisor-badge"></div></div>
      <button type="button" class="dlg__x" data-close aria-label="Закрыть">×</button></div>
    <div class="advisor" id="advisor"></div>
  </div>`;
  box.querySelector('[data-close]').addEventListener('click', closeAdvisor);
  box.onclick = e => { if (e.target === box) closeAdvisor(); };
  renderAdvisor();
}
function closeAdvisor() { state.advisorOpen = false; closeModal(); }
const ADVISOR_ICON = '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.8 4.6L18.5 9l-4.7 1.4L12 15l-1.8-4.6L5.5 9l4.7-1.4z"/><path d="M5 17l.8 2 2 .8-2 .8L5 22.6l-.8-2-2-.8 2-.8z"/><path d="M19 15l.6 1.5 1.5.6-1.5.6L19 19.2l-.6-1.5-1.5-.6 1.5-.6z"/></svg>';
function renderAdvisor() {
  const box = $('#advisor');
  if (!box || !state.advisorOpen) return;
  if (!state.result?.valid || state.pending) { box.innerHTML = '<p class="advisor__empty">Соберите пять решений, и советник разберёт план.</p>'; return; }
  const x = state.explain;
  const mode = x ? x.mode : null;
  const badge = state.explainBusy ? '<span class="mode"><span class="spinner"></span>думаем</span>'
    : mode === 'live' ? `<span class="mode mode--live" title="${esc(x.model || '')}">AI · ${x.key_source === 'user' ? 'ваш ключ' : 'ключ сервера'}</span>`
    : mode === 'template' ? '<span class="mode mode--fallback" title="Разбор собран автоматически на основе расчёта, без нейросети">автоматический разбор</span>'
    : mode === 'error' ? '<span class="mode mode--fallback">ошибка</span>' : '';
  const stmt = it => `<li title="${esc(factText(it.fact_ids || []))}">${esc(it.text)}</li>`;
  let bodyHtml = '';
  if (state.explainBusy) bodyHtml = '<p class="advisor__empty"><span class="spinner"></span>Советник читает расчёт…</p>';
  else if (!x) bodyHtml = '<p class="advisor__empty">Нажмите «Объяснить»: советник разберёт сильные стороны, риски и предложит замены. Ключ OpenAI подключается в настройках, без него ответ соберётся из расчёта.</p>';
  else if (mode === 'error') bodyHtml = `<p class="advisor__empty">Не удалось получить объяснение: ${esc(x.reason || '')}</p>`;
  else {
    const e = x.explanation;
    bodyHtml = `<p>${esc(e.summary)}</p>
      ${x.comparison ? `<p class="advisor__cmp">${esc(x.comparison)}</p>` : ''}
      <h4 class="good">Сильные стороны</h4><ul>${e.strengths.map(stmt).join('')}</ul>
      <h4 class="warn">Риски и компромиссы</h4><ul>${e.risks.map(stmt).join('')}</ul>
      ${mode === 'template' ? `<p class="advisor__empty">Разбор собран автоматически на основе расчёта, без нейросети.</p>` : ''}`;
  }
  const cands = state.candidates;
  const candHtml = state.improveBusy ? '<h4>Улучшения</h4><p class="advisor__empty"><span class="spinner"></span>Перебираем замены одной меры…</p>'
    : state.candidatesError ? `<h4>Улучшения</h4><p class="advisor__empty advisor__err">Не удалось получить замены: ${esc(state.candidatesError)}</p><p><button type="button" class="btn btn--sm" id="btn-improve-retry">Повторить</button></p>`
    : cands == null ? '' : cands.length === 0 ? '<h4>Улучшения</h4><p class="advisor__empty">Улучшений заменой одной меры не найдено.</p>'
    : `<h4>Проверенные замены одной меры</h4>` + cands.map(c => {
      const a = measureById(c.replace.measure_id), b = measureById(c.with.measure_id);
      const where = d => d.district_id ? districtById(d.district_id).name : 'весь город';
      const note = (x?.explanation?.suggestions || []).find(s => s.candidate_id === c.id);
      return `<div class="alt"><div class="alt__body"><b>${pts(c.score)}</b> (${spts(c.delta)}) · бюджет ${c.cost}<small>${esc(a.name)} (${esc(where(c.replace))}) → ${esc(b.name)} (${esc(where(c.with))})</small>${note ? `<small>${esc(note.text)}</small>` : ''}</div>
        <button type="button" class="btn btn--sm" data-apply="${c.id}">Применить</button></div>`;
    }).join('');
  const chatHtml = `<div class="ask"><img class="ask__face" src="/static/img/advisor.png" alt="">
    <div class="ask__body"><h4 class="ask__h">Спросить советника</h4>
    <div class="chat" id="chat-log">${state.chat.map(m => `<div class="msg msg--${m.role}${m.mode === 'error' ? ' msg--err' : ''}">${esc(m.content)}${m.role === 'assistant' && m.mode === 'live' && m.checked === false ? '<small>числа не сверены с расчётом</small>' : ''}</div>`).join('')}${state.chatBusy ? '<div class="msg msg--assistant"><span class="spinner"></span>…</div>' : ''}</div>
    <form class="chatrow" id="chat-form"><input type="text" id="chat-input" placeholder="Например: что поменять, чтобы обогнать лучший план?" maxlength="500" ${state.chatBusy ? 'disabled' : ''}><button type="submit" class="btn" ${state.chatBusy ? 'disabled' : ''}>Спросить</button></form>
    <div class="ask__hint">Отвечает с ключом OpenAI (шестерёнка в шапке). Числа берёт из расчёта.</div></div></div>`;
  const bd = $('#advisor-badge'); if (bd) bd.innerHTML = badge;
  box.innerHTML = `${bodyHtml}${candHtml}${chatHtml}`;
  box.querySelectorAll('[data-apply]').forEach(b => b.addEventListener('click', () => applyCandidate(b.dataset.apply)));
  const retry = $('#btn-improve-retry'); if (retry) retry.addEventListener('click', findImprovements);
  $('#chat-form').addEventListener('submit', e => { e.preventDefault(); const inp = $('#chat-input'); const t = inp.value; inp.value = ''; sendChat(t); });
}

/* ---------- пример из ТЗ: набор ставится целиком, анимация только визуальная ---------- */
function applyExample() {
  const ex = state.city.example_scenario || [{ measure_id: 'M7', district_id: 'nura' }, { measure_id: 'M8', district_id: 'nura' }, { measure_id: 'M10', district_id: 'nura' }, { measure_id: 'M12' }, { measure_id: 'M5', district_id: 'saryarka' }];
  state.decisions = ex.map(d => ({ ...d }));
  afterChange();
  $('#map-marks').innerHTML = '';
  const gen = ++state.animGen;
  state.decisions.forEach((d, i) => setTimeout(() => { if (gen === state.animGen) dropMarker(d, true); }, i * 250));
}
state.animGen = 0;

function openSettings() {
  modalOpener = document.activeElement;
  document.querySelectorAll('.top, .stage').forEach(el => el.setAttribute('inert', ''));
  state.modal = { settings: true };
  const box = $('#modal'); box.hidden = false;
  box.innerHTML = `<div class="dlg dlg--settings" role="dialog" aria-modal="true" aria-label="Настройки">
    <div class="dlg__head"><div class="dlg__gear">${GEAR}</div><div><div class="dlg__kicker">Настройки</div><h3>Подключение AI-советника</h3>
      <div class="dlg__meta"><span>Ключ отправляется только на этот сервер и хранится в памяти вкладки</span></div></div></div>
    <div class="dlg__sec"><h4>Ключ OpenAI</h4>
      <div class="keyrow"><input type="password" id="key-input" placeholder="sk-…" value="${esc(state.key)}" autocomplete="off" spellcheck="false"><button type="button" class="btn" id="key-check">Проверить</button></div>
      <div class="dlg__note" id="key-status"></div></div>
    <div class="dlg__sec"><h4>Как это работает</h4>
      <ul class="how__list"><li>Числа считает сервер по формуле, модель их только объясняет.</li><li>С ключом: живое объяснение и диалог с советником.</li><li>Без ключа: объяснение собирается из фактов расчёта.</li></ul></div>
    <div class="dlg__foot"><button type="button" class="btn btn--ghost" data-clear>Убрать ключ</button><button type="button" class="btn" data-close>Готово</button></div>
  </div>`;
  const status = () => {
    const ks = state.keyStatus, el = $('#key-status');
    el.className = 'keystat' + (ks ? (ks.ok ? ' keystat--ok' : ' keystat--bad') : ' keystat--idle');
    if (ks && ks.ok) el.innerHTML = `<i>✓</i><div><b>Ключ работает</b><span>Модель ${esc(ks.model)}, источник: ${ks.key_source === 'user' ? 'ваш ключ' : 'ключ сервера'}</span></div>`;
    else if (ks) el.innerHTML = `<i>!</i><div><b>Ключ не подошёл</b><span>Проверьте, что он скопирован целиком и начинается с sk-.${ks.error ? ' Ответ сервера: ' + esc(ks.error) : ''}</span></div>`;
    else el.innerHTML = `<i>·</i><div><b>${state.key ? 'Ключ введён' : 'Ключ не задан'}</b><span>${state.key ? 'Нажмите «Проверить», чтобы убедиться, что он работает.' : 'Если ключ задан на сервере, советник использует его. Без ключа разбор соберётся из расчёта.'}</span></div>`;
  };
  status();
  const ki = $('#key-input');
  const mark = () => ki.classList.toggle('is-bad', !!(state.keyStatus && !state.keyStatus.ok));
  mark();
  const save = () => { state.key = ki.value.trim(); try { sessionStorage.setItem('akim.key', state.key); } catch (e) {} };
  ki.addEventListener('change', () => { save(); state.keyStatus = null; status(); });
  $('#key-check').addEventListener('click', async () => { save(); $('#key-check').disabled = true; await checkKey(); $('#key-check').disabled = false; status(); mark(); if (typeof renderAdvisor === 'function') renderAdvisor(); });
  box.querySelector('[data-clear]').addEventListener('click', () => { ki.value = ''; save(); state.keyStatus = null; status(); });
  box.querySelector('[data-close]').addEventListener('click', closeModal);
  box.onclick = e => { if (e.target === box) closeModal(); };
  ki.focus();
}
const GEAR = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h0a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v0a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>';

/* ---------- онбординг: три шага при первом входе ---------- */
const ONB = [
  { img: '/static/img/advisor.png', kicker: 'Шаг 1 из 3', title: 'Вы аким на пять часов', lead: 'Под вашим управлением 5 районов города: Есиль, Алматы, Сарыарка, Байконур и Нура.',
    points: ['У каждого района 10 показателей по шкале от 0 до 100.', 'Ваш бюджет: <b>100</b> единиц.', 'За всё время вы можете принять ровно <b>5</b> решений.', 'Задача: поднять общий балл города и не бросить самый слабый район.'] },
  { img: '/static/img/ic-school.png', kicker: 'Шаг 2 из 3', title: 'Как принимать решения', lead: 'Справа список из 14 мер по 5 направлениям: транспорт, экология, соцсфера, безопасность и сервисы.',
    points: ['Нажмите на меру и выберите район. Постройка появится на карте.', 'Из одного направления можно взять не больше <b>2</b> мер.', 'Некоторые меры нельзя сочетать, окно постройки об этом предупредит.', 'Бюджет превысить нельзя. Остаток не сгорает.'] },
  { img: '/static/img/patrol-dog.png', kicker: 'Шаг 3 из 3', title: 'Что будет после пятого решения', lead: 'Как только вы примете 5 решений, город пересчитается.',
    points: ['Вы увидите новый балл города и изменения в каждом районе.', 'Советник акима объяснит, что вышло хорошо, а что рискованно, и предложит замену.', 'Робот-собака Go2 патрулирует город: нажмите на неё, чтобы увидеть камеру и сигналы по районам.'] },
];
function openOnboarding(step = 0) {
  const o = ONB[step];
  if (!state.modal || !state.modal.onboarding) { modalOpener = document.activeElement; document.querySelectorAll('.top, .stage').forEach(el => el.setAttribute('inert', '')); }
  state.modal = { onboarding: step };
  const box = $('#modal'); box.hidden = false;
  box.innerHTML = `<div class="dlg dlg--onb" role="dialog" aria-modal="true" aria-label="${esc(o.title)}">
    <div class="dlg__head onb__head"><img class="onb__img" src="${o.img}" alt=""><div><div class="dlg__kicker">${o.kicker}</div><h3>${esc(o.title)}</h3></div>
      <button type="button" class="dlg__x" data-skip aria-label="Закрыть">×</button></div>
    <div class="dlg__sec onb__sec"><p class="onb__lead">${esc(o.lead)}</p><ul class="onb__list">${o.points.map(p => `<li>${p}</li>`).join('')}</ul></div>
    <div class="dlg__foot onb__foot"><div class="onb__dots">${ONB.map((_, i) => `<i class="${i === step ? 'on' : ''}"></i>`).join('')}</div>
      ${step > 0 ? '<button type="button" class="btn btn--ghost" data-prev>Назад</button>' : '<button type="button" class="btn btn--ghost" data-skip>Пропустить</button>'}
      ${step < ONB.length - 1 ? '<button type="button" class="btn" data-next>Далее</button>' : '<button type="button" class="btn btn--good" data-skip>Начать</button>'}</div>
  </div>`;
  const done = () => { try { localStorage.setItem('akim.onboarded', '1'); } catch (e) {} closeModal(); };
  box.querySelectorAll('[data-skip]').forEach(b => b.addEventListener('click', done));
  const n = box.querySelector('[data-next]'); if (n) n.addEventListener('click', () => openOnboarding(step + 1));
  const p = box.querySelector('[data-prev]'); if (p) p.addEventListener('click', () => openOnboarding(step - 1));
  box.onclick = e => { if (e.target === box) done(); };
  (box.querySelector('[data-next]') || box.querySelector('.btn--good')).focus();
}

function openHow() {
  const c = state.city;
  const mn = id => esc((measureById(id) || { name: id }).name); const indN = code => esc(((c.indicators || []).find(i => i.code === code) || { name: code }).name).toLowerCase();
  const syn = c.synergies.map(x => `<li><b>${mn(x.measures[0])}</b> плюс <b>${mn(x.measures[1])}</b>: показатель «${indN(x.indicator)}» получает ещё +${x.bonus} балла там, где стоит ${mn(x.district_of)}</li>`).join('');
  const inc = c.incompatibilities.map(x => `<li><b>${mn(x.measures[0])}</b> и <b>${mn(x.measures[1])}</b>: ${x.scope === 'any' ? 'в одном плане не бывают' : 'в один район не ставятся'}${x.reason ? ' (' + esc(x.reason) + ')' : ''}</li>`).join('');
  modalOpener = document.activeElement;
  document.querySelectorAll('.top, .stage').forEach(el => el.setAttribute('inert', ''));
  state.modal = { how: true };
  const box = $('#modal'); box.hidden = false;
  box.innerHTML = `<div class="dlg dlg--how" role="dialog" aria-modal="true" aria-label="Как считается балл">
    <div class="dlg__head"><div><div class="dlg__kicker">Правила</div><h3>Как считается балл города</h3></div><button type="button" class="dlg__x" data-close aria-label="Закрыть">×</button></div>
    <div class="dlg__sec"><h4>Ход игры</h4>
      <ol class="how__steps"><li>Вы аким. У города пять районов, у каждого десять показателей от 0 до 100: дороги, школы, воздух и так далее. В казне <b>${c.budget}</b> единиц.</li><li>Постройте ровно <b>${c.decisions_required}</b> объектов из ${c.measures.length} возможных. Школу или парк ставите в один район, а светофоры или платформу обращений получает весь город.</li><li>Как только пятый объект встал на карту, город пересчитывается: вы видите новый балл, что изменилось в районах и что об этом думает советник.</li></ol></div>
    <div class="dlg__sec"><h4>Формула</h4>
      <div class="how__formula">Балл = 0,7 × средний по городу + 0,3 × самый слабый район − число провалов ниже ${c.critical_threshold}</div>
      <ul class="how__list"><li>Стройка занимает время. Парк откроется через полгода, а ЛРТ только через год, поэтому за два года ЛРТ успеет дать лишь половину своего эффекта.</li><li>Средний балл по городу считается с поправкой на население: Есиль, где живёт четверть горожан, весит больше, чем Байконур.</li><li>Треть итога зависит от самого слабого района. Можно отстроить один район и всё равно проиграть, если другой остался в провале.</li><li>Каждый показатель ниже ${c.critical_threshold} это провал, и за каждый город теряет балл. На карте самый слабый район обведён кольцом, а цифра рядом с ним показывает, сколько у него провалов.</li></ul></div>
    <div class="dlg__sec"><h4>Ограничения</h4>
      <ul class="how__list"><li>Неистраченные деньги никуда не деваются, но и пользы не приносят: балл за экономию не растёт.</li><li>Каждый объект строится один раз. Из одной сферы, например транспорта, можно взять не больше ${c.max_per_direction} объектов.</li></ul>
      <h4 style="margin-top:12px">Что работает лучше вместе</h4><ul class="how__list">${syn}</ul>
      <h4 style="margin-top:12px">Что вместе не строится</h4><ul class="how__list">${inc}</ul></div>
    <div class="dlg__foot"><button type="button" class="btn btn--ghost" data-onb>Показать обучение</button><button type="button" class="btn" data-close>Понятно</button></div>
  </div>`;
  box.querySelector('[data-onb]').addEventListener('click', () => { closeModal(); openOnboarding(0); });
  box.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', closeModal));
  box.onclick = e => { if (e.target === box) closeModal(); };
  box.querySelector('.dlg__foot [data-close]').focus();
}

async function init() {
  await loadCity();
  renderMapStatic();
  initView();
  loadDraft();
  renderHeader(); renderTabs(); renderCards(); renderPlan(); renderMarks(); renderScore(); renderPlaques(); renderActions(); renderAdvisor();
  refreshResult();
  $('#btn-reset').addEventListener('click', () => { state.animGen++; state.decisions = []; afterChange(); renderMarks(); });
  $('#btn-example').addEventListener('click', applyExample);
  $('#btn-how').addEventListener('click', openHow);
  if (!state.decisions.length) setTimeout(() => openOnboarding(0), 600);
  $('#btn-settings').addEventListener('click', openSettings);
  $('#btn-settings').innerHTML = GEAR;
}
init();

})();
