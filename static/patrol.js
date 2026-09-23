/* Патруль робота-собаки Go2: движущийся маркер по районам, окно «камеры» с лентой событий ИИ-агента.
   Полностью на фронтенде, к расчёту Score и API не обращается. Все классы с префиксом patrol-. */
'use strict';
(() => {

const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* Маршрут по карте: точки в процентах от размера карты (viewBox 2000×1116). Идёт по дорогам через все пять районов. */
const ROUTE = [
  [22, 36, 'esil'], [30, 44, 'esil'], [40, 50, 'esil'], [48, 56, 'esil'],
  [56, 60, 'baikonur'], [62, 72, 'baikonur'], [66, 84, 'baikonur'],
  [76, 78, 'almaty'], [84, 66, 'almaty'], [90, 54, 'almaty'],
  [86, 40, 'nura'], [78, 30, 'nura'], [70, 18, 'nura'],
  [52, 22, 'esil'], [40, 30, 'esil'],
  [30, 56, 'saryarka'], [22, 68, 'saryarka'], [14, 82, 'saryarka'], [10, 60, 'saryarka'], [14, 44, 'esil'],
];
const DIST = { esil: 'Есиль', almaty: 'Алматы', saryarka: 'Сарыарка', baikonur: 'Байконур', nura: 'Нура' };

/* Сценарий событий: район, показатель симулятора, текст, статус. */
const EVENTS = [
  { d: 'nura', k: 'C1', t: 'Открытый люк на проезжей части, крышка отсутствует', s: 'передано в ЖКХ', lvl: 'warn' },
  { d: 'almaty', k: 'B2', t: 'Яма на дороге глубиной более 10 см у пешеходного перехода', s: 'передано в дорожную службу', lvl: 'warn' },
  { d: 'saryarka', k: 'E2', t: 'Газоанализатор: превышение CO у частного сектора', s: 'уведомлён экологический контроль', lvl: 'bad' },
  { d: 'esil', k: 'B1', t: 'Скопление людей у здания акимата, около 40 человек', s: 'наблюдаю', lvl: 'info' },
  { d: 'baikonur', k: 'B1', t: 'Ребёнок без сопровождения у стройплощадки', s: 'оператор уведомлён', lvl: 'bad' },
  { d: 'almaty', k: 'B1', t: 'Совпадение с ориентировкой по силуэту и одежде', s: 'передано в дежурную часть', lvl: 'bad' },
  { d: 'nura', k: 'B1', t: 'Неработающий фонарь на пешеходной дорожке', s: 'передано в ЖКХ', lvl: 'warn' },
  { d: 'saryarka', k: 'C1', t: 'Парение из теплотрассы, возможный порыв', s: 'передано в теплосети', lvl: 'warn' },
  { d: 'esil', k: 'B2', t: 'Автомобиль на велодорожке у набережной', s: 'зафиксировано, номер распознан', lvl: 'info' },
  { d: 'baikonur', k: 'C1', t: 'Переполненная контейнерная площадка', s: 'передано в ЖКХ', lvl: 'info' },
  { d: 'nura', k: 'E2', t: 'Дым от сжигания мусора в частном секторе', s: 'уведомлён экологический контроль', lvl: 'warn' },
  { d: 'almaty', k: 'B2', t: 'Ребёнок перебегает дорогу вне перехода у школы', s: 'оператор уведомлён', lvl: 'warn' },
  { d: 'nura', k: 'B1', t: 'Разбитое остекление остановки', s: 'передано в ЖКХ', lvl: 'info' },
  { d: 'saryarka', k: 'B1', t: 'Маршрут пройден, отклонений нет', s: 'патруль продолжается', lvl: 'ok' },
];

const state = { pos: 0, t: 0, feed: [], idx: 0, open: false, timer: null, raf: null, counts: {} };

function ensureMarker() {
  let m = $('#patrol-marker');
  if (m) return m;
  m = document.createElement('button');
  m.type = 'button'; m.id = 'patrol-marker'; m.className = 'patrol-marker';
  m.setAttribute('aria-label', 'Робот-собака Go2 на патруле: открыть камеру');
  m.innerHTML = `<span class="patrol-ring"></span><img src="/static/img/patrol-dog.png" alt=""><span class="patrol-tag">Go2 · патруль</span>`;
  m.addEventListener('click', openCamera);
  $('#map-marks').appendChild(m);
  return m;
}

function step(ts) {
  const m = ensureMarker();
  const speed = 0.00012; // доля отрезка в мс
  state.t += speed * 16;
  if (state.t >= 1) { state.t = 0; state.pos = (state.pos + 1) % ROUTE.length; }
  const a = ROUTE[state.pos], b = ROUTE[(state.pos + 1) % ROUTE.length];
  const x = a[0] + (b[0] - a[0]) * state.t, y = a[1] + (b[1] - a[1]) * state.t;
  m.style.left = x + '%'; m.style.top = y + '%';
  m.dataset.d = a[2];
  state.raf = requestAnimationFrame(step);
}

function pushEvent() {
  const e = EVENTS[state.idx % EVENTS.length]; state.idx++;
  const now = new Date();
  const time = now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  state.feed.unshift({ ...e, time });
  if (state.feed.length > 8) state.feed.pop();
  if (e.lvl !== 'ok') state.counts[e.d] = (state.counts[e.d] || 0) + 1;
  renderFeed();
}

function renderFeed() {
  const box = $('#patrol-feed'); if (!box) return;
  box.innerHTML = state.feed.map((e, i) => `<div class="patrol-ev patrol-ev--${e.lvl}${i === 0 ? ' patrol-ev--new' : ''}">
    <div class="patrol-ev__top"><span class="patrol-ev__time">${e.time}</span><span class="patrol-ev__d">${DIST[e.d]}</span><span class="patrol-ev__k">${e.k}</span></div>
    <div class="patrol-ev__t">${esc(e.t)}</div><div class="patrol-ev__s">${esc(e.s)}</div></div>`).join('');
  const counts = Object.entries(state.counts).sort((a, b) => b[1] - a[1]);
  const top = counts[0];
  const weak = weakestDistrict();
  $('#patrol-counts').innerHTML = Object.keys(DIST).map(d => `<span class="patrol-cnt"><b>${state.counts[d] || 0}</b>${DIST[d]}</span>`).join('') +
    (top ? `<div class="patrol-note">Больше всего сигналов: ${DIST[top[0]]}${weak && weak === top[0] ? ' — совпадает со слабейшим районом плана' : ''}</div>` : '');
}

function weakestDistrict() {
  const plq = Array.from(document.querySelectorAll('.plq'));
  let best = null, bv = Infinity;
  plq.forEach(p => { const v = parseFloat((p.querySelector('.plq__v') || {}).textContent?.replace(',', '.')); if (!isNaN(v) && v < bv) { bv = v; best = p.dataset.d; } });
  return best;
}

function openCamera() {
  if (state.open) return;
  state.open = true;
  const box = document.createElement('div');
  box.className = 'patrol-modal'; box.id = 'patrol-modal';
  box.innerHTML = `<div class="patrol-dlg" role="dialog" aria-modal="true" aria-label="Камера робота-собаки Go2">
    <div class="patrol-dlg__head"><div><div class="patrol-kicker">Безопасный город · робот-собака Go2</div><h3>Камера патруля</h3></div>
      <button type="button" class="patrol-close" aria-label="Закрыть">×</button></div>
    <div class="patrol-body">
      <div class="patrol-cam">
        <img src="/static/img/patrol-cam.jpg" alt="Кадр с камеры робота-собаки">
        <div class="patrol-ovl patrol-ovl--tl"><span class="patrol-rec"></span>LIVE · RTSP H.264 · 640×480 · 15 fps</div>
        <div class="patrol-ovl patrol-ovl--tr" id="patrol-clock"></div>
        <div class="patrol-ovl patrol-ovl--bl">ЦОУ · оператор 3 · <span id="patrol-where"></span></div>
        <div class="patrol-ovl patrol-ovl--br">Go2 · батарея 74 % · 4,1 км/ч</div>
        <div class="patrol-box" style="left:39%;top:44%;width:22%;height:11%"><span>открытый люк · 0,96</span></div>
        <div class="patrol-cross"></div>
      </div>
      <div class="patrol-side">
        <div class="patrol-side__h">Лента ИИ-агента</div>
        <div class="patrol-feed" id="patrol-feed"></div>
        <div class="patrol-counts" id="patrol-counts"></div>
      </div>
    </div>
  </div>`;
  document.body.appendChild(box);
  box.querySelector('.patrol-close').addEventListener('click', closeCamera);
  box.addEventListener('click', e => { if (e.target === box) closeCamera(); });
  document.addEventListener('keydown', escClose);
  if (!state.feed.length) { pushEvent(); pushEvent(); pushEvent(); } else renderFeed();
  state.timer = setInterval(pushEvent, 3200);
  tickClock();
}
function tickClock() {
  if (!state.open) return;
  const c = $('#patrol-clock'), w = $('#patrol-where');
  if (c) c.textContent = new Date().toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  if (w) w.textContent = DIST[ROUTE[state.pos][2]];
  setTimeout(tickClock, 1000);
}
function escClose(e) { if (e.key === 'Escape') closeCamera(); }
function closeCamera() {
  state.open = false; clearInterval(state.timer); document.removeEventListener('keydown', escClose);
  const b = $('#patrol-modal'); if (b) b.remove();
}

function boot() {
  if (!$('#map-marks')) { setTimeout(boot, 300); return; }
  ensureMarker();
  state.raf = requestAnimationFrame(step);
  // маркер живёт поверх построек: при перерисовке маркеров возвращаем его
  const mo = new MutationObserver(() => { if (!$('#patrol-marker')) ensureMarker(); });
  mo.observe($('#map-marks'), { childList: true });
}
boot();

})();
