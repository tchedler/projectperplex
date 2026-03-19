"""
main_streamlit.py — Interface Streamlit pour SENTINEL PRO KB5
=============================================================
Dashboard visuel complet.
Lit les données depuis market_state.pkl (bridge KB5 → UI).

Lancement : streamlit run main_streamlit.py
"""

# ── Imports Streamlit ─────────────────────────────────────────
try:
    import streamlit as st
except ModuleNotFoundError:
    raise SystemExit("Streamlit non installé. Lancez : pip install streamlit")

# ── Imports standard ──────────────────────────────────────────
import warnings
warnings.filterwarnings("ignore")

import os
import sys
import datetime

# Assurer que le dossier racine est dans le PATH
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ── Import Orchestrateur (graphiques Plotly) ──────────────────
try:
    from orchestrator import ProOrchestrator
    ORCH_OK = True
except ImportError:
    ORCH_OK = False

# ── Import Bridge (pont DataStore → Streamlit) ────────────────
try:
    from bridge.bridge import get_dashboard_data_from_cache, CB_COLORS, CB_LABELS, VERDICT_COLORS
    BRIDGE_OK = True
except ImportError:
    BRIDGE_OK = False
    CB_COLORS  = {0: "#00ff88", 1: "#f0b429", 2: "#ef5350", 3: "#b71c1c", 4: "#4a0000"}
    CB_LABELS  = {0: "NOMINAL", 1: "ALERTE", 2: "DANGER", 3: "CRITIQUE", 4: "SHUTDOWN"}
    VERDICT_COLORS = {}

# ── Import Interface Bot ──────────────────────────────────────
try:
    from interface.bot_settings import (
        render_bot_settings, is_bot_running,
        start_bot_process, stop_bot_process, load_config,
        PROFILE_LABELS, MODE_LABELS
    )
    from interface.bot_monitor import render_bot_monitor
    BOT_UI_OK = True
except ImportError:
    BOT_UI_OK = False

# ── Import Plotly ─────────────────────────────────────────────
try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

# ── Chemin cache pickle KB5 ───────────────────────────────────
CACHE_FILE = os.path.join(ROOT_DIR, "market_state.pkl")

# ─────────────────────────────────────────────────────────────
# CONFIG PAGE
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ICT SENTINEL KB5 — PRO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────
# CSS GLASSMORPHISM COMPLET
# ─────────────────────────────────────────────────────────────
st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Outfit:wght@500;700;900&display=swap');

