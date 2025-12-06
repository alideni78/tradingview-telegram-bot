"""Dashboard endpoint."""

from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ...core.config import Settings, get_settings

router = APIRouter()

# In-memory storage
webhook_history: List[Dict[str, Any]] = []
error_history: List[Dict[str, Any]] = []
start_time = datetime.now()


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    status: str
    version: str
    open_positions: int
    total_signals: int
    last_signal_time: str
    positions: List[Dict[str, Any]]
    recent_webhooks: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page() -> str:
    """Serve dashboard HTML page."""
    return """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>TradingView Bot Dashboard</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Arial,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px}.container{max-width:1200px;margin:0 auto}.header{background:#fff;padding:30px;border-radius:15px;margin-bottom:20px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}.header h1{color:#333;font-size:28px;margin-bottom:10px}.status{display:inline-block;padding:8px 16px;border-radius:20px;font-weight:bold;font-size:14px;background:#10b981;color:#fff}.card{background:#fff;padding:25px;border-radius:15px;margin-bottom:20px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}.card h2{color:#333;font-size:20px;margin-bottom:15px;border-bottom:2px solid #667eea;padding-bottom:10px}.stat{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #eee}.stat:last-child{border-bottom:none}.stat-label{color:#666;font-weight:600}.stat-value{color:#333;font-weight:bold}.position{background:#f8fafc;padding:15px;border-radius:10px;margin-bottom:10px;border-left:4px solid #10b981}.position-header{display:flex;justify-content:space-between;margin-bottom:8px}.position-symbol{font-weight:bold;font-size:16px;color:#333}.position-side{padding:4px 12px;border-radius:15px;font-size:12px;font-weight:bold;background:#d1fae5;color:#065f46}.webhook-item{background:#f0f9ff;padding:12px;border-radius:8px;margin-bottom:8px;border-left:3px solid #3b82f6}.webhook-time{font-size:11px;color:#1e40af;font-weight:bold}.webhook-message{font-size:13px;color:#333;margin-top:5px}.empty-state{text-align:center;color:#999;padding:30px;font-style:italic}</style>
</head><body><div class="container"><div class="header"><h1>📊 TradingView Bot Dashboard</h1><span class="status" id="statusBadge">🟢 Healthy</span><span style="float:right;color:#666;font-size:14px">Last: <span id="lastUpdate">-</span></span></div>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin-bottom:20px">
<div class="card"><h2>⚙️ System Stats</h2><div class="stat"><span class="stat-label">Status</span><span class="stat-value" id="systemStatus">Loading...</span></div><div class="stat"><span class="stat-label">Version</span><span class="stat-value" id="version">-</span></div><div class="stat"><span class="stat-label">Open Positions</span><span class="stat-value" id="openPositions">-</span></div></div>
<div class="card"><h2>🤖 Bot Info</h2><div class="stat"><span class="stat-label">Total Signals</span><span class="stat-value" id="totalSignals">-</span></div><div class="stat"><span class="stat-label">Recent Errors</span><span class="stat-value" id="errorCount">-</span></div><div class="stat"><span class="stat-label">Last Signal</span><span class="stat-value" id="lastSignal">-</span></div></div></div>
<div class="card"><h2>📈 Open Positions</h2><div id="positionsList"><div class="empty-state">Loading...</div></div></div>
<div class="card"><h2>📡 Recent Webhooks</h2><div id="webhooksList"><div class="empty-state">Loading...</div></div></div></div>
<script>
async function fetchData(){try{const r=await fetch('/api/dashboard/stats');const d=await r.json();
document.getElementById('statusBadge').className=d.status==='healthy'?'status':'status error';
document.getElementById('statusBadge').textContent=d.status==='healthy'?'🟢 Healthy':'🔴 Error';
document.getElementById('systemStatus').textContent=d.status||'Unknown';
document.getElementById('version').textContent=d.version||'-';
document.getElementById('openPositions').textContent=d.open_positions||0;
document.getElementById('totalSignals').textContent=d.total_signals||0;
document.getElementById('errorCount').textContent=d.errors?.length||0;
document.getElementById('lastSignal').textContent=d.last_signal_time||'Never';
const pl=document.getElementById('positionsList');
if(d.positions.length===0){pl.innerHTML='<div class="empty-state">No open positions</div>';}else{
pl.innerHTML=d.positions.map(p=>`<div class="position"><div class="position-header"><span class="position-symbol">${p.symbol}</span><span class="position-side">${p.side}</span></div><div style="font-size:13px;color:#666">Entry: ${p.entry_price} | SL: ${p.stop_loss} | ${p.status}</div></div>`).join('');}
const wl=document.getElementById('webhooksList');
if(d.recent_webhooks.length===0){wl.innerHTML='<div class="empty-state">No webhooks</div>';}else{
wl.innerHTML=d.recent_webhooks.slice(0,5).map(w=>`<div class="webhook-item"><div class="webhook-time">${w.time}</div><div class="webhook-message">${w.symbol} - ${w.signal_type}</div></div>`).join('');}
document.getElementById('lastUpdate').textContent=new Date().toLocaleTimeString();
}catch(e){console.error(e);document.getElementById('statusBadge').className='status error';document.getElementById('statusBadge').textContent='🔴 Error';}}
fetchData();setInterval(fetchData,5000);
</script></body></html>"""


@router.get("/api/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(
    settings: Settings = Depends(get_settings),
) -> DashboardStats:
    """Get dashboard statistics."""
    from ...main import position_manager
    
    open_positions = position_manager.get_all_open_positions()
    positions_list = [
        {
            "symbol": pos.symbol,
            "side": pos.side.value,
            "entry_price": f"{float(pos.entry_price):,.2f}",
            "stop_loss": f"{float(pos.stop_loss):,.2f}",
            "status": pos.status.value,
        }
        for pos in open_positions.values()
    ]
    
    last_signal = webhook_history[-1] if webhook_history else None
    last_signal_time = last_signal["time"] if last_signal else "Never"
    
    return DashboardStats(
        status="healthy",
        version="1.0.0",
        open_positions=len(open_positions),
        total_signals=len(webhook_history),
        last_signal_time=last_signal_time,
        positions=positions_list,
        recent_webhooks=webhook_history[-10:][::-1],
        errors=error_history[-10:][::-1],
    )


def log_webhook(symbol: str, signal_type: str) -> None:
    """Log webhook event."""
    webhook_history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "signal_type": signal_type,
    })
    if len(webhook_history) > 100:
        webhook_history.pop(0)


def log_error(message: str) -> None:
    """Log error event."""
    error_history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": message,
    })
    if len(error_history) > 50:
        error_history.pop(0)
