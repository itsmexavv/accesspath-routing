/* No external scripts. All user-controlled text is escaped before rendering. */
const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const peso = cents => new Intl.NumberFormat('en-PH', {style:'currency', currency:'PHP'}).format(cents/100);
const today = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
const option = (value, name) => `<option value="${esc(value)}">${esc(name)}</option>`;
const field = (label, name, type='text', extra='') => `<label class="field">${label}<input name="${name}" type="${type}" ${extra} required></label>`;
const stat = (label, value) => `<div class="stat"><span>${label}</span><strong>${esc(value)}</strong></div>`;
const empty = cols => `<tr><td class="empty" colspan="${cols}">No records yet. Add one to get started.</td></tr>`;
let toastTimer;
function toast(message, error=false) { const el=$('#toast'); el.textContent=message; el.className=error?'error':''; el.hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.hidden=true,6000); }
async function api(app, path, method='GET', data) {
  const response = await fetch(`/api/${app}${path}`, {method, ...(data===undefined?{}:{headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})});
  const result = await response.json();
  if(!response.ok) throw new Error(result.error || 'Request failed.');
  return result;
}
function bindForm(selector, action) {
  $(selector).addEventListener('submit', async event => {
    event.preventDefault(); const form=event.currentTarget, button=form.querySelector('button[type="submit"]');
    button.disabled=true;
    try { await action(Object.fromEntries(new FormData(form)), form); } catch(error) { toast(error.message,true); }
    finally { button.disabled=false; }
  });
}
function bindAction(selector, action) {
  $(selector).addEventListener('click', async event => { const button=event.target.closest('button'); if(!button) return; button.disabled=true;
    try { await action(button); } catch(error) { toast(error.message,true); } finally { button.disabled=false; }
  });
}
function hero(number, heading, description, track) { return `<header class="hero hero-row"><div><div class="eyebrow">AccessPath / ${track}</div><h1>${heading}</h1><p>${description}</p></div><span class="badge">Interactive demo</span></header>`; }
async function accesspath() {
  $('#view').innerHTML=hero('04','A path that fits your needs.','Compare the shortest route with a route that respects your mobility preferences.','Algorithms')+`<div class="notice">Fictional campus and unverified demo measurements. This is an algorithm demonstration, not real-world navigation guidance.</div><div class="split"><div><section class="panel"><h2>Campus route explorer</h2><svg id="map" class="map" viewBox="0 0 710 420" role="img" aria-label="Fictional campus paths with the planned route highlighted"></svg><p class="hint">Green = chosen route · Dashed = stairs · Red dotted = closed</p><div id="route-result" class="route-result" aria-live="polite">Choose your preferences, then plan a route.</div></section><section class="panel"><h2>Path conditions</h2><div id="segments" class="segments"></div></section></div><section class="panel"><h2>Your route preferences</h2><form id="route-form"><label class="field">Start<select name="start" id="start"></select></label><label class="field">Destination<select name="end" id="end"></select></label><label class="check"><input type="checkbox" name="step_free" checked> Avoid stairs</label>${field('Maximum slope (%)','max_slope','number','min="0" max="20" step="0.5" value="8"')}${field('Minimum path width (cm)','min_width','number','min="50" max="250" value="90"')}<button type="submit">Plan route</button></form><p>Close a segment below the map to test rerouting. Constraints are preferences, not accessibility certifications.</p></section></div>`;
  let map, chosen=[];
  function draw() { const nodes=Object.fromEntries(map.nodes.map(n=>[n.id,n])); $('#map').innerHTML=`<title>Fictional campus route</title>${map.edges.map(e=>{ const a=nodes[e.a],b=nodes[e.b]; return `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" class="${e.stairs?'stairs ':''}${e.blocked?'blocked ':''}${chosen.includes(e.id)?'route':''}"><title>${esc(a.name)} to ${esc(b.name)}: ${e.distance} m</title></line>`; }).join('')}${map.nodes.map(n=>`<g><circle cx="${n.x}" cy="${n.y}" r="10"/><text x="${n.x}" y="${n.y-20}" text-anchor="middle">${esc(n.name)}</text></g>`).join('')}`; $('#segments').innerHTML=map.edges.map(e=>`<div class="segment"><div>${esc(nodes[e.a].name)} ↔ ${esc(nodes[e.b].name)}<small>${e.distance} m · ${e.slope}% slope · ${e.width} cm wide${e.stairs?' · Stairs':''}</small></div><button class="small ${e.blocked?'danger':'secondary'}" data-id="${e.id}" data-blocked="${e.blocked}">${e.blocked?'Reopen':'Close path'}</button></div>`).join(''); }
  async function refresh() { map=await api('accesspath','/map'); draw(); }
  bindForm('#route-form',async d=>{ const result=await api('accesspath','/plan','POST',{start:d.start,end:d.end,step_free:d.step_free==='on',max_slope:Number(d.max_slope),min_width:Number(d.min_width)}); chosen=result.edges; draw(); const names=Object.fromEntries(map.nodes.map(n=>[n.id,n.name])); $('#route-result').innerHTML=result.found?`<strong>${result.distance} metres</strong>${result.nodes.map(n=>esc(names[n])).join(' → ')}<p>${result.excluded.length} segments excluded by your preferences or closures.</p>`:'<strong>No route available</strong>Try different preferences or reopen a path. Your constraints were respected.'; });
  bindAction('#segments',async b=>{ await api('accesspath',`/edges/${b.dataset.id}`,'PATCH',{blocked:b.dataset.blocked==='0'}); chosen=[]; await refresh(); $('#route-result').textContent='Path conditions changed. Plan again to refresh your route.'; toast('Path condition updated.'); });
  await refresh(); $('#start').innerHTML=map.nodes.map(n=>option(n.id,n.name)).join(''); $('#end').innerHTML=$('#start').innerHTML; $('#start').value='gate'; $('#end').value='lab';
}
Promise.resolve().then(()=>accesspath()).catch(error=>{toast(error.message,true); console.error(error);});
