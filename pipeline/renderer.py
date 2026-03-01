"""
renderer.py — Renders per-day tabbed digest with hamburger calendar sidebar.
"""

import json
from datetime import date, timedelta
from filter import MatchResult

PAGE_SIZE = 5

CHIP_PALETTES = [
    ("#dbeafe", "#1d4ed8", "#93c5fd", "#3b82f6"),
    ("#dcfce7", "#15803d", "#86efac", "#22c55e"),
    ("#fef3c7", "#b45309", "#fcd34d", "#f59e0b"),
    ("#fce7f3", "#be185d", "#f9a8d4", "#ec4899"),
    ("#ede9fe", "#6d28d9", "#c4b5fd", "#8b5cf6"),
    ("#ccfbf1", "#0f766e", "#5eead4", "#14b8a6"),
]
IRRELEVANT = {"background": "#f1f5f9", "color": "#94a3b8", "borderColor": "#e2e8f0"}


def _authors_str(paper) -> str:
    s = ", ".join(paper.authors[:3])
    return s + " et al." if len(paper.authors) > 3 else s


def _pdf_url(paper) -> str:
    return f"https://arxiv.org/pdf/{paper.id}"


def _tab_label(d: date, today: date) -> str:
    delta = (today - d).days
    if delta == 0: return "Today"
    if delta == 1: return "Yesterday"
    return d.strftime("%b %d")


