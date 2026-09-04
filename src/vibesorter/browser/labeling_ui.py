from __future__ import annotations

import html
import json

from ..labeling import LabelSession
from ..vibes import VIBES


def render_label_page(session: LabelSession) -> str:
    vibes = list(VIBES)
    vibe_buttons = "".join(
        f"<button class='vibe' data-label='{html.escape(vibe, quote=True)}'><kbd>{index + 1}</kbd> {html.escape(vibe)}</button>"
        for index, vibe in enumerate(vibes)
    )
    key_map = json.dumps({str(index + 1): vibe for index, vibe in enumerate(vibes)}, ensure_ascii=False)
    candidates = [item.to_dict() for item in session.remaining]
    payload = json.dumps(candidates, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    # Keep the HTML/JavaScript template independent of Python f-string parsing.
    # JavaScript uses many braces and template literals, so placeholders are
    # substituted after the raw string has been constructed.
    page = """<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>VibeSorter Assisted Labeling</title>
<style>
:root{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color-scheme:dark;background:#0d0e12;color:#eee}
*{box-sizing:border-box}body{margin:0;padding:24px;max-width:1250px;margin-inline:auto}h1{margin:0 0 4px}p{color:#aaa;margin:5px 0}.top{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:20px}.counter{font-size:13px;color:#aaa;text-align:right}
.review{display:grid;grid-template-columns:minmax(300px,1.25fr) minmax(300px,.75fr);gap:20px}.panel{border:1px solid #292c35;border-radius:16px;background:#15171d;padding:16px}.image-wrap{min-height:65vh;display:grid;place-items:center;background:#0d0e12;border-radius:12px;overflow:hidden}#image{max-width:100%;max-height:65vh;object-fit:contain}.missing{padding:40px;color:#888}
.prediction{font-size:22px;font-weight:700;margin:4px 0}.confidence{color:#aaa}.scores{display:grid;gap:7px;margin:16px 0}.score{display:flex;justify-content:space-between;border-top:1px solid #292c35;padding:8px 0;font-size:13px}.actions{display:grid;gap:8px}button{background:#1b1e26;color:#eee;border:1px solid #30333d;border-radius:10px;padding:10px 12px;cursor:pointer;text-align:left}button:hover,button:focus{border-color:#777;outline:none}kbd{display:inline-block;min-width:22px;padding:2px 5px;border:1px solid #555;border-radius:5px;text-align:center;background:#111318}.secondary{display:flex;gap:8px;margin-top:12px}.secondary button{flex:1;text-align:center}#status{min-height:22px;margin-top:12px;color:#aaa}.help{font-size:12px;color:#777;margin-top:14px;line-height:1.5}.done{padding:40px;text-align:center}a{color:#aaa}
@media(max-width:800px){body{padding:14px}.top{display:block}.counter{text-align:left;margin-top:8px}.review{grid-template-columns:1fr}.image-wrap{min-height:45vh}#image{max-height:45vh}}
</style></head><body>
<div class='top'><div><h1>Assisted labeling</h1><p>VibeSorter proposes. You confirm or correct. Nothing leaves this machine.</p></div><div id='counter' class='counter'></div></div>
<div id='app' class='review'></div>
<script id='candidate-data' type='application/json'>__PAYLOAD__</script>
<script>
const candidates=JSON.parse(document.getElementById('candidate-data').textContent);let index=0;let busy=false;
const app=document.getElementById('app'),counter=document.getElementById('counter');
const keyMap=__KEY_MAP__;
function esc(value){return String(value).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}
function render(){if(index>=candidates.length){app.innerHTML=`<section class='panel done'><h2>🎉 Review complete</h2><p>All selected images have a human label.</p><p>You can now run <code>vibesorter evaluate</code> on the output file.</p></section>`;counter.textContent=`${candidates.length} / ${candidates.length}`;return;}
const item=candidates[index];counter.textContent=`${index+1} / ${candidates.length} · ${item.ambiguous?'ambiguous':'confident'}`;const scores=(item.scores||[]).slice(0,5).map(s=>`<div class='score'><span>${esc(s.name)}</span><strong>${Math.round(Number(s.score)*100)}%</strong></div>`).join('');
app.innerHTML=`<section class='panel'><div class='image-wrap'><img id='image' src='/api/image?path=${encodeURIComponent(item.path)}' alt='${esc(item.prediction)}' onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'missing',textContent:'Image is no longer available'}))"></div></section><section class='panel'><p>VibeSorter thinks:</p><div class='prediction'>${esc(item.prediction)}</div><div class='confidence'>${Math.round(Number(item.confidence)*100)}% confidence</div><div class='scores'>${scores}</div><div class='actions'><button id='accept'><kbd>Enter</kbd> Accept <strong>${esc(item.prediction)}</strong></button>__VIBE_BUTTONS__<button id='skip'><kbd>S</kbd> Skip for later</button></div><div class='secondary'><button id='undo'><kbd>U</kbd> Undo last decision</button></div><div id='status'></div><div class='help'>Keys: <kbd>Enter</kbd> accept · <kbd>1–8</kbd> correct · <kbd>S</kbd> skip · <kbd>U</kbd> undo. Decisions are saved immediately.</div></section>`;
}
async function decide(label,skip=false){if(busy||index>=candidates.length)return;busy=true;const status=document.getElementById('status');status.textContent='Saving…';try{const response=await fetch('/api/label/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:candidates[index].path,label:label||null,skip})});const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);index++;render();}catch(error){status.textContent=error.message;}finally{busy=false;}}
function accept(){decide(candidates[index]?.prediction);}document.addEventListener('keydown',event=>{if(event.target instanceof HTMLInputElement||event.target instanceof HTMLTextAreaElement)return;if(event.key==='Enter'){event.preventDefault();accept();return;}if(event.key.toLowerCase()==='s'){event.preventDefault();decide(null,true);return;}if(event.key.toLowerCase()==='u'){event.preventDefault();undo();return;}const label=keyMap[event.key];if(label){event.preventDefault();decide(label);}});
async function undo(){if(busy)return;const status=document.getElementById('status');try{const response=await fetch('/api/label/undo',{method:'POST'});const data=await response.json();if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);if(data.undone&&index>0)index--;render();}catch(error){status.textContent=error.message;}}
app.addEventListener('click',event=>{const button=event.target.closest('button');if(!button)return;if(button.id==='accept')accept();else if(button.id==='skip')decide(null,true);else if(button.id==='undo')undo();else if(button.dataset.label)decide(button.dataset.label);});render();
</script></body></html>"""
    return (
        page
        .replace("__PAYLOAD__", payload)
        .replace("__KEY_MAP__", key_map)
        .replace("__VIBE_BUTTONS__", vibe_buttons)
    )
