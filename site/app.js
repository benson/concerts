const VIDEO = location.hostname === "localhost" ? "media/v/" : "https://pub-2d6e5c0e5cdc4d5490649e8847c34a82.r2.dev/";
const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let shows = [], open = new Set(), map, mapLayer, queue = [], qi = 0;

const fmtDate = d => { const [, m, day] = d.split("-"); return `${MONTHS[+m - 1]} ${+day}`; };
const ownTour = (s, band) => { const t = (s.lineup.find(x => x.band === band) || {}).tour; return t && !(s.event || "").includes(t) ? t : null; };
const bandOf = c => c.band ? c.band + (c.confidence === "low" ? "?" : "") : "unknown band";

function haystack(s) {
  const [y, m] = s.date.split("-");
  return [s.venue, s.city, s.event, s.date, `${MONTHS[+m - 1]} ${y}`,
    ...s.lineup.map(b => `${b.band} ${b.tour || ""}`),
    ...s.clips.map(c => `${c.band || ""} ${c.song || ""}`)].join(" ").toLowerCase();
}

function matches(s, terms) {
  return terms.every(t => s._hay.includes(t));
}

function clipMatches(c, terms) {
  const h = `${c.band || ""} ${c.song || ""}`.toLowerCase();
  return terms.some(t => h.includes(t));
}

function render() {
  const q = $("#q").value.trim().toLowerCase();
  const terms = q ? q.split(/\s+/) : [];
  const list = shows.filter(s => matches(s, terms));
  const el = $("#timeline");
  if (!list.length) { el.innerHTML = `<p class="empty">nothing matches “${esc(q)}”</p>`; return; }
  let html = "", year = null;
  for (const s of list) {
    const y = s.date.slice(0, 4);
    if (y !== year) { html += `<h2>${y}</h2>`; year = y; }
    const filmed = new Set(s.clips.map(c => c.band).filter(Boolean));
    const names = s.lineup.length ? s.lineup.map(b => b.band) : [...filmed];
    const lineup = names.map(b => `<span class="${filmed.has(b) ? "filmed" : ""}">${esc(b)}</span>`).join(", ");
    const n = s.clips.length;
    const expanded = open.has(s.id) || (terms.length && s.clips.some(c => clipMatches(c, terms)));
    html += `<article class="show${s.ticket_only ? " ticket-only" : ""}" data-id="${s.id}">
      <div class="show-head" tabindex="0">
        <span class="date">${fmtDate(s.date)}</span>
        <span><span class="venue">${esc(s.venue || "unknown venue")}</span>${s.event ? ` <span class="event">· ${esc(s.event)}</span>` : ""}<br><span class="lineup">${lineup}</span></span>
        <span class="count">${n ? `${n} clip${n > 1 ? "s" : ""}` : "no video"}</span>
      </div>
      ${expanded && n ? body(s, terms) : ""}
    </article>`;
  }
  el.innerHTML = html;
}

function body(s, terms) {
  const groups = [];
  for (const c of s.clips) {
    const name = bandOf(c);
    const g = groups.find(g => g.name === name);
    g ? g.clips.push(c) : groups.push({ name, band: c.band, clips: [c] });
  }
  const order = b => (s.lineup.find(x => x.band === b) || {}).play_order ?? 99;
  groups.sort((a, b) => order(a.band) - order(b.band));
  return `<div class="show-body">${groups.map(g => {
    const tour = ownTour(s, g.band);
    return `<div class="band-row"><div class="band-name">${esc(g.name)}${tour ? ` <span class="tour">· ${esc(tour)}</span>` : ""}</div>
      <div class="thumbs">${g.clips.map(c => `<img class="thumb" loading="lazy" tabindex="0" src="media/t/${c.id}.jpg"
        data-show="${s.id}" data-clip="${c.id}" alt="${esc(g.name)}${c.song ? " – " + esc(c.song) : ""}"
        title="${esc([c.time, c.song].filter(Boolean).join(" · "))}">`).join("")}</div></div>`;
  }).join("")}</div>`;
}

function play(showId, clipId) {
  const s = shows.find(x => x.id === showId);
  const groups = $(`[data-id="${showId}"] .show-body`) ? [...document.querySelectorAll(`[data-id="${showId}"] .thumb`)].map(t => t.dataset.clip) : s.clips.map(c => c.id);
  queue = groups.map(id => ({ s, c: s.clips.find(c => c.id === id) }));
  qi = Math.max(0, queue.findIndex(x => x.c.id === clipId));
  show();
}

