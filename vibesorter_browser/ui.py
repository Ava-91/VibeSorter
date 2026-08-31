"""Small dependency-free HTML interface for the local browser."""

from __future__ import annotations

import html
import json


def render_page(rows: list[dict], vibe: str | None = None, query: str | None = None) -> str:
    cards = []
    for row in rows:
        path = str(row.get("path") or "")
        label = str(row.get("vibe") or "Unclassified")
        confidence = row.get("confidence")
        confidence_text = f"{float(confidence):.0%}" if isinstance(confidence, (int, float)) and confidence <= 1 else (str(confidence) if confidence is not None else "—")
        cards.append(
            "<article class='card'>"
            f"<div class='thumb'>📷</div><div class='meta'><strong>{html.escape(label)}</strong>"
            f"<span>{html.escape(confidence_text)} confidence</span><small title='{html.escape(path)}'>{html.escape(path)}</small></div></article>"
        )
    content = "".join(cards) or "<div class='empty'>No cached analysis matched this filter.</div>"
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>VibeSorter Browser</title><style>
:root{{font-family:system-ui,sans-serif;color-scheme:dark;background:#0d0e12;color:#eee}}body{{margin:0;padding:32px;max-width:1300px;margin-inline:auto}}h1{{margin:0 0 6px}}p{{color:#aaa}}form{{display:flex;gap:10px;margin:24px 0}}input,button{{background:#181a21;color:#eee;border:1px solid #30333d;border-radius:10px;padding:10px 13px}}button{{cursor:pointer}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}}.card{{border:1px solid #292c35;border-radius:14px;overflow:hidden;background:#15171d}}.thumb{{height:150px;display:grid;place-items:center;background:linear-gradient(135deg,#242633,#111218);font-size:38px}}.meta{{padding:13px;display:grid;gap:5px}}.meta span{{font-size:12px;color:#aaa}}.meta small{{font-size:11px;color:#777;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.empty{{padding:40px;border:1px dashed #393c46;border-radius:14px;color:#999}}
</style></head><body><h1>VibeSorter</h1><p>Local browser · cached analysis only · no cloud upload</p>
<form><input name='q' value='{html.escape(query or '')}' placeholder='Search paths...'><input name='vibe' value='{html.escape(vibe or '')}' placeholder='Vibe...'><button>Filter</button></form>
<section class='grid'>{content}</section></body></html>"""
