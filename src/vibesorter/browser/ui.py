from __future__ import annotations

import html


FILTER_FAMILIES = ("media_type", "colors", "temperature", "saturation", "brightness", "vibes")


def render_page(rows: list[dict] | None = None, vibe: str | None = None, query: str | None = None) -> str:
    initial = "" if rows is None else "".join(_card(row) for row in rows)
    return f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>VibeSorter Browser</title>
<style>
:root{{font-family:system-ui,sans-serif;color-scheme:dark;background:#0d0e12;color:#eee}}*{{box-sizing:border-box}}body{{margin:0;padding:28px;max-width:1500px;margin-inline:auto}}h1{{margin:0 0 6px}}p{{color:#aaa;margin:0}}.layout{{display:grid;grid-template-columns:270px 1fr;gap:24px;margin-top:24px}}.sidebar{{border:1px solid #292c35;border-radius:14px;padding:14px;height:max-content;position:sticky;top:20px}}.group{{border-top:1px solid #292c35;padding:12px 0}}.group:first-child{{border-top:0;padding-top:0}}.group h2{{font-size:12px;color:#aaa;text-transform:uppercase;margin:0 0 8px}}.choices{{display:flex;flex-wrap:wrap;gap:6px}}label.choice{{background:#181a21;border:1px solid #30333d;border-radius:8px;padding:7px 9px;font-size:12px;cursor:pointer}}label.choice:has(input:checked){{border-color:#6ea8fe;background:#202733}}input[type=checkbox]{{accent-color:#6ea8fe}}form{{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 14px}}input[type=text],button{{background:#181a21;color:#eee;border:1px solid #30333d;border-radius:10px;padding:10px 13px}}input[type=text]{{min-width:260px}}button{{cursor:pointer}}button:hover{{border-color:#555b69}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}.card{{border:1px solid #292c35;border-radius:14px;overflow:hidden;background:#15171d;cursor:pointer}}.thumb{{display:block;width:100%;height:180px;object-fit:cover;background:#111218}}.meta{{padding:13px;display:grid;gap:5px}}.meta strong{{font-size:15px}}.meta span,.meta small{{font-size:12px;color:#aaa}}.toolbar{{display:flex;justify-content:space-between;margin:14px 0;color:#999;font-size:13px}}.empty{{padding:40px;border:1px dashed #393c46;border-radius:14px;color:#999}}.modal{{position:fixed;inset:0;background:#000b;display:grid;place-items:center;padding:24px;z-index:10}}.modal[hidden]{{display:none}}.dialog{{width:min(1000px,100%);max-height:90vh;overflow:auto;background:#15171d;border:1px solid #30333d;border-radius:18px;padding:20px;position:relative}}.close{{position:absolute;right:16px;top:16px}}.detail{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:28px}}.detail-image{{width:100%;max-height:65vh;object-fit:contain}}.profile{{display:grid;gap:8px}}.profile div{{display:flex;justify-content:space-between;border-top:1px solid #292c35;padding:8px 0;font-size:13px}}@media(max-width:850px){{.layout{{grid-template-columns:1fr}}.sidebar{{position:static}}.detail{{grid-template-columns:1fr}}}}
</style></head>
<body><h1>VibeSorter</h1><p>Local browser · cached analysis only · multidimensional filters</p>
<div class='layout'><aside class='sidebar'><div id='filters'>Loading filters…</div></aside><main>
<form id='search'><input id='query' type='text' placeholder='Search paths...' value='{html.escape(query or '', quote=True)}'><button type='submit'>Apply filters</button><button id='clear' type='button'>Clear</button></form>
<div class='toolbar'><span id='summary'>Loading…</span><button id='more' type='button' hidden>Load more</button></div><section id='grid' class='grid'>{initial}</section><div id='empty' class='empty' hidden>No cached analysis matched these filters.</div></main></div>
<div id='modal' class='modal' hidden><section class='dialog'><button id='close' class='close'>Close</button><div id='detail'></div></section></div>
<script>
const families=['media_type','colors','temperature','saturation','brightness','vibes'];const labels={{media_type:'Media type',colors:'Color',temperature:'Temperature',saturation:'Saturation',brightness:'Brightness',vibes:'Vibes'}};let page=1,total=0,limit=48;
const esc=v=>String(v??'').replace(/[&<>\"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[c]));
function renderFilters(values){{document.getElementById('filters').innerHTML=families.map(f=>`<section class='group'><h2>${{labels[f]}}</h2><div class='choices'>${{(values[f]||[]).map(v=>`<label class='choice'><input type='checkbox' name='${{f}}' value='${{esc(v)}}'> ${{esc(v)}}</label>`).join('')}}</div></section>`).join('');}}
function selectedParams(){{const p=new URLSearchParams();p.set('q',document.getElementById('query').value);families.forEach(f=>document.querySelectorAll(`input[name='${{f}}']:checked`).forEach(i=>p.append(f,i.value)));p.set('page',page);p.set('limit',limit);return p;}}
function card(row){{const path=String(row.path||'');const label=String(row.vibe||'Unclassified');const profile=row.profile||{{}};const tags=[profile.media_type?.value,...(profile.colors||[]).map(x=>x.value),profile.temperature?.value,profile.saturation?.value,profile.brightness?.value,...(profile.vibes||[]).map(x=>x.value)].filter(Boolean);return `<article class='card' tabindex='0' data-path='${{esc(path)}}'><img class='thumb' src='/api/image?path=${{encodeURIComponent(path)}}' alt='${{esc(label)}}' loading='lazy' onerror="this.style.visibility='hidden'"><div class='meta'><strong>${{esc(label)}}</strong><span>${{esc(tags.join(' · '))}}</span><small>${{esc(path)}}</small></div></article>`;}}
function bind(){{document.querySelectorAll('.card').forEach(c=>{{c.onclick=()=>openDetail(c.dataset.path);c.onkeydown=e=>{{if(e.key==='Enter')openDetail(c.dataset.path)}}}})}}
async function load(reset=true){{if(reset){{page=1;grid.innerHTML=''}}const r=await fetch('/api/images?'+selectedParams());const data=await r.json();total=data.total;data.items.forEach(x=>grid.insertAdjacentHTML('beforeend',card(x)));bind();summary.textContent=total?`Showing ${{Math.min(page*limit,total)}} of ${{total}} images`:'No results';empty.hidden=total!==0;more.hidden=page*limit>=total;}}
async function openDetail(path){{modal.hidden=false;detail.textContent='Loading…';const r=await fetch('/api/image-details?path='+encodeURIComponent(path));const d=await r.json();const p=d.profile||{{}};const values=[['Media type',p.media_type?.value],['Colors',(p.colors||[]).map(x=>x.value).join(', ')],['Temperature',p.temperature?.value],['Saturation',p.saturation?.value],['Brightness',p.brightness?.value],['Vibes',(p.vibes||[]).map(x=>x.value).join(', ')]];detail.innerHTML=`<div class='detail'><img class='detail-image' src='/api/image?path=${{encodeURIComponent(d.path)}}'><div><h2>${{esc(d.vibe||'Unclassified')}}</h2><div class='profile'>${{values.map(([k,v])=>`<div><span>${{esc(k)}}</span><strong>${{esc(v||'—')}}</strong></div>`).join('')}}</div></div></div>`;}}
document.getElementById('search').onsubmit=e=>{{e.preventDefault();load()}};document.getElementById('clear').onclick=()=>{{document.getElementById('query').value='';document.querySelectorAll('input[type=checkbox]').forEach(i=>i.checked=false);load()}};document.getElementById('more').onclick=()=>{{page++;load(false)}};document.getElementById('close').onclick=()=>modal.hidden=true;modal.onclick=e=>{{if(e.target===modal)modal.hidden=true}};
fetch('/api/attributes').then(r=>r.json()).then(d=>renderFilters(d.values));load();
</script></body></html>"""


def _card(row: dict) -> str:
    path = str(row.get("path") or "")
    label = str(row.get("vibe") or "Unclassified")
    confidence = row.get("confidence")
    text = f"{float(confidence):.0%}" if isinstance(confidence, (int, float)) and confidence <= 1 else (str(confidence) if confidence is not None else "—")
    return f"<article class='card'><img class='thumb' src='/api/image?path={html.escape(path, quote=True)}' alt='{html.escape(label, quote=True)}'><div class='meta'><strong>{html.escape(label)}</strong><span>{html.escape(text)} confidence</span><small>{html.escape(path)}</small></div></article>"
