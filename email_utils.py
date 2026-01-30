import smtplib
from email.message import EmailMessage
from typing import Dict, Any

def send_email_alert(
    smtp_server: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    to_email: str,
    subject: str,
    body: str,
) -> None:
    """Send a simple plaintext email via SMTP (Gmail app-password compatible)."""
    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


def format_alert_email(payload: Dict[str, Any]) -> str:
    """Create a human-readable email body from an alert payload dict."""
    def g(*keys, default=None):
        for k in keys:
            if k in payload and payload.get(k) is not None:
                return payload.get(k)
        return default

    extras = g('extras','Extras', default={}) or {}
    family = (g('signal_family','SignalFamily','family','Family') or extras.get('family') or '').upper()

    lines = []
    lines.append(f"Time: {g('time','Time','as_of','AsOf','asof')}" )
    lines.append(f"Symbol: {g('symbol','Symbol')}" )
    lines.append(
        f"Bias: {g('bias','Bias')}   Tier: {g('tier','Tier','stage','Stage')}   Score: {g('score','Score')}   Session: {g('session','Session')}"
    )
    lines.append('')
    lines.append(f"Last: {g('last','Last')}" )
    lines.append(f"Entry (limit): {g('entry_limit','Entry','entry')}" )
    lines.append(f"Chase line: {g('entry_chase_line','Chase','chase')}" )

    # Optional family-specific block (SWING) — isolated so other families are unaffected.
    if family == 'SWING':
        swing_stage = extras.get('swing_stage') or g('swing_stage','SwingStage')
        if swing_stage:
            lines.append(f"Swing stage: {swing_stage}")
        tls = extras.get('trend_lock_score')
        if tls is not None:
            lines.append(f"Trend lock: {tls}/5")
        retr = extras.get('retrace_pct')
        if retr is not None:
            try:
                lines.append(f"Retrace: {float(retr):.1f}%")
            except Exception:
                lines.append(f"Retrace: {retr}")
        pbq = extras.get('pullback_quality')
        pbq_r = extras.get('pullback_quality_reasons')
        if pbq is not None:
            lines.append(f"Pullback quality: {pbq}/6" + (f" ({pbq_r})" if pbq_r else ''))
        conf_n = extras.get('confluence_count')
        conf = extras.get('confluences')
        if conf_n is not None:
            lines.append(f"Confluence: {conf_n}" + (f" ({conf})" if conf else ''))
        ez = extras.get('entry_zone')
        if ez:
            lines.append(f"Entry zone: {ez}")
        tr_reason = extras.get('entry_trigger_reason')
        if tr_reason:
            lines.append(f"Entry trigger: {tr_reason}")

        # Pullback band can be stored as tuple/list in extras['pullback_band']
        pb1 = g('pb1','PB1') or extras.get('pb1')
        pb2 = g('pb2','PB2') or extras.get('pb2')
        if pb1 is None or pb2 is None:
            pb_band = g('pullback_band','PullbackBand') or extras.get('pullback_band')
            if isinstance(pb_band, (tuple, list)) and len(pb_band) == 2:
                try:
                    a = float(pb_band[0]); b = float(pb_band[1])
                    pb1, pb2 = (min(a, b), max(a, b))
                except Exception:
                    pb1, pb2 = str(pb_band[0]), str(pb_band[1])
        if pb1 is not None and pb2 is not None:
            lines.append(f"Pullback band: {pb1} – {pb2}")

    # Generic optional continuation fields (if present).
    br = g('break_trigger','BreakTrigger','breakTrigger')
    pb = g('pullback_entry','PullbackEntry','pullback_entry')
    if pb is not None:
        lines.append(f"Pullback entry: {pb}")
    # Pullback band for non-SWING families (legacy behavior)
    pb1 = g('pb1','PB1') or extras.get('pb1')
    pb2 = g('pb2','PB2') or extras.get('pb2')
    if family != 'SWING' and pb1 is not None and pb2 is not None:
        lines.append(f"Pullback band: {pb1} – {pb2}")

    if br is not None:
        lines.append(f"Break trigger: {br}")

    lines.append(f"Stop: {g('stop','Stop')}" )
    lines.append(f"TP0: {g('tp0','TP0')}" )
    lines.append(f"TP1: {g('tp1','TP1','t1','T1')}" )
    lines.append(f"TP2: {g('tp2','TP2','t2','T2')}" )
    lines.append(f"TP3: {g('tp3','TP3','t3','T3')}" )
    eta = g('eta_tp0_min','ETA TP0 (min)')
    if eta is not None:
        lines.append(f"ETA TP0 (min): {eta}")

    why = g('why','Why', default='') or ''
    lines.append('Why:')
    lines.append(str(why))

    if extras:
        lines.append('Diagnostics:')
        for k in [
            'liquidity_phase','vwap_logic','session_vwap_include_premarket',
            'accept_line','impulse_quality','disp_ratio','vol_ratio',
            'trend_lock_score','pullback_quality','pullback_quality_reasons',
            'retrace_pct','confluence_count','confluences','entry_zone','entry_trigger_reason',
            'seep_ok','character_ok','atr_pct','baseline_atr_pct','atr_ref_pct','atr_score_scale','htf_bias'
        ]:
            if k in extras:
                lines.append(f"- {k}: {extras.get(k)}")

    return "\n".join(lines)