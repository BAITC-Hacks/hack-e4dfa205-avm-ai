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

/* Названия показателей симулятора для ленты: код внутри, пользователю показываем слово. */
const KNAME = { C1: 'ЖКХ', B1: 'безопасность улиц', B2: 'дорожное движение', E2: 'воздух' };

/* Сценарий событий: район, показатель симулятора, текст, адресат (to) или статус (s).
   Это заранее заданный сценарий демонстрации: события никуда не отправляются, в ленте так и подписано. */
const DEMO_NOTE = 'демонстрация: событие не отправляется';
const EVENTS = [
  { d: 'nura', k: 'C1', t: 'Открытый люк на проезжей части, крышка отсутствует', to: 'ЖКХ', lvl: 'warn', f: 0 },
  { d: 'almaty', k: 'B2', t: 'Яма на дороге глубиной более 10 см у пешеходного перехода', to: 'дорожная служба', lvl: 'warn', f: 1 },
  { d: 'saryarka', k: 'E2', t: 'Газоанализатор: превышение CO у частного сектора', to: 'экологический контроль', lvl: 'bad', f: 2 },
  { d: 'esil', k: 'B1', t: 'Скопление людей у здания акимата, около 40 человек', s: 'наблюдение по сценарию', lvl: 'info', f: 3 },
  { d: 'baikonur', k: 'B1', t: 'Ребёнок без сопровождения у стройплощадки', to: 'оператор', lvl: 'bad', f: 4 },
  { d: 'almaty', k: 'B1', t: 'Совпадение с ориентировкой по силуэту и одежде', to: 'дежурная часть', lvl: 'bad', f: 3 },
  { d: 'nura', k: 'B1', t: 'Неработающий фонарь на пешеходной дорожке', to: 'ЖКХ', lvl: 'warn', f: 4 },
  { d: 'saryarka', k: 'C1', t: 'Парение из теплотрассы, возможный порыв', to: 'теплосети', lvl: 'warn', f: 2 },
  { d: 'esil', k: 'B2', t: 'Автомобиль на велодорожке у набережной', s: 'зафиксировано в сценарии', lvl: 'info', f: 1 },
  { d: 'baikonur', k: 'C1', t: 'Переполненная контейнерная площадка', to: 'ЖКХ', lvl: 'info', f: 4 },
  { d: 'nura', k: 'E2', t: 'Дым от сжигания мусора в частном секторе', to: 'экологический контроль', lvl: 'warn', f: 2 },
  { d: 'almaty', k: 'B2', t: 'Ребёнок перебегает дорогу вне перехода у школы', to: 'оператор', lvl: 'warn', f: 1 },
  { d: 'nura', k: 'B1', t: 'Разбитое остекление остановки', to: 'ЖКХ', lvl: 'info', f: 4 },
  { d: 'saryarka', k: 'B1', t: 'Маршрут пройден, отклонений нет', s: 'демонстрационный патруль продолжается', lvl: 'ok', f: 0 },
];

const DRONE_ROUTE = [
  [14, 76, 'saryarka'], [24, 62, 'saryarka'], [40, 58, 'esil'], [52, 44, 'esil'], [62, 66, 'baikonur'],
  [78, 78, 'almaty'], [90, 60, 'almaty'], [82, 42, 'nura'], [60, 24, 'esil'], [34, 30, 'esil'], [10, 50, 'saryarka'],
];
const DRONE_EVENTS = [
  { d: 'saryarka', k: 'E2', t: 'Газоанализатор: фиксирую превышение CH₄ у промзоны, ветер на жилой сектор. Прогноз: пик через 2 часа.', s: 'передано в экологическую службу', lvl: 'bad', f: 0 },
  { d: 'saryarka', k: 'E2', t: 'Вижу дым от котельной частного сектора, видимость снижена.', s: 'наблюдаю', lvl: 'warn', f: 0 },
  { d: 'almaty', k: 'B2', t: 'ДТП на перекрёстке, две полосы перекрыты. Объезд через соседние улицы поднимет нагрузку на них.', s: 'оператор уведомлён', lvl: 'bad', f: 1 },
  { d: 'almaty', k: 'T1', t: 'Затор 1,2 км из-за ремонта дороги. Перекрытие влияет на два маршрута автобусов.', s: 'передано в транспортный центр', lvl: 'warn', f: 2 },
  { d: 'esil', k: 'C1', t: 'Строительная площадка без разрешения по данным карты: ограждение, техника, котлован. Снимок с координатами сохранил.', s: 'передано в акимат', lvl: 'warn', f: 3 },
  { d: 'baikonur', k: 'C1', t: 'Осмотрел опору теплотрассы: трещин и деформаций не вижу, конструкция устойчива. Снимок сохранён.', s: 'без замечаний', lvl: 'info', f: 4 },
];
const FRAMES = {
  dog: ['/static/img/patrol-cam.jpg', '/static/img/patrol-dog2.jpg', '/static/img/patrol-dog3.jpg', '/static/img/patrol-dog4.jpg', '/static/img/patrol-dog5.jpg'],
  drone: ['/static/img/patrol-dronecam.jpg', '/static/img/patrol-drone2.jpg', '/static/img/patrol-drone3.jpg', '/static/img/patrol-drone4.jpg', '/static/img/patrol-drone5.jpg'],
};
function swapFrame(f) {
  const img = document.querySelector('.patrol-cam img'); if (!img) return;
  const list = FRAMES[state.unit] || FRAMES.dog;
  state.frame = (typeof f === 'number' ? f : ((state.frame || 0) + 1)) % list.length;
  const box = document.querySelector('.patrol-box');
  img.classList.add('patrol-cam--fade');
  setTimeout(() => { img.src = list[state.frame]; img.onload = () => img.classList.remove('patrol-cam--fade'); if (box) box.style.display = state.frame === 0 ? '' : 'none'; }, 260);
}
const state = { pos: 0, t: 0, feed: [], idx: 0, frame: 0, open: false, timer: null, raf: null, counts: {}, unit: 'dog', dpos: 0, dt: 0, dfeed: [], didx: 0 };

