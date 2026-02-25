"""
renderer.py — Renders matched papers as a fully interactive static HTML page.
No email, no server — just a self-contained index.html.
"""

import json
from filter import MatchResult

PAGE_SIZE = 5

CHIP_PALETTES = [
    ("#dbeafe", "#1d4ed8", "#93c5fd", "#3b82f6"),  # blue
    ("#dcfce7", "#15803d", "#86efac", "#22c55e"),  # green
    ("#fef3c7", "#b45309", "#fcd34d", "#f59e0b"),  # amber
    ("#fce7f3", "#be185d", "#f9a8d4", "#ec4899"),  # pink
    ("#ede9fe", "#6d28d9", "#c4b5fd", "#8b5cf6"),  # violet
    ("#ccfbf1", "#0f766e", "#5eead4", "#14b8a6"),  # teal
]


def _authors_str(paper) -> str:
    s = ", ".join(paper.authors[:3])
    return s + " et al." if len(paper.authors) > 3 else s


def _pdf_url(paper) -> str:
    return f"https://arxiv.org/pdf/{paper.id}"


def render_html(results: list[MatchResult], date_str: str) -> str:
    # Collect unique topic names in order of first appearance
    all_topics: list[str] = []
    seen: set[str] = set()
    for r in results:
        for t in r.matched_topics:
            if t not in seen:
                all_topics.append(t)
                seen.add(t)

    # Assign palette per topic
    kw_palette = {t: i % len(CHIP_PALETTES) for i, t in enumerate(all_topics)}

    active_styles = {
        t: {"background": CHIP_PALETTES[kw_palette[t]][0],
            "color":      CHIP_PALETTES[kw_palette[t]][1],
            "borderColor":CHIP_PALETTES[kw_palette[t]][2]}
        for t in all_topics
    }
    inactive_styles = {
        t: {"background": "#f1f5f9", "color": "#94a3b8", "borderColor": "#e2e8f0"}
        for t in all_topics
    }
    accent_colors = {t: CHIP_PALETTES[kw_palette[t]][3] for t in all_topics}

    active_styles_js  = json.dumps(active_styles)
    inactive_styles_js = json.dumps(inactive_styles)
    accent_colors_js  = json.dumps(accent_colors)

    # Build paper data for JS
    papers_data = [
        {
            "id":       r.paper.id,
            "title":    r.paper.title,
            "abstract": r.paper.abstract,
            "authors":  _authors_str(r.paper),
            "url":      _pdf_url(r.paper),
            "topics":   r.matched_topics,
        }
        for r in results
    ]
    papers_js  = json.dumps(papers_data, ensure_ascii=False)
    topics_js  = json.dumps(all_topics)
    total      = len(results)

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
      font-size: 15px;
      line-height: 1.65;
      min-height: 100vh;
    }}

    /* ── Sticky header ── */
    .sticky-top {{
      position: sticky; top: 0; z-index: 100;
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      padding: 14px 24px 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    }}
    .header-inner {{ max-width: 800px; margin: 0 auto; }}
    .header-row {{
      display: flex; align-items: baseline; gap: 14px; margin-bottom: 12px;
    }}
    .header-label {{
      font-size: 10px; font-weight: 700; letter-spacing: 0.18em;
      text-transform: uppercase; color: #94a3b8;
    }}
    .header-title {{
      font-size: 20px; font-weight: 700; color: #0f172a; letter-spacing: -0.4px;
    }}
    .header-meta {{ font-size: 13px; color: #94a3b8; margin-left: auto; }}

    /* ── Filter chips ── */
    .filter-bar {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .chip {{
      cursor: pointer; padding: 6px 16px; border-radius: 999px;
      font-size: 12px; font-weight: 600; border: 1.5px solid;
      transition: all 0.15s; user-select: none; letter-spacing: 0.02em;
    }}
    .chip:hover {{ filter: brightness(0.95); }}

    /* ── Content ── */
    .content {{ max-width: 800px; margin: 0 auto; padding: 28px 24px 80px; }}

    /* ── Paper card ── */
    .paper {{
      border: 1px solid #e2e8f0;
      border-left: 4px solid #cbd5e1;
      border-radius: 10px;
      padding: 22px 24px;
      margin-bottom: 14px;
      background: #fff;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      transition: box-shadow 0.15s;
    }}
    .paper:hover {{ box-shadow: 0 4px 16px rgba(0,0,0,0.08); }}
    .paper-title {{
      font-size: 17px; font-weight: 700; color: #0f172a;
      text-decoration: none; line-height: 1.4; display: block; margin-bottom: 6px;
    }}
    .paper-title:hover {{ color: #3b82f6; }}
    .paper-authors {{ font-size: 13px; color: #94a3b8; margin-bottom: 12px; }}
    .abstract-preview {{ font-size: 15px; color: #475569; line-height: 1.7; }}
    .abstract-full   {{ font-size: 15px; color: #475569; line-height: 1.7; display: none; }}
    .expand-btn {{
      background: none; border: none; cursor: pointer;
      font-size: 12px; font-weight: 600; color: #3b82f6;
      padding: 0; margin-top: 8px; display: block;
    }}
    .expand-btn:hover {{ color: #1d4ed8; }}
    .paper-footer {{
      display: flex; align-items: center; gap: 6px;
      margin-top: 16px; flex-wrap: wrap;
    }}
    .topic-chip {{
      font-size: 11px; font-weight: 600; padding: 3px 10px;
      border-radius: 999px; border: 1.5px solid;
    }}
    .pdf-link {{
      margin-left: auto; font-size: 12px; font-weight: 600;
      color: #64748b; text-decoration: none;
    }}
    .pdf-link:hover {{ color: #3b82f6; }}

    /* ── Pagination ── */
    .pagination {{
      display: flex; align-items: center; justify-content: center;
      gap: 6px; margin-top: 36px;
    }}
    .page-btn {{
      background: #fff; border: 1px solid #e2e8f0; color: #64748b;
      border-radius: 8px; padding: 7px 14px; font-size: 13px;
      font-weight: 500; cursor: pointer; transition: all 0.15s;
    }}
    .page-btn:hover {{ border-color: #93c5fd; color: #1d4ed8; background: #eff6ff; }}
    .page-btn.active {{
      border-color: #3b82f6; background: #3b82f6; color: #fff; font-weight: 700;
    }}
    .page-btn:disabled {{ opacity: 0.35; cursor: default; }}
    .page-info {{ font-size: 13px; color: #cbd5e1; padding: 0 4px; }}
    .empty {{ text-align: center; color: #94a3b8; padding: 64px 0; font-size: 15px; }}
  </style>
</head>
<body>

<div class="sticky-top">
  <div class="header-inner">
    <div class="header-row">
      <span class="header-label">arXiv Digest</span>
      <span class="header-title">{date_str}</span>
      <span class="header-meta" id="meta-count">{total} papers</span>
    </div>
    <div class="filter-bar" id="filter-bar"></div>
  </div>
</div>

<div class="content">
  <div id="paper-list"></div>
  <div class="pagination" id="pagination"></div>
</div>

<script>
const ALL_PAPERS   = {papers_js};
const ALL_TOPICS   = {topics_js};
const ACTIVE_ST    = {active_styles_js};
const INACTIVE_ST  = {inactive_styles_js};
const ACCENTS      = {accent_colors_js};
const PAGE_SIZE    = {PAGE_SIZE};

let activeTopics = new Set(ALL_TOPICS);
let currentPage  = 1;

function applyChip(el, topic, isActive) {{
  const s = isActive ? ACTIVE_ST[topic] : INACTIVE_ST[topic];
  el.style.background   = s.background;
  el.style.color        = s.color;
  el.style.borderColor  = s.borderColor;
}}

// Build filter chips
const bar = document.getElementById('filter-bar');
ALL_TOPICS.forEach(t => {{
  const btn = document.createElement('button');
  btn.className = 'chip';
  btn.textContent = t;
  applyChip(btn, t, true);
  btn.addEventListener('click', () => {{
    activeTopics.has(t) ? activeTopics.delete(t) : activeTopics.add(t);
    applyChip(btn, t, activeTopics.has(t));
    currentPage = 1;
    render();
  }});
  bar.appendChild(btn);
}});

function filtered() {{
  return ALL_PAPERS.filter(p => p.topics.some(t => activeTopics.has(t)));
}}

function render() {{
  const papers = filtered();
  const page   = papers.slice((currentPage-1)*PAGE_SIZE, currentPage*PAGE_SIZE);
  const list   = document.getElementById('paper-list');
  const meta   = document.getElementById('meta-count');

  meta.textContent = papers.length + ' paper' + (papers.length !== 1 ? 's' : '');
  list.innerHTML = '';

  if (!papers.length) {{
    list.innerHTML = '<div class="empty">No papers match the selected topics.</div>';
    renderPagination(0); return;
  }}

  page.forEach(p => {{
    const preview  = p.abstract.slice(0, 320) + (p.abstract.length > 320 ? '…' : '');
    const hasMore  = p.abstract.length > 320;
    const accent   = ACCENTS[p.topics[0]] || '#cbd5e1';
    const chips    = p.topics.map(t => {{
      const s = ACTIVE_ST[t] || {{}};
      return `<span class="topic-chip" style="background:${{s.background}};color:${{s.color}};border-color:${{s.borderColor}}">${{t}}</span>`;
    }}).join('');

    const card = document.createElement('div');
    card.className = 'paper';
    card.style.borderLeftColor = accent;
    card.innerHTML = `
      <a class="paper-title" href="${{p.url}}" target="_blank">${{p.title}}</a>
      <div class="paper-authors">${{p.authors}}</div>
      <div class="abstract-preview" id="pv-${{p.id}}">${{preview}}</div>
      ${{hasMore ? `
        <div class="abstract-full" id="fl-${{p.id}}">${{p.abstract}}</div>
        <button class="expand-btn" id="btn-${{p.id}}" onclick="toggle('${{p.id}}')">Show more ↓</button>
      ` : ''}}
      <div class="paper-footer">${{chips}}<a class="pdf-link" href="${{p.url}}" target="_blank">PDF →</a></div>
    `;
    list.appendChild(card);
  }});

  renderPagination(papers.length);
}}

function toggle(id) {{
  const pv  = document.getElementById('pv-'  + id);
  const fl  = document.getElementById('fl-'  + id);
  const btn = document.getElementById('btn-' + id);
  const exp = fl.style.display === 'block';
  pv.style.display  = exp ? 'block' : 'none';
  fl.style.display  = exp ? 'none'  : 'block';
  btn.textContent   = exp ? 'Show more ↓' : 'Show less ↑';
}}

function renderPagination(total) {{
  const pages = Math.ceil(total / PAGE_SIZE);
  const c = document.getElementById('pagination');
  c.innerHTML = '';
  if (pages <= 1) return;

  const prev = document.createElement('button');
  prev.className = 'page-btn'; prev.textContent = '← Prev';
  prev.disabled = currentPage === 1;
  prev.onclick = () => {{ currentPage--; render(); scrollTo(0,0); }};
  c.appendChild(prev);

  const range = [];
  for (let i = 1; i <= pages; i++) {{
    if (i===1 || i===pages || Math.abs(i-currentPage)<=2) range.push(i);
    else if (range[range.length-1] !== '…') range.push('…');
  }}
  range.forEach(item => {{
    if (item === '…') {{
      const s = document.createElement('span');
      s.className = 'page-info'; s.textContent = '…'; c.appendChild(s);
    }} else {{
      const btn = document.createElement('button');
      btn.className = 'page-btn' + (item===currentPage?' active':'');
      btn.textContent = item;
      btn.onclick = () => {{ currentPage=item; render(); scrollTo(0,0); }};
      c.appendChild(btn);
    }}
  }});

  const next = document.createElement('button');
  next.className = 'page-btn'; next.textContent = 'Next →';
  next.disabled = currentPage === pages;
  next.onclick = () => {{ currentPage++; render(); scrollTo(0,0); }};
  c.appendChild(next);
}}

render();
</script>
</body>
</html>"""