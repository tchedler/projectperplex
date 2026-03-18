# interface/war_room_layout.py
"""
══════════════════════════════════════════════════════════════
Sentinel Pro KB5 — War Room Layout (Composants Statiques)
══════════════════════════════════════════════════════════════
Construit toutes les zones du dashboard War Room.
Rempli dynamiquement par les callbacks (war_room_callbacks.py).

Zones :
  Zone 0 — Barre de commande (header fixe)
  Zone 1 — Panneau Narratif (col gauche)
  Zone 2 — Graphique Multi-Couches (centre)
  Zone 3 — Audit Panel live (col droite)
  Zone 4 — Confluence Matrix heatmap
  Zone 5 — Journal d'Audit complet
══════════════════════════════════════════════════════════════
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from interface.war_room_styles import (
    STYLE_APP, STYLE_HEADER, STYLE_MAIN_GRID,
    STYLE_LEFT_COL, STYLE_CENTER_COL, STYLE_RIGHT_COL,
    STYLE_BOTTOM_ROW, STYLE_CARD,
    BG_CARD, BORDER_SUBTLE, BORDER_ACTIVE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    NEON_BULL, NEON_BEAR, NEON_PURPLE, NEON_GOLD, NEON_CYAN, NEON_PINK,
    FONT_MONO, FONT_SANS,
    PLOTLY_BASE_LAYOUT,
    PYRAMID_TFS, ICT_CONCEPTS,
)

# ══════════════════════════════════════════════════════════════
# ZONE 0 ── BARRE DE COMMANDE
# ══════════════════════════════════════════════════════════════

def build_zone0_header(pairs: list) -> html.Div:
    """Header fixe — sélecteurs, score gauge, clocks, alertes."""
    return html.Div(
        id="wr-header",
        style=STYLE_HEADER,
        children=[
            # Logotype
            html.Div([
                html.Span("⚔", style={"fontSize": "18px", "marginRight": "4px"}),
                html.Span("WAR ROOM", style={
                    "fontFamily": FONT_MONO,
                    "fontWeight": "700",
                    "fontSize": "13px",
                    "letterSpacing": "0.1em",
                    "color": NEON_PURPLE,
                }),
            ], style={"display": "flex", "alignItems": "center"}),

            # Separator
            html.Div(style={
                "width": "1px", "height": "28px",
                "background": BORDER_SUBTLE,
                "flexShrink": "0",
            }),

            # Pair selector
            dcc.Dropdown(
                id="wr-pair-select",
                options=[{"label": p, "value": p} for p in pairs],
                value=pairs[0] if pairs else None,
                clearable=False,
                style={
                    "minWidth": "130px",
                    "fontFamily": FONT_MONO,
                    "fontSize": "12px",
                    "background": BG_CARD,
                    "border": f"1px solid {BORDER_SUBTLE}",
                    "color": TEXT_PRIMARY,
                    "borderRadius": "8px",
                },
                className="wr-dropdown",
            ),

            # TF buttons
            html.Div(
                id="wr-tf-buttons",
                style={"display": "flex", "gap": "4px", "flexWrap": "wrap"},
                children=[
                    html.Button(
                        tf,
                        id={"type": "wr-tf-btn", "index": tf},
                        n_clicks=0,
                        className="wr-tab-btn" + (" active" if tf == "H1" else ""),
                        style={"fontFamily": FONT_MONO},
                    )
                    for tf in PYRAMID_TFS
                ],
            ),

            # Mode radio
            dbc.RadioItems(
                id="wr-mode-select",
                options=[
                    {"label": "Analyse",  "value": "analyse"},
                    {"label": "Audit",    "value": "audit"},
                    {"label": "Replay",   "value": "replay"},
                ],
                value="analyse",
                inline=True,
                style={
                    "fontFamily": FONT_MONO,
                    "fontSize": "10px",
                    "color": TEXT_SECONDARY,
                },
                inputStyle={"marginRight": "4px"},
                labelStyle={"marginRight": "12px", "cursor": "pointer"},
            ),

            # Spacer
            html.Div(style={"flex": "1"}),

            # Score gauge mini
            html.Div(
                className="wr-gauge-wrap",
                children=[
                    dcc.Graph(
                        id="wr-score-gauge",
                        config={"displayModeBar": False, "staticPlot": True},
                        style={"width": "72px", "height": "52px"},
                        figure=_empty_gauge(),
                    ),
                ],
            ),

            # Verdict chip
            html.Div(
                id="wr-verdict-chip",
                style={
                    "fontFamily": FONT_MONO,
                    "fontWeight": "700",
                    "fontSize": "11px",
                    "padding": "5px 12px",
                    "borderRadius": "20px",
                    "border": f"1px solid {BORDER_SUBTLE}",
                    "color": TEXT_MUTED,
                    "background": f"rgba(255,255,255,0.04)",
                    "letterSpacing": "0.06em",
                },
                children="––",
            ),

            # Session indicator
            html.Div([
                html.Span(className="wr-session-dot", id="wr-session-dot"),
                html.Span(id="wr-session-label", style={
                    "fontFamily": FONT_MONO,
                    "fontSize": "10px",
                    "color": TEXT_SECONDARY,
                }),
            ], style={"display": "flex", "alignItems": "center"}),

            # Triple clock
            html.Div(
                id="wr-clocks",
                style={
                    "fontFamily": FONT_MONO,
                    "fontSize": "9px",
                    "color": TEXT_MUTED,
                    "lineHeight": "1.8",
                    "textAlign": "right",
                },
            ),

            # Alert button
            html.Div(
                id="wr-alert-btn",
                style={"cursor": "pointer", "display": "none"},
                children=[
                    html.Span("! SIGNAL", className="wr-alert-badge"),
                ],
            ),

            # Interval: data refresh
            dcc.Interval(id="wr-interval-data",  interval=5_000,  n_intervals=0),
            # Interval: clock refresh
            dcc.Interval(id="wr-interval-clock", interval=1_000,  n_intervals=0),
        ],
    )


# ══════════════════════════════════════════════════════════════
# ZONE 1 ── PANNEAU NARRATIF (colonne gauche)
# ══════════════════════════════════════════════════════════════

def build_zone1_narrative() -> html.Div:
    """Narratif algo + décision tree + pyramide barres."""
    return html.Div(
        style={**STYLE_LEFT_COL, "height": "calc(100vh - 62px)", "overflowY": "auto"},
        children=[

            # ── Narratif Market ──────────────────────
            html.Div(className="wr-card", style=STYLE_CARD, children=[
                html.Div("NARRATION DU MARCHÉ", className="wr-zone-label"),
                html.Div(
                    id="wr-narrative-algo",
                    className="wr-narrative",
                    children="Chargement de l'analyse…",
                ),
                # Bouton LLM
                html.Button(
                    "🤖 Générer analyse IA",
                    id="wr-btn-llm",
                    n_clicks=0,
                    style={
                        "marginTop": "8px",
                        "background": f"rgba(124,92,252,0.15)",
                        "border": f"1px solid {NEON_PURPLE}",
                        "color": NEON_PURPLE,
                        "borderRadius": "8px",
                        "padding": "5px 12px",
                        "fontFamily": FONT_MONO,
                        "fontSize": "10px",
                        "cursor": "pointer",
                        "width": "100%",
                    },
                ),
                dcc.Loading(
                    id="wr-llm-spinner",
                    type="dot",
                    color=NEON_PURPLE,
                    children=html.Div(
                        id="wr-narrative-llm",
                        className="wr-narrative",
                        style={"marginTop": "8px", "display": "none"},
                    ),
                ),
            ]),

            # ── Score Pyramide ───────────────────────
            html.Div(className="wr-card", style=STYLE_CARD, children=[
                html.Div("PYRAMIDE KB5", className="wr-zone-label"),
                html.Div(id="wr-pyramid-bars"),
            ]),

            # ── Arbre de Décision ────────────────────
            html.Div(className="wr-card", style=STYLE_CARD, children=[
                html.Div("ARBRE DE DÉCISION", className="wr-zone-label"),
                dcc.Graph(
                    id="wr-decision-tree",
                    config={"displayModeBar": False},
                    style={"height": "200px"},
                    figure=_empty_tree(),
                ),
            ]),

            # ── Biais HTF ────────────────────────────
            html.Div(className="wr-card", style=STYLE_CARD, children=[
                html.Div("BIAIS HTF", className="wr-zone-label"),
                html.Div(id="wr-bias-panel"),
            ]),

            # ── Confluences actives ──────────────────
            html.Div(className="wr-card", style=STYLE_CARD, children=[
                html.Div("CONFLUENCES ACTIVES", className="wr-zone-label"),
                html.Div(id="wr-confluences-badges"),
            ]),

        ],
    )


# ══════════════════════════════════════════════════════════════
# ZONE 2 ── GRAPHIQUE MULTI-COUCHES (centre)
# ══════════════════════════════════════════════════════════════

def build_zone2_chart() -> html.Div:
    """Graphique principal 10 couches ICT annotées."""
    return html.Div(
        style=STYLE_CENTER_COL,
        children=[

            # TF tab labels (affiche TF sélectionné)
            html.Div(
                id="wr-chart-header",
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "10px",
                    "paddingBottom": "6px",
                },
                children=[
                    html.Span(id="wr-chart-pair-tf", style={
                        "fontFamily": FONT_MONO,
                        "fontWeight": "700",
                        "fontSize": "13px",
                        "color": TEXT_PRIMARY,
                    }, children="Chargement…"),
                    html.Span(id="wr-chart-price", style={
                        "fontFamily": FONT_MONO,
                        "fontSize": "13px",
                        "color": NEON_CYAN,
                    }),
                    # Couches toggle
                    html.Div(
                        id="wr-layer-toggles",
                        style={"display": "flex", "gap": "5px", "marginLeft": "auto"},
                        children=_build_layer_toggles(),
                    ),
                ],
            ),

            # Chart principal
            html.Div(className="wr-card", style={**STYLE_CARD, "padding": "8px"}, children=[
                dcc.Graph(
                    id="wr-main-chart",
                    config={
                        "displayModeBar": True,
                        "modeBarButtonsToRemove": [
                            "autoScale2d", "lasso2d", "select2d",
                            "toggleSpikelines", "hoverClosestCartesian",
                        ],
                        "displaylogo": False,
                        "scrollZoom": True,
                        "toImageButtonOptions": {
                            "format": "png", "filename": "war_room_chart",
                            "width": 1800, "height": 900,
                        },
                    },
                    style={"height": "calc(100vh - 220px)", "minHeight": "480px"},
                    figure=_empty_chart(),
                    # Renvoi des clicks vers audit panel
                    clickData=None,
                ),
            ]),

            # Minibar sous le chart : Entry / SL / TP / RR
            html.Div(
                id="wr-entry-bar",
                style={
                    **STYLE_CARD,
                    "display": "grid",
                    "gridTemplateColumns": "repeat(5, 1fr)",
                    "gap": "8px",
                    "padding": "8px 14px",
                },
                children=[_entry_metric(lbl, eid) for lbl, eid in [
                    ("ENTRY",     "wr-em-entry"),
                    ("STOP",      "wr-em-sl"),
                    ("TARGET",    "wr-em-tp"),
                    ("RR",        "wr-em-rr"),
                    ("TYPE",      "wr-em-type"),
                ]],
            ),
        ],
    )


# ══════════════════════════════════════════════════════════════
# ZONE 3 ── AUDIT PANEL (col droite)
# ══════════════════════════════════════════════════════════════

def build_zone3_audit() -> html.Div:
    """Panneau d'audit live — raisonnement en temps réel."""
    return html.Div(
        style={**STYLE_RIGHT_COL, "height": "calc(100vh - 62px)", "overflowY": "auto"},
        children=[

            # ── Verdict banner ───────────────────────
            html.Div(id="wr-verdict-banner", children=[
                html.Div("EN ATTENTE D'ANALYSE", className="wr-verdict-banner no_trade"),
            ]),

            # ── Élément sélectionné ──────────────────
            html.Div(className="wr-card", style=STYLE_CARD, children=[
                html.Div("ÉLÉMENT SÉLECTIONNÉ", className="wr-zone-label"),
                html.Div(id="wr-audit-detail", children=[
                    html.Span(
                        "Cliquez sur un élément du graphique pour voir les détails ICT.",
                        style={"color": TEXT_MUTED, "fontSize": "11px"},
                    ),
                ]),
            ]),

            # ── Journal de raisonnement ──────────────
            html.Div(className="wr-card", style=STYLE_CARD, children=[
                html.Div([
                    html.Div("RAISONNEMENT LIVE", className="wr-zone-label",
                             style={"display": "inline-block"}),
                    html.Span(id="wr-feed-count", style={
                        "float": "right",
                        "fontFamily": FONT_MONO,
                        "fontSize": "9px",
                        "color": TEXT_MUTED,
                    }),
                ]),
                html.Div(id="wr-audit-feed", className="wr-audit-feed"),
            ]),

            # ── KillSwitches ─────────────────────────
            html.Div(className="wr-card", style=STYLE_CARD, children=[
                html.Div("KILLSWITCHES", className="wr-zone-label"),
                html.Div(id="wr-ks-panel"),
            ]),

            # ── Circuit Breaker ──────────────────────
            html.Div(className="wr-card", style=STYLE_CARD, children=[
                html.Div("CIRCUIT BREAKER", className="wr-zone-label"),
                html.Div(id="wr-cb-panel"),
            ]),

            # ── Entry Model Detail ───────────────────
            html.Div(className="wr-card", style=STYLE_CARD, children=[
                html.Div("INVALIDATION", className="wr-zone-label"),
                html.Div(id="wr-invalidation-panel"),
            ]),
        ],
    )


