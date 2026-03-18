# interface/war_room.py
"""
══════════════════════════════════════════════════════════════
Sentinel Pro KB5 — War Room Dashboard (Plotly Dash)
══════════════════════════════════════════════════════════════
Point d'entrée principal. Lance un serveur Dash sur port 8050.

Usage :
    cd <project_root>
    python interface/war_room.py

URL : http://localhost:8050
══════════════════════════════════════════════════════════════
"""

import sys
import os
import logging
from pathlib import Path

# Ajouter la racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import dash
import dash_bootstrap_components as dbc
from dash import html

from interface.war_room_styles import GLOBAL_CSS, GOOGLE_FONTS_URL, BG_BASE
from interface.war_room_callbacks import register_all_callbacks
from gateway.mt5_connector import MT5Connector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("war_room")

# ──────────────────────────────────────────────────────────────
# PAIRES ACTIVES (depuis settings ou par défaut)
# ──────────────────────────────────────────────────────────────

def _get_pairs() -> list:
    try:
        from config.settings_manager import SettingsManager
        s = SettingsManager()
        pairs = s.get_active_pairs()
        if pairs:
            return pairs
    except Exception:
        pass
    return ["EURUSDm", "GBPUSDm", "XAUUSDm", "USTECm"]

# ──────────────────────────────────────────────────────────────
# APPLICATION DASH
# ──────────────────────────────────────────────────────────────

def create_app(pairs: list = None) -> dash.Dash:
    """Crée et configure l'application Dash War Room."""
    if pairs is None:
        pairs = _get_pairs()

    app = dash.Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.CYBORG,
            GOOGLE_FONTS_URL,
        ],
        suppress_callback_exceptions=True,
        title="Sentinel Pro — War Room",
        update_title=None,
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"},
            {"name": "description", "content": "Sentinel Pro KB5 — War Room Trading Intelligence"},
        ],
    )

    # Injection CSS global
    app.index_string = f"""<!DOCTYPE html>
<html>
<head>
    {{%metas%}}
    <title>{{%title%}}</title>
    {{%favicon%}}
    {{%css%}}
    <style>
    {GLOBAL_CSS}

    /* ── Dash Dropdown override ── */
    .wr-dropdown .Select-control {{
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 8px !important;
        color: #fff !important;
    }}
    .wr-dropdown .Select-menu-outer {{
        background: #0a0a14 !important;
        border: 1px solid rgba(124,92,252,0.25) !important;
        border-radius: 8px !important;
    }}
    .wr-dropdown .Select-option {{
        background: transparent !important;
        color: rgba(255,255,255,0.75) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
    }}
    .wr-dropdown .Select-option.is-focused,
    .wr-dropdown .Select-option.is-selected {{
        background: rgba(124,92,252,0.15) !important;
        color: #fff !important;
    }}
    .wr-dropdown .Select-value-label {{
        color: #fff !important;
        font-family: 'JetBrains Mono', monospace !important;
    }}

    /* ── Radio items ── */
    .form-check-input:checked {{
        background-color: #7c5cfc !important;
        border-color: #7c5cfc !important;
    }}
    .form-check-label {{
        color: rgba(255,255,255,0.65) !important;
        font-size: 11px !important;
    }}

    /* ── Plotly chart ── */
    .js-plotly-plot .plotly .user-select-none {{
        cursor: crosshair;
    }}
    .modebar {{
        background: transparent !important;
    }}
    .modebar-btn path {{
        fill: rgba(255,255,255,0.3) !important;
    }}
    .modebar-btn:hover path {{
        fill: #7c5cfc !important;
    }}
    </style>
</head>
<body>
{{%app_entry%}}
<footer>
{{%config%}}
{{%scripts%}}
{{%renderer%}}
</footer>
</body>
</html>"""

    # Layout
    from interface.war_room_layout import build_full_layout
    app.layout = build_full_layout(pairs)

    # Callbacks
    register_all_callbacks(app)

    return app


# ──────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # ── Initialisation MT5 ──
    logger.info("War Room — Initialisation de la connexion MT5...")
    mt5_conn = MT5Connector()
    if not mt5_conn.connect():
        logger.error("War Room — Impossible de connecter MT5. Les graphiques risquent d'être vides.")
    
    pairs = _get_pairs()
    logger.info(f"War Room démarrage — paires: {pairs}")
    app = create_app(pairs)
    app.run(
        host="0.0.0.0",
        port=8050,
        debug=False,
        dev_tools_silence_routes_logging=True,
    )
