# interface/war_room_styles.py
"""
══════════════════════════════════════════════════════════════
Sentinel Pro KB5 — War Room Design System
══════════════════════════════════════════════════════════════
Design tokens, palette, CSS-in-Python, composant styles.
Police : Inter (textes) + JetBrains Mono (prix/scores)
Thème : Ultra-dark glassmorphism + néons ICT
══════════════════════════════════════════════════════════════
"""

# ══════════════════════════════════════════════════════════════
# PALETTE COULEURS
# ══════════════════════════════════════════════════════════════

# Fonds
BG_BASE       = "#050508"
BG_DEEP       = "#030306"
BG_CARD       = "rgba(255, 255, 255, 0.025)"
BG_CARD_HOVER = "rgba(255, 255, 255, 0.045)"
BG_GLASS      = "rgba(12, 12, 25, 0.85)"

# Bordures
BORDER_SUBTLE  = "rgba(255, 255, 255, 0.06)"
BORDER_ACTIVE  = "rgba(124, 92, 252, 0.4)"
BORDER_BULL    = "rgba(0, 255, 136, 0.3)"
BORDER_BEAR    = "rgba(255, 51, 85, 0.3)"

# Accents ICT
NEON_BULL     = "#00ff88"     # vert bullish
NEON_BEAR     = "#ff3355"     # rouge bearish
NEON_PURPLE   = "#7c5cfc"     # violet — neutral/info/setup
NEON_GOLD     = "#f5b942"     # or — ordre block, premium
NEON_CYAN     = "#00d4ff"     # cyan — FVG, imbalance
NEON_ORANGE   = "#ff8c42"     # orange — sweep, manipulation
NEON_PINK     = "#ff4db8"     # rose — killzone, timing
NEON_LIME     = "#b4ff44"     # lime — MSS, momentum

# Textes
TEXT_PRIMARY   = "#ffffff"
TEXT_SECONDARY = "rgba(255, 255, 255, 0.55)"
TEXT_MUTED     = "rgba(255, 255, 255, 0.30)"
TEXT_ACCENT    = NEON_PURPLE

# Verdict colors (clés identiques à scoring_engine)
VERDICT_COLORS = {
    "EXECUTE":  NEON_BULL,
    "WATCH":    NEON_GOLD,
    "NO_TRADE": NEON_BEAR,
    "UNKNOWN":  TEXT_MUTED,
}

# Grade colors
GRADE_COLORS = {
    "A+": NEON_BULL,
    "A":  NEON_BULL,
    "A-": "#88ffbb",
    "B+": NEON_GOLD,
    "B":  NEON_GOLD,
    "B-": "#c8a030",
    "C":  NEON_BEAR,
}

# Score → couleur
def score_color(score: int) -> str:
    if score >= 80: return NEON_BULL
    if score >= 65: return NEON_GOLD
    if score >= 40: return NEON_ORANGE
    return NEON_BEAR

# Direction → couleur
def dir_color(direction: str) -> str:
    if direction == "BULLISH": return NEON_BULL
    if direction == "BEARISH": return NEON_BEAR
    return TEXT_SECONDARY

# Direction → icône
def dir_icon(direction: str) -> str:
    if direction == "BULLISH": return "▲"
    if direction == "BEARISH": return "▼"
    return "━"

# ══════════════════════════════════════════════════════════════
# TYPOGRAPHIE
# ══════════════════════════════════════════════════════════════

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@300;400;500;600;700&"
    "family=JetBrains+Mono:wght@400;500;700&"
    "display=swap"
)

FONT_SANS = "'Inter', system-ui, sans-serif"
FONT_MONO = "'JetBrains Mono', 'Fira Code', monospace"

# ══════════════════════════════════════════════════════════════
# STYLES CSS GLOBAUX (injecté dans app.index_string)
# ══════════════════════════════════════════════════════════════

