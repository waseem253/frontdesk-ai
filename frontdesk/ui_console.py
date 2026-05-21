"""The single-page demo console.

Kept as one self-contained string so Vercel can serve it without
worrying about static assets or build steps. Tokens like __COMPANY__,
__PHONE__, __BOT__, __FEE__ are substituted by main.home().
"""

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__COMPANY__ — AI Receptionist & Booking</title>
<style>
:root{
  --bg:#0a0e16; --card:#121a27; --card2:#172132; --line:#243049;
  --ink:#e9eef9; --mut:#8a99b3; --mut2:#5a6a85;
  --green:#1fb888; --green-d:#0f7a5e;
  --blue:#4a9eff; --blue-d:#1f5fb8;
  --amber:#e8a23a; --red:#e25555;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--ink);
  font-family:-apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif;
  min-height:100vh}
a{color:var(--blue);text-decoration:none}
.wrap{max-width:1240px;margin:0 auto;padding:18px 22px 60px}

/* ── HEADER ─────────────────────────────────────────────────────── */
.head{display:flex;align-items:center;justify-content:space-between;
  gap:14px;margin-bottom:18px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:12px}
.logo{width:42px;height:42px;border-radius:11px;
  background:linear-gradient(135deg,var(--green),var(--blue));
  display:flex;align-items:center;justify-content:center;
  font-weight:800;color:#fff;font-size:18px;letter-spacing:.5px}
.brand h1{font-size:17px;letter-spacing:.2px}
.brand .sub{font-size:12px;color:var(--mut);margin-top:2px}
.badges{display:flex;gap:8px;flex-wrap:wrap}
.badge{font-size:11px;padding:5px 9px;border-radius:999px;
  background:#15202e;border:1px solid var(--line);color:var(--mut)}
.badge.live{color:var(--green);border-color:#1d5443;background:#0f2a22}
.badge.dry{color:var(--amber);border-color:#4a3a18;background:#251c0c}

/* ── AGENT TOGGLE ───────────────────────────────────────────────── */
.agents{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px}
.agent{background:var(--card);border:1px solid var(--line);
  border-radius:14px;padding:14px 16px;cursor:pointer;
  display:flex;align-items:center;gap:14px;transition:all .15s ease}
.agent:hover{border-color:#2f4366}
.agent.on{border-color:var(--green);box-shadow:0 0 0 2px #1fb88822}
.avatar{width:44px;height:44px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-weight:700;font-size:18px;color:#fff;flex:none}
.avatar.amanda{background:linear-gradient(135deg,#1fb888,#1a857c)}
.avatar.tony{background:linear-gradient(135deg,#4a9eff,#3a4dbb)}
.agent .who{font-weight:600;font-size:14px}
.agent .why{font-size:11.5px;color:var(--mut);margin-top:2px;line-height:1.4}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;
  background:var(--mut);margin-right:6px;vertical-align:middle}
.agent.on .dot{background:var(--green);
  box-shadow:0 0 0 3px #1fb88830;animation:pulse 1.4s ease-out infinite}
@keyframes pulse{
  0%{box-shadow:0 0 0 0 #1fb88860}
  100%{box-shadow:0 0 0 8px #1fb88800}
}

/* ── MAIN GRID ──────────────────────────────────────────────────── */
.grid{display:grid;grid-template-columns:1fr 360px;gap:16px}
@media (max-width:980px){.grid{grid-template-columns:1fr}}

/* ── CALL PANEL ─────────────────────────────────────────────────── */
.call{background:var(--card);border:1px solid var(--line);
  border-radius:16px;overflow:hidden;display:flex;flex-direction:column}
.phbar{display:flex;align-items:center;gap:12px;padding:14px 18px;
  background:linear-gradient(90deg,#142435,#0d1828);border-bottom:1px solid var(--line)}
.phbar .icon{width:34px;height:34px;border-radius:50%;
  background:#0f2a22;border:1px solid #1d5443;color:var(--green);
  display:flex;align-items:center;justify-content:center;font-size:16px}
.phbar.ring .icon{animation:ring 1s ease-in-out infinite;
  background:#251c0c;border-color:#4a3a18;color:var(--amber)}
.phbar.active .icon{background:#0f2a22;color:var(--green)}
@keyframes ring{
  0%,100%{transform:rotate(0)}
  20%{transform:rotate(-12deg)}
  40%{transform:rotate(10deg)}
  60%{transform:rotate(-8deg)}
  80%{transform:rotate(6deg)}
}
.phbar .lbl{font-weight:600;font-size:14px}
.phbar .sublbl{font-size:12px;color:var(--mut);margin-top:2px}
.phbar .right{margin-left:auto;display:flex;align-items:center;gap:8px}
.status{font-size:11px;padding:5px 10px;border-radius:999px;
  background:#15202e;border:1px solid var(--line);color:var(--mut);
  letter-spacing:.4px;text-transform:uppercase}
.status.active{color:var(--green);border-color:#1d5443;background:#0f2a22}
.status.ring{color:var(--amber);border-color:#4a3a18;background:#251c0c}
.status.ended{color:var(--mut);background:#1a1f2a}
.status.esc{color:var(--red);border-color:#5b2a2a;background:#2a1414}

/* escalation banner */
.esc-banner{display:none;background:#2a1414;border-left:3px solid var(--red);
  color:#ffb8b8;padding:10px 16px;font-size:13px}
.esc-banner.on{display:block}
.esc-banner b{color:#ffd9d9}

/* transcript */
.chat{flex:1;min-height:360px;max-height:440px;overflow-y:auto;
  padding:18px;display:flex;flex-direction:column;gap:8px;background:#0c1320}
.msg{max-width:78%;padding:10px 13px;border-radius:13px;
  font-size:14px;line-height:1.5;animation:slide .25s ease-out}
@keyframes slide{from{opacity:0;transform:translateY(6px)}to{opacity:1}}
.msg.you{align-self:flex-end;background:#0e3e2f;color:#d6f1e5;
  border-bottom-right-radius:4px}
.msg.agent{align-self:flex-start;background:#1a2333;
  border-bottom-left-radius:4px}
.role{font-size:10.5px;color:var(--mut2);margin:6px 4px 0;letter-spacing:.4px}
.you+.role,.role.you{text-align:right}
.typing{align-self:flex-start;background:#1a2333;padding:11px 14px;
  border-radius:13px;border-bottom-left-radius:4px;display:none}
.typing.on{display:flex;gap:4px}
.typing span{width:6px;height:6px;border-radius:50%;background:var(--mut);
  animation:bounce 1.2s ease-in-out infinite}
.typing span:nth-child(2){animation-delay:.15s}
.typing span:nth-child(3){animation-delay:.3s}
@keyframes bounce{0%,80%,100%{opacity:.3;transform:translateY(0)}
  40%{opacity:1;transform:translateY(-4px)}}

/* booking confirmation card inside chat */
.confirm{align-self:stretch;background:linear-gradient(135deg,#0f2a22,#11362a);
  border:1px solid #1d5443;border-radius:12px;padding:14px 16px;
  display:flex;gap:14px;align-items:flex-start;margin-top:4px}
.confirm .ck{font-size:22px;color:var(--green);line-height:1}
.confirm b{font-size:13px;display:block;margin-bottom:6px}
.confirm .meta{font-size:12px;color:#bdd9cc;line-height:1.55}
.confirm .meta i{color:#7fb09b;font-style:normal;margin-right:4px}

/* input bar */
.bar{display:flex;gap:8px;padding:12px;border-top:1px solid var(--line);
  background:#101723}
.bar input{flex:1;background:#0a121d;border:1px solid var(--line);
  color:var(--ink);padding:11px 14px;border-radius:22px;font-size:14px;outline:none}
.bar input:focus{border-color:var(--green)}
.bar input:disabled{opacity:.45;cursor:not-allowed}
.btn{background:var(--green);color:#fff;border:0;padding:0 18px;
  border-radius:22px;cursor:pointer;font-weight:600;font-size:14px;
  transition:transform .1s ease}
.btn:hover{filter:brightness(1.07)}
.btn:active{transform:translateY(1px)}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn.start{padding:11px 22px}
.btn.ghost{background:#1a2535;color:#cdd7e6;border:1px solid var(--line)}
.btn.ghost:hover{background:#22324a}

/* idle screen (before call connects) */
.idle{padding:46px 24px;display:flex;flex-direction:column;align-items:center;
  gap:14px;background:#0c1320;flex:1;min-height:360px;text-align:center}
.idle .ph{font-size:26px;font-weight:700;letter-spacing:.5px}
.idle .ph .small{display:block;font-size:12px;color:var(--mut);
  font-weight:400;margin-top:6px;letter-spacing:.2px}
.idle .opening{max-width:520px;color:#bcc8de;font-size:13.5px;line-height:1.6;
  background:#101a28;border:1px solid var(--line);border-radius:12px;padding:14px}
.idle .opening b{color:#fff}

/* ── SIDE PANEL ─────────────────────────────────────────────────── */
.side{display:flex;flex-direction:column;gap:14px;min-width:0}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;
  overflow:hidden}
.panel h3{font-size:13px;padding:12px 16px;letter-spacing:.4px;
  text-transform:uppercase;color:#bcc8de;background:#101a28;
  border-bottom:1px solid var(--line);font-weight:600}
.panel .body{padding:8px 0}

/* live intake list */
.field{display:flex;align-items:center;gap:10px;padding:9px 16px;
  border-bottom:1px dashed #1c2638;font-size:13px}
.field:last-child{border-bottom:0}
.field .ic{width:18px;height:18px;border-radius:50%;flex:none;
  background:#1a2333;border:1.5px solid var(--mut2);color:var(--mut);
  display:flex;align-items:center;justify-content:center;font-size:11px}
.field.done .ic{background:var(--green);border-color:var(--green);
  color:#001a12}
.field.done .ic::after{content:"✓"}
.field .lbl{color:var(--mut);min-width:108px;flex:none}
.field .val{color:var(--ink);font-weight:500;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;
  font-size:12.5px}
.field.done .lbl{color:#bcc8de}
.field.flash{animation:flash 1s ease-out}
@keyframes flash{0%{background:#1fb8881a}100%{background:transparent}}

/* scenario buttons */
.scn{display:flex;flex-direction:column;gap:2px;padding:6px 0}
.scn button{text-align:left;background:transparent;border:0;
  color:#dde6f4;padding:10px 16px;font-size:13px;cursor:pointer;
  display:flex;align-items:center;gap:10px;width:100%;
  border-left:2px solid transparent;transition:all .12s ease}
.scn button:hover{background:#15202e;border-left-color:var(--green)}
.scn button:disabled{opacity:.4;cursor:not-allowed}
.scn .ttag{font-size:9.5px;padding:2px 6px;border-radius:4px;
  letter-spacing:.5px;text-transform:uppercase;font-weight:600;flex:none}
.scn .ttag.booking{background:#0f2a22;color:var(--green)}
.scn .ttag.objection{background:#251c0c;color:var(--amber)}
.scn .ttag.escalate{background:#2a1414;color:var(--red)}
.scn .ts{flex:1;min-width:0}
.scn .tt{display:block;font-weight:500;line-height:1.35}
.scn .td{display:block;font-size:11px;color:var(--mut);margin-top:2px;line-height:1.4}

/* bookings list */
.bk{font-size:12.5px;color:#cdd7e6;padding:11px 16px;
  border-bottom:1px dashed #1c2638;line-height:1.55}
.bk:last-child{border-bottom:0}
.bk b{color:#fff;font-size:13px}
.bk .meta{color:var(--mut);font-size:11.5px;margin-top:3px}
.bk .pill{display:inline-block;font-size:10px;padding:1px 6px;border-radius:4px;
  background:#15202e;color:var(--mut);margin-right:6px;letter-spacing:.3px;
  text-transform:uppercase}
.bk .pill.in{background:#0f2a22;color:var(--green)}
.bk .pill.out{background:#16243d;color:var(--blue)}
.empty{padding:18px;color:var(--mut);font-size:12.5px;text-align:center}

/* tg note */
.tg-note{background:#0e1a26;border:1px solid #1a3b5a;border-left:3px solid var(--blue);
  border-radius:10px;padding:11px 14px;font-size:12.5px;color:#bcd2e6;line-height:1.5;
  margin-bottom:14px}
.tg-note a{font-weight:600}

/* outbound lead form */
.lead{padding:14px 16px;display:flex;flex-direction:column;gap:8px}
.lead label{font-size:11px;color:var(--mut);letter-spacing:.4px;
  text-transform:uppercase}
.lead input{background:#0a121d;border:1px solid var(--line);
  color:var(--ink);padding:9px 11px;border-radius:8px;font-size:13px;outline:none}
.lead input:focus{border-color:var(--blue)}
.lead .row{display:grid;gap:8px}
</style>
</head>
<body>
<div class="wrap">

  <div class="head">
    <div class="brand">
      <div class="logo">S</div>
      <div>
        <h1>__COMPANY__ — AI Receptionist & Booking</h1>
        <div class="sub">Demo · Twilio voice · SMS · Telegram · diagnostic-fee qualified</div>
      </div>
    </div>
    <div class="badges" id="badges">
      <span class="badge" id="ttsBadge" onclick="toggleTTS()" style="cursor:pointer" title="Toggle voice playback">🔊 voice · on</span>
    </div>
  </div>

  <div class="tg-note">
    📲 <b>Make the Telegram confirmation real for this demo:</b>
    open <a href="https://t.me/__BOT__" target="_blank">t.me/__BOT__</a>,
    tap <b>Start</b>, then finish a booking below — the confirmation lands
    in your own Telegram. With no token configured it still dry-runs and
    completes end-to-end.
  </div>

  <div class="agents" id="agents"></div>

  <div class="grid">

    <!-- ─── LEFT: call panel ─── -->
    <div class="call" id="callPanel">
      <div class="phbar" id="phbar">
        <div class="icon">📞</div>
        <div>
          <div class="lbl" id="phLabel">__PHONE__</div>
          <div class="sublbl" id="phSub">Inbound — Amanda is ready</div>
        </div>
        <div class="right">
          <span class="status" id="status">Idle</span>
        </div>
      </div>

      <div class="esc-banner" id="escBanner">
        <b>⚠ Escalation:</b> <span id="escReason"></span> · transferring to a human dispatcher.
      </div>

      <!-- idle screen -->
      <div class="idle" id="idle">
        <div class="ph">__PHONE__
          <span class="small">demo line — click "Connect call" to start</span>
        </div>
        <button class="btn start" onclick="startCall()">⌃ Connect call</button>
        <div class="opening" id="openingPreview"></div>
      </div>

      <!-- chat (hidden until call starts) -->
      <div class="chat" id="chat" style="display:none"></div>

      <div class="bar" id="inputBar" style="display:none">
        <input id="t" placeholder="Speak as the caller…" autocomplete="off">
        <button class="btn" id="sendBtn" onclick="send()">Send</button>
      </div>
    </div>

    <!-- ─── RIGHT: side panel ─── -->
    <div class="side">

      <div class="panel">
        <h3>Live intake</h3>
        <div class="body" id="fields"></div>
      </div>

      <div class="panel" id="outboundPanel" style="display:none">
        <h3>Outbound lead (Yelp / Thumbtack)</h3>
        <div class="lead">
          <label>Name</label><input id="lead-name" value="Marcus Lee">
          <label>Phone</label><input id="lead-phone" value="+1 510 555 0119">
          <label>Problem</label><input id="lead-problem" value="GE dryer not heating, drum spins fine">
          <button class="btn" style="margin-top:6px" onclick="startOutbound()">📞 Place outbound call</button>
        </div>
      </div>

      <div class="panel">
        <h3>Try a scenario</h3>
        <div class="scn" id="scenarios"></div>
      </div>

      <div class="panel">
        <h3>Confirmed bookings</h3>
        <div class="body" id="bookings">
          <div class="empty">No bookings yet — run a scenario above.</div>
        </div>
      </div>

    </div>
  </div>
</div>

<script>
// ─── state ────────────────────────────────────────────────────────
let CFG = null;
let agent = "amanda";
let inCall = false;
let busy = false;          // a turn is in-flight or scenario is playing
let ttsOn = true;
const fieldEls = {};

// ─── browser TTS — Amanda (female) + Tony (male) ─────────────────
let voiceCache = {amanda: null, tony: null};
function pickVoices(){
  const vs = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  if (!vs.length) return;
  const en = vs.filter(v => /en[-_]/i.test(v.lang));
  const pool = en.length ? en : vs;
  const female = pool.find(v => /samantha|victoria|karen|moira|tessa|allison|female|fiona|google us english/i.test(v.name)) || pool[0];
  const male   = pool.find(v => /daniel|alex|tom|fred|aaron|male|google uk english male/i.test(v.name)) || pool[pool.length-1] || pool[0];
  voiceCache.amanda = female;
  voiceCache.tony   = male;
}
if (window.speechSynthesis){
  window.speechSynthesis.onvoiceschanged = pickVoices;
  pickVoices();
}
function speak(text, who){
  if (!ttsOn || !window.speechSynthesis) return;
  try { window.speechSynthesis.cancel(); } catch(e){}
  const u = new SpeechSynthesisUtterance(text);
  const v = voiceCache[who];
  if (v) u.voice = v;
  u.rate = 1.02; u.pitch = (who === "amanda") ? 1.08 : 0.92;
  window.speechSynthesis.speak(u);
}
function toggleTTS(){
  ttsOn = !ttsOn;
  document.getElementById("ttsBadge").textContent = ttsOn ? "🔊 voice · on" : "🔇 voice · off";
  if (!ttsOn && window.speechSynthesis) window.speechSynthesis.cancel();
}

// ─── boot ─────────────────────────────────────────────────────────
async function boot(){
  CFG = await (await fetch("/api/config")).json();
  renderBadges();
  renderAgents();
  renderFields();
  renderScenarios();
  updateOpeningPreview();
  loadBookings();
}
boot();

function renderBadges(){
  const b = document.getElementById("badges");
  b.innerHTML = "";
  b.appendChild(badge(CFG.llm_live ? "LLM · live (Claude)" : "LLM · scripted fallback", CFG.llm_live));
  b.appendChild(badge(CFG.telegram_live ? "Telegram · live" : "Telegram · dry-run", CFG.telegram_live));
  b.appendChild(badge("SMS · dry-run (Twilio in prod)", false));
}
function badge(text, live){
  const e = document.createElement("span");
  e.className = "badge " + (live ? "live" : "dry");
  e.textContent = text;
  return e;
}

function renderAgents(){
  const c = document.getElementById("agents"); c.innerHTML = "";
  CFG.agents.forEach(a => {
    const el = document.createElement("div");
    el.className = "agent" + (a.key === agent ? " on" : "");
    el.onclick = () => switchAgent(a.key);
    el.innerHTML =
      `<div class="avatar ${a.key}">${a.name[0]}</div>
       <div style="flex:1">
         <div class="who"><span class="dot"></span>${a.name} — ${a.channel}</div>
         <div class="why">${escapeHtml(a.voice)}</div>
       </div>`;
    c.appendChild(el);
  });
}

function switchAgent(key){
  if (busy) return;
  agent = key;
  inCall = false;
  document.getElementById("outboundPanel").style.display = (key === "tony") ? "block" : "none";
  document.querySelectorAll(".agent").forEach((e,i) => {
    e.classList.toggle("on", CFG.agents[i].key === key);
  });
  resetPanel();
  updateOpeningPreview();
}

function updateOpeningPreview(){
  const a = CFG.agents.find(x => x.key === agent);
  const opening = document.getElementById("openingPreview");
  const role = agent === "amanda"
    ? "Inbound caller dials in →"
    : "Tony places the call to a fresh Yelp lead →";
  opening.innerHTML = `<div style="color:var(--mut);font-size:11.5px;margin-bottom:6px;letter-spacing:.3px;text-transform:uppercase">${role}</div><b>${a.name}:</b> "${escapeHtml(a.opening)}"`;
  document.getElementById("phSub").textContent =
    (a.channel === "inbound" ? "Inbound — " : "Outbound — ") + a.name + " is ready";
}

function renderFields(){
  const c = document.getElementById("fields"); c.innerHTML = "";
  CFG.fields.forEach(f => {
    const e = document.createElement("div");
    e.className = "field";
    e.innerHTML = `<div class="ic"></div><div class="lbl">${escapeHtml(f.label)}</div><div class="val">—</div>`;
    fieldEls[f.key] = e;
    c.appendChild(e);
  });
}

function renderScenarios(){
  const c = document.getElementById("scenarios"); c.innerHTML = "";
  CFG.scenarios.forEach(s => {
    const b = document.createElement("button");
    b.disabled = busy;
    b.onclick = () => playScenario(s.key);
    b.innerHTML =
      `<span class="ttag ${s.tag}">${s.tag}</span>
       <span class="ts">
         <span class="tt">${escapeHtml(s.title)}</span>
         <span class="td">${escapeHtml(s.summary)}</span>
       </span>`;
    c.appendChild(b);
  });
}

// ─── call lifecycle ──────────────────────────────────────────────
function setStatus(label, cls){
  const s = document.getElementById("status");
  s.textContent = label;
  s.className = "status " + (cls || "");
  const bar = document.getElementById("phbar");
  bar.classList.remove("ring","active");
  if (cls === "ring") bar.classList.add("ring");
  if (cls === "active") bar.classList.add("active");
}

function resetPanel(){
  document.getElementById("chat").innerHTML = "";
  document.getElementById("chat").style.display = "none";
  document.getElementById("inputBar").style.display = "none";
  document.getElementById("idle").style.display = "flex";
  document.getElementById("escBanner").classList.remove("on");
  setStatus("Idle","");
  Object.values(fieldEls).forEach(el => {
    el.classList.remove("done","flash");
    el.querySelector(".val").textContent = "—";
  });
}

async function startCall(){
  if (busy) return;
  busy = true;
  setStatus("Ringing…","ring");
  document.getElementById("idle").style.display = "none";
  document.getElementById("chat").style.display = "flex";
  document.getElementById("inputBar").style.display = "flex";
  enableInput();
  await wait(700);
  const j = await api("/api/call/start", {agent, caller: callerId()});
  appendMsg("agent", j.reply, CFG.agents.find(a => a.key === agent).name);
  setStatus("In call · " + agentName(),"active");
  applySnapshot(j);
  inCall = true;
  busy = false;
  document.getElementById("t").focus();
}

async function startOutbound(){
  if (busy) return;
  busy = true;
  const name = document.getElementById("lead-name").value.trim();
  const phone = document.getElementById("lead-phone").value.trim();
  const problem = document.getElementById("lead-problem").value.trim();
  switchAgent("tony");
  setStatus("Dialing lead…","ring");
  document.getElementById("idle").style.display = "none";
  document.getElementById("chat").style.display = "flex";
  document.getElementById("inputBar").style.display = "flex";
  enableInput();
  await wait(900);
  const j = await api("/api/outbound", {name, phone, problem});
  window.__caller = j.caller || phone;
  appendMsg("agent", j.reply, "Tony");
  setStatus("In call · Tony","active");
  applySnapshot(j);
  inCall = true;
  busy = false;
  document.getElementById("t").focus();
}

function callerId(){
  if (agent === "tony" && window.__caller) return window.__caller;
  return "web-demo-" + agent;
}

function agentName(){
  return (CFG.agents.find(a => a.key === agent) || {}).name || "Agent";
}

// ─── one turn (user types) ───────────────────────────────────────
async function send(){
  const inp = document.getElementById("t");
  const v = inp.value.trim();
  if (!v || !inCall || busy) return;
  inp.value = "";
  await sendLine(v);
}

async function sendLine(text){
  busy = true;
  appendMsg("you", text);
  showTyping(true);
  const j = await api("/api/call/turn", {agent, caller: callerId(), text});
  await wait(380);
  showTyping(false);
  appendMsg("agent", j.reply, agentName());
  applySnapshot(j);
  if (j.escalation){
    showEscalation(j.escalation);
    setStatus("Escalated","esc");
    endCall();
  } else if (j.booked){
    showConfirm(j.booking, j.telegram, j.sms);
    setStatus("Booked · call ended","ended");
    endCall();
    loadBookings();
  }
  busy = false;
}

function endCall(){
  inCall = false;
  const t = document.getElementById("t");
  const b = document.getElementById("sendBtn");
  t.disabled = true; b.disabled = true;
  t.placeholder = "Call ended — switch agents or run another scenario";
}

function enableInput(){
  const t = document.getElementById("t");
  t.disabled = false;
  document.getElementById("sendBtn").disabled = false;
  t.placeholder = "Speak as the caller…";
}

// ─── scenarios ───────────────────────────────────────────────────
async function playScenario(key){
  if (busy) return;
  const s = await (await fetch("/api/scenarios/" + key)).json();
  switchAgent(s.agent);
  document.querySelectorAll(".scn button").forEach(b => b.disabled = true);
  if (s.agent === "tony" && s.seed){
    document.getElementById("lead-name").value = s.seed.name || "";
    document.getElementById("lead-phone").value = s.seed.phone || "";
    document.getElementById("lead-problem").value = s.seed.problem || "";
    await startOutbound();
  } else {
    await startCall();
  }
  for (const line of s.lines){
    if (!inCall) break;            // stop on escalation
    await wait(900 + Math.random()*500);
    await sendLine(line);
  }
  document.querySelectorAll(".scn button").forEach(b => b.disabled = false);
}

// ─── snapshot helpers ────────────────────────────────────────────
function applySnapshot(j){
  if (!j || !j.fields) return;
  CFG.fields.forEach(f => {
    const v = j.fields[f.key];
    const el = fieldEls[f.key];
    if (!el) return;
    const had = el.classList.contains("done");
    if (v === undefined || v === null || v === "" || v === false){
      // not yet
    } else {
      const display = (f.key === "fee_agreed") ? "Accepted ✓" : String(v);
      el.querySelector(".val").textContent = display;
      el.classList.add("done");
      if (!had){
        el.classList.add("flash");
        setTimeout(() => el.classList.remove("flash"), 1000);
      }
    }
  });
}

function showEscalation(reason){
  const label = ({
    sealed_system: "Sealed-system / Freon",
    refund: "Refund request",
    warranty: "Warranty question",
    angry: "Angry caller",
    out_of_area: "Out of service area",
  })[reason] || reason;
  document.getElementById("escReason").textContent = label;
  document.getElementById("escBanner").classList.add("on");
}

function showConfirm(b, tg, sms){
  const chat = document.getElementById("chat");
  const e = document.createElement("div");
  e.className = "confirm";
  e.innerHTML =
    `<div class="ck">✓</div>
     <div>
       <b>Booking confirmed · Ref ${b.id}</b>
       <div class="meta">
         <div><i>Customer</i>${escapeHtml(b.name)} · ${escapeHtml(b.phone)}</div>
         <div><i>Address</i>${escapeHtml(b.address)}</div>
         <div><i>Appliance</i>${escapeHtml(b.appliance)} · ${escapeHtml(b.brand)} · model ${escapeHtml(b.model || "n/a")}</div>
         <div><i>Problem</i>${escapeHtml(b.problem)}</div>
         <div><i>Window</i>${escapeHtml(b.window)}</div>
         <div><i>Access</i>${escapeHtml(b.access || "—")}</div>
         <div><i>Fee</i>$__FEE__ diagnostic — accepted</div>
         <div style="margin-top:6px"><i>Telegram</i>${tg && tg.via === "telegram" ? "delivered ✓" : "dry-run"} · <i>SMS</i>${sms === "sent" ? "sent ✓" : "dry-run"}</div>
       </div>
     </div>`;
  chat.appendChild(e);
  chat.scrollTop = chat.scrollHeight;
}

// ─── UI primitives ───────────────────────────────────────────────
function appendMsg(role, text, label){
  const chat = document.getElementById("chat");
  const m = document.createElement("div");
  m.className = "msg " + (role === "you" ? "you" : "agent");
  m.textContent = text;
  chat.appendChild(m);
  if (label){
    const r = document.createElement("div");
    r.className = "role";
    r.textContent = label;
    chat.appendChild(r);
  }
  chat.scrollTop = chat.scrollHeight;
  if (role !== "you") speak(text, agent);
}

let typingEl = null;
function showTyping(on){
  const chat = document.getElementById("chat");
  if (on){
    typingEl = document.createElement("div");
    typingEl.className = "typing on";
    typingEl.innerHTML = "<span></span><span></span><span></span>";
    chat.appendChild(typingEl);
    chat.scrollTop = chat.scrollHeight;
  } else if (typingEl){
    typingEl.remove();
    typingEl = null;
  }
}

async function loadBookings(){
  try {
    const j = await (await fetch("/api/bookings")).json();
    const c = document.getElementById("bookings");
    if (!j.bookings.length){
      c.innerHTML = `<div class="empty">No bookings yet — run a scenario above.</div>`;
      return;
    }
    c.innerHTML = j.bookings.map(b => `
      <div class="bk">
        <span class="pill ${b.channel === "inbound" ? "in" : "out"}">${b.channel}</span>
        <b>${escapeHtml(b.name)}</b> — ${escapeHtml(b.appliance)} (${escapeHtml(b.brand)})
        <div class="meta">${escapeHtml(b.window)} · ${escapeHtml(b.address)}</div>
        <div class="meta">Ref ${b.id} · ${(b.agent || "agent")} · fee ${b.fee_agreed ? "accepted" : "—"}</div>
      </div>`).join("");
  } catch (e){}
}

async function api(path, body){
  const r = await fetch(path, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(body || {})
  });
  return r.json();
}

function wait(ms){ return new Promise(r => setTimeout(r, ms)); }
function escapeHtml(s){
  return String(s == null ? "" : s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

document.getElementById("t").addEventListener("keydown", e => {
  if (e.key === "Enter") send();
});
</script>
</body></html>
"""
