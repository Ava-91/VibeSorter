from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import quote


def _image_uri(path: str) -> str:
    """Create a browser-safe local file URI without reading the image."""
    return Path(path).expanduser().resolve().as_uri()


def render_gallery(data: dict, output: Path) -> Path:
    """Render a lightweight local HTML gallery from an existing proposal/review JSON."""
    operations = data.get("operations", [])
    review = {int(item["id"]): item["status"] for item in data.get("review", []) if "id" in item and "status" in item}
    cards = []
    for operation in operations:
        path = str(operation["source"])
        vibe = str(operation.get("vibe", "Unknown"))
        score = float(operation.get("score", 0))
        status = review.get(int(operation["id"]), "proposed")
        cards.append((vibe.casefold(), -score, int(operation["id"]), f'''<article class="card" data-vibe="{html.escape(vibe, quote=True)}" data-status="{html.escape(status, quote=True)}">\n  <img src="{html.escape(_image_uri(path), quote=True)}" loading="lazy" decoding="async" alt="{html.escape(Path(path).name, quote=True)}">\n  <div class="meta"><strong>{html.escape(vibe)}</strong><span>{score:.0%}</span></div>\n  <small>{html.escape(status)} · {html.escape(path)}</small>\n</article>'''))
    cards.sort(key=lambda item: (item[0], item[1], item[2]))
    unique_vibes = sorted({str(op.get("vibe", "Unknown")) for op in operations}, key=str.casefold)
    options = "<option value=\"\">All vibes</option>" + "".join(f'<option>{html.escape(vibe)}</option>' for vibe in unique_vibes)
    body = "\n".join(card[3] for card in cards)
    title = html.escape(Path(output).stem)
    document = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — VibeSorter gallery</title>
<style>
:root {{ color-scheme: dark; font-family: system-ui, sans-serif; }}
body {{ margin: 0; background: #111; color: #eee; }}
header {{ position: sticky; top: 0; z-index: 2; padding: 16px; background: rgba(17,17,17,.94); backdrop-filter: blur(12px); border-bottom: 1px solid #333; }}
h1 {{ margin: 0 0 12px; font-size: 20px; }}
.controls {{ display: flex; gap: 8px; flex-wrap: wrap; }}
input, select {{ background: #1c1c1c; color: #eee; border: 1px solid #444; border-radius: 8px; padding: 9px 11px; }}
#grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; padding: 16px; }}
.card {{ overflow: hidden; border: 1px solid #2d2d2d; border-radius: 10px; background: #181818; }}
.card img {{ display: block; width: 100%; aspect-ratio: 1; object-fit: cover; background: #222; }}
.meta {{ display: flex; justify-content: space-between; padding: 9px 10px 2px; }}
small {{ display: block; padding: 0 10px 10px; color: #999; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.empty {{ padding: 32px 16px; color: #999; }}
</style>
</head>
<body>
<header>
<h1>VibeSorter gallery · {len(cards)} images</h1>
<div class="controls"><select id="vibe">{options}</select><input id="search" type="search" placeholder="Search file paths…"><select id="status"><option value="">All statuses</option><option>accepted</option><option>rejected</option><option>pending</option><option>proposed</option></select></div>
</header>
<main id="grid">{body}</main>
<script>
const cards=[...document.querySelectorAll('.card')];
const vibe=document.querySelector('#vibe'), search=document.querySelector('#search'), status=document.querySelector('#status');
function filter() {{ const q=search.value.toLowerCase(); cards.forEach(card=>{{ const okV=!vibe.value||card.dataset.vibe===vibe.value; const okS=!status.value||card.dataset.status===status.value; const okQ=!q||card.innerText.toLowerCase().includes(q); card.hidden=!(okV&&okS&&okQ); }}); }}
vibe.onchange=filter; search.oninput=filter; status.onchange=filter;
</script>
</body>
</html>
'''
    output = output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    return output


def gallery_from_file(source: Path, output: Path) -> Path:
    data = json.loads(source.expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("operations"), list):
        raise ValueError("gallery source must be a proposal or reviewed proposal JSON")
    return render_gallery(data, output)
