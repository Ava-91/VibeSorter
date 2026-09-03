from __future__ import annotations

import html


def render_page(rows: list[dict] | None = None, vibe: str | None = None, query: str | None = None) -> str:
    initial = "" if rows is None else "".join(_card(row) for row in rows)
    selected = html.escape(vibe or "", quote=True)
    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>VibeSorter Browser</title>
<style>
:root{{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color-scheme:dark;background:#0d0e12;color:#eee}}
*{{box-sizing:border-box}}body{{margin:0;padding:28px;max-width:1500px;margin-inline:auto}}
h1{{margin:0 0 6px;font-size:30px}}p{{color:#aaa;margin:0}}
.layout{{display:grid;grid-template-columns:240px 1fr;gap:24px;margin-top:24px}}.sidebar{{border:1px solid #292c35;border-radius:14px;padding:14px;height:max-content;position:sticky;top:20px}}
.sidebar h2{{font-size:14px;margin:0 0 10px;color:#aaa}}.vibes{{display:grid;gap:6px}}.vibe{{display:flex;justify-content:space-between;align-items:center;width:100%;text-align:left;background:#181a21;color:#eee;border:1px solid transparent;border-radius:9px;padding:9px 10px;cursor:pointer}}.vibe:hover,.vibe.active{{border-color:#555b69;background:#20232c}}.count{{color:#999;font-size:11px}}
form{{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 14px}}input,button{{background:#181a21;color:#eee;border:1px solid #30333d;border-radius:10px;padding:10px 13px}}input{{min-width:220px}}button{{cursor:pointer}}button:hover{{border-color:#555b69}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}.card{{border:1px solid #292c35;border-radius:14px;overflow:hidden;background:#15171d;min-width:0}}
.thumb{{display:block;width:100%;height:180px;object-fit:cover;background:#111218}}.thumb-placeholder{{height:180px;display:grid;place-items:center;background:linear-gradient(135deg,#242633,#111218);font-size:38px}}
.meta{{padding:13px;display:grid;gap:5px}}.meta strong{{font-size:15px}}.meta span{{font-size:12px;color:#aaa}}.meta small{{font-size:11px;color:#777;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.toolbar{{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:14px 0;color:#999;font-size:13px}}.empty{{padding:40px;border:1px dashed #393c46;border-radius:14px;color:#999}}
@media(max-width:800px){{.layout{{grid-template-columns:1fr}}.sidebar{{position:static}}.vibes{{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}}}}
</style>
</head>
<body>
<h1>VibeSorter</h1>
<p>Local browser · cached analysis only · no cloud upload</p>
<div class='layout'>
<aside class='sidebar'><h2>VIBES</h2><div id='vibes' class='vibes'><div class='count'>Loading…</div></div></aside>
<main>
<form id='filters'><input id='query' name='q' value='{html.escape(query or '', quote=True)}' placeholder='Search paths...'><button type='submit'>Filter</button><button id='clear' type='button'>Clear</button></form>
<div class='toolbar'><span id='summary'>Loading…</span><button id='load-more' type='button' hidden>Load more</button></div>
<section id='grid' class='grid'>{initial}</section>
<div id='empty' class='empty' hidden>No cached analysis matched this filter.</div>
</main>
</div>
<script>
const grid = document.getElementById('grid');
const empty = document.getElementById('empty');
const summary = document.getElementById('summary');
const more = document.getElementById('load-more');
const filters = document.getElementById('filters');
const vibes = document.getElementById('vibes');
let page = 1;
let total = 0;
let limit = 48;
let selectedVibe = '{selected}';

function escapeHtml(value) {{
  return String(value).replace(/[&<>\"']/g, char => ({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[char]));
}}
function card(row) {{
  const path = String(row.path || '');
  const label = String(row.vibe || 'Unclassified');
  const confidence = row.confidence == null ? '—' : (Number(row.confidence) <= 1 ? `${{Math.round(Number(row.confidence) * 100)}}%` : escapeHtml(row.confidence));
  const src = `/api/image?path=${{encodeURIComponent(path)}}`;
  return `<article class='card'><img class='thumb' src='${{src}}' alt='${{escapeHtml(label)}}' loading='lazy' decoding='async' onerror="this.replaceWith(Object.assign(document.createElement('div'),{{className:'thumb-placeholder',textContent:'📷'}}))"><div class='meta'><strong>${{escapeHtml(label)}}</strong><span>${{confidence}} confidence</span><small title='${{escapeHtml(path)}}'>${{escapeHtml(path)}}</small></div></article>`;
}}
function renderVibes(items) {{
  vibes.innerHTML = `<button class='vibe ${{selectedVibe ? '' : 'active'}}' data-vibe=''><span>All images</span></button>` + items.map(item => `<button class='vibe ${{item.vibe === selectedVibe ? 'active' : ''}}' data-vibe='${{escapeHtml(item.vibe)}}'><span>${{escapeHtml(item.vibe)}}</span><span class='count'>${{item.count}}</span></button>`).join('');
  vibes.querySelectorAll('.vibe').forEach(button => button.addEventListener('click', () => {{ selectedVibe = button.dataset.vibe || ''; load(true); }}));
}}
async function loadVibes() {{
  try {{ const response = await fetch('/api/vibes', {{headers: {{Accept:'application/json'}}}}); if (!response.ok) throw new Error('Unable to load vibes'); renderVibes((await response.json()).items || []); }}
  catch (error) {{ vibes.innerHTML = `<div class='count'>${{escapeHtml(error.message)}}</div>`; }}
}}
async function load(reset) {{
  if (reset) {{ page = 1; grid.innerHTML = ''; }}
  more.disabled = true;
  const params = new URLSearchParams({{q: document.getElementById('query').value, vibe: selectedVibe, page, limit}});
  try {{
    const response = await fetch(`/api/images?${{params}}`, {{headers: {{Accept:'application/json'}}}});
    if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
    const data = await response.json(); total = data.total; limit = data.limit;
    data.items.forEach(row => grid.insertAdjacentHTML('beforeend', card(row)));
    empty.hidden = total !== 0; summary.textContent = total ? `Showing ${{Math.min(page * limit, total)}} of ${{total}} images` : 'No results';
    more.hidden = page * limit >= total; more.disabled = false;
    renderVibesFromSelection();
  }} catch (error) {{ grid.innerHTML = `<div class='empty'>Unable to load cached analysis: ${{escapeHtml(error.message)}}</div>`; more.hidden = true; }}
}}
function renderVibesFromSelection() {{ vibes.querySelectorAll('.vibe').forEach(button => button.classList.toggle('active', (button.dataset.vibe || '') === selectedVibe)); }}
filters.addEventListener('submit', event => {{ event.preventDefault(); load(true); }});
document.getElementById('clear').addEventListener('click', () => {{ document.getElementById('query').value = ''; selectedVibe = ''; load(true); }});
more.addEventListener('click', () => {{ page += 1; load(false); }});
loadVibes();
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
