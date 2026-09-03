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
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}.card{{border:1px solid #292c35;border-radius:14px;overflow:hidden;background:#15171d;min-width:0;cursor:pointer}}.card:focus{{outline:2px solid #6ea8fe;outline-offset:2px}}
.thumb{{display:block;width:100%;height:180px;object-fit:cover;background:#111218}}.thumb-placeholder{{height:180px;display:grid;place-items:center;background:linear-gradient(135deg,#242633,#111218);font-size:38px}}
.meta{{padding:13px;display:grid;gap:5px}}.meta strong{{font-size:15px}}.meta span{{font-size:12px;color:#aaa}}.meta small{{font-size:11px;color:#777;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.toolbar{{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:14px 0;color:#999;font-size:13px}}.empty{{padding:40px;border:1px dashed #393c46;border-radius:14px;color:#999}}
.modal{{position:fixed;inset:0;background:#000b;display:grid;place-items:center;padding:24px;z-index:10}}.modal[hidden]{{display:none}}.dialog{{width:min(1000px,100%);max-height:90vh;overflow:auto;background:#15171d;border:1px solid #30333d;border-radius:18px;padding:20px;position:relative}}.close{{position:absolute;right:16px;top:16px}}.detail{{display:grid;grid-template-columns:minmax(280px,1fr) minmax(260px,1fr);gap:20px;margin-top:28px}}.detail-image{{width:100%;max-height:65vh;object-fit:contain;background:#0d0e12;border-radius:12px}}.detail h2{{margin:0 0 6px}}.detail dl{{display:grid;grid-template-columns:max-content 1fr;gap:8px 14px;font-size:13px}}.detail dt{{color:#999}}.score{{display:flex;justify-content:space-between;border-top:1px solid #292c35;padding:9px 0}}.feature{{display:flex;justify-content:space-between;color:#bbb;font-size:13px}}
@media(max-width:800px){{.layout{{grid-template-columns:1fr}}.sidebar{{position:static}}.vibes{{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}}.detail{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<h1>VibeSorter</h1><p>Local browser · cached analysis only · no cloud upload</p>
<div class='layout'><aside class='sidebar'><h2>VIBES</h2><div id='vibes' class='vibes'><div class='count'>Loading…</div></div></aside>
<main><form id='filters'><input id='query' name='q' value='{html.escape(query or '', quote=True)}' placeholder='Search paths...'><button type='submit'>Filter</button><button id='clear' type='button'>Clear</button></form>
<div class='toolbar'><span id='summary'>Loading…</span><button id='load-more' type='button' hidden>Load more</button></div><section id='grid' class='grid'>{initial}</section><div id='empty' class='empty' hidden>No cached analysis matched this filter.</div></main></div>
<div id='modal' class='modal' hidden><section class='dialog' role='dialog' aria-modal='true' aria-labelledby='detail-title'><button id='close' class='close' type='button' aria-label='Close'>Close</button><div id='detail'>Loading…</div></section></div>
<script>
const grid=document.getElementById('grid'),empty=document.getElementById('empty'),summary=document.getElementById('summary'),more=document.getElementById('load-more'),filters=document.getElementById('filters'),vibes=document.getElementById('vibes'),modal=document.getElementById('modal'),detail=document.getElementById('detail');
let page=1,total=0,limit=48,selectedVibe='{selected}';
function escapeHtml(value){{return String(value).replace(/[&<>\"']/g,char=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[char]));}}
function card(row){{const path=String(row.path||''),label=String(row.vibe||'Unclassified'),confidence=row.confidence==null?'—':(Number(row.confidence)<=1?`${{Math.round(Number(row.confidence)*100)}}%`:escapeHtml(row.confidence)),src=`/api/image?path=${{encodeURIComponent(path)}}`;return `<article class='card' tabindex='0' data-path='${{escapeHtml(path)}}'><img class='thumb' src='${{src}}' alt='${{escapeHtml(label)}}' loading='lazy' decoding='async' onerror="this.replaceWith(Object.assign(document.createElement('div'),{{className:'thumb-placeholder',textContent:'📷'}}))"><div class='meta'><strong>${{escapeHtml(label)}}</strong><span>${{confidence}} confidence</span><small title='${{escapeHtml(path)}}'>${{escapeHtml(path)}}</small></div></article>`;}}
function bindCards(){{grid.querySelectorAll('.card').forEach(card=>{{card.addEventListener('click',()=>openDetail(card.dataset.path));card.addEventListener('keydown',event=>{{if(event.key==='Enter'||event.key===' '){{event.preventDefault();openDetail(card.dataset.path);}}}});}});}}
function renderVibes(items){{vibes.innerHTML=`<button class='vibe ${{selectedVibe?'':'active'}}' data-vibe=''><span>All images</span></button>`+items.map(item=>`<button class='vibe ${{item.vibe===selectedVibe?'active':''}}' data-vibe='${{escapeHtml(item.vibe)}}'><span>${{escapeHtml(item.vibe)}}</span><span class='count'>${{item.count}}</span></button>`).join('');vibes.querySelectorAll('.vibe').forEach(button=>button.addEventListener('click',()=>{{selectedVibe=button.dataset.vibe||'';load(true);}}));}}
async function loadVibes(){{try{{const response=await fetch('/api/vibes',{{headers:{{Accept:'application/json'}}}});if(!response.ok)throw new Error('Unable to load vibes');renderVibes((await response.json()).items||[]);}}catch(error){{vibes.innerHTML=`<div class='count'>${{escapeHtml(error.message)}}</div>`;}}}}
async function load(reset){{if(reset){{page=1;grid.innerHTML='';}}more.disabled=true;const params=new URLSearchParams({{q:document.getElementById('query').value,vibe:selectedVibe,page,limit}});try{{const response=await fetch(`/api/images?${{params}}`,{{headers:{{Accept:'application/json'}}}});if(!response.ok)throw new Error(`HTTP ${{response.status}}`);const data=await response.json();total=data.total;limit=data.limit;data.items.forEach(row=>grid.insertAdjacentHTML('beforeend',card(row)));bindCards();empty.hidden=total!==0;summary.textContent=total?`Showing ${{Math.min(page*limit,total)}} of ${{total}} images`:'No results';more.hidden=page*limit>=total;more.disabled=false;}}catch(error){{grid.innerHTML=`<div class='empty'>Unable to load cached analysis: ${{escapeHtml(error.message)}}</div>`;more.hidden=true;}}}}
async function openDetail(path){{modal.hidden=false;detail.textContent='Loading…';try{{const response=await fetch(`/api/image-details?path=${{encodeURIComponent(path)}}`,{{headers:{{Accept:'application/json'}}}});if(!response.ok)throw new Error(`HTTP ${{response.status}}`);const data=await response.json();const scores=(data.scores||[]).map(score=>`<div class='score'><span>${{escapeHtml(score.name)}}</span><strong>${{Math.round(Number(score.score)*100)}}%</strong></div>`).join('');const features=Object.entries(data.features||{}).map(([key,value])=>`<div class='feature'><span>${{escapeHtml(key)}}</span><span>${{typeof value==='number'?Number(value).toFixed(3):escapeHtml(value)}}</span></div>`).join('');detail.innerHTML=`<div class='detail'><div><img class='detail-image' src='/api/image?path=${{encodeURIComponent(data.path)}}' alt='${{escapeHtml(data.vibe||'Image')}'></div><div><h2 id='detail-title'>${{escapeHtml(data.vibe||'Unclassified')}}</h2><p>${{Math.round(Number(data.confidence)*100)}}% confidence · ${{data.ambiguous?'ambiguous':'confident'}}</p><dl><dt>Path</dt><dd>${{escapeHtml(data.path)}}</dd><dt>File exists</dt><dd>${{data.file.exists?'yes':'no'}}</dd><dt>Size</dt><dd>${{data.file.size==null?'—':`${{data.file.size}} bytes`}}</dd></dl><h3>Vibe scores</h3>${{scores||'<p>No score data available.</p>'}}<h3>Feature signals</h3>${{features||'<p>No feature data available.</p>'}}</div></div>`;}}catch(error){{detail.innerHTML=`<div class='empty'>Unable to load image details: ${{escapeHtml(error.message)}}</div>`;}}}}
function closeModal(){{modal.hidden=true;detail.textContent='';}}
filters.addEventListener('submit',event=>{{event.preventDefault();load(true);}});document.getElementById('clear').addEventListener('click',()=>{{document.getElementById('query').value='';selectedVibe='';load(true);}});more.addEventListener('click',()=>{{page+=1;load(false);}});document.getElementById('close').addEventListener('click',closeModal);modal.addEventListener('click',event=>{{if(event.target===modal)closeModal();}});document.addEventListener('keydown',event=>{{if(event.key==='Escape'&&!modal.hidden)closeModal();}});loadVibes();load(false);
</script>
</body></html>"""


def _card(row: dict) -> str:
    path = str(row.get("path") or "")
    label = str(row.get("vibe") or "Unclassified")
    confidence = row.get("confidence")
    confidence_text = f"{float(confidence):.0%}" if isinstance(confidence, (int, float)) and confidence <= 1 else (str(confidence) if confidence is not None else "—")
    src = f"/api/image?path={html.escape(path, quote=True)}"
    return f"<article class='card' tabindex='0' data-path='{html.escape(path, quote=True)}'><img class='thumb' src='{src}' alt='{html.escape(label, quote=True)}' loading='lazy' decoding='async'><div class='meta'><strong>{html.escape(label)}</strong><span>{html.escape(confidence_text)} confidence</span><small title='{html.escape(path, quote=True)}'>{html.escape(path)}</small></div></article>"
