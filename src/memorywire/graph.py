"""Trust-graph report: render an agent's memory store as a self-contained HTML graph.

Nodes are memories (and their sources), colored strictly by trust verdict from the recovery
classifier (clean / quarantine / purge). Edges are **provenance**: each distinct ``source`` links
to the memories it produced. Click a source to light up its *blast radius* — every memory it
planted — which is the picture that makes poisoning legible.

The output is one standalone HTML file: an inline vanilla-JS SVG force layout, no server, no CDN,
no external calls. Build it via ``memorywire graph`` (see cli) or:

    from memorywire.graph import build_graph, render_html
"""
from __future__ import annotations

import html
import json
from typing import Any

from memorywire.recovery.report import EntryVerdict, MemoryRecord, Verdict
from memorywire.recovery.strategies import DEFAULT_TRUSTED

# verdict -> (css class, human label)
_VERDICT = {
    Verdict.KEEP: ("clean", "clean"),
    Verdict.QUARANTINE: ("quarantine", "quarantined (needs review)"),
    Verdict.PURGE: ("purge", "poisoned (untrusted origin)"),
    Verdict.EXPIRE: ("purge", "expired"),
}


def build_graph(
    records: list[MemoryRecord],
    verdicts: list[EntryVerdict],
    *,
    trusted_sources: frozenset[str] | set[str] = DEFAULT_TRUSTED,
) -> dict[str, Any]:
    """Turn classified memory records into a {nodes, edges, legend} graph."""
    trusted = set(trusted_sources)
    by_id = {v.record.id: v for v in verdicts}
    nodes: list[dict] = []
    edges: list[dict] = []
    sources: dict[str, dict] = {}

    for r in records:
        v = by_id.get(r.id)
        vclass, vlabel = _VERDICT.get(v.verdict if v else Verdict.KEEP, ("clean", "clean"))
        content = r.content if isinstance(r.content, str) else json.dumps(r.content)
        nodes.append({
            "id": r.id,
            "kind": "memory",
            "label": (content[:38] + "…") if len(content) > 39 else content,
            "content": content,
            "source": r.source or "unknown",
            "confidence": r.confidence,
            "trust": vclass,
            "trust_label": vlabel,
            "reason": v.reason if v else "",
        })
        src = (r.source or "unknown").strip()
        if src not in sources:
            sources[src] = {
                "id": f"src:{src}",
                "kind": "source",
                "label": src,
                "trusted": src in trusted,
            }
        edges.append({"from": f"src:{src}", "to": r.id})

    # A source node's own color reflects whether it is a trusted origin.
    for s in sources.values():
        s["trust"] = "clean" if s["trusted"] else "purge"
    nodes = list(sources.values()) + nodes
    return {"nodes": nodes, "edges": edges}


def render_html(graph: dict[str, Any], *, title: str = "memorywire trust graph") -> str:
    data = json.dumps(graph)
    t = html.escape(title)
    counts = {"clean": 0, "quarantine": 0, "purge": 0}
    for n in graph["nodes"]:
        if n["kind"] == "memory":
            counts[n["trust"]] = counts.get(n["trust"], 0) + 1
    return _TEMPLATE.replace("__TITLE__", t).replace("__DATA__", data).replace(
        "__CLEAN__", str(counts["clean"])).replace(
        "__QUAR__", str(counts["quarantine"])).replace("__PURGE__", str(counts["purge"]))


