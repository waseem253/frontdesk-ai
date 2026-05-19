"""FastAPI: receptionist simulator + booking + real Telegram + outbound."""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .pipeline import handle_turn, outbound_call
from .store import bookings
from .telegram import handle_update, set_webhook

app = FastAPI(title="FrontDesk", version="1.0.0")

BOT = "inbound_call_bot"  # t.me/inbound_call_bot


@app.get("/health")
def health() -> dict:
    return {"ok": True, "bookings": len(bookings()),
            "telegram": bool(os.environ.get("TELEGRAM_BOT_TOKEN"))}


class Turn(BaseModel):
    caller: str = "web-demo"
    text: str


@app.post("/sim")
def sim(t: Turn) -> dict:
    return handle_turn(t.caller, t.text)


class Lead(BaseModel):
    name: str = "Alex Morgan"
    phone: str = "+10000000000"
    service: str = "callback consult"


@app.post("/outbound")
def outbound(l: Lead) -> dict:
    return outbound_call(l.name, l.phone, l.service)


@app.post("/telegram/webhook")
async def tg_webhook(request: Request) -> JSONResponse:
    try:
        handle_update(await request.json())
    except Exception:
        pass
    return JSONResponse({"ok": True})


@app.get("/admin/set-webhook")
def admin_set_webhook(request: Request) -> dict:
    base = str(request.base_url).rstrip("/")
    return set_webhook(base)


@app.get("/api/bookings")
def api_bookings() -> dict:
    return {"bookings": [b.__dict__ for b in bookings()]}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return _HTML.replace("__BOT__", BOT)


_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FrontDesk — AI Voice Receptionist & Booking</title>
<style>
 :root{--bg:#0c1118;--card:#141b26;--line:#243042;--ink:#e9eef7;--mut:#8a99b3;--g:#16a37f;--gd:#0f7a5e}
 *{box-sizing:border-box;margin:0;padding:0}
 body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink);padding:26px}
 .wrap{max-width:1000px;margin:0 auto}
 h1{font-size:20px}.sub{color:var(--mut);font-size:13px;margin:4px 0 18px}
 .tg{background:#15212e;border:1px solid #1f6feb33;border-left:3px solid #229ed9;border-radius:10px;padding:12px 16px;font-size:13px;margin-bottom:18px}
 .tg a{color:#48b9e7;font-weight:600;text-decoration:none}
 .grid{display:grid;grid-template-columns:1fr 380px;gap:18px}
 .panel{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
 .ph{background:var(--gd);padding:11px 16px;font-weight:600;font-size:14px}
 .ph small{display:block;font-weight:400;opacity:.85;font-size:12px}
 .chat{height:420px;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px}
 .b{max-width:80%;padding:8px 12px;border-radius:10px;font-size:14px;line-height:1.4}
 .u{align-self:flex-end;background:#0c5a47}.a{align-self:flex-start;background:#1d2733}
 .meta{font-size:10px;color:#5d6f8e;align-self:flex-start}
 .bar{display:flex;gap:8px;padding:12px;border-top:1px solid var(--line)}
 input{flex:1;background:#0e1620;border:1px solid var(--line);color:var(--ink);padding:10px 12px;border-radius:20px;font-size:14px;outline:none}
 button{background:var(--g);border:0;color:#fff;font-weight:600;padding:0 16px;border-radius:20px;cursor:pointer}
 .side{display:flex;flex-direction:column;gap:18px}
 .card2{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
 .card2 b{font-size:13px}.card2 p{color:var(--mut);font-size:12px;margin:6px 0 10px;line-height:1.5}
 .ob{width:100%;background:#23324a;color:#cfe0ff;border:1px solid #33476a;padding:9px;border-radius:8px;cursor:pointer;font-weight:600;font-size:13px}
 table{width:100%;border-collapse:collapse;font-size:12px}
 td{padding:7px 4px;border-bottom:1px solid #1b2533;color:#cdd7e6}
 .empty{color:var(--mut);font-size:12px;padding:14px 0}
 code{background:#0e1620;padding:1px 5px;border-radius:4px}
</style></head><body><div class="wrap">
<h1>FrontDesk — AI Voice Receptionist &amp; Booking</h1>
<div class="sub">Inbound "call" → AI books the appointment → confirmation hits Telegram + SMS, logged. Built for the Twilio / SMS / Telegram brief.</div>
<div class="tg">📲 <b>Make the Telegram part real:</b> open <a href="https://t.me/__BOT__" target="_blank">t.me/__BOT__</a>, tap <b>Start</b>, then complete a booking below — the confirmation arrives in your own Telegram. (No token configured → it dry-runs and still completes.)</div>
<div class="grid">
 <div class="panel">
  <div class="ph">FrontDesk Receptionist<small>AI · books in-call · Telegram + SMS confirm</small></div>
  <div class="chat" id="chat"></div>
  <div class="bar"><input id="t" placeholder="Speak as the caller… e.g. 'Hi, I'd like to book'" autocomplete="off"><button onclick="send()">Send</button></div>
 </div>
 <div class="side">
  <div class="card2"><b>Scope 2 — Outbound</b><p>A new lead triggers an automated outbound call that books and logs through the same path (prod adds smart retries).</p><button class="ob" onclick="outbound()">Trigger outbound auto-call</button></div>
  <div class="card2"><b>Bookings (live log)</b><table id="bk"><tr><td class="empty">No bookings yet.</td></tr></table></div>
 </div>
</div></div>
<script>
const chat=document.getElementById('chat');const t=document.getElementById('t');
function add(c,x,m){const d=document.createElement('div');d.className='b '+c;d.textContent=x;chat.appendChild(d);if(m){const e=document.createElement('div');e.className='meta';e.textContent=m;chat.appendChild(e);}chat.scrollTop=chat.scrollHeight;}
async function send(){const v=t.value.trim();if(!v)return;add('u',v);t.value='';
 const r=await fetch('/sim',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:v})});
 const j=await r.json();add('a',j.reply, j.booked? 'booked ✓ · telegram: '+(j.telegram&&j.telegram.via)+' · sms: '+j.sms : '');
 if(j.booked) load();}
async function outbound(){const r=await fetch('/outbound',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const j=await r.json();add('a','Outbound auto-call placed → '+j.booking.name+' booked '+j.booking.slot+'.','telegram: '+(j.telegram&&j.telegram.via));load();}
async function load(){const j=await(await fetch('/api/bookings')).json();const t=document.getElementById('bk');
 if(!j.bookings.length){t.innerHTML='<tr><td class="empty">No bookings yet.</td></tr>';return;}
 t.innerHTML=j.bookings.map(b=>`<tr><td><b>${esc(b.name)}</b><br><span style="color:#7d8ba3">${esc(b.service)} · ${esc(b.slot)}</span><br><span style="color:#566a82">${esc(b.channel)}</span></td></tr>`).join('');}
function esc(s){return(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
t.addEventListener('keydown',e=>{if(e.key==='Enter')send();});
add('a',"Thanks for calling — may I take your name?");
load();
</script></body></html>"""