# ══════════════════════════════════════════════════════════════
# ZONE 4 ── CONFLUENCE MATRIX (heatmap)
# ══════════════════════════════════════════════════════════════

def build_zone4_matrix() -> html.Div:
    """Heatmap TF × Concepts ICT."""
    return html.Div(className="wr-card", style={**STYLE_CARD, **STYLE_BOTTOM_ROW}, children=[
        html.Div([
            html.Div("CONFLUENCE MATRIX — Timeframes × Concepts ICT", className="wr-zone-label"),
            html.Span(
                "Intensité = bonus scoring | Cliquer cellule → voir règle",
                style={"fontSize": "9px", "color": TEXT_MUTED, "float": "right"},
            ),
        ]),
        dcc.Graph(
            id="wr-confluence-matrix",
            config={"displayModeBar": False},
            style={"height": "220px"},
            figure=_empty_heatmap(),
        ),
    ])


# ══════════════════════════════════════════════════════════════
# ZONE 5 ── JOURNAL D'AUDIT COMPLET
# ══════════════════════════════════════════════════════════════

def build_zone5_journal() -> html.Div:
    """Journal scrollable + export CSV."""
    return html.Div(
        className="wr-card",
        style={**STYLE_CARD, "margin": "0 14px 14px"},
        children=[
            html.Div([
                html.Div("JOURNAL D'AUDIT — Historique Complet", className="wr-zone-label",
                         style={"display": "inline-block", "marginBottom": "0"}),
                # Filtres
                html.Div([
                    dcc.Dropdown(
                        id="wr-journal-filter-pair",
                        placeholder="Paire…",
                        clearable=True,
                        options=[],
                        style={"minWidth": "110px", "fontSize": "11px", "background": BG_CARD},
                        className="wr-dropdown",
                    ),
                    dcc.Dropdown(
                        id="wr-journal-filter-concept",
                        placeholder="Concept…",
                        clearable=True,
                        options=[{"label": c, "value": c} for c in ICT_CONCEPTS],
                        style={"minWidth": "120px", "fontSize": "11px", "background": BG_CARD},
                        className="wr-dropdown",
                    ),
                    dcc.Dropdown(
                        id="wr-journal-filter-verdict",
                        placeholder="Verdict…",
                        clearable=True,
                        options=[
                            {"label": "EXECUTE",  "value": "EXECUTE"},
                            {"label": "WATCH",    "value": "WATCH"},
                            {"label": "NO_TRADE", "value": "NO_TRADE"},
                        ],
                        style={"minWidth": "110px", "fontSize": "11px", "background": BG_CARD},
                        className="wr-dropdown",
                    ),
                    html.Button(
                        "⬇ Export CSV",
                        id="wr-journal-export",
                        n_clicks=0,
                        style={
                            "background": "transparent",
                            "border": f"1px solid {BORDER_SUBTLE}",
                            "color": TEXT_SECONDARY,
                            "borderRadius": "6px",
                            "padding": "4px 10px",
                            "fontFamily": FONT_MONO,
                            "fontSize": "10px",
                            "cursor": "pointer",
                        },
                    ),
                    dcc.Download(id="wr-journal-download"),
                ], style={"display": "flex", "gap": "8px", "alignItems": "center", "float": "right"}),
            ], style={"overflow": "hidden", "marginBottom": "10px"}),
            html.Div(
                id="wr-journal-table",
                style={"overflowX": "auto"},
            ),
        ],
    )


