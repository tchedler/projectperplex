# interface/war_room_callbacks.py
"""
══════════════════════════════════════════════════════════════
Sentinel Pro KB5 — War Room Callbacks
══════════════════════════════════════════════════════════════
Tous les callbacks Dash :
  - Horloge triple timezone
  - Chargement données MT5 + cache
  - Graphique 10 couches ICT
  - Narratif algorithmique + LLM
  - Audit feed live
  - Heatmap confluence
  - Journal d'audit + export CSV
  - Sélection TF / couches
══════════════════════════════════════════════════════════════
"""

import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
from dash import Input, Output, State, callback, ctx, no_update, dcc, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash import html

logger = logging.getLogger(__name__)

# Imports internes
try:
    from execution.market_state_cache import MarketStateCache
    _cache = MarketStateCache()
    _cache.load_from_disk()
except Exception as e:
    logger.warning(f"MarketStateCache indisponible: {e}")
    _cache = None

try:
    from gateway.candle_fetcher import CandleFetcher
    _fetcher = CandleFetcher()
except Exception as e:
    logger.warning(f"CandleFetcher indisponible (MT5 non connecté): {e}")
    _fetcher = None

try:
    from config.settings_manager import SettingsManager
    _settings = SettingsManager()
except Exception:
    _settings = None

from analysis.llm_narrative import generate_narrative
from interface.war_room_styles import (
    NEON_BULL, NEON_BEAR, NEON_PURPLE, NEON_GOLD, NEON_CYAN,
    NEON_ORANGE, NEON_LIME, NEON_PINK,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BORDER_SUBTLE, BORDER_ACTIVE, BG_CARD,
    FONT_MONO, FONT_SANS,
    PLOTLY_BASE_LAYOUT, HEATMAP_COLORSCALE,
    PYRAMID_TFS, ICT_CONCEPTS, PYRAMID_WEIGHTS,
    score_color, dir_color, dir_icon, VERDICT_COLORS,
)

# Imports pour Analyse Live
from datastore.data_store import DataStore
from analysis.fvg_detector import FVGDetector
from analysis.ob_detector import OBDetector
from analysis.smt_detector import SMTDetector
from analysis.bias_detector import BiasDetector
from analysis.kb5_engine import KB5Engine
from analysis.liquidity_detector import LiquidityDetector

class LiveEngine:
    """Moteur d'analyse léger pour le Dashboard."""
    def __init__(self):
        self.ds = DataStore()
        self.fvg = FVGDetector(self.ds)
        self.ob = OBDetector(self.ds)
        self.smt = SMTDetector(self.ds)
        self.bias = BiasDetector(self.ds, self.fvg, self.ob, self.smt)
        self.liq = LiquidityDetector(self.ds)
        self.engine = KB5Engine(self.ds, self.fvg, self.ob, self.smt, self.bias, self.liq)
        logger.info("LiveEngine Dashboard initialisé.")

    def run(self, pair: str):
        """Lance une analyse complète et met à jour le cache."""
        try:
            # Récupérer les bougies via MT5/Fetcher et les mettre dans DataStore
            for tf in PYRAMID_TFS:
                df = _fetch_candles_mt5(pair, tf, count=300)
                if not df.empty:
                    self.ds.set_candles(pair, tf, df)
            
            # Analyser
            result = self.engine.analyze(pair)
            
            # Mettre à jour le cache global pour que les autres callbacks en profitent
            if _cache:
                _cache.update(pair, {"kb5_result": result, "last_update": datetime.now().isoformat()})
                _cache.save_to_disk()
            return result
        except Exception as e:
            logger.error(f"Erreur LiveAnalysis {pair}: {e}")
            return {}

_live_engine = None

def get_live_engine():
    global _live_engine
    if _live_engine is None:
        _live_engine = LiveEngine()
    return _live_engine

# ──────────────────────────────────────────────────────────────
# HELPERS DATA
# ──────────────────────────────────────────────────────────────

def _get_cache_state(pair: str) -> dict:
    if _cache:
        try:
            _cache.load_from_disk()
        except Exception:
            pass
        return _cache.get(pair, {}) or {}
    return {}

def _fetch_candles_mt5(pair: str, tf: str, count: int = 300) -> pd.DataFrame:
    """Récupère les bougies depuis MT5 via CandleFetcher."""
    if _fetcher is None:
        return pd.DataFrame()
    
    # ── Fallback Cache pour H1 si MT5 indisponible ──
    try:
        df = _fetcher.fetch(pair, tf)
        if (df is None or df.empty) and tf == "H1" and _cache:
            state = _cache.get(pair, {})
            cached_candles = state.get("candles", [])
            if cached_candles:
                logger.info(f"War Room — Utilisation du cache pour {pair}/{tf}")
                return pd.DataFrame(cached_candles)
        return df
    except Exception as e:
        logger.warning(f"MT5 candles {pair}/{tf}: {e}")
        return pd.DataFrame()

