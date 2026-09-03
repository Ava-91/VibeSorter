from __future__ import annotations

import html


def render_page(rows: list[dict] | None = None, vibe: str | None = None, query: str | None = None) -> str:
    initial = "" if rows is None else "".join(_card(row) for row in rows)
    initial_json = "[]" if rows is None else "null"
    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>VibeSorter Browser</title>
<style>
:root{{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color-scheme:dark;background:#0d0e12;color:#eee}}
*{{box-sizing:border-box}}body{{margin:0;padding:28px;max-width:1400px;margin-inline:auto}}
h1{{margin:0 0 6px;font-size:30px}}p{{color:#aaa;margin:0}}
form{{display:flex;flex-wrap:wrap;gap:10px;margin:24px 0}}
input,button{{background:#181a21;color:#eee;border:1px solid #30333d;border-radius:10px;padding:10px 13px}}
input{{min-width:220px}}button{{cursor:pointer}}button:hover{{border-color:#555b69}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}
.card{{border:1px solid #292c35;border-radius:14px;overflow:hidden;background:#15171d;min-width:0}}
.thumb{{display:block;width:100%;height:180px;object-fit:cover;background:#111218}}
.thumb-placeholder{{height:180px;display:grid;place-items:center;background:linear-gradient(135deg,#242633,#111218);font-size:38px}}
.meta{{padding:13px;display:grid;gap:5px}}.meta strong{{font-size:15px}}
.meta span{{font-size:12px;color:#aaa}}.meta small{{font-size:11px;color:#777;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.toolbar{{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:14px 0;color:#999;font-size:13px}}
.empty{{padding:40px;border:1px dashed #393c46;border-radius:14px;color:#999}}
</style>
</head>
<body>
<h1>VibeSorter</h1>
<p>Local browser · cached analysis only · no cloud upload</p>
<form id='filters'>
<input id='query' name='q' value='{html.escape(query or '')}' placeholder='Search paths...'>
<input id='vibe' name='vibe' value='{html.escape(vibe or '')}' placeholder='Vibe...'>
<button type='submit'>Filter</button>
</form>
<div class='toolbar'><span id='summary'>Loading…</span><button id='load-more' type='button' hidden>Load more</button></div>
<section id='grid' class='grid'>{initial}</section>
<div id='empty' class='empty' hidden>No cached analysis matched this filter.</div>
<script>
const grid = document.getElementById('grid');
const empty = document.getElementById('empty');
const summary = document.getElementById('summary');
const more = document.getElementById('load-more');
const filters = document.getElementById('filters');
let page = 1;
let total = 0;
let limit = 48;

function escapeHtml(value) {{
  return String(value).replace(/[&<>\"']/g, char => ({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[char]));
}}
function card(row) {{
  const path = String(row.path || '');
  const label = String(row.vibe || 'Unclassified');
  const confidence = row.confidence == null ? '—' : (Number(row.confidence) <= 1 ? `${{Number(row.confidence) * 100 | 0}}%` : escapeHtml(row.confidence));
  const src = `/api/image?path=${{encodeURIComponent(path)}}`;
  return `<article class='card'><img class='thumb' src='${{src}}' alt='${{escapeHtml(label)}}' loading='lazy' decoding='async' onerror="this.replaceWith(Object.assign(document.createElement('div'),{{className:'thumb-placeholder',textContent:'📷'}}))"><div class='meta'><strong>${{escapeHtml(label)}}</strong><span>${{confidence}} confidence</span><small title='${{escapeHtml(path)}}'>${{escapeHtml(path)}}</small></div></article>`;
}}
async function load(reset) {{
  if (reset) {{ page = 1; grid.innerHTML = ''; }}
  more.disabled = true;
  const params = new URLSearchParams({{q: document.getElementById('query').value, vibe: document.getElementById('vibe').value, page, limit}});
  try {{
    const response = await fetch(`/api/images?${{params}}`, {{headers: {{Accept:'application/json'}}}});
    if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
    const data = await response.json();
    total = data.total;
    limit = data.limit;
    data.items.forEach(row => grid.insertAdjacentHTML('beforeend', card(row)));
    empty.hidden = total !== 0;
    summary.textContent = total ? `Showing ${{Math.min(page * limit, total)}} of ${{total}} images` : 'No results';
    more.hidden = page * limit >= total;
    more.disabled = false;
  }} catch (error) {{
    grid.innerHTML = `<div class='empty'>Unable to load cached analysis: ${{escapeHtml(error.message)}}</div>`;
    more.hidden = true;
  }}
}}
filters.addEventListener('submit', event => {{ event.preventDefault(); load(true); }});
more.addEventListener('click', () => {{ page += 1; load(false); }});
load(false);
</script>
</body>
</html>"""


def _card(row: dict) -> str:
    path = str(row.get("path") or "")
    label = str(row.get("vibe") or "Unclassified")
    confidence = row.get("confidence")
    confidence_text = f"{float(confidence):.0%}" if isinstance(confidence, (int, float)) and confidence <= 1 else (str(confidence) if confidence is not None else "—")
    src = f"/api/image?path={html.escape(path, quote=True)}"
    return f"<article class='card'><img class='thumb' src='{src}' alt='{html.escape(label, quote=True)}' loading='lazy' decoding='async'><div class='meta'><strong>{html.escape(label)}</strong><span>{html.escape(confidence_text)} confidence</span><small title='{html.escape(path, quote=True)}'>{html.escape(path)}</small></div></article>"
