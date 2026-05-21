"""Ops dashboard HTML — the demo Maya asked for on 5/20.

Lead arrives (Yelp / Thumbtack) → router visibly runs all gates with
per-step timing → < 2s budget visualized → Vapi web-call auto-places
with the chosen agent → live transcript streams → booking lands in
the (mock) Google Sheet + Telegram alert fires.

Single self-contained string so Vercel can serve it without static
build steps. Tokens (__COMPANY__, __FEE__, __PHONE__, __BOT__) are
substituted by main.home().
"""

OPS_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__COMPANY__ — AI Dispatcher</title>
<style>
:root{
  --bg:#070b13; --bg2:#0c1320; --card:#0f1828; --card2:#15203a;
  --line:#22304a; --line2:#2f4264;
  --ink:#e9eef9; --mut:#8a99b3; --mut2:#5a6a85;
  --green:#1fb888; --green-d:#0e6e54;
  --teal:#2bd0bd;
  --blue:#5ba8ff; --blue-d:#2056a8;
  --amber:#e8a23a; --amber-d:#7a5413;
  --red:#e25555; --red-d:#5b2424;
  --purple:#a07cff;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:radial-gradient(1200px 600px at 10% -10%,#11244a55,transparent),var(--bg);
  color:var(--ink);min-height:100vh;
  font-family:-apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif;
  font-size:14px}
a{color:var(--blue);text-decoration:none}

.wrap{max-width:1380px;margin:0 auto;padding:18px 22px 80px}

/* ── HEADER ─────────────────────────────────────────────────────── */
.head{display:flex;align-items:center;justify-content:space-between;
  gap:14px;margin-bottom:14px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:12px}