function show() {
  const { s, c } = queue[qi];
  const p = $("#player"), v = $("video", p);
  p.hidden = false;
  v.src = `${VIDEO}${c.id}.mp4`;
  v.play().catch(() => {});
  const tour = ownTour(s, c.band) || s.event;
  $(".caption", p).innerHTML = `${esc(bandOf(c))}${c.song ? " – " + esc(c.song) : ""}<br>
    <span class="meta">${esc(s.venue || "")} · ${fmtDate(s.date)} ${s.date.slice(0, 4)}${c.time ? " · " + c.time : ""}${tour ? " · " + esc(tour) : ""}</span>`;
}

function closePlayer() {
  const p = $("#player");
  $("video", p).pause();
  p.hidden = true;
}

function setView(view) {
  document.querySelectorAll("nav button").forEach(b => b.classList.toggle("on", b.dataset.view === view));
  $("#timeline").hidden = view !== "timeline";
  $("#map").hidden = view !== "map";
  if (view === "map") drawMap();
}

function drawMap() {
  if (!map) {
    map = L.map("map", { zoomControl: true, attributionControl: true });
    const dark = matchMedia("(prefers-color-scheme: dark)").matches;
    L.tileLayer(`https://{s}.basemaps.cartocdn.com/${dark ? "dark_all" : "light_all"}/{z}/{x}/{y}{r}.png`, {
      attribution: "&copy; OpenStreetMap &copy; CARTO", maxZoom: 19,
    }).addTo(map);
  }
  setTimeout(() => map.invalidateSize(), 0);
  if (mapLayer) mapLayer.remove();
  const terms = $("#q").value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const venues = {};
  for (const s of shows.filter(s => matches(s, terms))) {
    if (s.lat == null || !s.venue) continue;
    (venues[s.venue] ||= { lat: s.lat, lon: s.lon, shows: [] }).shows.push(s);
  }
  const fg = getComputedStyle(document.documentElement).getPropertyValue("--fg");
  mapLayer = L.featureGroup(Object.entries(venues).map(([name, v]) =>
    L.circleMarker([v.lat, v.lon], { radius: 4 + Math.sqrt(v.shows.length) * 3, color: fg, weight: 1, fillOpacity: 0.35 })
      .bindPopup(`<strong>${esc(name)}</strong><br>${v.shows.map(s =>
        `<a href="#" data-goto="${s.id}">${fmtDate(s.date)} ${s.date.slice(0, 4)}</a> ${esc(s.lineup.slice(0, 3).map(b => b.band).join(", "))}`).join("<br>")}`)
  )).addTo(map);
  if (Object.keys(venues).length) map.fitBounds(mapLayer.getBounds().pad(0.1), { maxZoom: 14 });
}

document.addEventListener("click", e => {
  const head = e.target.closest(".show-head");
  if (head) {
    const id = head.parentElement.dataset.id;
    open.has(id) ? open.delete(id) : open.add(id);
    render();
    return;
  }
  const t = e.target.closest(".thumb");
  if (t) return play(t.dataset.show, t.dataset.clip);
  const step = e.target.closest("[data-step]");
  if (step) { qi = (qi + +step.dataset.step + queue.length) % queue.length; return show(); }
  if (e.target.closest("[data-close]") || e.target.id === "player") return closePlayer();
  const v = e.target.closest("nav button");
  if (v) return setView(v.dataset.view);
  const go = e.target.closest("[data-goto]");
  if (go) {
    e.preventDefault();
    open.add(go.dataset.goto);
    setView("timeline");
    render();
    document.querySelector(`[data-id="${go.dataset.goto}"]`)?.scrollIntoView({ block: "center" });
  }
});

document.addEventListener("keydown", e => {
  const p = $("#player");
  if (!p.hidden) {
    if (e.key === "Escape") closePlayer();
    if (e.key === "ArrowRight") { qi = (qi + 1) % queue.length; show(); }
    if (e.key === "ArrowLeft") { qi = (qi - 1 + queue.length) % queue.length; show(); }
    return;
  }
  if (e.key === "Enter" && e.target.matches(".show-head, .thumb")) e.target.click();
});

$("video").addEventListener("ended", () => { if (qi < queue.length - 1) { qi++; show(); } });
$("#q").addEventListener("input", () => { render(); if (!$("#map").hidden) drawMap(); });

fetch("data/catalog.json?v=" + Date.now()).then(r => r.json()).then(data => {
  shows = data;
  shows.forEach(s => s._hay = haystack(s));
  const withVideo = shows.filter(s => s.clips.length);
  const bands = new Set(shows.flatMap(s => s.clips.map(c => c.band).filter(Boolean)));
  const years = shows.map(s => s.date.slice(0, 4));
  $("#stats").textContent = `${withVideo.length} filmed shows · ${shows.length - withVideo.length} more from tickets · ${bands.size} bands · ${shows.reduce((n, s) => n + s.clips.length, 0)} clips · ${years.at(-1)}–${years[0]}`;
  render();
});
