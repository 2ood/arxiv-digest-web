/**
 * display.js — Shared rendering logic for index.html and date.html.
 *
 * Expects on window:
 *   DigestDisplay.init(config) — called by each page after loading data
 *
 * Data contract (papers in JSON):
 *   { id, title, abstract, authors[], url, matched_topics[], best_score }
 */

const DigestDisplay = (() => {

  // ── Constants ──────────────────────────────────────────────────────────────
  const PAGE_SIZE = 5;

  const CHIP_PALETTES = [
    ["#dbeafe","#1d4ed8","#93c5fd","#3b82f6"],
    ["#dcfce7","#15803d","#86efac","#22c55e"],
    ["#fef3c7","#b45309","#fcd34d","#f59e0b"],
    ["#fce7f3","#be185d","#f9a8d4","#ec4899"],
    ["#ede9fe","#6d28d9","#c4b5fd","#8b5cf6"],
    ["#ccfbf1","#0f766e","#5eead4","#14b8a6"],
  ];

  const IRREL_STYLE = {
    background: "#f1f5f9", color: "#94a3b8", borderColor: "#e2e8f0"
  };

  // ── Topic style maps (built once per page load) ───────────────────────────
  let activeStyles   = {};
  let inactiveStyles = {};
  let accentColors   = {};
  let allTopics      = [];

  function buildTopicStyles(topics) {
    allTopics = topics;
    topics.forEach((t, i) => {
      const pal = CHIP_PALETTES[i % CHIP_PALETTES.length];
      activeStyles[t]   = { background: pal[0], color: pal[1], borderColor: pal[2] };
      inactiveStyles[t] = { background: "#f1f5f9", color: "#94a3b8", borderColor: "#e2e8f0" };
      accentColors[t]   = pal[3];
    });
  }

  // ── Sidebar ────────────────────────────────────────────────────────────────
  function openSidebar() {
    document.getElementById("sidebar").classList.add("open");
    document.getElementById("overlay").classList.add("open");
    document.body.style.overflow = "hidden";
  }

  function closeSidebar() {
    document.getElementById("sidebar").classList.remove("open");
    document.getElementById("overlay").classList.remove("open");
    document.body.style.overflow = "";
  }

  // ── Calendar ───────────────────────────────────────────────────────────────
  // availableDatesHierarchy: { "2026": { "02": ["27","26",...], "01": [...] }, ... }
  // todayStr: "2026-02-27"
  // onDateClick: function(dateStr) — what to do when a date is clicked
  function buildCalendar(availableDatesHierarchy, todayStr, onDateClick) {
    const body = document.getElementById("calendar-body");
    if (!body) return;
    body.innerHTML = "";

    // Flatten to a Set for O(1) lookup
    const hasData = new Set();
    Object.entries(availableDatesHierarchy).forEach(([y, months]) => {
      Object.entries(months).forEach(([m, days]) => {
        days.forEach(d => hasData.add(`${y}-${m}-${d}`));
      });
    });

    const DOWS = ["Su","Mo","Tu","We","Th","Fr","Sa"];

    // Build months in reverse chronological order
    const monthKeys = [];
    Object.entries(availableDatesHierarchy).forEach(([y, months]) => {
      Object.keys(months).forEach(m => monthKeys.push(`${y}-${m}`));
    });
    monthKeys.sort().reverse();

    monthKeys.forEach(ym => {
      const [y, m] = ym.split("-").map(Number);
      const label = new Date(y, m-1, 1)
        .toLocaleString("en-US", { month: "long", year: "numeric" });
      const firstDow   = new Date(y, m-1, 1).getDay();
      const daysInMonth = new Date(y, m, 0).getDate();

      const block = document.createElement("div");
      block.className = "cal-month";
      block.innerHTML = `<div class="cal-month-label">${label}</div>`;

      const grid = document.createElement("div");
      grid.className = "cal-grid";

      DOWS.forEach(d => {
        const h = document.createElement("div");
        h.className = "cal-dow"; h.textContent = d;
        grid.appendChild(h);
      });

      for (let i = 0; i < firstDow; i++) {
        const e = document.createElement("div");
        e.className = "cal-day empty"; grid.appendChild(e);
      }

      for (let day = 1; day <= daysInMonth; day++) {
        const ds = `${y}-${String(m).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
        const cell = document.createElement("div");
        cell.textContent = day;

        if (ds === todayStr) {
          cell.className = "cal-day is-today has-data";
          cell.onclick = () => { closeSidebar(); onDateClick(ds); };
        } else if (hasData.has(ds)) {
          cell.className = "cal-day has-data";
          cell.onclick = () => { closeSidebar(); onDateClick(ds); };
        } else {
          cell.className = "cal-day";
        }
        grid.appendChild(cell);
      }

      block.appendChild(grid);
      body.appendChild(block);
    });
  }

  // ── Filter chips ───────────────────────────────────────────────────────────
  function buildFilterChips(containerId, activeTopics, onToggle) {
    const bar = document.getElementById(containerId);
    if (!bar) return;
    bar.innerHTML = "";

    allTopics.forEach(t => {
      const btn = document.createElement("button");
      btn.className = "chip";
      btn.textContent = t;
      _applyChipStyle(btn, t, activeTopics.has(t));
      btn.addEventListener("click", () => {
        activeTopics.has(t) ? activeTopics.delete(t) : activeTopics.add(t);
        _applyChipStyle(btn, t, activeTopics.has(t));
        onToggle();
      });
      bar.appendChild(btn);
    });
  }

  function _applyChipStyle(el, t, on) {
    const s = on ? (activeStyles[t] || IRREL_STYLE) : (inactiveStyles[t] || IRREL_STYLE);
    el.style.background  = s.background;
    el.style.color       = s.color;
    el.style.borderColor = s.borderColor;
  }

  // ── Paper card ─────────────────────────────────────────────────────────────
  function buildCard(p, isIrrelevant) {
    const preview = p.abstract.slice(0, 320) + (p.abstract.length > 320 ? "…" : "");
    const hasMore = p.abstract.length > 320;
    const accent  = isIrrelevant
      ? "#e2e8f0"
      : (accentColors[p.matched_topics && p.matched_topics[0]] || "#cbd5e1");

    const chips = isIrrelevant
      ? `<span class="topic-chip" style="background:${IRREL_STYLE.background};color:${IRREL_STYLE.color};border-color:${IRREL_STYLE.borderColor}">irrelevant</span>
         <span class="score-badge">score ${p.best_score}</span>`
      : (p.matched_topics || []).map(t => {
          const s = activeStyles[t] || IRREL_STYLE;
          return `<span class="topic-chip" style="background:${s.background};color:${s.color};border-color:${s.borderColor}">${t}</span>`;
        }).join("");

    const authorsArr = p.authors || [];
    const authorsStr = authorsArr.slice(0, 3).join(", ") + (authorsArr.length > 3 ? " et al." : "");
    const uid = p.id.replace(/[^a-zA-Z0-9]/g, "-");

    const card = document.createElement("div");
    card.className = "paper" + (isIrrelevant ? " irrelevant" : "");
    card.style.borderLeftColor = accent;
    card.innerHTML = `
      <a class="paper-title" href="${p.url}" target="_blank">${p.title}</a>
      <div class="paper-authors">${authorsStr}</div>
      <div class="abstract-preview" id="pv-${uid}">${preview}</div>
      ${hasMore ? `
        <div class="abstract-full" id="fl-${uid}">${p.abstract}</div>
        <button class="expand-btn" id="btn-${uid}" onclick="DigestDisplay.toggle('${uid}')">Show more ↓</button>
      ` : ""}
      <div class="paper-footer">${chips}<a class="pdf-link" href="${p.url}" target="_blank">PDF →</a></div>
    `;
    return card;
  }

  // ── Expand/collapse abstract ───────────────────────────────────────────────
  function toggle(uid) {
    const pv  = document.getElementById("pv-"  + uid);
    const fl  = document.getElementById("fl-"  + uid);
    const btn = document.getElementById("btn-" + uid);
    if (!fl) return;
    const expanded = fl.style.display === "block";
    pv.style.display  = expanded ? "block" : "none";
    fl.style.display  = expanded ? "none"  : "block";
    btn.textContent   = expanded ? "Show more ↓" : "Show less ↑";
  }

  // ── Render paper lists (matched + unmatched) ───────────────────────────────
  // matchedListId, unmatchedListId: DOM ids for list containers
  // matchedPagId, unmatchedPagId:   DOM ids for pagination containers
  // matchedPapers: papers with matched_topics (already filtered by topic toggles)
  // unmatchedPapers: papers with no matched_topics
  // pages: { matched: int, unmatched: int }
  // onPage: function(which, page) — "matched" | "unmatched"
  function renderLists({ matchedListId, unmatchedListId, matchedPagId, unmatchedPagId,
                         matchedPapers, unmatchedPapers, pages, onPage }) {
    // Matched
    const mList = document.getElementById(matchedListId);
    if (mList) {
      mList.innerHTML = "";
      if (!matchedPapers.length) {
        mList.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:48px 0;font-size:14px">No papers match the selected topics.</div>';
      } else {
        matchedPapers
          .slice((pages.matched - 1) * PAGE_SIZE, pages.matched * PAGE_SIZE)
          .forEach(p => mList.appendChild(buildCard(p, false)));
      }
    }
    renderPagination(matchedPagId, matchedPapers.length, pages.matched,
      pg => onPage("matched", pg));

    // Unmatched
    const uList = document.getElementById(unmatchedListId);
    if (uList) {
      uList.innerHTML = "";
      unmatchedPapers
        .slice((pages.unmatched - 1) * PAGE_SIZE, pages.unmatched * PAGE_SIZE)
        .forEach(p => uList.appendChild(buildCard(p, true)));
    }
    renderPagination(unmatchedPagId, unmatchedPapers.length, pages.unmatched,
      pg => onPage("unmatched", pg));
  }

  // ── Pagination ─────────────────────────────────────────────────────────────
  function renderPagination(containerId, total, current, onPage) {
    const pages = Math.ceil(total / PAGE_SIZE);
    const c = document.getElementById(containerId);
    if (!c) return;
    c.innerHTML = "";
    if (pages <= 1) return;

    const prev = document.createElement("button");
    prev.className = "page-btn"; prev.textContent = "← Prev";
    prev.disabled = current === 1;
    prev.onclick = () => onPage(current - 1);
    c.appendChild(prev);

    const range = [];
    for (let i = 1; i <= pages; i++) {
      if (i===1 || i===pages || Math.abs(i-current)<=2) range.push(i);
      else if (range[range.length-1] !== "…") range.push("…");
    }
    range.forEach(item => {
      if (item === "…") {
        const s = document.createElement("span");
        s.className = "page-info"; s.textContent = "…"; c.appendChild(s);
      } else {
        const b = document.createElement("button");
        b.className = "page-btn" + (item===current ? " active" : "");
        b.textContent = item;
        b.onclick = () => onPage(item);
        c.appendChild(b);
      }
    });

    const next = document.createElement("button");
    next.className = "page-btn"; next.textContent = "Next →";
    next.disabled = current === pages;
    next.onclick = () => onPage(current + 1);
    c.appendChild(next);
  }

  // ── Loading / error helpers ────────────────────────────────────────────────
  function showLoading(containerId) {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = '<div class="loading"><div class="spinner"></div>Loading…</div>';
  }

  function showError(containerId, title, msg) {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = `<div class="state"><h2>${title}</h2><p>${msg}</p></div>`;
  }

  // ── Public API ─────────────────────────────────────────────────────────────
  return {
    buildTopicStyles,
    buildCalendar,
    buildFilterChips,
    buildCard,
    toggle,
    renderLists,
    renderPagination,
    openSidebar,
    closeSidebar,
    showLoading,
    showError,
  };

})();
