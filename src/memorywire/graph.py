"""Trust-graph report: render an agent's memory store as a self-contained HTML graph.

Nodes are memories (circles, colored by the recovery classifier's verdict) and their sources
(gray squares, ringed green if a trusted origin / red if untrusted). Edges are **provenance**:
each source links to the memories it produced. Click an untrusted source to light up its *blast
radius* — every memory it planted — and purge them, live.

The output is one standalone HTML file (inline vanilla-JS SVG, no server/CDN/external calls),
hardened against attacker-controlled memory content (this is a poison-recovery tool). Build via
``memorywire graph`` or:

    from memorywire.graph import build_graph, render_html
"""
from __future__ import annotations

import html
import json
from typing import Any

from memorywire.recovery.report import EntryVerdict, MemoryRecord, Verdict
from memorywire.recovery.strategies import DEFAULT_TRUSTED

# verdict -> (css/js class, human label). Honest: PURGE = "purged by provenance", not "detected".
_VERDICT = {
    Verdict.KEEP: ("clean", "clean"),
    Verdict.QUARANTINE: ("quarantine", "quarantined (needs review)"),
    Verdict.PURGE: ("purge", "purged (untrusted origin)"),
    Verdict.EXPIRE: ("expired", "expired"),
}


def build_graph(
    records: list[MemoryRecord],
    verdicts: list[EntryVerdict],
    *,
    trusted_sources: frozenset[str] | set[str] = DEFAULT_TRUSTED,
) -> dict[str, Any]:
    """Turn classified memory records into a {nodes, edges} graph."""
    trusted = set(trusted_sources)
    by_id = {v.record.id: v for v in verdicts}
    nodes: list[dict] = []
    edges: list[dict] = []
    sources: dict[str, dict] = {}

    for r in records:
        v = by_id.get(r.id)
        # An unclassified record is treated as quarantine (review), never silently "clean".
        vclass, vlabel = _VERDICT.get(v.verdict, ("quarantine", "unclassified")) if v \
            else ("quarantine", "unclassified")
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
            sources[src] = {"id": f"src:{src}", "kind": "source", "label": src,
                            "trust": "source", "trusted": src in trusted}
        edges.append({"from": f"src:{src}", "to": r.id})

    # Sources keep their own "source" kind/color (gray) — ring, not fill, marks trust.
    nodes = list(sources.values()) + nodes
    return {"nodes": nodes, "edges": edges}


def render_html(graph: dict[str, Any], *, title: str = "memorywire trust graph") -> str:
    counts = {"clean": 0, "quarantine": 0, "purge": 0, "expired": 0}
    for n in graph["nodes"]:
        if n["kind"] == "memory":
            counts[n["trust"]] = counts.get(n["trust"], 0) + 1
    # </ split so poisoned content can't break out of the <script> tag (XSS hardening).
    data = json.dumps(graph).replace("</", "<\\/")
    out = _TEMPLATE
    out = out.replace("__TITLE__", html.escape(title))
    out = out.replace("__CLEAN__", str(counts["clean"]))
    out = out.replace("__QUAR__", str(counts["quarantine"]))
    out = out.replace("__PURGE__", str(counts["purge"]))
    out = out.replace("__DATA__", data)  # data replaced LAST so its content can't macro-expand
    return out