.logo{width:44px;height:44px;border-radius:12px;
  background:linear-gradient(135deg,#22d3a5,#5ba8ff);
  display:flex;align-items:center;justify-content:center;
  font-weight:800;color:#04121a;font-size:20px;letter-spacing:.4px}
.brand h1{font-size:17px;letter-spacing:.2px}
.brand .sub{font-size:12px;color:var(--mut);margin-top:3px}
.badges{display:flex;gap:8px;flex-wrap:wrap}
.badge{font-size:11px;padding:5px 9px;border-radius:999px;
  background:#162033;border:1px solid var(--line);color:var(--mut);cursor:default}
.badge.live{color:#7af5cb;border-color:#235e4a;background:#0e2a22}
.badge.dry{color:#f5cf7a;border-color:#5e4a23;background:#241c0e}

.tabs{display:flex;gap:8px;margin-bottom:18px}
.tab{padding:8px 14px;border:1px solid var(--line);border-radius:10px;
  background:#101a2c;color:#bcc8de;font-size:12.5px;font-weight:500;
  cursor:pointer;text-decoration:none}
.tab.on{background:linear-gradient(135deg,#1e3358,#11244a);border-color:#3d5e9c;color:#fff}
.tab:hover{border-color:var(--line2)}

/* ── AGENT FLOOR ────────────────────────────────────────────────── */
.floor{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:14px}
@media (max-width:880px){.floor{grid-template-columns:1fr}}
.agent{background:linear-gradient(135deg,#101a2c,#0c1424);
  border:1px solid var(--line);border-radius:14px;padding:13px 15px;
  display:flex;align-items:center;gap:13px;
  position:relative;overflow:hidden}
.agent::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--mut2)}
.agent.idle::before{background:var(--green)}
.agent.busy::before{background:var(--amber);box-shadow:0 0 14px var(--amber)}
.agent.offline::before{background:var(--mut2)}
.av{width:40px;height:40px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-weight:700;font-size:16px;color:#fff;flex:none}
.av.amanda{background:linear-gradient(135deg,#1fb888,#0e6e54)}
.av.tony{background:linear-gradient(135deg,#5ba8ff,#2056a8)}
.av.sofia{background:linear-gradient(135deg,#a07cff,#6244a8)}
.agent .nm{font-weight:600;font-size:14.5px;display:flex;align-items:center;gap:8px}
.agent .nm .dot{width:7px;height:7px;border-radius:50%;background:var(--mut)}
.agent.idle .nm .dot{background:var(--green);
  box-shadow:0 0 0 3px #1fb88830;animation:pulse 1.6s ease-out infinite}
.agent.busy .nm .dot{background:var(--amber);
  box-shadow:0 0 0 3px #e8a23a30;animation:pulse 1s ease-out infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 currentColor}
  100%{box-shadow:0 0 0 8px transparent}}
.agent .why{font-size:11px;color:var(--mut);margin-top:3px;line-height:1.45}
.agent .stat{margin-left:auto;text-align:right}
.agent .st{font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:var(--mut2)}
.agent .sv{font-size:12.5px;font-weight:600;color:var(--ink)}
.agent .lang{display:inline-block;font-size:9.5px;padding:1px 5px;border-radius:3px;
  background:#15203a;color:#bcc8de;letter-spacing:.5px;margin-right:3px}

/* ── LEAD SOURCE STRIP ──────────────────────────────────────────── */
.fire{background:#0f1828;border:1px solid var(--line);border-radius:14px;
  padding:13px 15px;margin-bottom:14px}
.fire h3{font-size:11px;letter-spacing:.7px;text-transform:uppercase;
  color:#bcc8de;margin-bottom:10px;display:flex;align-items:center;gap:8px}
.fire h3 .hint{font-weight:400;color:var(--mut);text-transform:none;letter-spacing:0;font-size:11px;margin-left:auto}
.fire-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
@media (max-width:880px){.fire-grid{grid-template-columns:1fr 1fr}}
@media (max-width:600px){.fire-grid{grid-template-columns:1fr}}
.scn{background:#0a1322;border:1px solid var(--line);border-radius:10px;
  padding:10px 12px;cursor:pointer;text-align:left;color:var(--ink);
  display:flex;flex-direction:column;gap:4px;transition:all .15s ease;
  position:relative;overflow:hidden}
.scn:hover{border-color:var(--green);background:#0e1d33}
.scn:disabled{opacity:.4;cursor:not-allowed}
.scn .tag{position:absolute;top:8px;right:8px;font-size:9px;padding:2px 6px;
  border-radius:4px;letter-spacing:.5px;text-transform:uppercase;font-weight:600}
.scn .tag.booking{background:#0f2a22;color:var(--green)}
.scn .tag.spanish{background:#1c1a3b;color:var(--purple)}
.scn .tag.rollover{background:#231c0c;color:var(--amber)}
.scn .tag.queued{background:#162638;color:var(--blue)}
.scn .tag.rejected{background:#2a1414;color:var(--red)}
.scn .tag.text{background:#1a1a2c;color:#9cb3da}
.scn .label{font-size:12.5px;font-weight:600;padding-right:50px;line-height:1.4}
.scn .summary{font-size:11px;color:var(--mut);line-height:1.45}

/* ── MAIN GRID ──────────────────────────────────────────────────── */
.main{display:grid;grid-template-columns:1.45fr 1fr;gap:14px}
@media (max-width:1080px){.main{grid-template-columns:1fr}}

.panel{background:#0f1828;border:1px solid var(--line);border-radius:14px;
  overflow:hidden;margin-bottom:14px}
.panel h3{font-size:11px;letter-spacing:.7px;text-transform:uppercase;
  color:#bcc8de;padding:12px 16px;background:#0b1424;
  border-bottom:1px solid var(--line);font-weight:600;
  display:flex;align-items:center;gap:9px}
.panel h3 .meta{margin-left:auto;font-weight:400;color:var(--mut);letter-spacing:0;text-transform:none;font-size:11.5px}
.panel .body{padding:14px 16px}
.panel.empty .body{color:var(--mut);font-size:12px;padding:18px 16px}

/* ── ROUTING VIZ ────────────────────────────────────────────────── */
.lead-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.lead-head .src{background:#16243d;color:var(--blue);font-size:10px;letter-spacing:.5px;
  text-transform:uppercase;padding:3px 7px;border-radius:4px;font-weight:600}
.lead-head .nm{font-weight:600;font-size:14px}
.lead-head .why{color:var(--mut);font-size:12.5px}
.lead-head .lang{font-size:10px;background:#1c1a3b;color:var(--purple);padding:2px 6px;border-radius:3px;letter-spacing:.5px}

.budget{background:#0a1322;border:1px solid var(--line);border-radius:10px;
  padding:10px 14px;margin-bottom:12px;display:flex;align-items:center;gap:14px}
.budget .lbl{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.5px}
.budget .bar{flex:1;background:#0a1626;border:1px solid var(--line);height:8px;border-radius:4px;overflow:hidden;position:relative}
.budget .fill{height:100%;background:linear-gradient(90deg,#22d3a5,#5ba8ff);
  width:0;transition:width .3s ease-out}
.budget .fill.over{background:linear-gradient(90deg,#e8a23a,#e25555)}
.budget .now{font-size:14px;font-weight:700;font-variant-numeric:tabular-nums;color:#fff;min-width:80px;text-align:right}
.budget .max{font-size:11px;color:var(--mut);min-width:64px}
.budget.hit .now{color:var(--green)}
.budget.miss .now{color:var(--red)}

.steps{display:flex;flex-direction:column;gap:6px;margin-bottom:12px}
.step{display:grid;grid-template-columns:60px 22px 1fr auto;gap:10px;align-items:center;
  padding:8px 10px;border-radius:8px;background:#0a1322;
  border:1px solid #18243d;
  opacity:0;transform:translateX(-6px);transition:all .25s ease}
.step.show{opacity:1;transform:translateX(0)}
.step.ok{border-color:#1d5443}
.step.bad{border-color:#5b2a2a}
.step .ms{font-variant-numeric:tabular-nums;color:var(--mut);font-size:11.5px;text-align:right}
.step .ic{width:18px;height:18px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:11px;flex:none}
.step.ok .ic{background:#0f2a22;color:var(--green);border:1px solid #1d5443}
.step.ok .ic::after{content:"✓"}
.step.bad .ic{background:#2a1414;color:var(--red);border:1px solid #5b2a2a}
.step.bad .ic::after{content:"✕"}
.step .lbl{font-weight:600;font-size:13px}
.step .det{font-size:11.5px;color:var(--mut);grid-column:3;}

.outcome{display:flex;align-items:center;gap:10px;padding:11px 14px;border-radius:10px;
  background:#0a1322;border:1px solid var(--line);margin-bottom:10px}
.outcome .ic{font-size:18px}
.outcome.call{border-color:#1d5443;background:#0e2a22}
.outcome.queue{border-color:#235e8c;background:#0d2238}
.outcome.sms{border-color:#5e4a23;background:#241c0e}
.outcome.reject{border-color:#5b2a2a;background:#2a1414}
.outcome .txt{font-size:13px}
.outcome .why{color:var(--mut);font-size:11.5px;margin-top:2px}
.outcome .btn{margin-left:auto}

.btn{background:linear-gradient(135deg,#22d3a5,#1fa884);color:#04121a;
  border:0;padding:9px 16px;border-radius:8px;cursor:pointer;font-weight:700;
  font-size:13px;letter-spacing:.2px;transition:transform .1s ease;display:inline-flex;align-items:center;gap:7px}
.btn:hover{filter:brightness(1.08)}
.btn:active{transform:translateY(1px)}
.btn:disabled{opacity:.45;cursor:not-allowed;filter:none}
.btn.ghost{background:#1a2535;color:#cdd7e6;border:1px solid var(--line)}
.btn.ghost:hover{background:#22324a}
.btn.danger{background:#3a1a1a;color:#ffb8b8;border:1px solid #5b2a2a}

/* ── LIVE CALL ──────────────────────────────────────────────────── */
.live{background:#0f1828;border:1px solid var(--line);border-radius:14px;
  overflow:hidden;margin-bottom:14px;display:flex;flex-direction:column}
.live .head{display:flex;align-items:center;gap:12px;padding:12px 16px;
  background:linear-gradient(90deg,#142a48,#0e1d33);
  border-bottom:1px solid var(--line);margin:0;flex-wrap:nowrap}
.live .head .av{width:36px;height:36px;border-radius:50%;font-size:14px}
.live .head .nm{font-weight:600;font-size:14px}
.live .head .stat{font-size:11px;color:var(--mut);margin-top:2px;display:flex;align-items:center;gap:6px}
.live .head .stat .rd{width:6px;height:6px;border-radius:50%;background:var(--red);animation:rec 1.4s ease-in-out infinite}
@keyframes rec{0%,100%{opacity:.3}50%{opacity:1}}
.live .head .pull{margin-left:auto;display:flex;gap:8px}

.transcript{flex:1;min-height:240px;max-height:380px;overflow-y:auto;padding:14px 16px;
  display:flex;flex-direction:column;gap:8px;background:#080f1c}
.tline{max-width:78%;padding:9px 12px;border-radius:11px;font-size:13.5px;line-height:1.5}
.tline.bot{align-self:flex-start;background:#152138;border-bottom-left-radius:3px}
.tline.you{align-self:flex-end;background:#0e3e2f;color:#d6f1e5;border-bottom-right-radius:3px}
.trole{font-size:10px;color:var(--mut2);letter-spacing:.4px;margin:6px 4px 0}
.trole.you{align-self:flex-end}
.tline.empty{align-self:center;color:var(--mut);background:transparent;font-style:italic;font-size:12px}

/* ── GOOGLE SHEET ───────────────────────────────────────────────── */
.sheet{display:flex;flex-direction:column;gap:0}
.sheet-row{display:grid;grid-template-columns:48px 1fr 1fr 22px;gap:8px;padding:8px 0;border-bottom:1px dashed #16223a;font-size:12px;align-items:center}
.sheet-row.head{font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--mut);border-bottom:1px solid var(--line);padding-bottom:9px;font-weight:600}
.sheet-row:last-child{border-bottom:0}
.sheet-row .t{font-weight:600;color:#dde6f4}
.sheet-row.free .t{color:var(--green)}
.sheet-row.taken .t{color:var(--mut2)}
.sheet-row .booked-ic{font-size:13px}
.sheet-row.taken{opacity:.55}
.sheet-row.held{background:#1c1a3b;border-radius:6px;padding:8px 6px}
.sheet-row.held .booked-ic{color:var(--purple)}

/* ── QUEUE ──────────────────────────────────────────────────────── */
.queue-row{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px dashed #16223a;font-size:12.5px}
.queue-row:last-child{border-bottom:0}
.queue-row .ic{font-size:14px;flex:none}
.queue-row .sum{flex:1;color:var(--ink)}
.queue-row .fire{color:var(--amber);font-size:11.5px;font-variant-numeric:tabular-nums}
.queue-row .reason{font-size:10.5px;color:var(--mut);background:#15203a;padding:1px 6px;border-radius:3px;letter-spacing:.3px;text-transform:uppercase}

/* ── BOOKINGS ───────────────────────────────────────────────────── */
.bk{display:flex;flex-direction:column;gap:3px;padding:11px 0;border-bottom:1px dashed #16223a;font-size:12.5px;line-height:1.55}
.bk:last-child{border-bottom:0}
.bk b{font-size:13.5px;color:#fff}
.bk .meta{color:var(--mut);font-size:11.5px}
.bk .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.bk .pill{font-size:9.5px;padding:1px 6px;border-radius:3px;
  background:#15203a;color:var(--mut);letter-spacing:.5px;text-transform:uppercase;font-weight:600}
.bk .pill.in{background:#0f2a22;color:var(--green)}
.bk .pill.out{background:#16243d;color:var(--blue)}

/* ── MISC ───────────────────────────────────────────────────────── */
.lead-feed-empty{color:var(--mut);font-style:italic;font-size:12.5px;text-align:center;padding:30px 14px}
.timestamp{color:var(--mut);font-size:11px;font-variant-numeric:tabular-nums}
.muted{color:var(--mut)}
.right{margin-left:auto}
</style>
</head>
<body>
<div class="wrap">

<div class="head">
  <div class="brand">
    <div class="logo">S</div>
    <div>
      <h1>__COMPANY__ — AI Dispatcher</h1>
      <div class="sub">Sub-2-second lead-to-call · Yelp · Thumbtack · Vapi · Telegram</div>
    </div>
  </div>
  <div class="badges" id="badges"></div>
</div>

<div class="tabs">
  <a class="tab on">⚡ Live Operations</a>
  <a class="tab" href="/console">🎙 Conversation Engine</a>
  <span style="flex:1"></span>
  <button class="tab" onclick="resetDemo()" style="background:#2a1414;border-color:#5b2a2a;color:#ffb8b8">↻ Reset demo</button>
</div>

<!-- AGENT FLOOR -->
<div class="floor" id="agents"></div>

<!-- LEAD SOURCE STRIP -->
<div class="fire">
  <h3>⚡ Fire a lead
    <span class="hint">Each click simulates the real Yelp/Thumbtack webhook payload</span>
  </h3>
  <div class="fire-grid" id="leads"></div>
</div>

<!-- MAIN GRID -->
<div class="main">

  <div>
    <!-- ROUTING VIZ -->
    <div class="panel" id="routerPanel">
      <h3>🧭 Routing pipeline <span class="meta" id="routerMeta">awaiting first lead…</span></h3>
      <div class="body" id="routerBody">
        <div class="lead-feed-empty">Click any lead above to fire a webhook into the dispatcher.</div>
      </div>
    </div>

    <!-- LIVE CALL -->
    <div class="live" id="livePanel" style="display:none">
      <div class="head">
        <div class="av" id="liveAv">T</div>
        <div>
          <div class="nm" id="liveAgent">Tony</div>
          <div class="stat" id="liveStat"><span class="rd"></span> connecting…</div>
        </div>
        <div class="pull">
          <button class="btn ghost" onclick="testRespond()">📋 paste reply</button>
          <button class="btn danger" onclick="endCallManual()">end call</button>
        </div>
      </div>
      <div class="transcript" id="transcript">
        <div class="tline empty">Transcript will stream here as the call progresses.</div>
      </div>
    </div>
  </div>

  <div>
    <!-- GOOGLE SHEET (mock) -->
    <div class="panel">
      <h3>📊 Technician Availability <span class="meta">Google Sheet (mock)</span></h3>
      <div class="body">
        <div class="sheet" id="sheet">
          <div class="sheet-row head"><span>Tech</span><span>Day</span><span>Window</span><span></span></div>
        </div>
      </div>
    </div>

    <!-- QUEUE -->
    <div class="panel" id="queuePanel">
      <h3>⏰ Queue & retry ladder <span class="meta" id="queueMeta">empty</span></h3>
      <div class="body" id="queueBody">
        <div class="muted" style="font-size:12px">After-hours leads and unanswered retries land here (20 min → 24 h → 72 h, max 3 attempts).</div>
      </div>
    </div>

    <!-- BOOKINGS -->
    <div class="panel" id="bookingsPanel">
      <h3>✅ Confirmed bookings <span class="meta" id="bkMeta">0</span></h3>
      <div class="body" id="bookings">
        <div class="muted" style="font-size:12px">No bookings yet.</div>
      </div>
    </div>
  </div>
</div>
</div>

<!-- Vapi web SDK loader (lazy, only when first call starts) -->
<script>
let CFG = null;
let CURRENT_CALL = null;
let CURRENT_LEAD = null;
let vapi = null;

async function boot(){
  CFG = await (await fetch("/api/config")).json();
  renderBadges();
  renderAgents(CFG);
  renderLeadButtons();
  loadSheet();
  loadQueue();
  loadBookings();
  startPolling();
}
boot();

function renderBadges(){
  const b = document.getElementById("badges");
  b.innerHTML = "";
  b.appendChild(badge(CFG.llm_live ? "LLM · live" : "LLM · scripted", CFG.llm_live));
  b.appendChild(badge(CFG.vapi_live ? "Vapi · live" : "Vapi · not configured", CFG.vapi_live));
  b.appendChild(badge(CFG.telegram_live ? "Telegram · live" : "Telegram · dry-run", CFG.telegram_live));
  b.appendChild(badge("SMS · dry-run (Twilio in prod)", false));
}
function badge(text, live){
  const e = document.createElement("span");
  e.className = "badge " + (live ? "live" : "dry");
  e.textContent = text;
  return e;
}

function renderAgents(cfg){
  const wrap = document.getElementById("agents");
  wrap.innerHTML = "";
  cfg.agents.forEach(a => {
    const el = document.createElement("div");
    el.className = "agent idle";
    el.id = "agent-" + a.key;
    el.innerHTML = `
      <div class="av ${a.key}">${a.name[0]}</div>
      <div style="flex:1;min-width:0">
        <div class="nm"><span class="dot"></span>${a.name}</div>
        <div class="why">${escapeHtml(a.voice)}</div>
        <div style="margin-top:4px">${(a.languages||[]).map(l => '<span class="lang">' + l + '</span>').join('')}<span class="lang">${a.channel}</span></div>
      </div>
      <div class="stat">
        <div class="st">status</div>
        <div class="sv" id="agent-st-${a.key}">idle</div>
      </div>`;
    wrap.appendChild(el);
  });
}

async function refreshAgents(){
  try {
    const j = await (await fetch("/api/agents/status")).json();
    Object.entries(j.agents).forEach(([k,a]) => {
      const card = document.getElementById("agent-" + k);
      const sv = document.getElementById("agent-st-" + k);
      if (card){
        card.classList.remove("idle","busy","offline");
        card.classList.add(a.status || "idle");
      }
      if (sv) sv.textContent = a.status || "idle";
    });
  } catch(e){}
}

function renderLeadButtons(){
  const c = document.getElementById("leads"); c.innerHTML = "";
  CFG.sample_leads.forEach(s => {
    const b = document.createElement("button");
    b.className = "scn";
    b.onclick = () => fireLead(s.key);
    b.innerHTML = `
      <span class="tag ${s.tag}">${s.tag}</span>
      <span class="label">${escapeHtml(s.label)}</span>
      <span class="summary">${escapeHtml(s.summary)}</span>`;
    c.appendChild(b);
  });
}

// ─── FIRE LEAD ───────────────────────────────────────────────────
async function fireLead(key){
  document.querySelectorAll("#leads .scn").forEach(b => b.disabled = true);
  const r = await api("/api/leads/simulate", {key});
  CURRENT_LEAD = r;
  await animateDecision(r);
  if (r.decision.action === "call"){
    const start = await api("/api/vapi/start", {lead_id: r.lead_id});
    CURRENT_CALL = start;
    await startVapiCall(start);
  }
  await Promise.all([refreshAgents(), loadSheet(), loadQueue()]);
  document.querySelectorAll("#leads .scn").forEach(b => b.disabled = false);
}

// ─── ROUTING ANIMATION ───────────────────────────────────────────
async function animateDecision(r){
  const body = document.getElementById("routerBody");
  const d = r.decision;
  const lead = r.lead;
  document.getElementById("routerMeta").textContent =
    `${d.total_s}s · budget ${d.budget_hit ? '✓' : '✗'}`;

  body.innerHTML = `
    <div class="lead-head">
      <span class="src">${escapeHtml(lead.source)}</span>
      <span class="nm">${escapeHtml(lead.name || '(no name)')}</span>
      <span class="why">${escapeHtml(lead.city || '')} · ${escapeHtml(lead.appliance_hint || '')}</span>
      ${lead.language === "es" ? '<span class="lang">ES</span>' : ''}
      ${!lead.consent ? '<span class="lang" style="background:#2a1414;color:#e25555">NO CONSENT</span>' : ''}
      ${!lead.phone ? '<span class="lang" style="background:#241c0e;color:#e8a23a">NO PHONE</span>' : ''}
    </div>
    <div class="budget ${d.budget_hit ? 'hit' : 'miss'}">
      <span class="lbl">Lead → talk</span>
      <div class="bar"><div class="fill" id="budgetFill"></div></div>
      <span class="now" id="budgetNow">0 ms</span>
      <span class="max">/ 2000 ms</span>
    </div>
    <div class="steps" id="steps"></div>
    <div id="outcome"></div>`;

  const stepsHost = document.getElementById("steps");
  const fill = document.getElementById("budgetFill");
  const nowEl = document.getElementById("budgetNow");
  const start = performance.now();
  const allMs = d.steps.length ? d.steps[d.steps.length - 1].ms : 0;
  const replayMs = Math.max(allMs, 1400);   // stretch slightly so each step is legible

  for (let i = 0; i < d.steps.length; i++){
    const s = d.steps[i];
    const targetT = (s.ms / Math.max(1, allMs)) * replayMs;
    const elapsed = performance.now() - start;
    if (targetT > elapsed) await wait(targetT - elapsed);

    const row = document.createElement("div");
    row.className = "step " + (s.ok ? "ok" : "bad");
    row.innerHTML = `
      <span class="ms">${Math.round(s.ms)} ms</span>
      <span class="ic"></span>
      <span class="lbl">${escapeHtml(s.label)}</span>`;
    if (s.detail){
      const det = document.createElement("span");
      det.className = "det";
      det.textContent = s.detail;
      row.appendChild(det);
    }
    stepsHost.appendChild(row);
    requestAnimationFrame(() => row.classList.add("show"));

    const pct = Math.min(100, (s.ms / 2000) * 100);
    fill.style.width = pct + "%";
    if (s.ms > 2000) fill.classList.add("over");
    nowEl.textContent = Math.round(s.ms) + " ms";
  }

  // Outcome card
  const out = document.getElementById("outcome");
  const map = {
    call:   {ic:"📞", txt:"Placing Vapi call now",  why:`Routing to ${(d.agent_key||'').toUpperCase()} · ${d.reason}`, cls:"call"},
    queue:  {ic:"⏰", txt:"Queued",                 why:`${d.reason} · fires later`,                                   cls:"queue"},
    sms:    {ic:"💬", txt:"Sending text instead",   why:d.reason,                                                       cls:"sms"},
    reject: {ic:"🚫", txt:"Cannot serve this lead", why:d.reason,                                                       cls:"reject"},
  };
  const m = map[d.action] || map.queue;
  out.innerHTML = `
    <div class="outcome ${m.cls}">
      <div class="ic">${m.ic}</div>
      <div>
        <div class="txt"><b>${m.txt}</b></div>
        <div class="why">${escapeHtml(m.why)}</div>
      </div>
    </div>`;
}

// ─── VAPI WEB CALL ───────────────────────────────────────────────
async function startVapiCall(start){
  const live = document.getElementById("livePanel");
  live.style.display = "flex";
  document.getElementById("liveAgent").textContent = start.agent.name;
  const av = document.getElementById("liveAv");
  av.textContent = start.agent.name[0];
  av.className = "av " + start.agent.key;
  document.getElementById("liveStat").innerHTML = '<span class="rd"></span> connecting…';
  const tr = document.getElementById("transcript");
  tr.innerHTML = "";

  if (!start.vapi_configured || !start.public_key){
    addLine("system",
      "(Vapi is not configured in this environment — set VAPI_PUBLIC_KEY + VAPI_API_KEY in Vercel env. " +
      "The routing flow above is fully functional; the chat console at /console exercises the same brain in browser-text mode.)");
    setTimeout(() => addLine("bot", start.assistant.firstMessage, start.agent.name), 600);
    return;
  }

  try {
    // Vapi's @vapi-ai/web ships ESM-only and some CDNs double-wrap the
    // default export. Try a few candidate paths and CDNs.
    if (!window.__VapiCtor){
      addLine("system", "Loading Vapi SDK…");
      const cdns = [
        "https://esm.sh/@vapi-ai/web@latest",
        "https://cdn.jsdelivr.net/npm/@vapi-ai/web@latest/+esm",
        "https://cdn.skypack.dev/@vapi-ai/web",
      ];
      let lastErr = null;
      for (const url of cdns){
        try {
          const mod = await import(url);
          const ctor = _resolveCtor(mod);
          if (ctor){ window.__VapiCtor = ctor; break; }
          lastErr = "no constructor in " + url + " · keys=" + _keys(mod);
        } catch (e){ lastErr = url + " → " + (e?.message || e); }
      }
      if (!window.__VapiCtor){
        addLine("system", "Couldn't load Vapi SDK from any CDN. " + (lastErr || ""));
        document.getElementById("liveStat").textContent = "sdk load failed";
        return;
      }
      tr.innerHTML = "";
    }
    if (!vapi){
      vapi = new window.__VapiCtor(start.public_key);
      wireVapi();
    }
    document.getElementById("liveStat").innerHTML = '<span class="rd"></span> requesting mic…';
    await vapi.start(start.assistant);
  } catch (e){
    const msg = e?.message || String(e);
    addLine("system", "Vapi error: " + msg);
    if (/permission|denied|NotAllowed/i.test(msg)){
      addLine("system",
        "Looks like the browser blocked mic access. Click the 🔒 / 🎤 icon in the URL bar → " +
        "Allow microphone for this site → reload the page → fire the lead again.");
    }
    document.getElementById("liveStat").textContent = "call failed";
  }
}

function wireVapi(){
  vapi.on("call-start", () => {
    document.getElementById("liveStat").innerHTML = '<span class="rd"></span> in call';
    postEvent({kind:"in_progress"});
  });
  vapi.on("call-end", () => {
    document.getElementById("liveStat").textContent = "call ended";
    postEvent({kind:"ended", outcome:"answered"}).then(() => {
      loadBookings(); refreshAgents(); loadSheet();
    });
  });
  vapi.on("message", (msg) => {
    if (msg.type === "transcript" && msg.transcriptType === "final"){
      const role = msg.role === "user" ? "you" : "bot";
      addLine(role, msg.transcript, role === "bot" ? CURRENT_CALL.agent.name : "Customer");
      postEvent({kind:"transcript", role: msg.role, text: msg.transcript});
    }
  });
  vapi.on("error", (e) => {
    addLine("system", "Vapi error: " + (e?.message || JSON.stringify(e)));
  });
}

function postEvent(ev){
  if (!CURRENT_CALL) return Promise.resolve();
  return fetch("/api/vapi/event", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({call_id: CURRENT_CALL.call_id, ...ev}),
  }).catch(() => {});
}

function endCallManual(){
  if (vapi){ try { vapi.stop(); } catch(e){} }
  if (CURRENT_CALL) postEvent({kind:"ended", outcome:"answered"}).then(() => {
    loadBookings(); refreshAgents();
  });
  document.getElementById("liveStat").textContent = "call ended";
}

function testRespond(){
  const v = prompt("Type what the customer says (used when no mic / Vapi disabled):", "");
  if (!v) return;
  addLine("you", v, "Customer");
  postEvent({kind:"transcript", role:"user", text:v});
}

function addLine(role, text, label){
  const tr = document.getElementById("transcript");
  if (tr.querySelector(".tline.empty")) tr.innerHTML = "";
  const m = document.createElement("div");
  if (role === "system"){
    m.className = "tline empty"; m.textContent = text;
  } else {
    m.className = "tline " + (role === "you" ? "you" : "bot");
    m.textContent = text;
  }
  tr.appendChild(m);
  if (label && role !== "system"){
    const r = document.createElement("div");
    r.className = "trole" + (role === "you" ? " you" : "");
    r.textContent = label;
    tr.appendChild(r);
  }
  tr.scrollTop = tr.scrollHeight;
}

// ─── SHEET (technician availability) ─────────────────────────────
async function loadSheet(){
  const j = await (await fetch("/api/slots")).json();
  const wrap = document.getElementById("sheet");
  wrap.innerHTML = '<div class="sheet-row head"><span>Tech</span><span>Day</span><span>Window</span><span></span></div>';
  j.slots.forEach(s => {
    const row = document.createElement("div");
    const cls = s.free ? "free" : (s.held_for ? "held" : "taken");
    row.className = "sheet-row " + cls;
    row.innerHTML = `
      <span class="t">${escapeHtml(s.technician)}</span>
      <span>${escapeHtml(s.day)}</span>
      <span>${escapeHtml(s.window)}</span>
      <span class="booked-ic">${s.free ? "·" : (s.held_for ? "⏳" : "✕")}</span>`;
    wrap.appendChild(row);
  });
}

// ─── QUEUE ───────────────────────────────────────────────────────
async function loadQueue(){
  const j = await (await fetch("/api/queue")).json();
  const body = document.getElementById("queueBody");
  document.getElementById("queueMeta").textContent =
    j.queued.length ? `${j.queued.length} waiting` : "empty";
  if (!j.queued.length){
    body.innerHTML = '<div class="muted" style="font-size:12px">After-hours leads and unanswered retries land here (20 min → 24 h → 72 h, max 3 attempts).</div>';
    return;
  }
  body.innerHTML = j.queued.map(q => {
    const ic = q.reason === "retry" ? "🔁" : (q.reason === "outside business hours" ? "🌙" : "⏰");
    return `<div class="queue-row">
      <span class="ic">${ic}</span>
      <span class="sum">${escapeHtml(q.summary)}</span>
      <span class="reason">${escapeHtml(q.reason)}</span>
      <span class="fire">${escapeHtml(q.fire_label)}</span>
    </div>`;
  }).join("");
}

// ─── BOOKINGS ────────────────────────────────────────────────────
async function loadBookings(){
  const j = await (await fetch("/api/bookings")).json();
  document.getElementById("bkMeta").textContent = j.bookings.length;
  const c = document.getElementById("bookings");
  if (!j.bookings.length){
    c.innerHTML = '<div class="muted" style="font-size:12px">No bookings yet.</div>';
    return;
  }
  c.innerHTML = j.bookings.map(b => `
    <div class="bk">
      <div class="row">
        <span class="pill ${b.channel === "inbound" ? "in" : "out"}">${b.channel || b.agent}</span>
        <b>${escapeHtml(b.name || "(no name)")}</b>
      </div>
      <div class="meta">${escapeHtml(b.appliance || "")} ${b.brand ? " · " + escapeHtml(b.brand) : ""}</div>
      <div class="meta">${escapeHtml(b.window || "")} · ${escapeHtml(b.address || "")}</div>
      <div class="meta">Ref ${escapeHtml(b.id)} · agent ${escapeHtml(b.agent || "")} · fee ${b.fee_agreed ? "accepted" : "—"}</div>
    </div>`).join("");
}

// ─── POLLING ─────────────────────────────────────────────────────
function startPolling(){
  setInterval(() => {
    refreshAgents();
    loadQueue();
  }, 3000);
}

async function resetDemo(){
  await api("/api/demo/reset", {});
  CURRENT_LEAD = null; CURRENT_CALL = null;
  document.getElementById("routerBody").innerHTML =
    '<div class="lead-feed-empty">Click any lead above to fire a webhook into the dispatcher.</div>';
  document.getElementById("routerMeta").textContent = "awaiting first lead…";
  document.getElementById("livePanel").style.display = "none";
  await Promise.all([refreshAgents(), loadSheet(), loadQueue(), loadBookings()]);
}

// ─── helpers ─────────────────────────────────────────────────────
async function api(path, body){
  const r = await fetch(path, {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify(body || {}),
  });
  return r.json();
}
function wait(ms){ return new Promise(r => setTimeout(r, ms)); }

function _resolveCtor(m){
  // Try common export shapes from CJS→ESM transforms.
  const candidates = [
    m,
    m?.default,
    m?.default?.default,
    m?.Vapi,
    m?.default?.Vapi,
  ];
  for (const c of candidates){
    if (typeof c === "function") return c;
  }
  return null;
}
function _keys(o){ try { return Object.keys(o||{}).join(","); } catch(e){ return "?"; } }
function loadScript(src){
  return new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = src; s.onload = res; s.onerror = rej;
    document.head.appendChild(s);
  });
}
function escapeHtml(s){
  return String(s == null ? "" : s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
</script>
</body></html>
"""