function ensureMarker() {
  let m = $('#patrol-marker');
  if (m) return m;
  m = document.createElement('button');
  m.type = 'button'; m.id = 'patrol-marker'; m.className = 'patrol-marker';
  m.setAttribute('aria-label', 'Робот-собака Go2, демонстрация патруля: открыть окно камеры');
  m.innerHTML = `<span class="patrol-ring"></span><img src="/static/img/patrol-dog.png" alt=""><span class="patrol-tag">Go2 · демо-патруль</span>`;
  m.addEventListener('click', openCamera);
  $('#map-marks').appendChild(m);
  return m;
}

function ensureDrone() {
  let m = $('#patrol-drone');
  if (m) return m;
  m = document.createElement('button');
  m.type = 'button'; m.id = 'patrol-drone'; m.className = 'patrol-marker patrol-marker--drone';
  m.setAttribute('aria-label', 'Дрон Astana Dynamics в полёте: открыть камеру');
  m.innerHTML = `<span class="patrol-shadow"></span><img src="/static/img/patrol-drone.png" alt="" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'patrol-emoji',textContent:'🛸'}))"><span class="patrol-tag patrol-tag--drone"><i class="patrol-dot"></i>Дрон · открыть камеру</span>`;
  m.addEventListener('click', () => openCamera('drone'));
  $('#map-marks').appendChild(m);
  return m;
}
function step(ts) {
  const m = ensureMarker();
  const dm = ensureDrone();
  state.dt += 0.00022 * 16;
  if (state.dt >= 1) { state.dt = 0; state.dpos = (state.dpos + 1) % DRONE_ROUTE.length; }
  const da = DRONE_ROUTE[state.dpos], db = DRONE_ROUTE[(state.dpos + 1) % DRONE_ROUTE.length];
  dm.style.left = (da[0] + (db[0] - da[0]) * state.dt) + '%'; dm.style.top = (da[1] + (db[1] - da[1]) * state.dt) + '%';
  dm.dataset.d = da[2];
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
  const drone = state.unit === 'drone';
  const list = drone ? DRONE_EVENTS : EVENTS;
  const e = list[(drone ? state.didx : state.idx) % list.length]; if (drone) state.didx++; else state.idx++;
  const now = new Date();
  const time = now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const feed = drone ? state.dfeed : state.feed;
  feed.unshift({ ...e, time });
  if (feed.length > 8) feed.pop();
  if (e.lvl !== 'ok') state.counts[e.d] = (state.counts[e.d] || 0) + 1;
  renderFeed();
  if (state.open) swapFrame(e.f);
}