GLOBAL_CSS = f"""
/* ─ Reset & Base ─────────────────────── */
*, *::before, *::after {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}

html, body, #react-entry-point {{
    background: {BG_BASE};
    color: {TEXT_PRIMARY};
    font-family: {FONT_SANS};
    font-size: 13px;
    line-height: 1.55;
    overflow-x: hidden;
    min-height: 100vh;
}}

::-webkit-scrollbar {{
    width: 4px;
    height: 4px;
}}
::-webkit-scrollbar-track {{
    background: transparent;
}}
::-webkit-scrollbar-thumb {{
    background: rgba(124, 92, 252, 0.4);
    border-radius: 2px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: rgba(124, 92, 252, 0.7);
}}

/* ─ Glassmorphism Card ──────────────── */
.wr-card {{
    background: {BG_CARD};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 12px;
    padding: 14px 18px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    transition: border-color 0.2s ease, background 0.2s ease;
}}
.wr-card:hover {{
    border-color: {BORDER_ACTIVE};
    background: {BG_CARD_HOVER};
}}

/* ─ Header Bar (Zone 0) ─────────────── */
#wr-header {{
    position: sticky;
    top: 0;
    z-index: 999;
    background: rgba(5, 5, 8, 0.95);
    border-bottom: 1px solid {BORDER_SUBTLE};
    backdrop-filter: blur(20px);
    padding: 8px 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
}}

/* ─ Score Gauge ─────────────────────── */
.wr-gauge-wrap {{
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 80px;
}}

/* ─ Session Dot (pulse) ─────────────── */
.wr-session-dot {{
    display: inline-block;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: {NEON_BULL};
    box-shadow: 0 0 0 0 rgba(0,255,136,0.6);
    animation: pulse-green 2s infinite;
    margin-right: 5px;
    flex-shrink: 0;
}}
@keyframes pulse-green {{
    0%   {{ box-shadow: 0 0 0 0   rgba(0,255,136,0.6); }}
    70%  {{ box-shadow: 0 0 0 8px rgba(0,255,136,0); }}
    100% {{ box-shadow: 0 0 0 0   rgba(0,255,136,0); }}
}}
.wr-session-dot.bear {{
    background: {NEON_BEAR};
    animation: pulse-red 2s infinite;
}}
@keyframes pulse-red {{
    0%   {{ box-shadow: 0 0 0 0   rgba(255,51,85,0.6); }}
    70%  {{ box-shadow: 0 0 0 8px rgba(255,51,85,0); }}
    100% {{ box-shadow: 0 0 0 0   rgba(255,51,85,0); }}
}}

/* ─ Neon text ───────────────────────── */
.wr-neon-bull {{ color: {NEON_BULL}; text-shadow: 0 0 8px rgba(0,255,136,0.5); }}
.wr-neon-bear {{ color: {NEON_BEAR}; text-shadow: 0 0 8px rgba(255,51,85,0.5); }}
.wr-neon-purple {{ color: {NEON_PURPLE}; text-shadow: 0 0 8px rgba(124,92,252,0.5); }}
.wr-neon-gold {{ color: {NEON_GOLD}; text-shadow: 0 0 8px rgba(245,185,66,0.4); }}
.wr-mono {{ font-family: {FONT_MONO}; }}

/* ─ Zone Labels ─────────────────────── */
.wr-zone-label {{
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {TEXT_MUTED};
    margin-bottom: 8px;
}}

/* ─ Confluence Badge ────────────────── */
.wr-conf-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    font-family: {FONT_MONO};
    margin: 2px 3px;
    border: 1px solid;
    line-height: 1.6;
    cursor: pointer;
    transition: opacity 0.15s;
}}
.wr-conf-badge:hover {{ opacity: 0.75; }}

/* ─ Audit Feed ──────────────────────── */
.wr-audit-feed {{
    height: 340px;
    overflow-y: auto;
    padding: 8px 4px;
}}
.wr-audit-entry {{
    display: flex;
    gap: 10px;
    padding: 5px 8px;
    border-left: 2px solid transparent;
    border-radius: 0 6px 6px 0;
    margin-bottom: 2px;
    font-size: 11px;
    font-family: {FONT_MONO};
    line-height: 1.6;
    transition: background 0.15s;
}}
.wr-audit-entry:hover {{
    background: rgba(255,255,255,0.04);
}}
.wr-audit-entry.bull {{ border-left-color: {NEON_BULL}; }}
.wr-audit-entry.bear {{ border-left-color: {NEON_BEAR}; }}
.wr-audit-entry.info {{ border-left-color: {NEON_PURPLE}; }}
.wr-audit-entry.warn {{ border-left-color: {NEON_GOLD}; }}
.wr-audit-ts {{ color: {TEXT_MUTED}; min-width: 58px; }}
.wr-audit-pair {{ color: {NEON_CYAN}; min-width: 60px; font-weight: 700; }}
.wr-audit-msg {{ color: {TEXT_SECONDARY}; flex: 1; }}

/* ─ Pyramid Score Bar ───────────────── */
.wr-pyramid-bar-wrap {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}}
.wr-pyramid-label {{
    font-family: {FONT_MONO};
    font-size: 10px;
    font-weight: 700;
    min-width: 32px;
    color: {TEXT_SECONDARY};
}}
.wr-pyramid-bar-bg {{
    flex: 1;
    height: 6px;
    background: rgba(255,255,255,0.07);
    border-radius: 3px;
    overflow: hidden;
}}
.wr-pyramid-bar-fill {{
    height: 100%;
    border-radius: 3px;
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}}
.wr-pyramid-score {{
    font-family: {FONT_MONO};
    font-size: 10px;
    min-width: 30px;
    text-align: right;
}}

/* ─ Decision Tree node ──────────────── */
.wr-tree-node {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border-radius: 20px;
    border: 1px solid;
    font-size: 10px;
    font-weight: 600;
    font-family: {FONT_MONO};
    cursor: pointer;
    transition: all 0.2s;
}}
.wr-tree-node:hover {{ filter: brightness(1.2); }}

/* ─ Heatmap cell override ───────────── */
.wr-heatmap-label {{
    font-size: 9px;
    font-family: {FONT_MONO};
    text-align: center;
}}

/* ─ Narrative ───────────────────────── */
.wr-narrative {{
    font-size: 13px;
    color: {TEXT_SECONDARY};
    line-height: 1.8;
    font-style: italic;
    padding: 12px 16px;
    border-left: 3px solid {NEON_PURPLE};
    background: rgba(124, 92, 252, 0.05);
    border-radius: 0 8px 8px 0;
    margin-bottom: 12px;
}}
.wr-narrative strong {{ color: {TEXT_PRIMARY}; font-style: normal; }}

/* ─ Tabs ────────────────────────────── */
.wr-tab-btn {{
    background: transparent;
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-family: {FONT_MONO};
    font-size: 10px;
    font-weight: 600;
    padding: 4px 10px;
    cursor: pointer;
    transition: all 0.2s;
    letter-spacing: 0.04em;
}}
.wr-tab-btn.active, .wr-tab-btn:hover {{
    border-color: {NEON_PURPLE};
    color: {NEON_PURPLE};
    background: rgba(124, 92, 252, 0.1);
}}

/* ─ Alertes ─────────────────────────── */
.wr-alert-badge {{
    background: {NEON_BEAR};
    color: #fff;
    font-family: {FONT_MONO};
    font-size: 9px;
    font-weight: 700;
    padding: 2px 5px;
    border-radius: 10px;
    animation: blink 1.2s infinite;
}}
@keyframes blink {{
    0%, 100% {{ opacity: 1; }}
    50%       {{ opacity: 0.3; }}
}}

/* ─ Verdict Banner ──────────────────── */
.wr-verdict-banner {{
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 14px;
    font-family: {FONT_MONO};
    text-align: center;
    border: 1px solid;
    letter-spacing: 0.06em;
    margin-bottom: 10px;
}}
.wr-verdict-banner.execute {{
    background: rgba(0,255,136,0.08);
    border-color: {NEON_BULL};
    color: {NEON_BULL};
    box-shadow: 0 0 20px rgba(0,255,136,0.15);
}}
.wr-verdict-banner.watch {{
    background: rgba(245,185,66,0.08);
    border-color: {NEON_GOLD};
    color: {NEON_GOLD};
}}
.wr-verdict-banner.no_trade {{
    background: rgba(255,51,85,0.08);
    border-color: {NEON_BEAR};
    color: {NEON_BEAR};
}}
"""