# ══════════════════════════════════════════════════════════════
# ASSEMBLAGE LAYOUT COMPLET
# ══════════════════════════════════════════════════════════════

def build_full_layout(pairs: list) -> html.Div:
    """Assemble toutes les zones dans le layout final."""
    return html.Div(
        style=STYLE_APP,
        children=[
            # Zone 0 — Header
            build_zone0_header(pairs),

            # Main grid : left | center | right
            html.Div(
                style=STYLE_MAIN_GRID,
                children=[
                    # Col gauche — Narratif
                    build_zone1_narrative(),
                    # Col centre — Chart
                    build_zone2_chart(),
                    # Col droite — Audit
                    build_zone3_audit(),
                ],
            ),

            # Bottom — Heatmap
            html.Div(style=STYLE_BOTTOM_ROW, children=[
                build_zone4_matrix(),
            ]),

            # Bottom — Journal
            build_zone5_journal(),

            # Store partagé (données JSON entre callbacks)
            dcc.Store(id="wr-store-data"),
            dcc.Store(id="wr-store-tf",    data="H1"),
            dcc.Store(id="wr-store-layers", data={
                "fvg": True, "lv": True, "ob": True, "bb": True,
                "ssl_bsl": True, "dol": True, "entry": True,
                "sessions": True,
            }),

            # Intervalles de rafraîchissement
            dcc.Interval(id="wr-interval-clock", interval=1000, n_intervals=0),
            dcc.Interval(id="wr-interval-data",  interval=5000, n_intervals=0),
        ],
    )