def render_html(
    results_by_date: dict[date, tuple[list[MatchResult], list[MatchResult]]],
    date_str: str,
    all_available_dates: list[date] | None = None,
) -> str:
    today = max(results_by_date.keys()) if results_by_date else date.today()

    # For the calendar: use all_available_dates if provided, else just what we have
    calendar_dates = sorted(all_available_dates or list(results_by_date.keys()), reverse=True)
    calendar_dates_js = json.dumps([d.isoformat() for d in calendar_dates])

    # Collect unique topic names across all days
    all_topics: list[str] = []
    seen_t: set[str] = set()
    for matched, _ in results_by_date.values():
        for r in matched:
            for t in r.matched_topics:
                if t not in seen_t:
                    all_topics.append(t)
                    seen_t.add(t)

    kw_palette      = {t: i % len(CHIP_PALETTES) for i, t in enumerate(all_topics)}
    active_styles   = {
        t: {"background": CHIP_PALETTES[kw_palette[t]][0],
            "color":       CHIP_PALETTES[kw_palette[t]][1],
            "borderColor": CHIP_PALETTES[kw_palette[t]][2]}
        for t in all_topics
    }
    inactive_styles = {
        t: {"background": "#f1f5f9", "color": "#94a3b8", "borderColor": "#e2e8f0"}
        for t in all_topics
    }
    accent_colors   = {t: CHIP_PALETTES[kw_palette[t]][3] for t in all_topics}

    # Per-day data
    days_data = []
    for d in sorted(results_by_date.keys(), reverse=True):
        matched, unmatched = results_by_date[d]
        days_data.append({
            "date":  d.isoformat(),
            "label": _tab_label(d, today),
            "matched": [{
                "id": r.paper.id, "title": r.paper.title,
                "abstract": r.paper.abstract, "authors": _authors_str(r.paper),
                "url": _pdf_url(r.paper), "topics": r.matched_topics,
                "score": r.best_semantic_score,
            } for r in matched],
            "unmatched": [{
                "id": r.paper.id, "title": r.paper.title,
                "abstract": r.paper.abstract, "authors": _authors_str(r.paper),
                "url": _pdf_url(r.paper), "score": round(r.best_semantic_score, 3),
            } for r in unmatched],
        })

    days_js        = json.dumps(days_data,      ensure_ascii=False)
    topics_js      = json.dumps(all_topics)
    active_js      = json.dumps(active_styles)
    inactive_js    = json.dumps(inactive_styles)
    accents_js     = json.dumps(accent_colors)
    irrelevant_js  = json.dumps(IRRELEVANT)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>arXiv Digest · {date_str}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #f8fafc;
      color: #1e293b;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 15px; line-height: 1.65; min-height: 100vh;
      overflow-x: hidden;
    }}

    /* ── Sidebar overlay ── */
    .sidebar-overlay {{
      display: none; position: fixed; inset: 0;
      background: rgba(0,0,0,0.3); z-index: 200; backdrop-filter: blur(2px);
    }}
    .sidebar-overlay.open {{ display: block; }}

    /* ── Sidebar panel ── */
    .sidebar {{
      position: fixed; top: 0; left: 0; bottom: 0;
      width: 300px; background: #fff;
      border-right: 1px solid #e2e8f0;
      box-shadow: 4px 0 24px rgba(0,0,0,0.1);
      z-index: 201; transform: translateX(-100%);
      transition: transform 0.25s cubic-bezier(0.4,0,0.2,1);
      display: flex; flex-direction: column;
    }}
    .sidebar.open {{ transform: translateX(0); }}

    .sidebar-header {{
      padding: 20px 20px 16px;
      border-bottom: 1px solid #f1f5f9;
      display: flex; align-items: center; justify-content: space-between;
    }}
    .sidebar-title {{
      font-size: 13px; font-weight: 700; color: #0f172a; letter-spacing: -0.2px;
    }}
    .sidebar-close {{
      background: none; border: none; cursor: pointer;
      color: #94a3b8; font-size: 18px; line-height: 1; padding: 2px;
    }}
    .sidebar-close:hover {{ color: #475569; }}

    .sidebar-body {{ flex: 1; overflow-y: auto; padding: 16px 20px 24px; }}

    /* ── Calendar ── */
    .cal-month {{ margin-bottom: 24px; }}
    .cal-month-label {{
      font-size: 11px; font-weight: 700; letter-spacing: 0.12em;
      text-transform: uppercase; color: #94a3b8; margin-bottom: 10px;
    }}
    .cal-grid {{
      display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px;
    }}
    .cal-dow {{
      font-size: 10px; font-weight: 600; color: #cbd5e1;
      text-align: center; padding: 3px 0;
    }}
    .cal-day {{
      font-size: 12px; text-align: center;
      padding: 5px 2px; border-radius: 6px;
      color: #cbd5e1; cursor: default;
    }}
    .cal-day.has-data {{
      color: #475569; font-weight: 600; cursor: pointer;
      background: #f8fafc;
    }}
    .cal-day.has-data:hover {{ background: #dbeafe; color: #1d4ed8; }}
    .cal-day.today {{
      background: #3b82f6; color: #fff !important; font-weight: 700;
    }}
    .cal-day.today:hover {{ background: #2563eb; }}
    .cal-day.empty {{ visibility: hidden; }}

    /* ── Sticky header ── */
    .sticky-top {{
      position: sticky; top: 0; z-index: 100;
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      padding: 14px 24px 0;
      box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    }}
    .header-inner {{ max-width: 800px; margin: 0 auto; }}
    .header-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }}
    .hamburger {{
      background: none; border: none; cursor: pointer;
      color: #94a3b8; padding: 4px; border-radius: 6px;
      font-size: 18px; line-height: 1; flex-shrink: 0;
      transition: color 0.15s, background 0.15s;
    }}
    .hamburger:hover {{ color: #475569; background: #f1f5f9; }}
    .header-label {{
      font-size: 10px; font-weight: 700; letter-spacing: 0.18em;
      text-transform: uppercase; color: #94a3b8;
    }}
    .header-title {{
      font-size: 20px; font-weight: 700; color: #0f172a; letter-spacing: -0.4px;
    }}
    .header-meta {{ font-size: 13px; color: #94a3b8; margin-left: auto; }}

    /* ── Tabs ── */
    .tab-bar {{
      display: flex; gap: 0; overflow-x: auto;
      scrollbar-width: none; margin-top: 4px;
    }}
    .tab-bar::-webkit-scrollbar {{ display: none; }}
    .tab {{
      padding: 10px 18px; font-size: 13px; font-weight: 600; color: #94a3b8;
      border-bottom: 2px solid transparent; cursor: pointer; white-space: nowrap;
      transition: all 0.15s; user-select: none;
      background: none; border-top: none; border-left: none; border-right: none;
    }}
    .tab:hover {{ color: #475569; }}
    .tab.active {{ color: #3b82f6; border-bottom-color: #3b82f6; }}
    .tab-count {{
      display: inline-block; margin-left: 5px; font-size: 11px; font-weight: 700;
      background: #f1f5f9; color: #94a3b8; padding: 1px 6px;
      border-radius: 999px; vertical-align: middle;
    }}
    .tab.active .tab-count {{ background: #dbeafe; color: #3b82f6; }}

    /* ── Filter chips ── */
    .filter-bar {{
      display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 24px;
      max-width: 800px; margin: 0 auto;
    }}
    .chip {{
      cursor: pointer; padding: 6px 16px; border-radius: 999px;
      font-size: 12px; font-weight: 600; border: 1.5px solid;
      transition: all 0.15s; user-select: none;
    }}
    .chip:hover {{ filter: brightness(0.95); }}

    /* ── Content ── */
    .content {{ max-width: 800px; margin: 0 auto; padding: 20px 24px 80px; }}

    /* ── Section divider ── */
    .section-divider {{
      display: flex; align-items: center; gap: 12px; margin: 36px 0 18px;
    }}
    .section-divider-line {{ flex: 1; height: 1px; background: #e2e8f0; }}
    .section-divider-label {{
      font-size: 11px; font-weight: 700; letter-spacing: 0.14em;
      text-transform: uppercase; color: #cbd5e1; white-space: nowrap;
    }}

    /* ── Paper card ── */
    .paper {{
      border: 1px solid #e2e8f0; border-left: 4px solid #cbd5e1;
      border-radius: 10px; padding: 22px 24px; margin-bottom: 14px;
      background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      transition: box-shadow 0.15s;
    }}
    .paper:hover {{ box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
    .paper.irrelevant {{ background: #fafafa; opacity: 0.75; }}
    .paper.irrelevant:hover {{ opacity: 1; }}
    .paper-title {{
      font-size: 17px; font-weight: 700; color: #0f172a;
      text-decoration: none; line-height: 1.4; display: block; margin-bottom: 6px;
    }}
    .paper-title:hover {{ color: #3b82f6; }}
    .paper-authors {{ font-size: 13px; color: #94a3b8; margin-bottom: 12px; }}
    .abstract-preview, .abstract-full {{
      font-size: 15px; color: #475569; line-height: 1.7;
    }}
    .abstract-full {{ display: none; }}
    .expand-btn {{
      background: none; border: none; cursor: pointer;
      font-size: 12px; font-weight: 600; color: #3b82f6;
      padding: 0; margin-top: 8px; display: block;
    }}
    .expand-btn:hover {{ color: #1d4ed8; }}
    .paper-footer {{
      display: flex; align-items: center; gap: 6px; margin-top: 16px; flex-wrap: wrap;
    }}
    .topic-chip {{
      font-size: 11px; font-weight: 600; padding: 3px 10px;
      border-radius: 999px; border: 1.5px solid;
    }}
    .score-badge {{ font-size: 11px; color: #cbd5e1; margin-left: 4px; }}
    .pdf-link {{
      margin-left: auto; font-size: 12px; font-weight: 600;
      color: #64748b; text-decoration: none;
    }}
    .pdf-link:hover {{ color: #3b82f6; }}

    /* ── Pagination ── */
    .pagination {{
      display: flex; align-items: center; justify-content: center;
      gap: 6px; margin-top: 28px;
    }}
    .page-btn {{
      background: #fff; border: 1px solid #e2e8f0; color: #64748b;
      border-radius: 8px; padding: 7px 14px; font-size: 13px;
      font-weight: 500; cursor: pointer; transition: all 0.15s;
    }}
    .page-btn:hover {{ border-color: #93c5fd; color: #1d4ed8; background: #eff6ff; }}
    .page-btn.active {{ border-color: #3b82f6; background: #3b82f6; color: #fff; font-weight: 700; }}
    .page-btn:disabled {{ opacity: 0.35; cursor: default; }}
    .page-info {{ font-size: 13px; color: #cbd5e1; padding: 0 4px; }}
    .empty {{ text-align: center; color: #94a3b8; padding: 48px 0; font-size: 14px; }}
  </style>
</head>
<body>

<!-- Sidebar overlay (click to close) -->
<div class="sidebar-overlay" id="overlay" onclick="closeSidebar()"></div>

<!-- Sidebar -->
<div class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <span class="sidebar-title">📅 Browse by Date</span>
    <button class="sidebar-close" onclick="closeSidebar()">✕</button>
  </div>
  <div class="sidebar-body" id="calendar-body"></div>
</div>

<!-- Sticky header -->
<div class="sticky-top">
  <div class="header-inner">
    <div class="header-row">
      <button class="hamburger" onclick="openSidebar()" title="Browse history">☰</button>
      <div>
        <div class="header-label">arXiv Digest</div>
        <div class="header-title">{date_str}</div>
      </div>
      <span class="header-meta" id="meta-count"></span>
    </div>
    <div class="tab-bar" id="tab-bar"></div>
  </div>
</div>

<div class="filter-bar" id="filter-bar"></div>

<div class="content">
  <div id="matched-list"></div>
  <div class="pagination" id="matched-pagination"></div>
  <div class="section-divider">
    <div class="section-divider-line"></div>
    <div class="section-divider-label">Filtered out · sorted by relevance</div>
    <div class="section-divider-line"></div>
  </div>
  <div id="unmatched-list"></div>
  <div class="pagination" id="unmatched-pagination"></div>
</div>

<script>
const DAYS          = {days_js};
const ALL_TOPICS    = {topics_js};
const ACTIVE_ST     = {active_js};
const INACTIVE_ST   = {inactive_js};
const ACCENTS       = {accents_js};
const IRREL         = {irrelevant_js};
const CALENDAR_DATES = {calendar_dates_js};
const PAGE_SIZE     = {PAGE_SIZE};

let activeTab     = 0;
let activeTopics  = new Set(ALL_TOPICS);
let matchedPage   = 1;
let unmatchedPage = 1;

// ── Sidebar ───────────────────────────────────────────────────────────────────
function openSidebar() {{
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}}
function closeSidebar() {{
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('open');
  document.body.style.overflow = '';
}}

// ── Calendar builder ──────────────────────────────────────────────────────────
(function buildCalendar() {{
  if (!CALENDAR_DATES.length) return;

  const hasData  = new Set(CALENDAR_DATES);
  const todayStr = CALENDAR_DATES[0];   // newest = today
  const today    = new Date(todayStr + 'T00:00:00');

  // Group dates by year-month
  const months = {{}};
  CALENDAR_DATES.forEach(d => {{
    const key = d.slice(0, 7);   // "YYYY-MM"
    if (!months[key]) months[key] = [];
    months[key].push(d);
  }});

  const body = document.getElementById('calendar-body');
  const DOWS = ['Su','Mo','Tu','We','Th','Fr','Sa'];

  Object.keys(months).sort().reverse().forEach(ym => {{
    const [y, m] = ym.split('-').map(Number);
    const label  = new Date(y, m-1, 1).toLocaleString('en-US', {{month:'long', year:'numeric'}});
    const firstDow = new Date(y, m-1, 1).getDay();
    const daysInMonth = new Date(y, m, 0).getDate();

    const block = document.createElement('div');
    block.className = 'cal-month';
    block.innerHTML = `<div class="cal-month-label">${{label}}</div>`;

    const grid = document.createElement('div');
    grid.className = 'cal-grid';

    // Day-of-week headers
    DOWS.forEach(d => {{
      const h = document.createElement('div');
      h.className = 'cal-dow'; h.textContent = d;
      grid.appendChild(h);
    }});

    // Empty cells before first day
    for (let i = 0; i < firstDow; i++) {{
      const e = document.createElement('div');
      e.className = 'cal-day empty'; grid.appendChild(e);
    }}

    // Day cells
    for (let day = 1; day <= daysInMonth; day++) {{
      const dateStr = `${{y}}-${{String(m).padStart(2,'0')}}-${{String(day).padStart(2,'0')}}`;
      const cell = document.createElement('div');
      cell.textContent = day;

      if (dateStr === todayStr) {{
        cell.className = 'cal-day today';
        cell.title = 'Today';
        cell.onclick = () => {{ closeSidebar(); }};
      }} else if (hasData.has(dateStr)) {{
        cell.className = 'cal-day has-data';
        cell.title = dateStr;
        cell.onclick = () => {{
          closeSidebar();
          window.location.href = `date.html#${{dateStr}}`;
        }};
      }} else {{
        cell.className = 'cal-day';
      }}
      grid.appendChild(cell);
    }}

    block.appendChild(grid);
    body.appendChild(block);
  }});
}})();

// ── Tabs ──────────────────────────────────────────────────────────────────────
const tabBar = document.getElementById('tab-bar');
DAYS.forEach((day, i) => {{
  const btn = document.createElement('button');
  btn.className = 'tab' + (i === 0 ? ' active' : '');
  btn.innerHTML = day.label + `<span class="tab-count">${{day.matched.length}}</span>`;
  btn.addEventListener('click', () => {{
    activeTab = i; matchedPage = 1; unmatchedPage = 1;
    document.querySelectorAll('.tab').forEach((t, j) => t.classList.toggle('active', j === i));
    renderAll();
  }});
  tabBar.appendChild(btn);
}});

// ── Filter chips ──────────────────────────────────────────────────────────────
const filterBar = document.getElementById('filter-bar');
ALL_TOPICS.forEach(t => {{
  const btn = document.createElement('button');
  btn.className = 'chip'; btn.textContent = t;
  applyChipStyle(btn, t, true);
  btn.addEventListener('click', () => {{
    activeTopics.has(t) ? activeTopics.delete(t) : activeTopics.add(t);
    applyChipStyle(btn, t, activeTopics.has(t));
    matchedPage = 1; renderAll();
  }});
  filterBar.appendChild(btn);
}});

function applyChipStyle(el, t, on) {{
  const s = on ? ACTIVE_ST[t] : INACTIVE_ST[t];
  el.style.background = s.background; el.style.color = s.color;
  el.style.borderColor = s.borderColor;
}}

// ── Card ──────────────────────────────────────────────────────────────────────
function buildCard(p, irrel) {{
  const preview = p.abstract.slice(0, 320) + (p.abstract.length > 320 ? '…' : '');
  const hasMore = p.abstract.length > 320;
  const accent  = irrel ? '#e2e8f0' : (ACCENTS[p.topics && p.topics[0]] || '#cbd5e1');
  const chips   = irrel
    ? `<span class="topic-chip" style="background:${{IRREL.background}};color:${{IRREL.color}};border-color:${{IRREL.borderColor}}">irrelevant</span><span class="score-badge">score ${{p.score}}</span>`
    : p.topics.map(t => {{
        const s = ACTIVE_ST[t] || {{}};
        return `<span class="topic-chip" style="background:${{s.background}};color:${{s.color}};border-color:${{s.borderColor}}">${{t}}</span>`;
      }}).join('');

  const card = document.createElement('div');
  card.className = 'paper' + (irrel ? ' irrelevant' : '');
  card.style.borderLeftColor = accent;
  card.innerHTML = `
    <a class="paper-title" href="${{p.url}}" target="_blank">${{p.title}}</a>
    <div class="paper-authors">${{p.authors}}</div>
    <div class="abstract-preview" id="pv-${{p.id}}">${{preview}}</div>
    ${{hasMore ? `<div class="abstract-full" id="fl-${{p.id}}">${{p.abstract}}</div>
      <button class="expand-btn" id="btn-${{p.id}}" onclick="toggle('${{p.id}}')">Show more ↓</button>` : ''}}
    <div class="paper-footer">${{chips}}<a class="pdf-link" href="${{p.url}}" target="_blank">PDF →</a></div>
  `;
  return card;
}}

// ── Render ────────────────────────────────────────────────────────────────────
function renderAll() {{
  const day      = DAYS[activeTab];
  const filtered = day.matched.filter(p => p.topics.some(t => activeTopics.has(t)));

  document.getElementById('meta-count').textContent =
    filtered.length + ' matched · ' + day.unmatched.length + ' unmatched';

  const mList = document.getElementById('matched-list');
  mList.innerHTML = '';
  if (!filtered.length) {{
    mList.innerHTML = '<div class="empty">No papers match the selected topics.</div>';
  }} else {{
    filtered.slice((matchedPage-1)*PAGE_SIZE, matchedPage*PAGE_SIZE)
      .forEach(p => mList.appendChild(buildCard(p, false)));
  }}
  renderPagination('matched-pagination', filtered.length, matchedPage,
    p => {{ matchedPage = p; renderAll(); scrollTo(0,0); }});

  const uList = document.getElementById('unmatched-list');
  uList.innerHTML = '';
  day.unmatched.slice((unmatchedPage-1)*PAGE_SIZE, unmatchedPage*PAGE_SIZE)
    .forEach(p => uList.appendChild(buildCard(p, true)));
  renderPagination('unmatched-pagination', day.unmatched.length, unmatchedPage,
    p => {{ unmatchedPage = p; renderAll(); scrollTo(0,0); }});
}}

// ── Expand ────────────────────────────────────────────────────────────────────
function toggle(id) {{
  const pv = document.getElementById('pv-' + id);
  const fl = document.getElementById('fl-' + id);
  const b  = document.getElementById('btn-' + id);
  const ex = fl.style.display === 'block';
  pv.style.display = ex ? 'block' : 'none';
  fl.style.display = ex ? 'none'  : 'block';
  b.textContent    = ex ? 'Show more ↓' : 'Show less ↑';
}}

// ── Pagination ────────────────────────────────────────────────────────────────
function renderPagination(id, total, current, onPage) {{
  const pages = Math.ceil(total / PAGE_SIZE);
  const c = document.getElementById(id);
  c.innerHTML = '';
  if (pages <= 1) return;

  const prev = document.createElement('button');
  prev.className = 'page-btn'; prev.textContent = '← Prev';
  prev.disabled = current === 1;
  prev.onclick = () => onPage(current - 1);
  c.appendChild(prev);

  const range = [];
  for (let i = 1; i <= pages; i++) {{
    if (i===1 || i===pages || Math.abs(i-current)<=2) range.push(i);
    else if (range[range.length-1] !== '…') range.push('…');
  }}
  range.forEach(item => {{
    if (item === '…') {{
      const s = document.createElement('span');
      s.className = 'page-info'; s.textContent = '…'; c.appendChild(s);
    }} else {{
      const b = document.createElement('button');
      b.className = 'page-btn' + (item===current ? ' active' : '');
      b.textContent = item;
      b.onclick = () => onPage(item);
      c.appendChild(b);
    }}
  }});

  const next = document.createElement('button');
  next.className = 'page-btn'; next.textContent = 'Next →';
  next.disabled = current === pages;
  next.onclick = () => onPage(current + 1);
  c.appendChild(next);
}}

renderAll();
</script>
</body>
</html>"""