_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{--bg:#0f1115;--ink:#e6e6e6;--muted:#9aa0aa;--line:#2a2d34;
        --clean:#009E73;--quarantine:#C28400;--purge:#CC3311;--expired:#7d7668;--source:#8a91a2;--hi:#4691CF;}
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink)}
  header{padding:14px 18px;border-bottom:1px solid var(--line)}
  header h1{font-size:1.05rem;margin:0}
  header .sub{color:var(--muted);font-size:.82rem;margin-top:3px}
  .legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:9px;font-size:.8rem;color:var(--muted);align-items:center}
  .legend svg{vertical-align:middle;margin-right:5px}
  #wrap{display:flex;height:calc(100vh - 104px)}
  #canvas{flex:1;display:block}
  #panel{width:330px;border-left:1px solid var(--line);padding:16px;overflow:auto;font-size:.86rem}
  #panel h2{font-size:.95rem;margin:.2rem 0 .6rem}
  #panel .k{color:var(--muted);margin:.7rem 0 .1rem}
  #panel p{margin:.2rem 0}
  .pill{display:inline-block;padding:2px 9px;border-radius:10px;font-size:.75rem;color:#0c0d10;font-weight:600}
  .btn{margin-top:12px;display:inline-block;background:var(--purge);color:#fff;border:0;border-radius:7px;
       padding:8px 14px;font-size:.85rem;cursor:pointer;font-weight:600}
  .btn small{font-weight:400;opacity:.85}
  .hint{color:var(--muted);font-size:.82rem}
  circle,rect{cursor:pointer}
</style></head><body>
<header>
  <h1>__TITLE__</h1>
  <div class="sub">Agent memory colored by trust. Click an <b>untrusted source</b> (red-ringed square) to light up its blast radius &mdash; every memory it planted &mdash; then purge them.</div>
  <div class="legend">
    <span><svg width="14" height="14"><circle cx="7" cy="7" r="6" fill="#009E73"/></svg>clean (__CLEAN__)</span>
    <span><svg width="16" height="14"><circle cx="7" cy="7" r="6" fill="#C28400"/><circle cx="7" cy="7" r="6.5" fill="none" stroke="#C28400" stroke-dasharray="3 2"/></svg>quarantined (__QUAR__)</span>
    <span><svg width="14" height="14"><circle cx="7" cy="7" r="6" fill="#CC3311"/><line x1="3.5" y1="3.5" x2="10.5" y2="10.5" stroke="#0f1115" stroke-width="1.6"/><line x1="10.5" y1="3.5" x2="3.5" y2="10.5" stroke="#0f1115" stroke-width="1.6"/></svg>purged / untrusted (__PURGE__)</span>
    <span><svg width="16" height="16"><rect x="2" y="2" width="12" height="12" rx="3" fill="#8a91a2" stroke="#009E73" stroke-width="2"/></svg>trusted source</span>
    <span><svg width="16" height="16"><rect x="2" y="2" width="12" height="12" rx="3" fill="#8a91a2" stroke="#CC3311" stroke-width="2"/></svg>untrusted source</span>
  </div>
</header>
<div id="wrap">
  <svg id="canvas"></svg>
  <div id="panel"><p class="hint">Click any node for details. Click an untrusted source (red-ringed square) to see and purge its blast radius.</p></div>
</div>
<script>
const G = __DATA__;
const svg = document.getElementById('canvas'), panel = document.getElementById('panel');
const COL = {clean:'#009E73',quarantine:'#C28400',purge:'#CC3311',expired:'#7d7668',source:'#8a91a2',hi:'#4691CF'};
const BG='#0f1115';
let W = svg.clientWidth || 900, H = svg.clientHeight || 500;
let N = G.nodes, E = G.edges;
const esc = s => String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
N.forEach(n=>{n.x=W/2+(Math.random()-.5)*W*.6; n.y=H/2+(Math.random()-.5)*H*.6; n.vx=0; n.vy=0; n.op=1;});
const idx = {}; N.forEach((n,i)=>idx[n.id]=i);
const kids = {}; N.forEach(n=>{if(n.kind==='source')kids[n.id]=[];});
E.forEach(e=>{if(kids[e.from])kids[e.from].push(e.to);});
// density-derived constants so 14 nodes and 400 nodes both lay out sanely
const K = Math.max(28, Math.sqrt((W*H)/Math.max(1,N.length)));
let alpha = N.length ? 1 : 0, hi = null;
function live(){return N.filter(n=>!n.dead);}
function tick(){
  const L = live();
  for(let i=0;i<L.length;i++)for(let j=i+1;j<L.length;j++){
    const a=L[i],b=L[j];let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+.01,d=Math.sqrt(d2);
    const rep=(K*K*0.35)/d2;let fx=dx/d*rep,fy=dy/d*rep;a.vx+=fx;a.vy+=fy;b.vx-=fx;b.vy-=fy;}
  E.forEach(e=>{const a=N[idx[e.from]],b=N[idx[e.to]];if(a.dead||b.dead)return;
    let dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)+.01;const f=(d-K*0.9)*.02;
    let fx=dx/d*f,fy=dy/d*f;a.vx+=fx;a.vy+=fy;b.vx-=fx;b.vy-=fy;});
  L.forEach(n=>{n.vx=(n.vx+(W/2-n.x)*.002)*.85;n.vy=(n.vy+(H/2-n.y)*.002)*.85;
    n.vx=Math.max(-40,Math.min(40,n.vx));n.vy=Math.max(-40,Math.min(40,n.vy));
    n.x=Math.max(24,Math.min(W-24,n.x+n.vx));n.y=Math.max(24,Math.min(H-24,n.y+n.vy));});
}
function nodeSVG(n,i){
  const dim = hi && !hi.has(n.id) ? .22 : n.op;
  const on = hi && hi.has(n.id);
  if(n.kind==='source'){
    const ring = n.trusted?COL.clean:COL.purge;
    let s=`<rect x="${n.x-9}" y="${n.y-9}" width="18" height="18" rx="3" fill="${COL.source}" stroke="${on?COL.hi:ring}" stroke-width="${on?3:2.5}" opacity="${dim}" data-i="${i}"/>`;
    if(N.length<=40) s+=`<text x="${n.x}" y="${n.y+24}" text-anchor="middle" font-size="11" fill="#9aa0aa" opacity="${dim}">${esc(n.label)}</text>`;
    return s;
  }
  const c=COL[n.trust]||COL.source, r=9;
  let s=`<circle cx="${n.x}" cy="${n.y}" r="${r}" fill="${c}" opacity="${dim}" stroke="${on?COL.hi:BG}" stroke-width="${on?3:1.5}" data-i="${i}"/>`;
  if(n.trust==='purge') s+=`<line x1="${n.x-4}" y1="${n.y-4}" x2="${n.x+4}" y2="${n.y+4}" stroke="${BG}" stroke-width="1.6" opacity="${dim}"/><line x1="${n.x+4}" y1="${n.y-4}" x2="${n.x-4}" y2="${n.y+4}" stroke="${BG}" stroke-width="1.6" opacity="${dim}"/>`;
  if(n.trust==='quarantine') s+=`<circle cx="${n.x}" cy="${n.y}" r="${r+3}" fill="none" stroke="${c}" stroke-dasharray="3 2" opacity="${dim}"/>`;
  return s;
}
function draw(){
  if(!N.length){svg.innerHTML=`<text x="${W/2}" y="${H/2}" text-anchor="middle" fill="#9aa0aa">no memories in store</text>`;return;}
  let s='';
  E.forEach(e=>{const a=N[idx[e.from]],b=N[idx[e.to]];if(a.dead||b.dead)return;
    const on=hi&&hi.has(e.from)&&hi.has(e.to);const op=Math.min(a.op,b.op)*(hi&&!on?.25:1);
    s+=`<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${on?COL.hi:'#2a2d34'}" stroke-width="${on?2:1}" opacity="${op}"/>`;});
  N.forEach((n,i)=>{if(!n.dead)s+=nodeSVG(n,i);});
  svg.innerHTML=s;
  svg.querySelectorAll('[data-i]').forEach(el=>el.onclick=ev=>{ev.stopPropagation();select(+el.dataset.i);});
}
svg.onclick=()=>{hi=null;draw();panel.innerHTML='<p class="hint">Click any node for details.</p>';};
function loop(){if(alpha>0.02){for(let k=0;k<3;k++)tick();alpha*=0.97;}draw();requestAnimationFrame(loop);}
requestAnimationFrame(loop);
function select(i){
  const n=N[i];
  if(n.kind==='source'){
    hi=new Set([n.id]);kids[n.id].forEach(m=>hi.add(m));draw();
    const ch=kids[n.id].map(m=>N[idx[m]]);const pois=ch.filter(k=>k.trust==='purge').length;
    panel.innerHTML=`<h2>Source: ${esc(n.label)}</h2>
      <p class="pill" style="background:${n.trusted?COL.clean:COL.purge}">${n.trusted?'trusted origin':'UNTRUSTED origin'}</p>
      <p class="k">blast radius</p><p><b>${ch.length}</b> memories from this source (${pois} would be purged by provenance).</p>
      <p class="hint">Highlighted: every memory this source wrote. Edges show provenance (which source wrote which memory), not influence.</p>
      ${(!n.trusted&&pois)?`<button class="btn" id="pb">Purge by provenance &nbsp;<small>(origin-based, not detection)</small></button>`:''}`;
    const pb=document.getElementById('pb');if(pb)pb.onclick=()=>purge(n.id);
  } else {
    hi=null;draw();
    panel.innerHTML=`<h2>Memory</h2>
      <p><span class="pill" style="background:${COL[n.trust]}">${esc(n.trust_label)}</span></p>
      <p class="k">source</p><p>${esc(n.source)}</p>
      <p class="k">confidence</p><p>${esc(n.confidence)}</p>
      <p class="k">content</p><p>${esc(n.content)}</p>
      ${n.reason?`<p class="k">why</p><p>${esc(n.reason)}</p>`:''}`;
  }
}
function purge(srcId){
  const targets=kids[srcId].map(m=>N[idx[m]]).filter(k=>k.trust==='purge');
  const t0=performance.now();
  (function fade(t){const p=Math.min(1,(t-t0)/600);targets.forEach(k=>k.op=1-p);draw();
    if(p<1){requestAnimationFrame(fade);}else{
      targets.forEach(k=>{k.dead=true;});hi=null;draw();retally();
      panel.innerHTML=`<h2>Purged</h2><p>Removed <b>${targets.length}</b> memories from an untrusted source.</p>
        <p class="hint">Provenance-based purge. Directives hidden inside <em>trusted</em> memories are not auto-removed &mdash; those are quarantined for a human.</p>`;
    }})(t0);
}
function retally(){
  const c={clean:0,quarantine:0,purge:0};N.forEach(n=>{if(n.kind==='memory'&&!n.dead&&c[n.trust]!=null)c[n.trust]++;});
  const L=document.querySelectorAll('.legend span');
  if(L[0])L[0].lastChild.textContent=`clean (${c.clean})`;
  if(L[1])L[1].lastChild.textContent=`quarantined (${c.quarantine})`;
  if(L[2])L[2].lastChild.textContent=`purged / untrusted (${c.purge})`;
}
addEventListener('resize',()=>{const nW=svg.clientWidth,nH=svg.clientHeight;if(!nW||!nH)return;
  N.forEach(n=>{n.x*=nW/W;n.y*=nH/H;});W=nW;H=nH;alpha=Math.max(alpha,.4);});
</script></body></html>"""