function renderFeed() {
  const box = $('#patrol-feed'); if (!box) return;
  const feed = state.unit === 'drone' ? state.dfeed : state.feed;
  box.innerHTML = feed.map((e, i) => `<div class="patrol-ev patrol-ev--${e.lvl}${i === 0 ? ' patrol-ev--new' : ''}">
    <div class="patrol-ev__top"><span class="patrol-ev__time">${e.time}</span><span class="patrol-ev__d">${DIST[e.d]}</span><span class="patrol-ev__k">${esc(KNAME[e.k] || e.k)}</span></div>
    <div class="patrol-ev__t">${esc(e.t)}</div><div class="patrol-ev__s">${e.to ? `адресат: ${esc(e.to)} · ${DEMO_NOTE}` : esc(e.s)}</div></div>`).join('');
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

function openCamera(unit) {
  if (state.open) return;
  state.open = true; state.unit = unit === 'drone' ? 'drone' : 'dog'; state.frame = 0;
  const drone = state.unit === 'drone';
  const box = document.createElement('div');
  box.className = 'patrol-modal'; box.id = 'patrol-modal';
  box.innerHTML = `<div class="patrol-dlg" role="dialog" aria-modal="true" aria-label="Камера робота-собаки Go2, демонстрация концепции">
    <div class="patrol-dlg__head"><div><div class="patrol-kicker">${drone ? 'Экология и безопасность · Дрон · Astana Dynamics · демо' : 'Безопасный город · робот-собака Go2 · демо'}</div><h3>${drone ? 'Камера дрона · в полёте · высота 80 м' : 'Камера патруля'}</h3></div>
      <div class="patrol-units"><button type="button" class="patrol-unit ${drone ? '' : 'on'}" data-unit="dog">Go2</button><button type="button" class="patrol-unit ${drone ? 'on' : ''}" data-unit="drone">Дрон</button></div>
      <button type="button" class="patrol-close" aria-label="Закрыть">×</button></div>
    <div class="patrol-demo" role="note">Демонстрация концепции: камера и события заранее заданы, реального робота и потока нет.</div>
    <div class="patrol-body">
      <div class="patrol-cam">
        <img src="${drone ? '/static/img/patrol-dronecam.jpg' : '/static/img/patrol-cam.jpg'}" alt="Демонстрационный кадр: как выглядел бы кадр с камеры ${drone ? 'дрона' : 'робота-собаки'}">
        <div class="patrol-ovl patrol-ovl--tl"><span class="patrol-rec"></span>ДЕМО · запись · 640×480</div>
        <div class="patrol-ovl patrol-ovl--tr" id="patrol-clock"></div>
        <div class="patrol-ovl patrol-ovl--bl">демонстрация · район: <span id="patrol-where"></span></div>
        <div class="patrol-ovl patrol-ovl--br">Go2 · телеметрия условная</div>
        <div class="patrol-box" style="left:39%;top:44%;width:22%;height:11%"><span>открытый люк · пример разметки</span></div>
        <div class="patrol-cross"></div>
      </div>
      <div class="patrol-side">
        <div class="patrol-side__h">Лента событий · сценарий демо</div>
        <div class="patrol-feed" id="patrol-feed"></div>
        <div class="patrol-counts" id="patrol-counts"></div>
        <div class="patrol-concept">Концепт · демонстрационные данные</div>
      </div>
    </div>
  </div>`;
  document.body.appendChild(box);
  box.querySelectorAll('.patrol-unit').forEach(b => b.addEventListener('click', () => { const u = b.dataset.unit; closeCamera(); openCamera(u); }));
  box.querySelector('.patrol-close').addEventListener('click', closeCamera);
  box.addEventListener('click', e => { if (e.target === box) closeCamera(); });
  document.addEventListener('keydown', escClose);
  const cur = drone ? state.dfeed : state.feed;
  if (!cur.length) { pushEvent(); pushEvent(); pushEvent(); } else { renderFeed(); swapFrame(cur[0].f); }
  state.timer = setInterval(pushEvent, 3200);
  tickClock();
}
function tickClock() {
  if (!state.open) return;
  const c = $('#patrol-clock'), w = $('#patrol-where');
  if (c) c.textContent = new Date().toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  if (w) w.textContent = DIST[(state.unit === 'drone' ? DRONE_ROUTE[state.dpos] : ROUTE[state.pos])[2]];
  setTimeout(tickClock, 1000);
}
function escClose(e) { if (e.key === 'Escape') closeCamera(); }
function closeCamera() {
  state.open = false; clearInterval(state.timer); document.removeEventListener('keydown', escClose);
  const b = $('#patrol-modal'); if (b) b.remove();
}

/* Уведомления патруля: подсказывают, что собака кликабельна */
let toastIdx = 0;
function showToast() {
  if (state.open || document.querySelector('.patrol-toast') || !document.getElementById('modal')?.hidden) return;
  const e = EVENTS[toastIdx % EVENTS.length]; toastIdx++;
  const t = document.createElement('div');
  t.className = 'patrol-toast';
  t.innerHTML = `<img src="/static/img/patrol-dog.png" alt=""><div class="patrol-toast__b"><div class="patrol-toast__k">Патруль Go2 · ${DIST[e.d]}</div><div class="patrol-toast__t">${esc(e.t)}</div></div><button type="button" class="patrol-toast__btn">Камера</button><button type="button" class="patrol-toast__x" aria-label="Закрыть">×</button>`;
  $('#stage-map').appendChild(t);
  const close = () => { t.classList.add('patrol-toast--out'); setTimeout(() => t.remove(), 300); };
  t.querySelector('.patrol-toast__btn').addEventListener('click', () => { close(); openCamera('dog'); });
  t.querySelector('.patrol-toast__x').addEventListener('click', close);
  setTimeout(() => { if (t.isConnected) close(); }, 9000);
}

function boot() {
  if (!$('#map-marks')) { setTimeout(boot, 300); return; }
  ensureMarker();
  setTimeout(showToast, 12000);
  setInterval(showToast, 45000);
  state.raf = requestAnimationFrame(step);
  // маркер живёт поверх построек: при перерисовке маркеров возвращаем его
  const mo = new MutationObserver(() => { if (!$('#patrol-marker')) ensureMarker(); if (!$('#patrol-drone')) ensureDrone(); });
  mo.observe($('#map-marks'), { childList: true });
}
boot();

})();