def _df_to_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise le DataFrame OHLCV depuis MT5."""
    if df.empty:
        return df
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], utc=True)
            df = df.set_index("time")
    return df

# ──────────────────────────────────────────────────────────────
# CALLBACK 1 — HORLOGE TRIPLE TIMEZONE
# ──────────────────────────────────────────────────────────────

def register_clock_callback(app):
    @app.callback(
        Output("wr-clocks", "children"),
        Input("wr-interval-clock", "n_intervals"),
    )
    def update_clock(_):
        now_utc = datetime.now(timezone.utc)
        now_est = now_utc - timedelta(hours=5)
        now_cet = now_utc + timedelta(hours=1)
        return html.Div([
            html.Div(f"UTC  {now_utc.strftime('%H:%M:%S')}"),
            html.Div(f"EST  {now_est.strftime('%H:%M:%S')}"),
            html.Div(f"CET  {now_cet.strftime('%H:%M:%S')}"),
        ])

# ──────────────────────────────────────────────────────────────
# CALLBACK 2 — STORE DATA (chargement données toutes les 5s)
# ──────────────────────────────────────────────────────────────

def register_data_callback(app):
    @app.callback(
        Output("wr-store-data", "data"),
        Input("wr-interval-data",  "n_intervals"),
        Input("wr-pair-select",    "value"),
        Input("wr-store-tf",       "data"),
    )
    def refresh_data(_, pair, tf):
        if not pair:
            raise PreventUpdate
        
        state = _get_cache_state(pair)
        kb5 = state.get("kb5_result", {})
        
        # Si vide ou trop vieux, on lance une analyse Live
        if not kb5:
            logger.info(f"Dashboard — Analyse Live requise pour {pair}")
            engine = get_live_engine()
            kb5 = engine.run(pair)
            
        scoring = state.get("scoring_output", {}) or {}
        return {"pair": pair, "tf": tf or "H1", "kb5": kb5, "scoring": scoring}

# ──────────────────────────────────────────────────────────────
# CALLBACK 3 — TF STORE (sélection timeframe)
# ──────────────────────────────────────────────────────────────

def register_tf_callback(app):
    @app.callback(
        Output("wr-store-tf", "data"),
        Input({"type": "wr-tf-btn", "index": "MN"}, "n_clicks"),
        Input({"type": "wr-tf-btn", "index": "W1"}, "n_clicks"),
        Input({"type": "wr-tf-btn", "index": "D1"}, "n_clicks"),
        Input({"type": "wr-tf-btn", "index": "H4"}, "n_clicks"),
        Input({"type": "wr-tf-btn", "index": "H1"}, "n_clicks"),
        Input({"type": "wr-tf-btn", "index": "M15"}, "n_clicks"),
        prevent_initial_call=True,
    )
    def update_tf(*_):
        triggered = ctx.triggered_id
        if triggered and isinstance(triggered, dict):
            return triggered.get("index", "H1")
        return "H1"

    @app.callback(
        Output({"type": "wr-tf-btn", "index": ALL}, "className"),
        Input("wr-store-tf", "data"),
    )
    def update_tf_styles(current_tf):
        return [
            "wr-tab-btn active" if tf == current_tf else "wr-tab-btn"
            for tf in PYRAMID_TFS
        ]

def register_layers_callback(app):
    @app.callback(
        Output("wr-store-layers", "data"),
        Input({"type": "wr-layer-btn", "index": ALL}, "n_clicks"),
        State("wr-store-layers", "data"),
        prevent_initial_call=True,
    )
    def update_layers(n_clicks, current_layers):
        if not ctx.triggered_id:
            raise PreventUpdate
        
        triggered_index = ctx.triggered_id["index"]
        current_layers = current_layers or {
            "fvg": True, "lv": True, "ob": True, "bb": True,
            "ssl_bsl": True, "dol": True, "kz": True, "entry": True
        }
        
        # Toggle la couche sélectionnée
        current_layers[triggered_index] = not current_layers.get(triggered_index, True)
        return current_layers

    @app.callback(
        Output({"type": "wr-layer-btn", "index": ALL}, "style"),
        Input("wr-store-layers", "data"),
    )
    def update_layer_styles(layers):
        if not layers:
            return [no_update] * 8
            
        styles = []
        # On doit suivre l'ordre de _build_layer_toggles dans le layout
        # FVG, LV, OB, BB, LIQ (ssl_bsl), DOL, KZ, ENTRÉE (entry)
        for lid in ["fvg", "lv", "ob", "bb", "ssl_bsl", "dol", "kz", "entry"]:
            active = layers.get(lid, True)
            styles.append({
                "opacity": "1" if active else "0.3",
                "filter": "grayscale(0%)" if active else "grayscale(100%)",
                "cursor": "pointer",
                "transition": "all 0.2s"
            })
        return styles

# ──────────────────────────────────────────────────────────────
# CALLBACK 4 — GRAPHIQUE PRINCIPAL 10 COUCHES ICT
# ──────────────────────────────────────────────────────────────

def register_chart_callback(app):
    @app.callback(
        Output("wr-main-chart",    "figure"),
        Output("wr-chart-pair-tf", "children"),
        Output("wr-chart-price",   "children"),
        Input("wr-store-data",  "data"),
        Input("wr-store-tf",    "data"),
        State("wr-store-layers","data"),
    )
    def update_chart(data, tf, layers):
        if not data:
            raise PreventUpdate
        pair = data.get("pair", "")
        tf   = tf or "H1"
        kb5  = data.get("kb5", {})
        layers = layers or {}

        fig = go.Figure()
        fig.update_layout(**PLOTLY_BASE_LAYOUT, height=600)

        # ── BOUGIES MT5 ──────────────────────────────────────
        df = _fetch_candles_mt5(pair, tf)
        df = _df_to_ohlcv(df)

        price_label = "–"
        if not df.empty:
            price_label = f"{df['close'].iloc[-1]:.5f}"
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df["open"], high=df["high"],
                low=df["low"],   close=df["close"],
                name="Prix",
                increasing=dict(line=dict(color=NEON_BULL, width=1),
                                fillcolor="rgba(0,255,136,0.25)"),
                decreasing=dict(line=dict(color=NEON_BEAR, width=1),
                                fillcolor="rgba(255,51,85,0.25)"),
                hoverinfo="x+y",
            ))

        structs = kb5.get("structures", {}) or {}

        # ── COUCHE: FVG ───────────────────────────────────
        if layers.get("fvg", True):
            for fvg in structs.get("fvg", []):
                if not isinstance(fvg, dict) or fvg.get("tf") != tf:
                    continue
                bull  = fvg.get("direction", "BULLISH") == "BULLISH"
                color = "rgba(0,212,255,0.12)" if bull else "rgba(255,51,85,0.10)"
                lc    = NEON_CYAN if bull else NEON_BEAR
                tag   = "BISI" if bull else "SIBI"
                # CORRECTION : Utiliser bottom/top
                lo, hi = fvg.get("bottom", 0), fvg.get("top", 0)
                if not lo or not hi: continue
                fig.add_hrect(y0=lo, y1=hi, fillcolor=color,
                              line=dict(color=lc, width=1),
                              annotation_text=f"FVG {tag} ({fvg.get('tf')})",
                              annotation_font=dict(size=7, color=lc))

        # ── COUCHE: ORDER BLOCKS ──────────────────────────
        if layers.get("ob", True):
            for ob in structs.get("ob", []):
                if not isinstance(ob, dict) or ob.get("tf") != tf:
                    continue
                status = ob.get("status", "")
                # CORRECTION : Utiliser bottom/top
                lo, hi = ob.get("bottom", 0), ob.get("top", 0)
                if not lo or not hi: continue
                color = "rgba(245,185,66,0.15)" if status == "VALID" else "rgba(200,200,200,0.05)"
                lc    = NEON_GOLD if status == "VALID" else TEXT_MUTED
                fig.add_hrect(y0=lo, y1=hi, fillcolor=color,
                              line=dict(color=lc, width=1.5, dash="dash"),
                              annotation_text=f"OB {ob.get('tf')} [{ob.get('quality','N')}]",
                              annotation_font=dict(size=7, color=lc))

        # ── COUCHE: BREAKER BLOCKS ────────────────────────
        if layers.get("bb", True):
            for bb in structs.get("bb", []):
                if not isinstance(bb, dict) or bb.get("tf") != tf:
                    continue
                # CORRECTION : Utiliser bottom/top
                lo, hi = bb.get("bottom", 0), bb.get("top", 0)
                if not lo or not hi: continue
                fig.add_hrect(y0=lo, y1=hi,
                              fillcolor="rgba(255,140,66,0.10)",
                              line=dict(color=NEON_ORANGE, width=1, dash="longdash"),
                              annotation_text=f"BB {bb.get('tf')}",
                              annotation_font=dict(size=7, color=NEON_ORANGE))

        # ── COUCHE: SSL / BSL (Liquidité) ─────────────────
        if layers.get("ssl_bsl", True):
            liq = structs.get("liq", {})
            for key, val in (liq.items() if isinstance(liq, dict) else []):
                price = val.get("price", 0) if isinstance(val, dict) else float(val or 0)
                if not price: continue
                is_bsl = "bsl" in key.lower() or "high" in key.lower()
                lc     = NEON_BEAR if is_bsl else NEON_BULL
                label  = "BSL" if is_bsl else "SSL"
                fig.add_hline(y=price, line=dict(color=lc, width=1.5, dash="dot"),
                              annotation_text=f"💧{label} {price:.5f}",
                              annotation_font=dict(size=8, color=lc))

        # ── COUCHE: DOL / ENTRY / SL / TP ─────────────────
        if layers.get("dol", True):
            dol = structs.get("dol", {})
            target = dol.get("target_level", 0)
            if target:
                fig.add_hline(y=target, line=dict(color=NEON_LIME, width=2, dash="dot"),
                              annotation_text=f"🎯 DOL {target:.5f}",
                              annotation_font=dict(size=9, color=NEON_LIME))

        if layers.get("entry", True):
            em = kb5.get("entry_model") or {}
            for key, clr, lbl in [
                ("entry", NEON_PURPLE, "ENTRY"),
                ("sl",    NEON_BEAR,   "SL"),
                ("tp",    NEON_BULL,   "TP"),
            ]:
                val = em.get(key, 0)
                if val:
                    fig.add_hline(y=val, line=dict(color=clr, width=1.5),
                                  annotation_text=f"{lbl} {val:.5f}",
                                  annotation_font=dict(size=9, color=clr))

        fig.update_layout(
            title=dict(
                text=f"<b>{pair} @ {tf}</b>",
                font=dict(family=FONT_MONO, size=12, color=TEXT_PRIMARY),
                x=0,
            ),
            xaxis_rangeslider_visible=False,
        )

        tf_label = f"{pair}  ·  {tf}"
        return fig, tf_label, price_label

# ──────────────────────────────────────────────────────────────
# CALLBACK 5 — SCORE GAUGE + VERDICT CHIP
# ──────────────────────────────────────────────────────────────

def register_gauge_callback(app):
    @app.callback(
        Output("wr-score-gauge",  "figure"),
        Output("wr-verdict-chip", "children"),
        Output("wr-verdict-chip", "style"),
        Output("wr-verdict-banner","children"),
        Input("wr-store-data", "data"),
    )
    def update_gauge(data):
        if not data:
            raise PreventUpdate
        scoring  = data.get("scoring", {})
        score    = scoring.get("score",   0)
        verdict  = scoring.get("verdict", "NO_TRADE")
        grade    = scoring.get("grade",   "C")
        vc       = VERDICT_COLORS.get(verdict, TEXT_MUTED)

        # Gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "transparent"},
                "bar":  {"color": score_color(score), "thickness": 0.3},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0,  40], "color": "rgba(255,51,85,0.10)"},
                    {"range": [40, 70], "color": "rgba(245,185,66,0.10)"},
                    {"range": [70,100], "color": "rgba(0,255,136,0.10)"},
                ],
            },
            number={"font": {"family": "JetBrains Mono", "size": 13, "color": TEXT_PRIMARY}},
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=4, r=4, t=0, b=0), height=52,
        )

        # Chip style
        chip_style = {
            "fontFamily": FONT_MONO, "fontWeight": "700", "fontSize": "11px",
            "padding": "5px 12px", "borderRadius": "20px",
            "border": f"1px solid {vc}", "color": vc,
            "background": f"rgba({_hex_rgb(vc)}, 0.10)",
            "letterSpacing": "0.06em",
        }

        # Verdict banner
        css_class = verdict.lower().replace("_", "")
        banner = html.Div(
            f"{verdict}  [{grade}]  {score}/100",
            className=f"wr-verdict-banner {css_class}",
        )

        return fig, f"{verdict} {grade}", chip_style, banner

# ──────────────────────────────────────────────────────────────
# CALLBACK 6 — SESSION INDICATOR
# ──────────────────────────────────────────────────────────────

def register_session_callback(app):
    @app.callback(
        Output("wr-session-label", "children"),
        Output("wr-session-dot",   "className"),
        Input("wr-interval-clock", "n_intervals"),
        State("wr-store-data",     "data"),
    )
    def update_session(_, data):
        scoring  = (data or {}).get("scoring", {})
        session  = scoring.get("session", "")
        in_kz    = scoring.get("in_killzone", False)
        if not session:
            hour = datetime.now(timezone.utc).hour
            if 7 <= hour < 12:   session = "LONDON"
            elif 12 <= hour < 16: session = "OVERLAP LDN/NY"
            elif 16 <= hour < 21: session = "NEW YORK"
            else:                 session = "ASIA"
        dot_cls = "wr-session-dot" + (" bear" if in_kz else "")
        return f"{session}{'  ⚡KZ' if in_kz else ''}", dot_cls

# ──────────────────────────────────────────────────────────────
# CALLBACK 7 — NARRATIF ALGORITHMIQUE
# ──────────────────────────────────────────────────────────────

def register_narrative_callback(app):
    @app.callback(
        Output("wr-narrative-algo", "children"),
        Input("wr-store-data", "data"),
    )
    def update_narrative(data):
        if not data:
            return "Chargement…"
        kb5     = data.get("kb5", {}) or {}
        scoring = data.get("scoring", {}) or {}
        pair    = data.get("pair", "")
        return _build_algo_narrative(pair, kb5, scoring)

# ──────────────────────────────────────────────────────────────
# CALLBACK 8 — NARRATIF LLM (bouton déclenché)
# ──────────────────────────────────────────────────────────────

def register_llm_callback(app):
    @app.callback(
        Output("wr-narrative-llm", "children"),
        Output("wr-narrative-llm", "style"),
        Input("wr-btn-llm",    "n_clicks"),
        State("wr-store-data", "data"),
        prevent_initial_call=True,
    )
    def generate_llm_narrative(n_clicks, data):
        if not n_clicks or not data:
            raise PreventUpdate
        kb5     = data.get("kb5", {}) or {}
        scoring = data.get("scoring", {}) or {}
        pair    = data.get("pair", "")
        try:
            cfg      = _settings.get_llm_config() if _settings else {}
            provider = cfg.get("llm_provider", "Gemini")
            api_key  = cfg.get("llm_api_key", "")
            
            # Fallback direct sur os.environ si config vide
            import os
            if not api_key:
                if provider == "Gemini": api_key = os.getenv("GEMINI_API_KEY", "")
                elif provider in ("Grok", "Groq"): api_key = os.getenv("GROQ_API_KEY", "") or os.getenv("GROK_API_KEY", "")

            text     = generate_narrative(provider, api_key, pair, kb5, scoring)
        except Exception as e:
            text = f"⚠️ Erreur: {e}"
        style = {
            "marginTop": "8px", "display": "block",
            "color": TEXT_SECONDARY, "fontSize": "12px",
            "lineHeight": "1.8", "fontStyle": "italic",
            "padding": "10px 14px",
            "borderLeft": f"3px solid {NEON_CYAN}",
            "background": f"rgba(0,212,255,0.04)",
            "borderRadius": "0 8px 8px 0",
        }
        return text, style

# ──────────────────────────────────────────────────────────────
# CALLBACK 9 — PYRAMIDE BARRES
# ──────────────────────────────────────────────────────────────

def register_pyramid_callback(app):
    @app.callback(
        Output("wr-pyramid-bars", "children"),
        Input("wr-store-data", "data"),
    )
    def update_pyramid(data):
        if not data:
            raise PreventUpdate
        kb5    = data.get("kb5", {}) or {}
        scores = kb5.get("pyramid_scores", {}) or {}
        bars   = []
        for tf in PYRAMID_TFS:
            score  = int(scores.get(tf, 0))
            weight = PYRAMID_WEIGHTS.get(tf, 0)
            color  = score_color(score)
            bars.append(html.Div(className="wr-pyramid-bar-wrap", children=[
                html.Div(tf,   className="wr-pyramid-label"),
                html.Div(className="wr-pyramid-bar-bg", children=[
                    html.Div(className="wr-pyramid-bar-fill", style={
                        "width": f"{score}%",
                        "background": f"linear-gradient(90deg, {color}cc, {color})",
                    }),
                ]),
                html.Div(f"{score}", className="wr-pyramid-score",
                         style={"color": color}),
                html.Div(f"{int(weight*100)}%", style={
                    "fontFamily": FONT_MONO, "fontSize": "8px",
                    "color": TEXT_MUTED, "minWidth": "28px",
                }),
            ]))
        return bars

# ──────────────────────────────────────────────────────────────
# CALLBACK 10 — CONFLUENCES BADGES
# ──────────────────────────────────────────────────────────────

def register_confluences_callback(app):
    @app.callback(
        Output("wr-confluences-badges", "children"),
        Input("wr-store-data", "data"),
    )
    def update_confluences(data):
        if not data:
            raise PreventUpdate
        kb5 = data.get("kb5", {}) or {}
        confluences = kb5.get("confluences", []) or []
        if not confluences:
            return html.Span("Aucune confluence détectée", style={"color": TEXT_MUTED, "fontSize": "11px"})
        badges = []
        for c in confluences[:20]:
            if not isinstance(c, dict):
                continue
            name  = c.get("name", str(c))
            bonus = c.get("bonus", c.get("points", 0))
            bull  = "BULL" in name.upper() or bonus > 0
            color = NEON_BULL if bull else NEON_BEAR
            badges.append(html.Span(
                f"{name} +{bonus}",
                className="wr-conf-badge",
                title=c.get("description", name),
                style={
                    "color": color,
                    "borderColor": f"{color}55",
                    "background": f"{color}15",
                },
            ))
        return badges

# ──────────────────────────────────────────────────────────────
# CALLBACK 11 — AUDIT FEED LIVE
# ──────────────────────────────────────────────────────────────

def register_audit_feed_callback(app):
    @app.callback(
        Output("wr-audit-feed",  "children"),
        Output("wr-feed-count",  "children"),
        Input("wr-store-data",   "data"),
    )
    def update_audit_feed(data):
        if not data:
            raise PreventUpdate
        kb5     = data.get("kb5", {}) or {}
        scoring = data.get("scoring", {}) or {}
        pair    = data.get("pair", "")
        entries = _build_audit_entries(pair, kb5, scoring)
        count   = f"{len(entries)} événements"
        return entries, count

# ──────────────────────────────────────────────────────────────
# CALLBACK 12 — HEATMAP CONFLUENCE MATRIX
# ──────────────────────────────────────────────────────────────

def register_heatmap_callback(app):
    @app.callback(
        Output("wr-confluence-matrix", "figure"),
        Input("wr-store-data", "data"),
    )
    def update_heatmap(data):
        if not data:
            raise PreventUpdate
        kb5         = data.get("kb5", {}) or {}
        confluences = kb5.get("confluences", []) or []
        structs     = kb5.get("structures", {}) or {}

        # ── Construire la matrice TF × Concept ────────────────
        z    = [[0.0] * len(ICT_CONCEPTS) for _ in PYRAMID_TFS]
        text = [[""] * len(ICT_CONCEPTS) for _ in PYRAMID_TFS]

        concept_map = {
            "FVG": "FVG", "LV": "LV", "OB": "OB", "BB": "BB",
            "BPR": "BPR", "SMT": "SMT", "MSS": "MSS", "CHOCH": "CHoCH",
            "PD": "PD", "SWEEP": "Sweep", "KILLZONE": "Killzone",
            "AMD": "AMD", "MACRO": "Macro", "IDM": "IDM", "COT": "COT",
        }

        # 1. Scanner les structures pour remplir les bases (FVG, OB, BB)
        for cat in ["fvg", "ob", "bb"]:
            for item in structs.get(cat, []):
                tf_item = (item.get("tf") or "").upper()
                if tf_item in PYRAMID_TFS:
                    ti = PYRAMID_TFS.index(tf_item)
                    ci = ICT_CONCEPTS.index(cat.upper())
                    z[ti][ci] = max(z[ti][ci], 15.0) # Base de présence
                    text[ti][ci] = "✓"

        # 2. Scanner les confluences pour les bonus
        for c in confluences:
            if not isinstance(c, dict):
                continue
            name  = (c.get("name") or "").upper()
            bonus = float(c.get("bonus", c.get("points", 0)) or 0)
            tf    = (c.get("tf") or "").upper()
            tf_idx = PYRAMID_TFS.index(tf) if tf in PYRAMID_TFS else None

            for key, concept in concept_map.items():
                if key in name and concept in ICT_CONCEPTS:
                    ci = ICT_CONCEPTS.index(concept)
                    if tf_idx is not None:
                        z[tf_idx][ci] = max(z[tf_idx][ci], bonus + 20)
                        text[tf_idx][ci] = f"+{int(bonus)}"
                    else:
                        for ti in range(len(PYRAMID_TFS)):
                            z[ti][ci] = max(z[ti][ci], bonus + 20)

        hover = [[
            f"<b>{ICT_CONCEPTS[ci]}</b> @ {PYRAMID_TFS[ti]}<br>Force: {z[ti][ci]:.0f}"
            for ci in range(len(ICT_CONCEPTS))]
            for ti in range(len(PYRAMID_TFS))
        ]

        fig = go.Figure(go.Heatmap(
            z=z, x=ICT_CONCEPTS, y=PYRAMID_TFS,
            text=text, texttemplate="%{text}",
            textfont=dict(size=8, family="JetBrains Mono"),
            colorscale=HEATMAP_COLORSCALE,
            showscale=False,
            hovertext=hover, hoverinfo="text",
            xgap=2, ygap=2,
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0), height=220,
            xaxis=dict(tickfont=dict(size=7, family="JetBrains Mono"), color=TEXT_MUTED),
            yaxis=dict(tickfont=dict(size=8, family="JetBrains Mono"), color=TEXT_MUTED),
        )
        return fig

# ──────────────────────────────────────────────────────────────
# CALLBACK 13 — ENTRY BAR (Entry/SL/TP/RR/Type)
# ──────────────────────────────────────────────────────────────

def register_entry_bar_callback(app):
    @app.callback(
        Output("wr-em-entry", "children"),
        Output("wr-em-sl",    "children"),
        Output("wr-em-tp",    "children"),
        Output("wr-em-rr",    "children"),
        Output("wr-em-type",  "children"),
        Output("wr-em-entry", "style"),
        Output("wr-em-sl",    "style"),
        Output("wr-em-tp",    "style"),
        Input("wr-store-data", "data"),
    )
    def update_entry_bar(data):
        mono_base = {"fontFamily": FONT_MONO, "fontWeight": "700", "fontSize": "12px"}
        if not data:
            empty = "–"
            s = {**mono_base, "color": TEXT_MUTED}
            return empty, empty, empty, empty, empty, s, s, s

        kb5 = data.get("kb5", {}) or {}
        em  = kb5.get("entry_model", {}) or {}
        dir_ = (kb5.get("direction") or data.get("scoring", {}).get("direction", ""))

        entry = em.get("entry")
        sl    = em.get("sl")
        tp    = em.get("tp")
        rr    = em.get("rr", 0.0)
        etype = em.get("entry_type", "–")
        dc    = dir_color(dir_)

        fmt = lambda v: f"{v:.5f}" if v else "–"
        style_entry  = {**mono_base, "color": dc}
        style_sl     = {**mono_base, "color": NEON_BEAR}
        style_tp     = {**mono_base, "color": NEON_BULL}

        return (fmt(entry), fmt(sl), fmt(tp),
                f"{rr:.2f}×" if rr else "–",
                etype or "–",
                style_entry, style_sl, style_tp)

# ──────────────────────────────────────────────────────────────
# CALLBACK 14 — KS + CB PANELS
# ──────────────────────────────────────────────────────────────

def register_ks_cb_callback(app):
    @app.callback(
        Output("wr-ks-panel", "children"),
        Output("wr-cb-panel", "children"),
        Output("wr-invalidation-panel", "children"),
        Input("wr-store-data", "data"),
    )
    def update_ks_cb(data):
        if not data:
            raise PreventUpdate
        scoring = data.get("scoring", {}) or {}
        kb5     = data.get("kb5",     {}) or {}

        # KS panel
        ks       = scoring.get("killswitches", {}) or {}
        blocked  = ks.get("blocked_by", []) or []
        warnings = ks.get("warnings",   []) or []
        ks_items = []
        for k in blocked:
            ks_items.append(html.Div(f"🔴 {k}", style={"color": NEON_BEAR, "fontFamily": FONT_MONO, "fontSize": "11px"}))
        for w in warnings:
            ks_items.append(html.Div(f"🟡 {w}", style={"color": NEON_GOLD, "fontFamily": FONT_MONO, "fontSize": "11px"}))
        if not ks_items:
            ks_items = [html.Div("✅ Tous KS clairs", style={"color": NEON_BULL, "fontFamily": FONT_MONO, "fontSize": "11px"})]

        # CB panel
        cb      = scoring.get("circuit_breaker", {}) or {}
        cb_lvl  = cb.get("level", 0)
        cb_ok   = cb.get("trading_ok", True)
        cb_clr  = NEON_BULL if cb_ok else NEON_BEAR
        cb_panel = html.Div([
            html.Span(f"CB{cb_lvl}", style={"fontFamily": FONT_MONO, "fontWeight": "700", "color": cb_clr, "fontSize": "13px"}),
            html.Span(f"  {'TRADING OK' if cb_ok else 'TRADING BLOQUÉ'}",
                      style={"fontFamily": FONT_MONO, "fontSize": "10px", "color": cb_clr}),
        ])

        # Invalidation
        inv = kb5.get("invalidation", {}) or {}
        inv_text = inv.get("condition", inv.get("level", "–")) if inv else "Non défini"
        inv_panel = html.Div(inv_text, style={"fontFamily": FONT_MONO, "fontSize": "11px", "color": NEON_ORANGE})

        return ks_items, cb_panel, inv_panel

# ──────────────────────────────────────────────────────────────
# CALLBACK 15 — JOURNAL TABLE + EXPORT CSV
# ──────────────────────────────────────────────────────────────

def register_journal_callback(app):
    @app.callback(
        Output("wr-journal-table",    "children"),
        Output("wr-journal-download", "data"),
        Input("wr-store-data",        "data"),
        Input("wr-journal-export",    "n_clicks"),
        State("wr-journal-filter-pair",    "value"),
        State("wr-journal-filter-concept", "value"),
        State("wr-journal-filter-verdict", "value"),
        prevent_initial_call=True,
    )
    def update_journal(data, n_export, f_pair, f_concept, f_verdict):
        triggered_id = ctx.triggered_id
        rows = _build_journal_rows(data, f_pair, f_concept, f_verdict)

        if triggered_id == "wr-journal-export" and rows:
            df_export = pd.DataFrame([r["props"]["data"] if hasattr(r, "props") else {} for r in rows])
            return rows, dcc.send_data_frame(df_export.to_csv, "war_room_audit.csv", index=False)

        headers = ["Heure", "Paire", "Concept ICT", "Description", "Bonus", "TF", "Score", "Verdict"]
        header_row = html.Tr([html.Th(h, style={
            "fontFamily": FONT_MONO, "fontSize": "9px", "fontWeight": "600",
            "letterSpacing": "0.08em", "color": TEXT_MUTED,
            "borderBottom": f"1px solid {BORDER_SUBTLE}", "padding": "5px 8px",
        }) for h in headers])

        return html.Table(
            [html.Thead(header_row), html.Tbody(rows)],
            style={"width": "100%", "borderCollapse": "collapse", "fontSize": "10px"},
        ), no_update

# ──────────────────────────────────────────────────────────────
# HELPERS INTERNES
# ──────────────────────────────────────────────────────────────

def _build_algo_narrative(pair: str, kb5: dict, scoring: dict) -> str:
    """Génère un narratif institutionnel algorithmique depuis les données."""
    direction = kb5.get("direction", scoring.get("direction", "NEUTRAL"))
    score     = scoring.get("score", 0)
    verdict   = scoring.get("verdict", "NO_TRADE")
    grade     = scoring.get("grade", "C")
    rr        = (kb5.get("entry_model") or {}).get("rr", 0)
    session   = scoring.get("session", "inconnu")
    in_kz     = scoring.get("in_killzone", False)
    bias      = scoring.get("bias", {}) or {}
    weekly    = (bias.get("weekly") or "–")
    daily     = (bias.get("daily") or "–")
    pd_zone   = (bias.get("pd_zone") or "UNKNOWN")
    confluences = kb5.get("confluences", []) or []
    n_conf    = len(confluences)
    em        = (kb5.get("entry_model") or {})
    entry     = em.get("entry")
    sl        = em.get("sl")
    tp        = em.get("tp")

    dir_txt = {"BULLISH": "haussier 📈", "BEARISH": "baissier 📉"}.get(direction, "neutre ━")
    kz_txt  = f"La session **{session}** est active{'  ⚡ Killzone en cours' if in_kz else ''}. "

    narrative = (
        f"Le biais institutionnel sur **{pair}** est **{dir_txt}** avec un alignement "
        f"Weekly **{weekly}** / Daily **{daily}**. "
        f"Le prix évolue en zone **{pd_zone}**, "
        f"{'zone optimale d\'achat' if pd_zone=='DISCOUNT' else 'zone optimale de vente' if pd_zone=='PREMIUM' else 'zone équilibre (éviter)'}. "
        f"{kz_txt}"
        f"**{n_conf}** confluence(s) ICT/SMC ont été détectées. "
    )
    if entry and sl and tp:
        narrative += (
            f"Le modèle d\'entrée propose : **Entry {entry:.5f}** | "
            f"SL {sl:.5f} | TP {tp:.5f} | RR **{rr:.2f}×**. "
        )
    narrative += (
        f"Score final : **{score}/100** → Verdict **{verdict} [{grade}]**."
    )
    return narrative


def _build_audit_entries(pair: str, kb5: dict, scoring: dict) -> list:
    """Construit les entrées du feed d'audit."""
    entries      = []
    confluences  = kb5.get("confluences", []) or []
    now_str      = datetime.now(timezone.utc).strftime("%H:%M:%S")
    direction    = (kb5.get("direction") or scoring.get("direction") or "NEUTRAL")
    score        = scoring.get("score", 0)
    verdict      = scoring.get("verdict", "")

    for c in confluences[:15]:
        if not isinstance(c, dict):
            continue
        name  = c.get("name", "?")
        bonus = c.get("bonus", c.get("points", 0))
        desc  = c.get("description", name)
        bull  = bonus > 0
        css   = "bull" if bull else "bear"
        entries.append(html.Div([
            html.Span(now_str,  className="wr-audit-ts"),
            html.Span(pair,     className="wr-audit-pair"),
            html.Span(f"{name}: {desc}  +{bonus}pts", className="wr-audit-msg"),
        ], className=f"wr-audit-entry {css}"))

    # Ajouter les détections de structures au feed
    structs = kb5.get("structures", {}) or {}
    for cat, label, css in [("fvg", "FVG", "info"), ("ob", "OB", "warn"), ("bb", "BB", "info")]:
        items = structs.get(cat, [])
        if items:
            last = items[-1]
            entries.append(html.Div([
                html.Span(now_str, className="wr-audit-ts"),
                html.Span(pair,    className="wr-audit-pair"),
                html.Span(f"DÉTECTION: {label} {last.get('tf')} {last.get('direction')} @ {last.get('top')}", 
                          className="wr-audit-msg"),
            ], className=f"wr-audit-entry {css}"))

    if verdict:
        vc  = "bull" if verdict == "EXECUTE" else "warn" if verdict == "WATCH" else "bear"
        entries.append(html.Div([
            html.Span(now_str, className="wr-audit-ts"),
            html.Span(pair,    className="wr-audit-pair"),
            html.Span(f"→ VERDICT: {verdict}  score={score}/100  dir={direction}",
                      className="wr-audit-msg"),
        ], className=f"wr-audit-entry {vc}"))

    return entries or [html.Div(
        "En attente de données d'analyse…",
        style={"color": TEXT_MUTED, "fontSize": "11px", "padding": "8px"},
    )]