.stApp {
    background: radial-gradient(circle at top right, #1a1f2c 0%, #0d1117 100%);
    color: #d1d4dc;
    font-family: 'Inter', sans-serif;
}
.hero-container { padding: 60px 20px; text-align: center; background: transparent; }

.report-card, .feature-card {
    background: rgba(30, 39, 58, 0.8);
    padding: 24px;
    border-radius: 16px;
    border: 1px solid rgba(41,98,255,0.25);
    margin-bottom: 16px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.feature-card:hover {
    transform: translateY(-8px);
    border-color: #00ff88;
    box-shadow: 0 12px 48px rgba(0,255,136,0.2);
    background: rgba(35, 45, 68, 0.95);
}
.feature-card h4 {
    color: #00ff88; margin: 0 0 12px 0;
    font-weight: 800; font-family: 'Outfit', sans-serif; letter-spacing: 0.5px;
}
.feature-card p { color: #cbd5e0 !important; font-size: 0.95rem; line-height: 1.6; }

.metric-box {
    background: rgba(45, 55, 72, 0.7);
    padding: 18px; border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.1);
    text-align: center; color: #fff;
    backdrop-filter: blur(8px);
}
.metric-box b { color: #4dabff; font-size: 1.1rem; }

.narrative-card {
    background: rgba(30, 39, 58, 0.8);
    padding: 28px; border-radius: 16px;
    border: 1px solid rgba(41,98,255,0.25);
}
.metric-yellow { color: #ffff00 !important; font-size: 2rem; font-weight: 800; }

.gate-card {
    background: linear-gradient(135deg, rgba(255,75,43,0.15) 0%, rgba(255,177,43,0.1) 100%) !important;
    padding: 24px; border-radius: 16px;
    box-shadow: 0 8px 32px rgba(255,75,43,0.15);
    margin-bottom: 20px; color: #fff !important;
    border: 1px solid rgba(255,75,43,0.5) !important;
    backdrop-filter: blur(12px);
}
.gate-card h4 {
    font-family: 'Outfit', sans-serif; font-weight: 800;
    color: #ffb12b !important;
    border-bottom: 1px solid rgba(255,75,43,0.3) !important;
    padding-bottom: 10px;
}
.gate-card b, .gate-card span { color: #fff !important; }
.gate-card p { color: #d1d4dc !important; }

.stTabs [data-baseweb='tab-list'] { gap: 12px; background-color: transparent; }
.stTabs [data-baseweb='tab'] {
    background-color: rgba(30,34,45,0.5);
    border-radius: 8px; color: #848e9c;
    padding: 10px 20px;
    border: 1px solid transparent;
    transition: all 0.2s ease;
}
.stTabs [data-baseweb='tab']:hover { border-color: rgba(41,98,255,0.5); color: #fff; }
.stTabs [aria-selected='true'] {
    background: linear-gradient(135deg, #2962ff 0%, #1c44b3 100%) !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(41,98,255,0.3);
}

[data-testid='stSidebar'] {
    background-color: #06090e;
    border-right: 1px solid rgba(255,255,255,0.05);
}
[data-testid='stWidgetLabel'] p,
[data-testid='stWidgetLabel'] span,
label p, label span,
.stCheckbox p, .stRadio p,
div[role='radiogroup'] p,
div[data-baseweb='checkbox'] p {
    color: #eab308 !important;
    font-weight: 500 !important;
}
[data-testid='stSidebar'] div[data-testid='stMarkdownContainer'] p { color: #eab308 !important; }
[data-testid='stMarkdownContainer'] p,
[data-testid='stMarkdownContainer'] span { color: #d1d4dc; }
button:disabled p { color: #848e9c !important; }

code {
    color: #00ff88 !important;
    background-color: rgba(0,255,136,0.1) !important;
    padding: 2px 7px !important;
    border-radius: 4px !important;
}
hr { border-color: rgba(255,255,255,0.1); }

.stButton button,
[data-testid='baseButton-primary'],
[data-testid='baseButton-secondary'] {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.stButton button:hover { transform: translateY(-2px); filter: brightness(1.15); }

.element-container:has(.btn-fermer-wrapper) .element-container button {
    background-color: #ff4b4b !important; color: white !important; border: none !important;
}
.element-container:has(.btn-retour-wrapper) .element-container button {
    background-color: #0066ff !important; color: white !important; border: none !important;
}
</style>
""")

# ─────────────────────────────────────────────────────────────
# PAIRES CONFIGURÉES — 24 symboles Exness Standard
# ─────────────────────────────────────────────────────────────
PAIRS_CONFIG = {
    "💶 EUR/USD":    "EURUSDm",
    "💷 GBP/USD":    "GBPUSDm",
    "🇯🇵 USD/JPY":   "USDJPYm",
    "🇨🇭 USD/CHF":   "USDCHFm",
    "🇨🇦 USD/CAD":   "USDCADm",
    "🇦🇺 AUD/USD":   "AUDUSDm",
    "🇳🇿 NZD/USD":   "NZDUSDm",
    "🇬🇧 GBP/JPY":   "GBPJPYm",
    "🇪🇺 EUR/JPY":   "EURJPYm",
    "🇪🇺 EUR/GBP":   "EURGBPm",
    "📈 US100 (NQ)": "USTECm",
    "📊 US500 (ES)": "US500m",
    "🇺🇸 US30 (YM)":  "US30m",
    "🇩🇪 DE30":      "DE30m",
    "🇬🇧 UK100":     "UK100m",
    "🇯🇵 JP225":     "JP225m",
    "🇪🇺 STOXX50":   "STOXX50m",
    "🛢️ UK Oil":     "UKOILm",
    "🥇 XAU/USD":    "XAUUSDm",
    "🥈 XAG/USD":    "XAGUSDm",
    "🛢️ WTI Oil":    "USOILm",
    "₿ BTC/USD":     "BTCUSDm",
    "🔷 ETH/USD":    "ETHUSDm",
    "💵 DXY":        "DXYm",
}

ALL_TFS = ["MN", "W1", "D1", "H4", "H1", "M15", "M5", "M1"]

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
_defaults = {
    "pair_cache":     None,
    "active_pairs":   [],
    "last_analysis":  None,
    "scores_summary": {},
    "bot_page":       "analyse",
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────
# FONCTIONS UTILITAIRES
# ─────────────────────────────────────────────────────────────
def load_dashboard_data() -> dict:
    """Charge les données depuis le cache pickle KB5."""
    if BRIDGE_OK:
        try:
            return get_dashboard_data_from_cache(CACHE_FILE)
        except Exception:
            pass
    return {}


# ─────────────────────────────────────────────────────────────
# RENDU — ONGLET PRICE ACTION
# ─────────────────────────────────────────────────────────────
def _render_pa_tab(sym: str, tf: str):
    """Onglet Price Action indépendant par TF."""
    if not ORCH_OK:
        st.warning("Module PAOrchestrator non disponible.")
        return
    try:
        from agents.pa_orchestrator import PAOrchestrator
        cfg         = load_config() if BOT_UI_OK else {}
        score_exec  = cfg.get("score_execute", 80)
        score_limit = cfg.get("score_limit",   65)
        with st.spinner("Analyse Price Action en cours…"):
            pa_orch = PAOrchestrator(sym)
            result  = pa_orch.analyze(tf, score_execute=score_exec, score_limit=score_limit)
        if not result.get("ok"):
            st.warning(f"PA : {result.get('narratif', 'Données MT5 indisponibles.')}")
            return

        score     = result["score"]
        verdict   = result["verdict"]
        direction = result.get("direction", "NEUTRE")
        levels    = result.get("levels", {})
        narratif  = result.get("narratif", "")
        features  = result.get("features", {})

        sc_color  = "#00ff88" if score >= score_exec else "#f0b429" if score >= score_limit else "#ef5350"
        dir_color = "#00ff88" if direction == "BUY" else "#ef5350" if direction == "SELL" else "#848e9c"
        dir_icon  = "🟢 ACHAT" if direction == "BUY" else "🔴 VENTE" if direction == "SELL" else "⚪ NEUTRE"
        cycle_type = features.get("cycle", {}).get("type", "?")
        ema_touch  = features.get("ema_position", {}).get("ema_touch_last3", False)
        cyc_color  = "#f0b429" if "CANAL" in cycle_type else "#00ff88" if "BREAKOUT" in cycle_type else "#ef5350" if "TIGHT" in cycle_type else "#848e9c"

        m1, m2, m3 = st.columns(3)
        m1.html(f"""<div class='metric-box' style='border-color:{sc_color}33'>
            <div style='font-size:0.7rem;color:#848e9c;text-transform:uppercase;letter-spacing:1px'>Score PA</div>
            <div style='font-size:2.4rem;font-weight:900;color:{sc_color};line-height:1.1'>{score}<span style='font-size:1rem'>/100</span></div>
            <div style='font-size:0.75rem;color:{sc_color};margin-top:4px;font-weight:700'>{verdict}</div>
        </div>""")
        m2.html(f"""<div class='metric-box' style='border-color:{dir_color}33'>
            <div style='font-size:0.7rem;color:#848e9c;text-transform:uppercase;letter-spacing:1px'>Direction PA</div>
            <div style='font-size:1.6rem;font-weight:900;color:{dir_color};margin:6px 0'>{dir_icon}</div>
        </div>""")
        m3.html(f"""<div class='metric-box'>
            <div style='font-size:0.7rem;color:#848e9c;text-transform:uppercase;letter-spacing:1px'>Cycle</div>
            <div style='font-size:1.1rem;font-weight:700;color:{cyc_color};margin:6px 0'>{cycle_type.replace("_"," ")}</div>
            <div style='font-size:0.72rem;color:#848e9c'>EMA Touche <b style='color:#d4d4d4'>{"OUI" if ema_touch else "NON"}</b></div>
        </div>""")
        st.html("<br/>")

        sl  = levels.get("sl",  "—")
        tp1 = levels.get("tp1", "—")
        tp2 = levels.get("tp2", "—")
        st.html(f"""<div style='display:flex;gap:12px;margin-bottom:14px'>
            <div style='flex:1;background:#1a1a2e;border:1px solid #ef535044;border-radius:10px;padding:12px;text-align:center'>
                <div style='font-size:0.65rem;color:#ef5350;text-transform:uppercase;letter-spacing:1px'>Stop Loss</div>
                <div style='font-size:1.1rem;font-weight:700;color:#ef5350;margin-top:4px'>{sl}</div>
            </div>
            <div style='flex:1;background:#1a2e1a;border:1px solid #00ff8844;border-radius:10px;padding:12px;text-align:center'>
                <div style='font-size:0.65rem;color:#00ff88;text-transform:uppercase;letter-spacing:1px'>Take Profit 1</div>
                <div style='font-size:1.1rem;font-weight:700;color:#00ff88;margin-top:4px'>{tp1}</div>
            </div>
            <div style='flex:1;background:#1a2e1a;border:1px solid #00ff8844;border-radius:10px;padding:12px;text-align:center'>
                <div style='font-size:0.65rem;color:#00e673;text-transform:uppercase;letter-spacing:1px'>Take Profit 2</div>
                <div style='font-size:1.1rem;font-weight:700;color:#00e673;margin-top:4px'>{tp2}</div>
            </div>
        </div>""")

        if narratif:
            st.html(f"""<div style='background:rgba(212,160,23,0.07);border:1px solid #d4a01730;
                border-left:4px solid #d4a017;border-radius:8px;padding:16px 20px;
                font-size:0.88rem;color:#d4d4d4;line-height:1.7'>{narratif}</div>""")
    except Exception as e:
        st.error(f"Erreur PA : {e}")


# ─────────────────────────────────────────────────────────────
# RENDU — ONGLET ICT (par TF)
# ─────────────────────────────────────────────────────────────
def _render_tf_tab(orch, symbol: str, tf: str, tf_data, gbias: dict, clock: dict, bias_color: str):
    """Rendu complet d'un onglet TF : score, graphique, 6 cartes droite."""
    if tf_data is None:
        st.warning(f"Données {tf} indisponibles pour {symbol}. Démarrez le bot KB5.")
        return

    try:
        df, smc, liq, exe, mmxm, smt_result = tf_data
    except (TypeError, ValueError):
        st.warning(f"Format de données {tf} incompatible.")
        return

    if smc is None:
        st.warning(f"Analyse SMC insuffisante pour {symbol} {tf}.")
        return

    try:
        col_left, col_mid, col_right = st.columns([1, 2.8, 1], gap="medium")

        # ── Colonne gauche : Score + Rapport ──────────────────
        with col_left:
            md, score, verdict = orch.chk_ac.generate(tf, smc, liq, gbias, exe, mmxm, clock)
            sc_color = "#00ff88" if score >= 80 else "#f0b429" if score >= 65 else "#ef5350"
            st.html(f"""<div style='text-align:center;padding:10px;background:rgba(255,255,0,0.1);
                border-radius:12px;border:1px solid rgba(255,255,0,0.3);margin-bottom:15px'>
                <small style='color:#848e9c'>SCORE SENTINELLE</small>
                <div class='metric-yellow'>{score}/100</div>
                <div style='color:{sc_color};font-size:0.9rem'>{verdict}</div>
            </div>""")
            st.html(f"<div class='report-card'>{md}</div>")

        # ── Colonne centrale : Graphique + Narratif ───────────
        with col_mid:
            if ORCH_OK:
                fig = orch.build_chart_pro(df, smc, liq, exe, mmxm, tf,
                                           clock=clock, smt_result=smt_result)
                st.plotly_chart(fig, use_container_width=True,
                                config={
                                    "displayModeBar": True,
                                    "scrollZoom": True,
                                    "editable": True,
                                    "modeBarButtonsToAdd": ["drawline", "drawrect", "eraseshape"],
                                    "displaylogo": False
                                },
                                key=f"plotly_{symbol}_{tf}")
            narrative_html = orch.chk_ac.generate_ia_narrative(
                tf, score, verdict, gbias, mmxm,
                smc=smc, liq=liq, exe=exe, clock=clock
            )
            st.html(f"""<div class='narrative-card'>
                <h3 style='color:#2962ff;margin-top:0'>🗣️ NARRATIF IA &nbsp;
                <span style='font-size:0.8rem;color:#848e9c;font-weight:400'>{symbol} · {tf}</span></h3>
                {narrative_html}
            </div>""")

        # ── Colonne droite : 6 cartes ICT ────────────────────
        with col_right:
            # 1. BIAIS HTF
            htf_bias = gbias.get("htf_bias", "?") if isinstance(gbias, dict) else str(gbias)
            dol_name = gbias.get("draw_on_liquidity", {}).get("name", "?") if isinstance(gbias, dict) else "?"
            dol_dist = gbias.get("draw_on_liquidity", {}).get("dist", 0) if isinstance(gbias, dict) else 0
            st.html(f"""<div class='report-card'>
                <h4>🌐 CONTEXTE HTF</h4>
                <p>Bias <code style='color:{bias_color}'>{htf_bias}</code></p>
                <p style='font-size:0.85rem'>DOL {dol_name}<br/>Dist {dol_dist:.4f}</p>
            </div>""")

            # 2. ERL SWEEP
            sweep     = smc.get("erl_sweep", {})
            sweep_val = sweep.get("swept", False)
            st.html(f"""<div class='{"report-card" if sweep_val else "gate-card"}'>
                <h4>🛡️ BALAYAGE ERL</h4>
                <p>{"✅ BALAYAGE CONFIRMÉ" if sweep_val else "⚠️ PAS DE BALAYAGE"}</p>
                <p style='font-size:0.8rem'>PDH: {sweep.get('pdh', 0):.5f}<br/>PDL: {sweep.get('pdl', 0):.5f}</p>
            </div>""")

            # 3. SMT DIVERGENCE
            smt_active = smt_result and smt_result.get("smt_divergence")
            smt_color  = "#ef5350" if smt_active else "#848e9c"
            smt_type   = smt_result.get("smt_type", "NONE") if smt_active else "Smooth Correlation"
            smt_corr   = smt_result.get("correlated_with", "N/A") if smt_result else "N/A"
            st.html(f"""<div class='report-card'>
                <h4>🔗 SMT DIVERGENCE</h4>
                <p style='color:{smt_color};font-weight:bold'>{smt_type}</p>
                <p style='font-size:0.8rem'>vs {smt_corr}</p>
            </div>""")

            # 4. CBDR
            cbdr      = liq.get("cbdr", {})
            cbdr_exp  = cbdr.get("cbdr_explosive", False)
            cbdr_color = "#f0b429" if cbdr_exp else "#848e9c"
            st.html(f"""<div class='report-card'>
                <h4>📊 CBDR</h4>
                <p style='font-size:0.8rem'>H <code>{cbdr.get('cbdr_high', 0):.5f}</code><br/>
                L <code>{cbdr.get('cbdr_low', 0):.5f}</code><br/>
                Range <b>{cbdr.get('cbdr_range_pips', 0):.1f} pips</b></p>
                <p style='color:{cbdr_color};font-size:0.9rem'>{'💥 EXPLOSIVE' if cbdr_exp else '⚪ Normal'}</p>
            </div>""")

            # 5. LIQUIDITÉ
            erl       = liq.get("erl", {})
            prox      = liq.get("proximal_liquidity", 0)
            h_status  = erl.get("high_status", "?")
            l_status  = erl.get("low_status",  "?")
            h_color   = "#f0b429" if h_status == "SWEPT" else "#ef5350"
            l_color   = "#f0b429" if l_status == "SWEPT" else "#26a69a"
            st.html(f"""<div class='report-card'>
                <h4>🧲 LIQUIDITÉ</h4>
                <p>BSL <code style='color:#ef5350'>{erl.get('high', 0):.5f}</code>
                   <span style='font-size:0.75rem;color:{h_color}'> {h_status}</span></p>
                <p>SSL <code style='color:#26a69a'>{erl.get('low', 0):.5f}</code>
                   <span style='font-size:0.75rem;color:{l_color}'> {l_status}</span></p>
                <p>Proximal <code>{prox:.5f}</code></p>
            </div>""")

            # 6. PD ARRAYS
            pd_html = "<div class='report-card'><h4>⚡ PD ARRAYS</h4>"
            for pd_item in exe.get("pd_hierarchy", [])[:5]:
                c = "#00ff88" if ("BULL" in pd_item["type"] or "BISI" in pd_item["type"]) else "#ef5350"
                inst = " ★" if pd_item.get("institutional") else ""
                pd_html += f"<p style='font-size:0.8rem;margin:3px 0'>{pd_item['type']}{inst} <b style='color:{c}'>{pd_item['price']:.5f}</b></p>"
            pd_html += "</div>"
            st.html(pd_html)

    except Exception as e:
        st.error(f"Erreur rendu TF {tf} : {e}")


# ─────────────────────────────────────────────────────────────
# RENDU PRINCIPAL D'UNE PAIRE
# ─────────────────────────────────────────────────────────────
def render_analysis_for_symbol(symbol: str, sym_cache: dict):
    """
    Affiche l'analyse complète d'une paire.
    sym_cache : données issues de market_state.pkl via le bridge.
    """
    label = sym_cache.get("label", symbol)

    # Lecture biais HTF depuis les données réelles KB5
    gbias_raw = sym_cache.get("global_bias", {})
    if isinstance(gbias_raw, str):
        gbias = {"htf_bias": gbias_raw, "draw_on_liquidity": {"name": "?", "dist": 0}}
    elif isinstance(gbias_raw, dict):
        gbias = gbias_raw
    else:
        gbias = {"htf_bias": "N/A", "draw_on_liquidity": {"name": "?", "dist": 0}}

    htf_bias   = gbias.get("htf_bias", "N/A")
    bias_color = "#00c864" if "BULL" in str(htf_bias) else "#ef5350" if "BEAR" in str(htf_bias) else "#848e9c"

    # Instanciation orchestrateur pour graphiques + narratif
    orch  = ProOrchestrator(symbol) if ORCH_OK else None
    clock = orch.time_ac.get_clock_state() if (orch and hasattr(orch, "time_ac")) else {}

    # ── En-tête paire (titre + boutons) ──────────────────────
    h_col, close_col, back_col = st.columns([8, 2, 2])
    with h_col:
        st.markdown(f"### 💎 {label}")
    with close_col:
        st.html("<div class='btn-fermer-wrapper'></div>")
        if st.button("❌ Fermer", key=f"close_{symbol}", use_container_width=True):
            active = st.session_state.get("active_pairs", [])
            if symbol in active:
                active.remove(symbol)
            st.session_state["active_pairs"] = active
            if not active:
                st.session_state["pair_cache"] = None
            st.rerun()
    with back_col:
        st.html("<div class='btn-retour-wrapper'></div>")
        if st.button("🏠 Retour", key=f"back_{symbol}", use_container_width=True):
            st.session_state["pair_cache"]   = None
            st.session_state["active_pairs"] = []
            st.session_state["last_analysis"] = None
            st.rerun()

    # ── 3 métriques permanentes (couche HTF) ─────────────────
    dol_name  = gbias.get("draw_on_liquidity", {}).get("name", "?")
    dol_price = gbias.get("draw_on_liquidity", {}).get("price", 0)
    session   = clock.get("killzone", "—") if clock else "—"

    m1, m2, m3 = st.columns(3)
    m1.html(f"<div class='metric-box'>🌍 BIAIS HTF<br/><b style='color:{bias_color}'>{htf_bias}</b></div>")
    m2.html(f"<div class='metric-box'>🕒 SESSION<br/><b>{session}</b></div>")
    m3.html(f"<div class='metric-box'>🎯 CIBLE DOL<br/><b style='color:{bias_color}'>{dol_name} {f'{dol_price:.5f}' if dol_price else ''}</b></div>")
    st.html("<br/>")

    # Erreur bot pas lancé
    if "error" in sym_cache:
        st.error(f"⚠️ {sym_cache['error']}")
        return

    # ── Sélecteur TF ─────────────────────────────────────────
    selected_tf = st.radio(
        "Timeframe", ALL_TFS, index=5,   # M15 par défaut
        horizontal=True, key=f"tf_{symbol}"
    )

    # Score et biais propres au TF sélectionné
    tf_scores = sym_cache.get("tf_scores", {})
    tf_score  = tf_scores.get(selected_tf, {}).get("score", 0)
    tf_bias   = tf_scores.get(selected_tf, {}).get("bias", htf_bias)
    tf_bcolor = "#00c864" if "BULL" in str(tf_bias) else "#ef5350" if "BEAR" in str(tf_bias) else "#848e9c"
    sc_color  = "#00ff88" if tf_score >= 80 else "#f0b429" if tf_score >= 65 else "#ef5350"
    aligned   = (("BULL" in str(htf_bias) and "BULL" in str(tf_bias)) or
                 ("BEAR" in str(htf_bias) and "BEAR" in str(tf_bias)))

    # Bandeau couche TF
    b1, b2, b3 = st.columns(3)
    b1.html(f"<div class='metric-box' style='border-color:{tf_bcolor}44'>🎯 BIAIS {selected_tf}<br/><b style='color:{tf_bcolor}'>{tf_bias}</b></div>")
    b2.html(f"<div class='metric-box' style='border-color:{sc_color}44'>⭐ SCORE {selected_tf}<br/><b style='color:{sc_color};font-size:1.4rem'>{tf_score}/100</b></div>")
    b3.html(f"<div class='metric-box'>🔗 ALIGNEMENT<br/><b style='color:{'#00ff88' if aligned else '#ef5350'}'>{'✅ ALIGNÉ HTF' if aligned else '⚠️ CONFLIT'}</b></div>")
    st.html("<br/>")

    # ── Onglets ICT / PA ──────────────────────────────────────
    tab_ict, tab_pa = st.tabs(["🛡️ Analyse ICT", "📊 Analyse Price Action"])

    with tab_ict:
        if orch:
            # Données TF depuis market_state.pkl
            timeframes = sym_cache.get("timeframes", {})
            tf_raw     = timeframes.get(selected_tf, None)
            _render_tf_tab(orch, symbol, selected_tf, tf_raw, gbias, clock, bias_color)
        else:
            st.warning("orchestrator.py non disponible — graphiques désactivés.")

    with tab_pa:
        _render_pa_tab(symbol, selected_tf)


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
st.sidebar.title("💎 SENTINEL KB5-PRO")

# Navigation
page = st.sidebar.radio(
    "Navigation",
    options=["analyse", "bot_settings", "bot_monitor"],
    format_func=lambda x: {
        "analyse":      "🔬 Analyse ICT",
        "bot_settings": "⚙️ Paramètres Bot",
        "bot_monitor":  "📡 Monitoring Bot",
    }.get(x, x),
    index=["analyse", "bot_settings", "bot_monitor"].index(
        st.session_state.get("bot_page", "analyse")
    ),
    key="nav_page"
)
st.session_state["bot_page"] = page

# Statut bot depuis le bridge
dash_data  = load_dashboard_data()
bot_status = dash_data.get("bot_status", {})
bot_running = bot_status.get("bot_is_running", False)
last_hb    = bot_status.get("last_heartbeat", "—")

if bot_running:
    st.sidebar.success(f"🟢 BOT ACTIF | {last_hb}")
else:
    st.sidebar.info("⚫ Bot arrêté")

# Pages secondaires (Settings / Monitor)
if page != "analyse":
    st.sidebar.markdown("---")
    if page == "bot_settings" and BOT_UI_OK:
        render_bot_settings()
        st.stop()
    elif page == "bot_monitor" and BOT_UI_OK:
        render_bot_monitor(bot_active=bot_running)
        st.stop()
    elif not BOT_UI_OK:
        st.error("Modules interface/bot_settings.py introuvables.")
        st.stop()

# ── Sélection des paires ─────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown(
    "<small style='color:#848e9c;font-weight:600;letter-spacing:1px'>📊 PAIRES À ANALYSER</small>",
    unsafe_allow_html=True
)

col_tout, col_aucun = st.sidebar.columns(2)
if col_tout.button("☑️ Tout", use_container_width=True, key="btn_tout"):
    for lbl in PAIRS_CONFIG:
        st.session_state[f"pair_{lbl}"] = True
    st.rerun()
if col_aucun.button("⬜ Aucun", use_container_width=True, key="btn_aucun"):
    for lbl in PAIRS_CONFIG:
        st.session_state[f"pair_{lbl}"] = False
    st.rerun()

selected_pairs = []
has_crypto = False
for label, symbol in PAIRS_CONFIG.items():
    default_val = st.session_state.get(f"pair_{label}", False)
    checked = st.sidebar.checkbox(label, value=default_val, key=f"pair_{label}")
    if checked:
        selected_pairs.append(symbol)
    if any(x in symbol.upper() for x in ["BTC", "ETH"]):
        has_crypto = True

if has_crypto:
    st.sidebar.warning("⚠️ Killzones/Macros ICT moins fiables sur Crypto 24/7.")

# ── Bouton LANCER (unique) ────────────────────────────────────
st.sidebar.markdown("---")
lancer = st.sidebar.button(
    "🔬 LANCER L'ANALYSE",
    use_container_width=True,
    type="primary",
    key="btn_lancer_unique",
    disabled=len(selected_pairs) == 0
)

last_ok = st.session_state.get("last_analysis")
if last_ok:
    st.sidebar.markdown(
        f"<small style='color:#848e9c'>🟢 Dernière analyse : <b>{last_ok}</b><br/>Recliquez pour mettre à jour.</small>",
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        "<small style='color:#848e9c'>Sélectionnez vos paires puis cliquez sur <b>LANCER</b>.</small>",
        unsafe_allow_html=True
    )

# Scores résumé latéral
if st.session_state["scores_summary"]:
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "<small style='color:#848e9c;font-weight:600;letter-spacing:1px'>SCORES KB5</small>",
        unsafe_allow_html=True
    )
    for sym, sc in st.session_state["scores_summary"].items():
        if sc >= 80:
            bar_color = "#00c864"; verdict_txt = "🚀 EXEC A+"
        elif sc >= 65:
            bar_color = "#f0b429"; verdict_txt = "🔍 WATCH"
        else:
            bar_color = "#ef5350"; verdict_txt = "❌ NO TRADE"
        st.sidebar.markdown(
            f"<div style='margin:6px 0'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:2px'>"
            f"<b style='color:#d1d4dc'>{sym}</b>"
            f"<span style='color:{bar_color};font-weight:700'>{sc}/100</span></div>"
            f"<div style='background:rgba(42,46,57,0.8);border-radius:4px;height:6px'>"
            f"<div style='width:{max(int(sc),3)}%;background:{bar_color};border-radius:4px;height:6px'></div></div>"
            f"<div style='font-size:0.72rem;color:{bar_color};margin-top:2px'>{verdict_txt}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

st.sidebar.markdown(
    "<small style='color:#848e9c'>🔌 MT5 via market_state.pkl</small>",
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────────────────────
# BANDEAU TRADES LIVE (refresh auto toutes les 5s)
# ─────────────────────────────────────────────────────────────
@st.fragment(run_every=5)
def _render_live_trades_banner():
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return
        positions = mt5.positions_get()
        if not positions:
            return

        cfg         = load_config() if BOT_UI_OK else {}
        profile_lbl = PROFILE_LABELS.get(cfg.get("profile", "DAY_TRADE"), "Inconnu") if BOT_UI_OK else ""
        mode_key    = cfg.get("op_mode", "PAPER")
        mode_badge  = "🟥 SIMULATION PAPER" if "PAPER" in mode_key else (
                      "🟨 SEMI-AUTO" if "SEMI" in mode_key else "🟩 ORDRES RÉELS")

        st.markdown(
            f"### 📡 Trades en cours — "
            f"<span style='font-size:0.7em;color:#4dabff'>{profile_lbl}</span> "
            f"<span style='font-size:0.6em;background:rgba(255,255,255,0.1);padding:2px 6px;border-radius:4px;margin-left:10px'>{mode_badge}</span>",
            unsafe_allow_html=True
        )
        cols = st.columns(min(len(positions), 4))
        for i, pos in enumerate(positions):
            col       = cols[i % 4]
            dir_color = "#00c864" if pos.type == 0 else "#ef5350"
            dir_label = "BUY 📈" if pos.type == 0 else "SELL 📉"
            pnl_color = "#00c864" if pos.profit > 0 else "#ef5350"
            sl_display = pos.sl if pos.sl > 0 else "⚠️ ABSENT"
            with col:
                st.html(f"""
                <div style="background:rgba(30,34,45,0.8);border:1px solid {dir_color}44;
                            border-radius:8px;padding:12px;margin-bottom:10px">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <strong style="font-size:1.1em;color:#fff">{pos.symbol}</strong>
                    <span style="color:{dir_color};font-weight:bold;font-size:0.9em;
                                 background:rgba(255,255,255,0.05);padding:2px 6px;border-radius:4px">
                      {dir_label} {pos.volume}
                    </span>
                  </div>
                  <div style="display:flex;justify-content:space-between;font-size:0.85em;color:#848e9c;margin-bottom:4px">
                    <span>Entry: <span style="color:#fff">{pos.price_open}</span></span>
                    <span>Now: <span style="color:#fff">{pos.price_current}</span></span>
                  </div>
                  <div style="display:flex;justify-content:space-between;font-size:0.85em;color:#848e9c;margin-bottom:8px">
                    <span>SL: <span style="color:#ef5350">{sl_display}</span></span>
                    <span>TP: <span style="color:#00ff88">{pos.tp if pos.tp > 0 else '–'}</span></span>
                  </div>
                  <div style="text-align:center;border-top:1px solid rgba(255,255,255,0.1);
                              padding-top:8px;font-weight:bold;font-size:1.1em;color:{pnl_color}">
                    {pos.profit:+.2f} $
                  </div>
                </div>""")
    except Exception:
        pass

_render_live_trades_banner()

# ─────────────────────────────────────────────────────────────
# CHARGEMENT DONNÉES (déclenchement unique)
# ─────────────────────────────────────────────────────────────
if lancer and selected_pairs:
    temp_cache  = {}
    temp_scores = {}
    with st.spinner("⏳ Chargement des analyses KB5…"):
        prog      = st.progress(0, text="Lecture en cours…")
        all_data  = load_dashboard_data()
        pairs_raw = all_data.get("pairs", {})      # dict  sym → données

        for idx, symbol in enumerate(selected_pairs):
            label = next((l for l, s in PAIRS_CONFIG.items() if s == symbol), symbol)
            if symbol in pairs_raw:
                entry = dict(pairs_raw[symbol])
                entry["label"] = label
                temp_cache[symbol]  = entry
                temp_scores[symbol] = entry.get("best_score", 0)
            else:
                temp_cache[symbol] = {
                    "label": label,
                    "error": f"{symbol} : pas encore analysé par le cerveau KB5. Démarrez le bot.",
                }
                temp_scores[symbol] = 0
            prog.progress((idx + 1) / len(selected_pairs))
        prog.progress(1.0, text="✅ Chargement terminé !")

    st.session_state["pair_cache"]     = temp_cache
    st.session_state["active_pairs"]   = selected_pairs
    st.session_state["scores_summary"] = temp_scores
    st.session_state["last_analysis"]  = datetime.datetime.now().strftime("%H:%M:%S")
    st.rerun()

# ─────────────────────────────────────────────────────────────
# RENDU PRINCIPAL
# ─────────────────────────────────────────────────────────────
pair_cache  = st.session_state.get("pair_cache")
active_list = st.session_state.get("active_pairs", [])

if pair_cache and active_list:
    # ── Écran analyse multi-paires ────────────────────────────
    valid_list = [s for s in active_list if s in pair_cache]
    if not valid_list:
        st.session_state["pair_cache"] = None
        st.rerun()

    # Circuit Breaker (si activé)
    cb_data = dash_data.get("circuit_breaker", {})
    cb_lvl  = cb_data.get("level", 0)
    if cb_lvl > 0 and BRIDGE_OK:
        st.html(
            f"<div style='background:rgba(239,83,80,0.15);border:1px solid #ef5350;"
            f"border-radius:8px;padding:10px 16px;margin-bottom:16px'>"
            f"🔴 <b>CIRCUIT BREAKER CB{cb_lvl}</b> — {CB_LABELS.get(cb_lvl, '')}</div>"
        )

    st.header(f"🔱 ICT SENTINEL KB5 — {len(valid_list)} PAIRE(S) ANALYSÉE(S)")

    tab_labels = [pair_cache[s].get("label", s) for s in valid_list]
    p_tabs     = st.tabs(tab_labels)
    for idx, sym in enumerate(valid_list):
        with p_tabs[idx]:
            render_analysis_for_symbol(sym, pair_cache[sym])

else:
    # ── Écran d'accueil ───────────────────────────────────────
    all_data   = load_dashboard_data()
    bot_status = all_data.get("bot_status", {})
    is_running = bot_status.get("bot_is_running", False)
    last_hb    = bot_status.get("last_heartbeat", "—")
    equity     = all_data.get("equity", 0.0)
    cb_data    = all_data.get("circuit_breaker", {})
    cb_lvl     = cb_data.get("level", 0)
    status_color = "#00ff88" if is_running else "#ef5350"
    status_txt   = "🟢 BOT ACTIF" if is_running else "⚫ BOT ARRÊTÉ"
    cb_color     = CB_COLORS.get(cb_lvl, "#00ff88")

    st.html(f"""
    <div style='text-align:center;padding:40px 20px'>
      <h2 style='color:#4dabff;font-family:Outfit,sans-serif;margin-bottom:5px'>
        🛡️ ICT Sentinel KB5 Pro
      </h2>
      <div style='display:inline-block;background:#111;border:1px solid {status_color};
           border-radius:10px;padding:8px 24px;margin:10px;font-weight:700;
           color:{status_color};font-size:1.0rem;letter-spacing:1px'>
        {status_txt} &nbsp;|&nbsp; {last_hb}
      </div>
      <div style='display:inline-block;background:#111;border:1px solid {cb_color};
           border-radius:10px;padding:8px 24px;margin:10px;font-weight:700;
           color:{cb_color};font-size:0.9rem'>
        CB{cb_lvl} — {CB_LABELS.get(cb_lvl, 'NOMINAL')}
      </div>
      <div style='color:#848e9c;margin:10px;font-size:1rem'>
        Équité : <b style='color:#4dabff'>{equity:.2f} $</b>
      </div>
    </div>
    """)

    c1, c2, c3 = st.columns(3)
    for col, icon, title, desc in [
        (c1, "🛡️", "ANALYSE ICT",  "Pyramide MN→M15 · 10 confluences · ERL Gate"),
        (c2, "🤖", "CERVEAU KB5",  "Circuit Breaker 4 niveaux · KillSwitch · BehaviourShield"),
        (c3, "📊", "MULTI-ÉCOLE",  "ICT + Price Action + Personnalisé · Score de convergence"),
    ]:
        col.markdown(f"""
        <div class='feature-card' style='text-align:center;padding:28px 20px'>
            <div style='font-size:2.2em;margin-bottom:8px'>{icon}</div>
            <h4>{title}</h4>
            <p>{desc}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center;margin-top:40px;padding:18px;
         border:2px dashed rgba(41,98,255,0.4);border-radius:10px;
         color:#2962ff;font-size:1.1em'>
        🚀 SÉLECTIONNEZ VOS PAIRES DANS LA BARRE LATÉRALE ⬅️
    </div>
    """, unsafe_allow_html=True)

    # Mini-scores live si bot actif
    scores_live = all_data.get("scores_summary", {})
    if scores_live:
        st.html("<br/>")
        cols = st.columns(min(len(scores_live), 4))
        for i, (sym, sc) in enumerate(list(scores_live.items())[:4]):
            sc_color = "#00ff88" if sc >= 80 else "#f0b429" if sc >= 65 else "#ef5350"
            with cols[i % 4]:
                st.html(
                    f"<div style='background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);"
                    f"border-radius:12px;padding:18px 14px;text-align:center'>"
                    f"<div style='font-size:1rem;font-weight:800;color:#4dabff'>{sym}</div>"
                    f"<div style='font-size:2rem;font-weight:900;color:{sc_color};margin:8px 0'>"
                    f"{sc}<span style='font-size:0.9rem'>/100</span></div>"
                    f"</div>"
                )