# ══════════════════════════════════════════════════════════════
# STYLES PLOTLY LAYOUT (dict appliqué à fig.update_layout)
# ══════════════════════════════════════════════════════════════

PLOTLY_BASE_LAYOUT = dict(
    paper_bgcolor = "rgba(0,0,0,0)",
    plot_bgcolor  = "rgba(0,0,0,0)",
    font          = dict(family="JetBrains Mono, monospace", color=TEXT_SECONDARY, size=10),
    margin        = dict(l=0, r=0, t=32, b=0),
    xaxis = dict(
        gridcolor   = "rgba(255,255,255,0.04)",
        zerolinecolor = "rgba(255,255,255,0.06)",
        color       = TEXT_MUTED,
        showgrid    = True,
        tickfont    = dict(family="JetBrains Mono", size=9),
    ),
    yaxis = dict(
        gridcolor   = "rgba(255,255,255,0.04)",
        zerolinecolor = "rgba(255,255,255,0.06)",
        color       = TEXT_MUTED,
        showgrid    = True,
        tickfont    = dict(family="JetBrains Mono", size=9),
        side        = "right",
    ),
    legend = dict(
        bgcolor     = "rgba(0,0,0,0)",
        font        = dict(size=9),
        orientation = "h",
        y           = 1.02,
        x           = 0,
    ),
    hoverlabel = dict(
        bgcolor  = "rgba(8,8,18,0.95)",
        font     = dict(family="JetBrains Mono", size=10),
        bordercolor = BORDER_ACTIVE,
    ),
    dragmode     = "pan",
    hovermode    = "x unified",
    showlegend   = True,
)