def _build_journal_rows(data: dict, f_pair, f_concept, f_verdict) -> list:
    """Construit les lignes du journal d'audit."""
    if not data:
        return []
    kb5         = data.get("kb5",     {}) or {}
    scoring     = data.get("scoring", {}) or {}
    pair        = data.get("pair", "")
    confluences = kb5.get("confluences", []) or []
    verdict     = scoring.get("verdict", "")
    score       = scoring.get("score", 0)
    now_str     = datetime.now(timezone.utc).strftime("%H:%M:%S")

    rows = []
    for c in confluences:
        if not isinstance(c, dict):
            continue
        name    = c.get("name", "?")
        desc    = c.get("description", name)
        bonus   = c.get("bonus", c.get("points", 0))
        tf      = c.get("tf", "–")

        if f_pair    and pair.upper() != f_pair.upper():     continue
        if f_concept and f_concept.upper() not in name.upper(): continue
        if f_verdict and verdict != f_verdict:               continue

        bull  = bonus > 0
        color = NEON_BULL if bull else NEON_BEAR
        rows.append(html.Tr([
            html.Td(now_str, style={"color": TEXT_MUTED,    "fontFamily": FONT_MONO, "padding": "4px 8px"}),
            html.Td(pair,    style={"color": NEON_CYAN,     "fontFamily": FONT_MONO, "fontWeight": "700"}),
            html.Td(name,    style={"color": color,         "fontFamily": FONT_MONO, "fontWeight": "600"}),
            html.Td(desc,    style={"color": TEXT_SECONDARY,"fontSize": "10px"}),
            html.Td(f"+{bonus}", style={"color": color,     "fontFamily": FONT_MONO}),
            html.Td(tf,      style={"color": TEXT_MUTED,    "fontFamily": FONT_MONO}),
            html.Td(str(score), style={"color": TEXT_SECONDARY}),
            html.Td(verdict, style={"color": VERDICT_COLORS.get(verdict, TEXT_MUTED)}),
        ], style={"borderBottom": f"1px solid {BORDER_SUBTLE}"}))

    # 3. Ajouter les structures détectées pour un audit exhaustif
    structs = kb5.get("structures", {}) or {}
    for cat, label, color in [("fvg", "FVG", NEON_CYAN), ("ob", "OB", NEON_GOLD), ("bb", "Breaker", NEON_ORANGE)]:
        for item in structs.get(cat, []):
            itf = item.get("tf", "–")
            if f_pair and pair.upper() != f_pair.upper(): continue
            if f_concept and label.upper() not in f_concept.upper(): continue
            
            rows.append(html.Tr([
                html.Td(now_str, style={"color": TEXT_MUTED, "padding": "4px 8px"}),
                html.Td(pair,    style={"color": NEON_CYAN, "fontWeight": "700"}),
                html.Td(f"STRUCT:{label}", style={"color": color, "fontWeight": "600"}),
                html.Td(f"{item.get('direction')} {label} @ {item.get('top')}", style={"color": TEXT_SECONDARY}),
                html.Td("–", style={"color": TEXT_MUTED}),
                html.Td(itf, style={"color": TEXT_MUTED}),
                html.Td("–", style={"color": TEXT_MUTED}),
                html.Td("AUDIT", style={"color": TEXT_MUTED}),
            ], style={"borderBottom": f"1px solid {BORDER_SUBTLE}", "opacity": "0.8"}))

    return rows


def _hex_rgb(hex_color: str) -> str:
    """#rrggbb → 'r,g,b'."""
    h = hex_color.lstrip("#")
    if len(h) == 3: h = "".join(c*2 for c in h)
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


# ──────────────────────────────────────────────────────────────
# ENREGISTREMENT DE TOUS LES CALLBACKS
# ──────────────────────────────────────────────────────────────

def register_all_callbacks(app):
    """Enregistre tous les callbacks sur l'app Dash."""
    register_clock_callback(app)
    register_data_callback(app)
    register_tf_callback(app)
    register_layers_callback(app)
    register_chart_callback(app)
    register_gauge_callback(app)
    register_session_callback(app)
    register_narrative_callback(app)
    register_llm_callback(app)
    register_pyramid_callback(app)
    register_confluences_callback(app)
    register_audit_feed_callback(app)
    register_heatmap_callback(app)
    register_entry_bar_callback(app)
    register_ks_cb_callback(app)
    register_journal_callback(app)