_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{--bg:#0f1115;--ink:#e6e6e6;--muted:#9aa0aa;--line:#2a2d34;
        --clean:#2c8c5e;--quarantine:#c99a2e;--purge:#d8504f;--source:#5b6472;--hi:#4f83cc;}
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink)}
  header{padding:14px 18px;border-bottom:1px solid var(--line)}
  header h1{font-size:1.05rem;margin:0}
  header .sub{color:var(--muted);font-size:.82rem;margin-top:3px}
  .legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;font-size:.8rem;color:var(--muted)}
  .legend b{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:middle}
  #wrap{display:flex;height:calc(100vh - 92px)}
  #canvas{flex:1}
  #panel{width:320px;border-left:1px solid var(--line);padding:16px;overflow:auto;font-size:.86rem}
  #panel h2{font-size:.95rem;margin:.2rem 0 .6rem}
  #panel .k{color:var(--muted)}
  .pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.75rem;color:#0c0d10}
  circle{cursor:pointer;stroke:#0f1115;stroke-width:1.5}
  line{stroke:var(--line)}
  .hint{color:var(--muted);font-size:.82rem}
</style></head><body>
<header>
  <h1>__TITLE__</h1>
  <div class="sub">Memory store colored by trust. Click a <b style="color:var(--source)">source</b> to light up its blast radius — every memory it planted.</div>
  <div class="legend">
    <span><b style="background:var(--clean)"></b>clean (__CLEAN__)</span>
    <span><b style="background:var(--quarantine)"></b>quarantined (__QUAR__)</span>
    <span><b style="background:var(--purge)"></b>poisoned / untrusted (__PURGE__)</span>
    <span><b style="background:var(--source)"></b>source</span>
  </div>
</header>
<div id="wrap">
  <svg id="canvas"></svg>
  <div id="panel"><p class="hint">Click any node for details. Click a source node to highlight its blast radius.</p></div>
</div>
<script>
const G = __DATA__;
const svg = document.getElementById('canvas'), panel = document.getElementById('panel');
const COL = {clean:'#2c8c5e',quarantine:'#c99a2e',purge:'#d8504f',source:'#5b6472'};
let W = svg.clientWidth, H = svg.clientHeight;
const N = G.nodes, E = G.edges;
const byId = {}; N.forEach(n=>{byId[n.id]=n; n.x=W/2+(Math.random()-.5)*W*.6; n.y=H/2+(Math.random()-.5)*H*.6; n.vx=0; n.vy=0;});
const adj = {}; N.forEach(n=>adj[n.id]=[]); E.forEach(e=>{adj[e.from].push(e.to); adj[e.to].push(e.from);});
// simple force sim
function tick(){
  for(let i=0;i<N.length;i++){for(let j=i+1;j<N.length;j++){
    const a=N[i],b=N[j]; let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+.01,d=Math.sqrt(d2);
    const rep=1400/d2; const fx=dx/d*rep, fy=dy/d*rep; a.vx+=fx;a.vy+=fy;b.vx-=fx;b.vy-=fy;}}
  E.forEach(e=>{const a=byId[e.from],b=byId[e.to];let dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)+.01;
    const f=(d-70)*.02;const fx=dx/d*f,fy=dy/d*f;a.vx+=fx;a.vy+=fy;b.vx-=fx;b.vy-=fy;});
  N.forEach(n=>{n.vx+=(W/2-n.x)*.002;n.vy+=(H/2-n.y)*.002;n.x+=n.vx*=.85;n.y+=n.vy*=.85;
    n.x=Math.max(20,Math.min(W-20,n.x));n.y=Math.max(20,Math.min(H-20,n.y));});
}
for(let i=0;i<260;i++)tick();
function draw(hi){
  let s='';
  E.forEach(e=>{const a=byId[e.from],b=byId[e.to];const on=hi&&(hi.has(e.from)&&hi.has(e.to));
    s+=`<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${on?'#4f83cc':'#2a2d34'}" stroke-width="${on?2:1}"/>`;});
  N.forEach(n=>{const r=n.kind==='source'?11:7;const c=COL[n.trust]||COL.source;
    const dim=hi&&!hi.has(n.id)?.25:1;
    s+=`<circle cx="${n.x}" cy="${n.y}" r="${r}" fill="${c}" opacity="${dim}" data-id="${n.id}"/>`;});
  svg.innerHTML=s;
  svg.querySelectorAll('circle').forEach(el=>el.onclick=()=>select(el.getAttribute('data-id')));
}
function select(id){
  const n=byId[id]; let hi=null;
  if(n.kind==='source'){hi=new Set([id]); adj[id].forEach(m=>hi.add(m));}
  draw(hi);
  const esc=s=>String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  if(n.kind==='source'){
    const kids=adj[id].map(m=>byId[m]); const poisoned=kids.filter(k=>k.trust==='purge').length;
    panel.innerHTML=`<h2>Source: ${esc(n.label)}</h2>
      <p class="k">${n.trusted?'trusted origin':'UNTRUSTED origin'}</p>
      <p>Blast radius: <b>${kids.length}</b> memories from this source (${poisoned} poisoned).</p>
      <p class="hint">Highlighted in blue: every memory this source planted.</p>`;
  } else {
    panel.innerHTML=`<h2>Memory</h2>
      <p><span class="pill" style="background:${COL[n.trust]}">${esc(n.trust_label)}</span></p>
      <p class="k">source</p><p>${esc(n.source)}</p>
      <p class="k">confidence</p><p>${esc(n.confidence)}</p>
      <p class="k">content</p><p>${esc(n.content)}</p>
      ${n.reason?`<p class="k">why</p><p>${esc(n.reason)}</p>`:''}`;
  }
}
addEventListener('resize',()=>{W=svg.clientWidth;H=svg.clientHeight;draw();});
draw();
</script></body></html>"""