PLOTLY_HEATMAP_LAYOUT = PLOTLY_BASE_LAYOUT.copy()
# Shallow copy the nested dicts before updating
PLOTLY_HEATMAP_LAYOUT["xaxis"] = PLOTLY_BASE_LAYOUT["xaxis"].copy()
PLOTLY_HEATMAP_LAYOUT["yaxis"] = PLOTLY_BASE_LAYOUT["yaxis"].copy()

PLOTLY_HEATMAP_LAYOUT["xaxis"].update(
    showgrid=False,
    zeroline=False,
    side="bottom",
    tickfont=dict(size=8, family="JetBrains Mono"),
)
PLOTLY_HEATMAP_LAYOUT["yaxis"].update(
    showgrid=False,
    zeroline=False,
    side="left",
    tickfont=dict(size=9, family="JetBrains Mono"),
)
PLOTLY_HEATMAP_LAYOUT.update(
    margin=dict(l=40, r=40, t=10, b=40),
    plot_bgcolor="transparent",
    paper_bgcolor="transparent",
    showlegend=False,
)

# ══════════════════════════════════════════════════════════════
# STRUCTURE STYLES (inline style dicts pour composants Dash)
# ══════════════════════════════════════════════════════════════

STYLE_CARD = {
    "background": BG_CARD,
    "border": f"1px solid {BORDER_SUBTLE}",
    "borderRadius": "12px",
    "padding": "14px 18px",
    "backdropFilter": "blur(12px)",
}

STYLE_HEADER = {
    "position": "sticky",
    "top": "0",
    "zIndex": "999",
    "background": "rgba(5, 5, 8, 0.97)",
    "borderBottom": f"1px solid {BORDER_SUBTLE}",
    "backdropFilter": "blur(20px)",
    "padding": "8px 20px",
    "display": "flex",
    "alignItems": "center",
    "gap": "14px",
    "flexWrap": "wrap",
}

STYLE_APP = {
    "background": BG_BASE,
    "minHeight": "100vh",
    "fontFamily": FONT_SANS,
}

STYLE_MAIN_GRID = {
    "display": "grid",
    "gridTemplateColumns": "300px 1fr 300px",
    "gridTemplateRows": "auto",
    "gap": "10px",
    "padding": "10px 14px",
    "maxWidth": "100%",
}

STYLE_LEFT_COL = {
    "display": "flex",
    "flexDirection": "column",
    "gap": "10px",
    "minWidth": "0",
}

STYLE_CENTER_COL = {
    "display": "flex",
    "flexDirection": "column",
    "gap": "10px",
    "minWidth": "0",
}

STYLE_RIGHT_COL = {
    "display": "flex",
    "flexDirection": "column",
    "gap": "10px",
    "minWidth": "0",
}

STYLE_BOTTOM_ROW = {
    "padding": "0 14px 14px",
}

# ══════════════════════════════════════════════════════════════
# COLORSCALE HEATMAP ICT
# ══════════════════════════════════════════════════════════════

HEATMAP_COLORSCALE = [
    [0.0,  "rgba(5,5,8,1)"],
    [0.25, "rgba(30,15,60,1)"],
    [0.5,  "rgba(80,40,160,1)"],
    [0.75, "rgba(0,180,100,1)"],
    [1.0,  "rgba(0,255,136,1)"],
]

# ══════════════════════════════════════════════════════════════
# CONSTANTES ICT CONCEPTS (pour heatmap)
# ══════════════════════════════════════════════════════════════

ICT_CONCEPTS = [
    "FVG", "LV", "OB", "BB", "BPR",
    "SMT", "MSS", "CHoCH", "PD", "Sweep",
    "Killzone", "AMD", "Macro", "IDM", "COT",
]

PYRAMID_TFS = ["MN", "W1", "D1", "H4", "H1", "M15"]

PYRAMID_WEIGHTS = {
    "MN":  0.30, "W1":  0.25, "D1":  0.20,
    "H4":  0.12, "H1":  0.08, "M15": 0.05,
}