# ══════════════════════════════════════════════════════════════
# HELPERS INTERNES
# ══════════════════════════════════════════════════════════════

def _empty_gauge() -> go.Figure:
    """Gauge vide initiale."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=0,
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "rgba(0,0,0,0)"},
            "bar":  {"color": NEON_PURPLE, "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 40],  "color": "rgba(255,51,85,0.15)"},
                {"range": [40, 70], "color": "rgba(245,185,66,0.15)"},
                {"range": [70, 100],"color": "rgba(0,255,136,0.15)"},
            ],
        },
        number={"font": {"family": "JetBrains Mono", "size": 14, "color": TEXT_PRIMARY}},
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=4, r=4, t=0, b=0),
        height=52,
    )
    return fig


def _empty_chart() -> go.Figure:
    """Graphique vide initial."""
    fig = go.Figure()
    fig.update_layout(
        **PLOTLY_BASE_LAYOUT,
        height=520,
        annotations=[dict(
            text="Connexion MT5 en cours…",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=13, color=TEXT_MUTED, family="JetBrains Mono"),
        )],
    )
    return fig


def _empty_tree() -> go.Figure:
    """Sankey vide initial."""
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=200,
    )
    return fig


def _empty_heatmap() -> go.Figure:
    """Heatmap vide initiale."""
    import numpy as np
    z = [[0] * len(ICT_CONCEPTS) for _ in PYRAMID_TFS]
    fig = go.Figure(go.Heatmap(
        z=z,
        x=ICT_CONCEPTS,
        y=PYRAMID_TFS,
        colorscale=[
            [0.0, "rgba(5,5,8,1)"],
            [1.0, "rgba(124,92,252,0.5)"],
        ],
        showscale=False,
        hoverongaps=False,
        xgap=2, ygap=2,
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=220,
        xaxis=dict(tickfont=dict(size=8, family="JetBrains Mono"), color=TEXT_MUTED),
        yaxis=dict(tickfont=dict(size=9, family="JetBrains Mono"), color=TEXT_MUTED),
    )
    return fig


def _build_layer_toggles() -> list:
    """Boutons pour activer/désactiver les couches du chart."""
    layers = [
        ("FVG",  "fvg",      NEON_CYAN),
        ("LV",   "lv",       NEON_PURPLE),
        ("OB",   "ob",       NEON_GOLD),
        ("BB",   "bb",       "#ff8c42"),
        ("LIQ",  "ssl_bsl",  NEON_BEAR),
        ("DOL",  "dol",      "#b4ff44"),
        ("KZ",   "sessions", NEON_PINK),
        ("ENTRY","entry",    NEON_BULL),
    ]
    buttons = []
    for label, layer_id, color in layers:
        buttons.append(
            html.Button(
                label,
                id={"type": "wr-layer-btn", "index": layer_id},
                n_clicks=0,
                style={
                    "background": f"rgba({_hex_to_rgba_str(color)}, 0.12)",
                    "border": f"1px solid {color}",
                    "borderRadius": "4px",
                    "color": color,
                    "fontFamily": FONT_MONO,
                    "fontSize": "9px",
                    "fontWeight": "600",
                    "padding": "2px 6px",
                    "cursor": "pointer",
                    "opacity": "1",
                    "transition": "opacity 0.15s",
                },
            )
        )
    return buttons


def _entry_metric(label: str, elem_id: str) -> html.Div:
    """Mini métrique d'entrée (entry bar sous graphique)."""
    return html.Div(
        style={"textAlign": "center"},
        children=[
            html.Div(label, style={
                "fontSize": "8px",
                "fontFamily": FONT_MONO,
                "fontWeight": "600",
                "letterSpacing": "0.1em",
                "color": TEXT_MUTED,
                "marginBottom": "2px",
            }),
            html.Div("–", id=elem_id, style={
                "fontFamily": FONT_MONO,
                "fontWeight": "700",
                "fontSize": "12px",
                "color": TEXT_SECONDARY,
            }),
        ],
    )


def _hex_to_rgba_str(hex_color: str) -> str:
    """Convertit #rrggbb en 'r,g,b' pour utilisation dans rgba()."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"{r},{g},{b}"
