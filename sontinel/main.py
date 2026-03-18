try:
    import streamlit as st
except ModuleNotFoundError:
    class DummyContainer:
        def __getattr__(self, name):
            def dummy(*args, **kwargs):
                if name == 'button': return False
                if name in ['columns', 'tabs']: return [DummyContainer() for _ in range(10)]
                if name == 'text_input': return kwargs.get('value', '') or (args[1] if len(args) > 1 else '')
                return DummyContainer()
            return dummy
    class DummyStreamlit(DummyContainer):
        def __init__(self):
            self.sidebar = DummyContainer()
    st = DummyStreamlit()

try:
    import MetaTrader5 as mt5
except ModuleNotFoundError:
    class DummyMT5:
        def __getattr__(self, name):
            if name == 'initialize': return lambda: True
            def dummy(*args, **kwargs): return None
            return dummy
    mt5 = DummyMT5()

try:
    import plotly.graph_objects as go
except ModuleNotFoundError:
    class DummyPlotly:
        def __getattr__(self, name):
            def dummy(*args, **kwargs): return DummyPlotly()
            return dummy
    go = DummyPlotly()

import pandas as pd
from datetime import datetime

# --- ORCHESTRATEUR ICT (source unique — partagé avec le bot) ---
from core.orchestrator import ProOrchestrator, log_diag

# --- BOT INTERFACES ---
try:
    from interface.bot_settings import render_bot_settings
    from interface.bot_monitor   import render_bot_monitor
    BOT_UI_AVAILABLE = True
except ImportError:
    BOT_UI_AVAILABLE = False

# log_diag est maintenant importé depuis core/orchestrator.py

# --- CONFIG ---
# Wrap top-level streamlit calls that may fail even with stubs if called during import
if __name__ == "__main__":
    st.set_page_config(page_title="ICT SENTINEL V9.3 - PRO", layout="wide")

# --- CSS GLASSMORPHISM PREMIUM ---
# On enveloppe le style dans une div avec une classe pour forcer le rendu HTML et 
# on cache cette div (display: none). Cela empêche Streamlit de l'interpréter
# comme du texte Markdown classique en cas d'erreur de parsing.
CSS_CODE = """
<div style="display: none;">
<meta name="google" content="notranslate">
<meta name="language" content="fr">
</div>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Outfit:wght@500;700;900&display=swap');

.stApp { 
    background: radial-gradient(circle at top right, #1a1f2c 0%, #0d1117 100%);
    color: #d1d4dc; 
    font-family: 'Inter', sans-serif; 
}

.hero-container {
    padding: 60px 20px;
    text-align: center;
    background: transparent;
}

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
    color: #00ff88; 
    margin: 0 0 12px 0; 
    font-weight: 800; 
    font-family: 'Outfit', sans-serif;
    letter-spacing: 0.5px;
}
.feature-card p {
    color: #cbd5e0 !important;
    font-size: 0.95rem;
    line-height: 1.6;
}

.metric-box {
    background: rgba(45, 55, 72, 0.7); 
    padding: 18px; 
    border-radius: 12px; 
    border: 1px solid rgba(255, 255, 255, 0.1); 
    text-align: center; color: #fff;
    backdrop-filter: blur(8px);
}
.metric-box b { color: #4dabff; font-size: 1.1rem; }

.narrative-card {
    background: rgba(30, 39, 58, 0.8); 
    padding: 28px; 
    border-radius: 16px;
    border: 1px solid rgba(41,98,255,0.25); 
}

.stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: transparent; }
.stTabs [data-baseweb="tab"] { 
    background-color: rgba(30, 34, 45, 0.5); 
    border-radius: 8px; 
    color: #848e9c; 
    padding: 10px 20px; 
    border: 1px solid transparent;
    transition: all 0.2s ease;
}
.stTabs [data-baseweb="tab"]:hover { border-color: rgba(41,98,255,0.5); color: #fff; }
.stTabs [aria-selected="true"] { 
    background: linear-gradient(135deg, #2962ff 0%, #1c44b3 100%) !important; 
    color: white !important; 
    box-shadow: 0 4px 12px rgba(41,98,255,0.3);
}

[data-testid="stSidebar"] {
    background-color: #06090e;
    border-right: 1px solid rgba(255,255,255,0.05);
}

[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span,
label p,
label span,
.stCheckbox p,
.stRadio p,
.stSlider p,
.stNumberInput p,
.stMultiSelect p,
.stToggle p,
div[role="radiogroup"] p,
div[data-baseweb="checkbox"] p {
    color: #eab308 !important;
    font-weight: 500 !important;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span {
    color: #d1d4dc;
}

[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p {
    color: #eab308 !important;
}
button[disabled] p,
button[disabled] div[data-testid="stMarkdownContainer"] p {
    color: #848e9c !important;
}

code { color: #00ff88 !important; background-color: rgba(0,255,136,0.1) !important; padding: 2px 7px !important; border-radius: 4px !important; }
hr { border-color: rgba(255,255,255,0.1); }

.gate-card {
    background: linear-gradient(135deg, rgba(255, 75, 43, 0.15) 0%, rgba(255, 177, 43, 0.1) 100%) !important;
    padding: 24px; border-radius: 16px;
    box-shadow: 0 8px 32px rgba(255,75,43,0.15);
    margin-bottom: 20px;
    color: #fff !important;
    border: 1px solid rgba(255, 75, 43, 0.5) !important;
    backdrop-filter: blur(12px);
}
.gate-card h4 { font-family: 'Outfit', sans-serif; font-weight: 800; color: #ffb12b !important; border-bottom: 1px solid rgba(255,75,43,0.3) !important; padding-bottom: 10px; }
.gate-card b, .gate-card span { color: #fff !important; }
.gate-card p { color: #d1d4dc !important; }

.stButton button, [data-testid="baseButton-primary"], [data-testid="baseButton-secondary"] {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.stButton button:hover, [data-testid="baseButton-primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(41,98,255,0.3) !important;
    filter: brightness(1.15);
}

.element-container:has(.btn-fermer-wrapper) + .element-container button,
[data-testid="stElementContainer"]:has(.btn-fermer-wrapper) + [data-testid="stElementContainer"] button,
[data-testid="element-container"]:has(.btn-fermer-wrapper) + [data-testid="element-container"] button {
    background-color: #ff4b4b !important;
    color: white !important;
    border: none !important;
}

.element-container:has(.btn-retour-wrapper) + .element-container button,
[data-testid="stElementContainer"]:has(.btn-retour-wrapper) + [data-testid="stElementContainer"] button,
[data-testid="element-container"]:has(.btn-retour-wrapper) + [data-testid="element-container"] button {
    background-color: #0066ff !important;
    color: white !important;
    border: none !important;
}

.metric-yellow {
    color: #ffff00 !important;
    font-size: 2rem;
    font-weight: 800;
}
</style>
"""

if __name__ == "__main__":
    st.html(CSS_CODE)

# ProOrchestrator est maintenant dans core/orchestrator.py
# L'import est fait en haut de ce fichier : from core.orchestrator import ProOrchestrator




if __name__ == "__main__":
    # --- BOOTSTRAP MT5 ---
    if not mt5.initialize():
        st.error(f"INITIALISATION MT5 IMPOSSIBLE: {mt5.last_error()}")
        st.stop()

    log_diag(f"MT5 OK - Session: {datetime.now().strftime('%H:%M')}")
    

    # ===========================================================
    # MAPPING PAIRES → SYMBOLES MT5 EXNESS (Standard 'm')
    # Source : interrogation MT5 Exness (08/03/2026)
    # ===========================================================
    PAIRS_CONFIG = {
        # ── FOREX MAJEURS ─────────────────────────────────────────
        "💶 EUR/USD":    "EURUSDm",
        "💷 GBP/USD":    "GBPUSDm",
        "🇯🇵 USD/JPY":   "USDJPYm",
        "🇨🇭 USD/CHF":   "USDCHFm",
        "🇨🇦 USD/CAD":   "USDCADm",
        "🇦🇺 AUD/USD":   "AUDUSDm",
        "🇳🇿 NZD/USD":   "NZDUSDm",
        # ── FOREX CROIX ───────────────────────────────────────────
        "🇬🇧 GBP/JPY":   "GBPJPYm",
        "🇪🇺 EUR/JPY":   "EURJPYm",
        "🇪🇺 EUR/GBP":   "EURGBPm",
        # ── INDICES US (ICT PRINCIPAUX) ───────────────────────────
        "📈 US100 (NQ)": "USTECm",    # Nasdaq 100 — Exness = USTECm
        "📊 US500 (ES)": "US500m",    # S&P 500
        "🇺🇸 US30 (YM)":  "US30m",    # Dow Jones
        # ── INDICES MONDIAUX ──────────────────────────────────────
        "🇩🇪 DE30":      "DE30m",     # DAX Allemagne
        "🇬🇧 UK100":     "UK100m",    # FTSE 100
        "🇯🇵 JP225":     "JP225m",    # Nikkei 225
        "🇪🇺 STOXX50":   "STOXX50m",  # Euro Stoxx 50
        # ── MÉTAUX PRÉCIEUX ───────────────────────────────────────
        "🥇 XAU/USD":    "XAUUSDm",   # Or (~2900$)
        "🥈 XAG/USD":    "XAGUSDm",   # Argent
        # ── ÉNERGIE ───────────────────────────────────────────────
        "🛢️ WTI Oil":    "USOILm",    # Pétrole WTI
        "🛢️ Brent Oil":  "UKOILm",    # Pétrole Brent
        # ── CRYPTO ────────────────────────────────────────────────
        "₿ BTC/USD":     "BTCUSDm",   # Bitcoin (~67 000$)
        "🔷 ETH/USD":    "ETHUSDm",   # Ethereum
        # ── INDICE DOLLAR ─────────────────────────────────────────
        "💵 DXY":        "DXYm",      # US Dollar Index
    }

    # ===========================================================
    # SESSION STATE — INITIALISATION
    # ===========================================================
    if "pair_cache"      not in st.session_state: st.session_state["pair_cache"]      = None
    if "active_pairs"    not in st.session_state: st.session_state["active_pairs"]    = []
    if "last_analysis"   not in st.session_state: st.session_state["last_analysis"]   = None
    if "scores_summary"  not in st.session_state: st.session_state["scores_summary"]  = {}
    # --- BOT STATE ---
    if "bot_is_running"  not in st.session_state: st.session_state["bot_is_running"]  = False
    if "bot_config"      not in st.session_state: st.session_state["bot_config"]      = {}
    if "bot_page"        not in st.session_state: st.session_state["bot_page"]        = "analyse"

    # ===========================================================
    # SIDEBAR — NAVIGATION + SÉLECTION
    # ===========================================================
    st.sidebar.title("💎 SENTINEL V9.3-PRO")

    # --- NAVIGATION PRINCIPALE ---
    page = st.sidebar.radio(
        "Navigation",
        options=["analyse", "bot_settings", "bot_monitor"],
        format_func=lambda x: {
            "analyse":     "🔬 Analyse ICT",
            "bot_settings":"⚙️ Paramètres Bot",
            "bot_monitor": "📡 Monitoring Bot",
        }.get(x, x),
        index=["analyse", "bot_settings", "bot_monitor"].index(
            st.session_state.get("bot_page", "analyse")
        ),
        key="nav_page"
    )
    st.session_state["bot_page"] = page

    # Statut Bot dans la sidebar - Lecture depuis bot_settings (process check)
    from interface.bot_settings import is_bot_running
    bot_running = is_bot_running()    
    st.session_state["bot_is_running"] = bot_running

    if bot_running:
        st.sidebar.success("🟢 BOT ACTIF")
    else:
        st.sidebar.info("⚫ Bot arrêté")

    # Séparer la navigation ICT du reste de la sidebar
    if page != "analyse":
        st.sidebar.markdown("---")
        if page == "bot_settings" and BOT_UI_AVAILABLE:
            render_bot_settings()
            st.stop()
        elif page == "bot_monitor" and BOT_UI_AVAILABLE:
            render_bot_monitor(
                journal=None,
                scheduler=None,
                latest_signals=None,
                order_manager=None,
                bot_active=bot_running
            )
            st.stop()
        elif not BOT_UI_AVAILABLE:
            st.error("Les modules interface/bot_settings.py et interface/bot_monitor.py sont introuvables.")
            st.stop()

    # --- Boutons navigation Analyse ---
    st.sidebar.markdown("---")
    has_results = st.session_state["pair_cache"] is not None
    nav1, nav2 = st.sidebar.columns(2)
    with nav1:
        st.markdown("<div class=\"btn-retour-wrapper\"></div>", unsafe_allow_html=True)
    retour = nav1.button("🏠 Accueil",    use_container_width=True, disabled=not has_results)
    refresh = nav2.button("🔄 Refresh", use_container_width=True, disabled=not has_results)

    if retour:
        st.session_state["pair_cache"]     = None
        st.session_state["active_pairs"]   = []
        st.session_state["scores_summary"] = {}
        st.session_state["last_analysis"]  = None
        st.rerun()
    st.sidebar.markdown(f"<small style='color:#848e9c;'>🟢 MT5 connecté</small>", unsafe_allow_html=True)

    st.sidebar.markdown("---")
    lancer = st.sidebar.button("🔬 LANCER L'ANALYSE", use_container_width=True, type="primary")
    # Texte d'aide sous le bouton
    last_ok = st.session_state.get("last_analysis", None)
    if last_ok:
        st.sidebar.markdown(
            f"<small style='color:#848e9c;'>"  
            f"🟢 Dermière analyse : <b>{last_ok}</b><br>"
            f"Recliquez pour mettre à jour.</small>",
            unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown(
            "<small style='color:#848e9c;'>"
            "ℹ️ <b>Ce bouton</b> lance l'analyse ICT multi-timeframe "
            "(FVG, OB, Liquidité, Score) sur les paires cochées ci-dessus.</small>",
            unsafe_allow_html=True
        )
    
    # --- M7 FIX : GESTION ROBUSTE DES PARAMÈTRES DE NAVIGATION ---
    if "nav_state" not in st.session_state:
        st.session_state["nav_state"] = {"symbol": None, "tf": None, "consumed": False}

    qp = st.query_params
    if "symbol" in qp and not st.session_state["nav_state"]["consumed"]:
        q_sym = qp["symbol"]
        q_tf  = qp.get("tf", None)

        # CORRECTION BUG « Détails » — Décocher TOUTES les paires d'abord
        # (sans ça, XAUUSD reste cochée par défaut même quand on navigue vers BTC)
        for lbl in PAIRS_CONFIG:
            st.session_state[f"pair_{lbl}"] = False

        # Puis cocher uniquement la paire cible
        reverse_map = {v: k for k, v in PAIRS_CONFIG.items()}
        sym_label = reverse_map.get(q_sym, None)
        if sym_label:
            st.session_state[f"pair_{sym_label}"] = True

        # Stocker pour le rendu (symbol + tf à afficher en premier)
        st.session_state["nav_state"] = {"symbol": q_sym, "tf": q_tf, "consumed": True}

        # Vider les query params pour éviter les reruns en boucle
        for key in list(st.query_params.keys()):
            del st.query_params[key]
        st.rerun()  # Un seul rerun propre

    st.sidebar.markdown("")
    selected_pairs = []
    has_crypto = False  # BUG FIX : initialiser avant la boucle
    for label, symbol in PAIRS_CONFIG.items():
        # Par défaut : Tout est décoché SAUF si l'utilisateur l'a déjà coché précédemment ou si on y accède via la navigation (Details)
        has_explicit_state = f"pair_{label}" in st.session_state
        default_val = False if not has_explicit_state else st.session_state[f"pair_{label}"]

        if st.sidebar.checkbox(label, value=default_val, key=f"pair_{label}"):
            selected_pairs.append((label, symbol))
            # Détection crypto : noms Exness
            if any(x in symbol.upper() for x in ["BTC", "ETH", "XRP", "SOL", "BNB"]):
                has_crypto = True

    if has_crypto:
        st.sidebar.warning("⚠️ Prudence : les concepts ICT temporel (Killzones, Macros) perdent en fiabilité sur les Cryptos (24/7).")

    col_sa, col_sc = st.sidebar.columns(2)
    if col_sa.button("☑️ Tout",  use_container_width=True):
        for k in PAIRS_CONFIG: st.session_state[f"pair_{k}"] = True
    if col_sc.button("⬜ Aucun", use_container_width=True):
        for k in PAIRS_CONFIG: st.session_state[f"pair_{k}"] = False


 





   

 


    # Définition du drapeau de chargement
    # do_load est vrai si click sur Lancer/Refresh OU si on vient de consommer une navigation
    do_load = lancer or refresh or (st.session_state["nav_state"]["consumed"] and st.session_state["nav_state"]["symbol"] is not None)
    
    # Reset du flag de navigation consommée après détection de do_load pour ne pas boucler
    if st.session_state["nav_state"]["consumed"]:
        # On garde les valeurs symbol/tf mais on marque à False pour que do_load = False au rerun suivant
        st.session_state["nav_state"]["consumed"] = False

    # --- Résumé dernière analyse + Scores visuels ---
    if st.session_state["scores_summary"]:
        st.sidebar.markdown("---")
        st.sidebar.markdown("<small style='color:#848e9c;font-weight:600;letter-spacing:1px;'>SCORES ICT</small>", unsafe_allow_html=True)
        for sym, sc in st.session_state["scores_summary"].items():
            if sc >= 80:
                bar_color = "#00c864"; verdict_txt = "🚀 EXEC A+"
            elif sc >= 65:
                bar_color = "#f0b429"; verdict_txt = "🔍 WATCH"
            else:
                bar_color = "#ef5350"; verdict_txt = "❌ INTERDIT"
            bar_w = max(sc, 3)
            st.sidebar.markdown(
                f"<div style='margin:6px 0;'>"
                f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:2px;'>"
                f"<b style='color:#d1d4dc;'>{sym}</b>"
                f"<span style='color:{bar_color};font-weight:700;'>{sc}/100</span>"
                f"</div>"
                f"<div style='background:rgba(42,46,57,0.8);border-radius:4px;height:6px;'>"
                f"<div style='width:{bar_w}%;background:{bar_color};border-radius:4px;height:6px;'></div>"
                f"</div>"
                f"<div style='font-size:0.72rem;color:{bar_color};margin-top:2px;'>{verdict_txt}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    # ===========================================================
    # FONCTION INTERNE — RENDU D'UN ONGLET TF (données pré-chargées)
    # ===========================================================
    def _render_tf_tab(orch, symbol, tf, tf_data, gbias, clock, bias_color):
        """Rendu instantané d'un onglet TF depuis données déjà calculées."""
        if tf_data is None:
            st.warning(f"Données {tf} indisponibles pour {symbol}.")
            return
        df, smc, liq, exe, mmxm, smt_result = tf_data
        if smc is None:
            st.warning(f"Analyse SMC insuffisante pour {symbol} {tf}.")
            return

        try:
            # --- 3-COLUMN BODY ---
            col_left, col_mid, col_right = st.columns([1, 2.8, 1], gap="medium")

            with col_left:
                md, score, verdict = orch.chk_ac.generate(tf, smc, liq, gbias, exe, mmxm, clock)
                st.html(
                    f"<div style='text-align: center; padding: 10px; background: rgba(255, 255, 0, 0.1); border-radius: 12px; border: 1px solid rgba(255, 255, 0, 0.3); margin-bottom: 15px;'>"
                    f"<small style='color: #848e9c;'>SCORE SENTINELLE</small>"
                    f"<div style='color: #ffff00; font-size: 2.5rem; font-weight: 900;'>{score}/100</div>"
                    f"<div style='color: {bias_color}; font-size: 0.9rem;'>{verdict}</div>"
                    f"</div>"
                )
                st.html(f"<div class='report-card'>{md}</div>")

            with col_mid:
                fig = orch.build_chart_pro(df, smc, liq, exe, mmxm, tf, clock=clock, smt_result=smt_result)
                st.plotly_chart(fig, use_container_width=True, config={
                    'displayModeBar': True,
                    'scrollZoom': True,
                    'editable': True,
                    'modeBarButtonsToAdd': ['drawline', 'drawrect', 'eraseshape'],
                    'displaylogo': False,
                }, key=f"plotly_chart_{symbol}_{tf}")
                narrative_html = orch.chk_ac._generate_ia_narrative(tf, score, verdict, gbias, mmxm, smc=smc, liq=liq, exe=exe, clock=clock)
                st.html(
                    f"<div class='narrative-card'>"
                    f"<h3 style='color:#2962ff; margin-top:0;'>🗣️ NARRATIF IA &nbsp; <span style='font-size:0.8rem; color:#848e9c; font-weight:400;'>{symbol} · {tf}</span></h3>"
                    f"{narrative_html}"
                    f"</div>"
                )

            with col_right:
                # 1. CONTEXTE HTF
                st.html(
                    f"<div class='report-card'>"
                    f"<h4>🌐 CONTEXTE HTF</h4>"
                    f"<p>Bias: <code style='color:{bias_color}'>{gbias['htf_bias']}</code></p>"
                    f"<p style='font-size:0.85rem;'>DOL: {gbias['draw_on_liquidity']['name']}<br>Dist: {gbias['draw_on_liquidity']['dist']:.4f}</p>"
                    f"</div>"
                )

                # 2. BOOLEAN SWEEP ERL
                sweep = smc.get('boolean_sweep_erl', {})
                sweep_val = sweep.get('value', False)
                sweep_icon = '✅' if sweep_val else '🔴'
                
                # Correction HTML: On s'assure que le bloc est bien fermé et sans tags orphelins
                sweep_details = ""
                if sweep.get('bullish_sweep'): sweep_details += "✅ Balayage BULL<br>"
                if sweep.get('bearish_sweep'): sweep_details += "✅ Balayage BEAR<br>"
                
                no_sweep_warning = ""
                if not sweep_val:
                    no_sweep_warning = f"<p style='color:#d32f2f !important; font-size:0.85rem; background:rgba(255,255,255,0.2); padding:5px; border-radius:5px;'>⚠️ SANS SWEEP ERL: MSS non valide</p>"

                st.html(
                    f"<div class='gate-card'>"
                    f"<h4>🛡️ BALAYAGE ERL (Portail)</h4>"
                    f"<p style='font-size:1.1rem; font-weight:bold;'>{sweep_icon} {'BALAYAGE CONFIRMÉ' if sweep_val else 'PAS DE BALAYAGE'}</p>"
                    f"<p style='font-size:0.85rem;'>PDH: <span class='val-box'>{sweep.get('pdh',0):.5f}</span><br>PDL: <span class='val-box'>{sweep.get('pdl',0):.5f}</span></p>"
                    f"<div style='font-size:0.85rem; margin-bottom:10px;'>{sweep_details}</div>"
                    f"{no_sweep_warning}"
                    f"</div>"
                )

                # 3. SMT DIVERGENCE
                if smt_result:
                    smt_color = '#ef5350' if smt_result.get('smt_divergence') else '#848e9c'
                    smt_trade_html = f"<p style='color:#f0b429; font-size:0.8rem;'>🎯 {smt_result.get('trade_direction','')} : {smt_result.get('stronger_pair','')}</p>" if smt_result.get('smt_divergence') else ""
                    st.html(
                        f"<div class='report-card'>"
                        f"<h4>🔗 SMT DIVERGENCE</h4>"
                        f"<p style='color:{smt_color}; font-weight:bold;'>{'⚡ ' + smt_result.get('smt_type','NONE') if smt_result.get('smt_divergence') else '⚪ Smooth Correlation'}</p>"
                        f"<p style='font-size:0.8rem;'>vs {smt_result.get('correlated_with','N/A')}</p>"
                        f"{smt_trade_html}"
                        f"</div>"
                    )

                # 4. CBDR
                cbdr = liq.get('cbdr', {})
                if cbdr and cbdr.get('cbdr_high', 0) > 0:
                    cbdr_color = '#f0b429' if cbdr.get('cbdr_explosive') else '#848e9c'
                    st.html(
                        f"<div class='report-card'>"
                        f"<h4>📊 CBDR</h4>"
                        f"<p style='font-size:0.8rem;'>H: <code>{cbdr.get('cbdr_high',0):.5f}</code><br>L: <code>{cbdr.get('cbdr_low',0):.5f}</code><br>Range: <b>{cbdr.get('cbdr_range_pips',0):.1f} pips</b></p>"
                        f"<p style='color:{cbdr_color}; font-size:0.9rem;'>{'💥 EXPLOSIVE — Mouvement fort demain' if cbdr.get('cbdr_explosive') else '⚪ Normal'}</p>"
                        f"</div>"
                    )

                # 5. LIQUIDITÉ
                prox = liq['proximal_liquidity']
                eqh_smooth = any(e['quality'] == 'SMOOTH' for e in liq['eqh'])
                eql_smooth = any(e['quality'] == 'SMOOTH' for e in liq['eql'])
                
                high_color = '#f0b429' if liq['erl'].get('high_status') == 'SWEPT' else '#ef5350'
                low_color = '#f0b429' if liq['erl'].get('low_status') == 'SWEPT' else '#26a69a'
                eqh_txt = "🔴 EQH Smooth ⭐" if eqh_smooth else "⚪ Pas d'EQH"
                eql_txt = "🟢 EQL Smooth ⭐" if eql_smooth else "⚪ Pas d'EQL"

                st.html(
                    f"<div class='report-card'>"
                    f"<h4>🧲 LIQUIDITÉ</h4>"
                    f"<p>BSL: <code style='color:#ef5350'>{liq['erl']['high']:.5f}</code> <span style='font-size:0.75rem; color:{high_color}'>[{liq['erl'].get('high_status','?')}]</span></p>"
                    f"<p>SSL: <code style='color:#26a69a'>{liq['erl']['low']:.5f}</code> <span style='font-size:0.75rem; color:{low_color}'>[{liq['erl'].get('low_status','?')}]</span></p>"
                    f"<p>Proximal: <code>{prox:.5f}</code></p>"
                    f"<div style='font-size:0.8rem; margin-top:6px;'>"
                    f"{eqh_txt}<br>"
                    f"{eql_txt}"
                    f"</div>"
                    f"</div>"
                )

                # 6. PD ARRAYS
                pd_html = "<div class='report-card'><h4>⚡ PD ARRAYS</h4>"
                for pd_item in exe['pd_hierarchy'][:5]:
                    c = "#00ff88" if "BULL" in pd_item['type'] or "BISI" in pd_item['type'] else "#ef5350"
                    inst_tag = " 🏛️" if pd_item.get('institutional') else ""
                    pd_html += f"<p style='font-size:0.8rem; margin:3px 0;'>{pd_item['type']}{inst_tag} @ <b style='color:{c}'>{pd_item['price']:.5f}</b></p>"
                pd_html += "</div>"
                st.html(pd_html)

                # No-Trade vendredi 14h+
                if clock.get('friday_no_trade'):
                    st.error("🚫 VENDREDI 14h+ NYC — NO NEW TRADES (Bible §12 Step 0)")

            st.html("<div style='margin-bottom: 40px;'></div>")

        except Exception as tab_err:
            log_diag(f"TAB ERROR {symbol} {tf}: {tab_err}")
            st.warning(f"Erreur lors du rendu {symbol} {tf}: {tab_err}")




    # ===========================================================
    # LANCEMENT / REFRESH / RENDU
    # ===========================================================
    # ===========================================================
    # PHASE DE CHARGEMENT (Fetch + Analyse)
    # ===========================================================
    if do_load:
        log_diag(f"Lancement lecture cache multi-paires: {[s for _,s in selected_pairs]}")

        ALL_TFS = ["MN", "W1", "D1", "H4", "H1", "M15", "M5"]
        n_pairs = len(selected_pairs)
        total_steps = n_pairs if n_pairs > 0 else 1

        temp_cache = {}
        temp_scores = {}

        from core.market_state_cache import MarketStateCache
        m_cache = MarketStateCache()

        with st.spinner("⏳ Récupération de l'analyse du Bot depuis le Casier..."):
            prog_bar  = st.progress(0, text="Lecture du cache en cours...")
            step = 0

            for p_idx, (label, symbol) in enumerate(selected_pairs):
                try:
                    # Instancier juste pour l'accès aux méthodes statiques ou pure render functions
                    orch = ProOrchestrator(symbol)

                    gbias = m_cache.get_global_bias(symbol)
                    if not gbias:
                        # AUDIT #25 FIX : réutiliser l'instance 'orch' déjà créée (pas de double instanciation)
                        # C2 FIX : Si le cache est vide (bot arrêté), lancer l'analyse directement depuis MT5
                        try:
                            d1_df  = orch._fetch_pro("D1")
                            w1_df  = orch._fetch_pro("W1")
                            mn_df  = orch._fetch_pro("MN")
                            if d1_df is not None:
                                gbias = orch.bias_ac.analyze(d1_df, w1_df, mn_df)
                                m_cache.update_global_bias(symbol, gbias)
                        except Exception:
                            pass
                    if not gbias:
                        temp_cache[symbol] = {'error': f'Biais Global non disponible pour {symbol}. Relancez une analyse ou démarrez le bot.'}
                        step += 1
                        prog_bar.progress(min(step / total_steps, 1.0))
                        continue
                    
                    max_score_pair = 0
                    tf_results = {}
                    clock = None
                    
                    for tf in ALL_TFS:
                        data = m_cache.get_symbol_tf(symbol, tf)
                        if data is not None:
                            # Reconstruire le tuple exactement comme avant
                            df = data.get("df")
                            smc = data.get("smc")
                            liq = data.get("liq")
                            exe = data.get("exe", {})
                            if exe is None: exe = {}
                            # Injection des positions actives globales dans l'objet execution par timeframe
                            symbol_positions = m_cache.state.get(symbol, {}).get("positions", [])
                            exe['active_positions'] = symbol_positions
                                
                            mmxm = data.get("mmxm")
                            smt_res = data.get("smt_result")
                            tf_results[tf] = (df, smc, liq, exe, mmxm, smt_res)
                            
                            if clock is None and data.get("clock"):
                                clock = data.get("clock")
                                
                            if tf == "M15":
                                max_score_pair = data.get("checklist", {}).get("score", 0)
                        else:
                            tf_results[tf] = None

                    if clock is None:
                         clock = orch.time_ac.get_audit() # Fallback

                    temp_cache[symbol] = {
                        'orch': orch, 'gbias': gbias, 'clock': clock,
                        'tfs': tf_results, 'label': label
                    }
                    temp_scores[symbol] = max_score_pair
                except Exception as e:
                    temp_cache[symbol] = {'error': f"Erreur de lecture du cache : {str(e)}"}
                
                step += 1
                prog_bar.progress(min(step / total_steps, 1.0))

            prog_bar.progress(1.0, text="✅ Lecture du cache terminée !")

        # I4 FIX : Le score résumé est maintenant le MEILLEUR score parmi tous les TFs
        for symbol, max_score_pair in temp_scores.items():
            if symbol in temp_cache and 'error' not in temp_cache[symbol]:
                best_tf_score = 0
                tfs_results = temp_cache[symbol].get('tfs', {})
                for tf_key, tf_val in tfs_results.items():
                    if tf_val is not None:
                        _, smc_v, liq_v, exe_v, mmxm_v, _ = tf_val
                        if all([smc_v, liq_v, exe_v, mmxm_v]):
                            try:
                                orch_v = temp_cache[symbol].get('orch')
                                gbias_v = temp_cache[symbol].get('gbias')
                                clock_v = temp_cache[symbol].get('clock')
                                if orch_v and gbias_v and clock_v:
                                    _, s, _ = orch_v.chk_ac.generate(tf_key, smc_v, liq_v, gbias_v, exe_v, mmxm_v, clock_v)
                                    if s > best_tf_score:
                                        best_tf_score = s
                            except Exception:
                                pass
                if best_tf_score > 0:
                    temp_scores[symbol] = best_tf_score

        # Update Session State
        st.session_state["pair_cache"]      = temp_cache
        st.session_state["active_pairs"]    = [s for _, s in selected_pairs]
        st.session_state["scores_summary"]  = temp_scores
        st.session_state["last_analysis"]   = datetime.now().strftime("%H:%M:%S")
        st.rerun() # Refresh with new data

    # ===========================================================
    # PHASE DE RENDU (Depuis cache)
    # ===========================================================

    def _render_pa_tab(sym: str, tf: str):
        """
        Rendu de l'analyse Price Action pour le symbole et le timeframe sélectionnés.
        Appelle PAOrchestrator de manière indépendante — aucun lien avec l'ICT.
        """
        from agents.pa_orchestrator import PAOrchestrator
        from interface.bot_settings  import load_config

        cfg = load_config()
        score_exec  = cfg.get("score_execute", 80)
        score_limit = cfg.get("score_limit", 65)

        with st.spinner("📊 Analyse Price Action en cours…"):
            pa_orch  = PAOrchestrator(sym)
            result   = pa_orch.analyze(tf, score_execute=score_exec, score_limit=score_limit)

        if not result.get("ok"):
            st.warning(f"⏳ {result.get('narratif', 'Données MT5 indisponibles — Vérifier la connexion.')}")
            return

        score     = result["score"]
        verdict   = result["verdict"]
        direction = result.get("direction", "NEUTRE")
        levels    = result.get("levels", {})
        narratif  = result.get("narratif", "")
        features  = result.get("features", {})

        sc_color  = "#00ff88" if score >= score_exec else ("#f0b429" if score >= score_limit else "#ef5350")
        dir_color = "#00ff88" if direction == "BUY" else ("#ef5350" if direction == "SELL" else "#848e9c")
        dir_icon  = "🟢 ACHAT" if direction == "BUY" else ("🔴 VENTE" if direction == "SELL" else "⬜ NEUTRE")

        # ══════════ BANDE SUPÉRIEURE : INDICATEURS CLÉS ══════════════
        cycle_type = features.get("cycle", {}).get("type", "?")
        ema_touch  = features.get("ema_position", {}).get("ema_touch_last3", False)
        b_setup    = features.get("bar_count", {}).get("bullish_setup") or ""
        s_setup    = features.get("bar_count", {}).get("bearish_setup") or ""
        setup_lbl  = b_setup or s_setup or "Aucun"
        mc_danger  = features.get("microchannel", {}).get("danger", False)
        pts_list   = features.get("patterns", {}).get("detected", [])
        mm         = features.get("measured_move", {})

        # Couleur du cycle
        cyc_color  = "#f0b429" if "CANAL" in cycle_type else ("#00ff88" if "BREAKOUT" in cycle_type else ("#ef5350" if "TIGHT" in cycle_type else "#848e9c"))

        # ── Ligne 1 : Score | Direction | Cycle ──────────────────────
        m1, m2, m3 = st.columns(3)
        m1.html(
            f"<div class='metric-box' style='border-color:{sc_color}33; text-align:center;'>"
            f"<div style='font-size:0.7rem; color:#848e9c; text-transform:uppercase; letter-spacing:1px;'>Score PA</div>"
            f"<div style='font-size:2.4rem; font-weight:900; color:{sc_color}; line-height:1.1;'>{score}<span style='font-size:1rem'>/100</span></div>"
            f"<div style='font-size:0.75rem; color:{sc_color}; margin-top:4px; font-weight:700;'>{verdict}</div>"
            f"</div>"
        )
        m2.html(
            f"<div class='metric-box' style='border-color:{dir_color}33; text-align:center;'>"
            f"<div style='font-size:0.7rem; color:#848e9c; text-transform:uppercase; letter-spacing:1px;'>Direction PA</div>"
            f"<div style='font-size:1.6rem; font-weight:900; color:{dir_color}; margin:6px 0;'>{dir_icon}</div>"
            f"<div style='font-size:0.72rem; color:#848e9c;'>Setup : <b style='color:#d4d4d4'>{setup_lbl}</b></div>"
            f"</div>"
        )
        m3.html(
            f"<div class='metric-box' style='text-align:center;'>"
            f"<div style='font-size:0.7rem; color:#848e9c; text-transform:uppercase; letter-spacing:1px;'>Cycle</div>"
            f"<div style='font-size:1.1rem; font-weight:700; color:{cyc_color}; margin:6px 0;'>{cycle_type.replace('_',' ')}</div>"
            f"<div style='font-size:0.72rem; color:#848e9c;'>EMA Touche : <b style='color:#d4d4d4'>{'✅ OUI' if ema_touch else '❌ NON'}</b></div>"
            f"</div>"
        )
        st.html("<br>")

        # ── Ligne 2 : Niveaux SL / TP1 / TP2 ────────────────────────
        sl, tp1, tp2 = levels.get("sl","—"), levels.get("tp1","—"), levels.get("tp2","—")
        st.html(
            f"<div style='display:flex; gap:12px; margin-bottom:14px;'>"
            f"<div style='flex:1; background:#1a1a2e; border:1px solid #ef535044; border-radius:10px; padding:12px; text-align:center;'>"
            f"<div style='font-size:0.65rem; color:#ef5350; text-transform:uppercase; letter-spacing:1px;'>🛑 Stop Loss</div>"
            f"<div style='font-size:1.1rem; font-weight:700; color:#ef5350; margin-top:4px;'>{sl}</div>"
            f"</div>"
            f"<div style='flex:1; background:#1a2e1a; border:1px solid #00ff8844; border-radius:10px; padding:12px; text-align:center;'>"
            f"<div style='font-size:0.65rem; color:#00ff88; text-transform:uppercase; letter-spacing:1px;'>🎯 Take Profit 1</div>"
            f"<div style='font-size:1.1rem; font-weight:700; color:#00ff88; margin-top:4px;'>{tp1}</div>"
            f"</div>"
            f"<div style='flex:1; background:#1a2e1a; border:1px solid #00ff8844; border-radius:10px; padding:12px; text-align:center;'>"
            f"<div style='font-size:0.65rem; color:#00e673; text-transform:uppercase; letter-spacing:1px;'>🏆 Take Profit 2 (MM)</div>"
            f"<div style='font-size:1.1rem; font-weight:700; color:#00e673; margin-top:4px;'>{tp2}</div>"
            f"</div>"
            f"</div>"
        )

        # ── Blocages actifs ───────────────────────────────────────────
        if mc_danger:
            st.html("<div style='background:#ef535020; border:1px solid #ef5350; border-radius:8px; padding:10px 14px; font-size:0.82rem; color:#ef5350; margin-bottom:10px;'>⛔ <b>ALERTE MICRO-CANAL :</b> Ne pas acheter contre un micro-canal baissier actif.</div>")
        if "TIGHT" in cycle_type:
            st.html("<div style='background:#ef535020; border:1px solid #ef5350; border-radius:8px; padding:10px 14px; font-size:0.82rem; color:#ef5350; margin-bottom:10px;'>⛔ <b>TIGHT TRADING RANGE (Barb Wire) :</b> Zone interdite — Attendre le Breakout.</div>")

        # ══════════ GRAPHIQUE PRICE ACTION ANNOTÉ ════════════════════
        st.markdown("#### 📈 Graphique Price Action Annoté")
        try:
            fig_pa = pa_orch.build_pa_chart(tf, features, direction, levels)
            if fig_pa is not None:
                st.plotly_chart(fig_pa, use_container_width=True, config={
                    "displayModeBar": True,
                    "modeBarButtonsToRemove": ["autoScale2d", "lasso2d", "select2d"],
                    "scrollZoom": True,
                })
            else:
                st.info("📊 Graphique indisponible (données insuffisantes)")
        except Exception as _chart_err:
            st.warning(f"Erreur graphique PA : {_chart_err}")

        # ══════════ NARRATIF COMPLET ══════════════════════════════════
        if narratif:
            st.markdown("#### 📝 Narratif Price Action")
            st.html(
                f"<div style='background:rgba(212,160,23,0.07); border:1px solid #d4a01730; border-left:4px solid #d4a017; "
                f"border-radius:8px; padding:16px 20px; font-size:0.88rem; color:#d4d4d4; line-height:1.7;'>"
                f"{narratif}</div>"
            )
        st.html("<br>")

        # ══════════ CHECKLIST DÉTAILLÉE (Bible PA) ════════════════════
        st.markdown("#### 📋 Checklist Price Action — Bible Complète")
        st.html(result.get("html", ""))

        # ══════════ MEASURED MOVE ═════════════════════════════════════
        if mm.get("valid"):
            leg1 = mm.get("leg1_size", "?")
            sh   = mm.get("last_sh", "?")
            sl_m = mm.get("last_sl", "?")
            mbt  = mm.get("mm_bull_target", "?")
            mbt2 = mm.get("mm_bear_target", "?")
            st.html("<br>")
            st.markdown("#### 🎯 Measured Move (Projection Mathématique)")
            st.html(
                f"<div style='background:#0e1117; border:1px solid #2a2e39; border-radius:10px; padding:14px 20px; font-size:0.82rem;'>"
                f"<b style='color:#d4a017'>Leg 1</b> : de <b>{sl_m}</b> à <b>{sh}</b> = <b style='color:#f0b429'>{leg1} pts</b><br>"
                f"<b style='color:#00ff88'>🎯 Cible Haussière (Leg 2) :</b> <b style='color:#00ff88'>{mbt}</b><br>"
                f"<b style='color:#ef5350'>📉 Cible Baissière (Leg 2) :</b> <b style='color:#ef5350'>{mbt2}</b>"
                f"</div>"
            )

        # ══════════ PATTERNS DÉTECTÉS ═════════════════════════════════
        if pts_list:
            st.html("<br>")
            st.markdown("#### 📐 Figures Chartistes Détectées")
            icons = {"DOUBLE_BOTTOM": "🅆", "DOUBLE_TOP": "🅂", "BULL_FLAG": "🚩", "SYMMETRIC_TRIANGLE": "△"}
            for p in pts_list:
                icon = icons.get(p, "📌")
                st.html(f"<div style='background:#1a2a1a; border:1px solid #00ff8830; border-radius:6px; padding:8px 14px; margin:4px 0; font-size:0.82rem; color:#00ff88;'>{icon} <b>{p.replace('_',' ')}</b></div>")

    # --- FONCTION DE RENDU STABLE ---
    def render_analysis_for_symbol(sym, pairs_data):
        """Rendu complet d'un symbole (En-tête, Radio TF, Grille)."""
        cache = pairs_data[sym]
        label = cache.get('label', sym)
        
        # --- En-tête de l'onglet et Bouton Fermer ---
        col_t, col_f, col_r = st.columns([8, 2, 2])
        with col_t:
            st.subheader(f"💎 {label}")
        with col_f:
            st.html('<div class="btn-fermer-wrapper"></div>')
            if st.button("❌ Fermer", key=f"close_{sym}", type="primary", help=f"Retirer {sym} de l'analyse actuelle", use_container_width=True):
                st.session_state["active_pairs"].remove(sym)
                if not st.session_state["active_pairs"]:
                    st.session_state["pair_cache"] = None
                st.rerun()
        with col_r:
            st.html('<div class="btn-retour-wrapper"></div>')
            if st.button("🏠 Retour", key=f"back_{sym}", help="Revenir à l'écran d'accueil", use_container_width=True):
                st.session_state["pair_cache"] = None
                st.session_state["active_pairs"] = []
                st.rerun()

        if 'error' in cache:
            st.error(f"⚠️ {cache['error']}")
            return

        gbias = cache['gbias']
        clock = cache['clock']
        orch  = cache['orch']
        tfs   = cache['tfs']
        bias_color = "#00ff88" if "BULL" in gbias['htf_bias'] else "#ef5350"

        # Header Paire
        m1, m2, m3 = st.columns(3)
        m1.html(f"<div class='metric-box'>🌍 BIAIS GLOBAL<br><b style='color:{bias_color}'>{gbias['htf_bias']}</b></div>")
        m2.html(f"<div class='metric-box'>🕒 SESSION NY<br><b>{clock['killzone']}</b></div>")
        m3.html(f"<div class='metric-box'>🎯 CIBLE DOL<br><b style='color:{bias_color}'>{gbias['draw_on_liquidity']['name']} @ {gbias['draw_on_liquidity']['price']:.2f}</b></div>")
        st.html("<br>")

        ALL_TFS = ["MN", "W1", "D1", "H4", "H1", "M15", "M5", "M1"]
        # Trouver l'index du TF demandé (via nav_state stable)
        default_idx = 0
        nav_info = st.session_state.get("nav_state", {})
        if nav_info.get("symbol") == sym and nav_info.get("tf") in ALL_TFS:
            default_idx = ALL_TFS.index(nav_info["tf"])

        # Utiliser un radio horizontal au lieu de tabs pour permettre le focus
        selected_tf = st.radio("Timeframe", ALL_TFS, index=default_idx, horizontal=True, key=f"tf_sel_{sym}")
        
        # ── Onglets ICT / Price Action ────────────────────────────────
        tab_ict, tab_pa = st.tabs(["🛡️ Analyse ICT", "📊 Analyse Price Action"])

        with tab_ict:
            _render_tf_tab(orch, sym, selected_tf, tfs.get(selected_tf), gbias, clock, bias_color)

        with tab_pa:
            _render_pa_tab(sym, selected_tf)

    # ===========================================================
    # BANDEAU TOP PAGE — TRADES EN COURS (Permanent)
    # ===========================================================
    @st.fragment(run_every=5)
    def _render_live_trades_banner():
        """Affiche les positions actives récupérées directement depuis MT5."""
        try:
            positions = mt5.positions_get()
            if not positions:
                return  # Rien à afficher s'il n'y a pas de trade

            # Récupération infos du profil actuel directement depuis le fichier
            from interface.bot_settings import load_config, PROFILE_LABELS, MODE_LABELS
            cfg = load_config()
            profile_key = cfg.get("profile", "DAY_TRADE")
            profile_lbl = PROFILE_LABELS.get(profile_key, "Inconnu")
            
            mode_key = cfg.get("op_mode", "PAPER")
            mode_lbl = MODE_LABELS.get(mode_key, "Paper Trading")
            
            # Badge de mode (Live / Simulation)
            mode_badge = "🟥 SIMULATION PAPER" if "PAPER" in mode_key else "🟩 ORDRES RÉELS"
            if "SEMI" in mode_key: mode_badge = "🟨 SEMI-AUTO (Confirmation)"
            if "Semi" in mode_lbl: mode_badge = "🟨 SEMI-AUTO (Confirmation)"

            st.markdown(f"### 📡 Trades en cours — <span style='font-size:0.7em; color:#4dabff;'>{profile_lbl}</span> <span style='font-size:0.6em; background:rgba(255,255,255,0.1); padding:2px 6px; border-radius:4px; margin-left:10px;'>{mode_badge}</span>", unsafe_allow_html=True)
            cols = st.columns(len(positions) if len(positions) <= 4 else 4)
            for i, pos in enumerate(positions):
                col = cols[i % 4]
                # Type: 0 = BUY, 1 = SELL
                dir_color = "#00c864" if pos.type == 0 else "#ef5350"
                dir_label = "BUY 📈" if pos.type == 0 else "SELL 📉"
                pnl_color = "#00c864" if pos.profit > 0 else "#ef5350"
                
                with col:
                    st.html(f"""
                    <div style="background: rgba(30, 34, 45, 0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <strong style="font-size: 1.1em; color: #fff;">{pos.symbol}</strong>
                            <span style="color: {dir_color}; font-weight: bold; font-size: 0.9em; background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px;">{dir_label} {pos.volume}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.85em; color: #848e9c; margin-bottom: 4px;">
                            <span>Entry: <span style="color: #fff;">{pos.price_open}</span></span>
                            <span>Now: <span style="color: #fff;">{pos.price_current}</span></span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.85em; color: #848e9c; margin-bottom: 8px;">
                            <span>SL: <span style="color: #ef5350;">{pos.sl if pos.sl > 0 else '-'}</span></span>
                            <span>TP: <span style="color: #00ff88;">{pos.tp if pos.tp > 0 else '-'}</span></span>
                        </div>
                        <div style="text-align: center; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px; font-weight: bold; font-size: 1.1em; color: {pnl_color};">
                            {pos.profit:.2f} $
                        </div>
                    </div>
                    """)
        except Exception as e:
            log_diag(f"Erreur bandeau trades: {e}")

    # On affiche le bandeau quoi qu'il arrive (écran accueil ou analyse)
    _render_live_trades_banner()

    if st.session_state.get("pair_cache"):
        pairs_data = st.session_state["pair_cache"]
        active_list = [p for p in st.session_state["active_pairs"] if p in pairs_data]

        if not active_list:
            st.session_state["pair_cache"] = None
            st.rerun()

        st.header(f"🔱 ICT SENTINEL PRO — {len(active_list)} PAIRE(S) ANALYSÉE(S)")

        # M7 FIX : TOUJOURS utiliser des TABS même pour 1 paire pour garder une hiérarchie DOM stable
        tab_labels = [pairs_data[s].get('label', s) for s in active_list]
        p_tabs = st.tabs(tab_labels)
        
        for idx, sym in enumerate(active_list):
            with p_tabs[idx]:
                render_analysis_for_symbol(sym, pairs_data)
        
        # Nettoyage des flags de navigation APRÈS le rendu (si encore présents dans session_state temporaire)
        if st.session_state["nav_state"]["symbol"] is not None:
            # On laisse le symbole pour garder l'info, mais on peut clear le TF demandé si on veut
            # st.session_state["nav_state"]["tf"] = None 
            pass
    else:
        # --- ÉCRAN D'ACCUEIL M7 FIX : Données live plutôt que cartes statiques ---
        try:
            from core.market_state_cache import MarketStateCache
            m_cache_home = MarketStateCache()
            bot_status = m_cache_home.get_bot_status()
            is_running = bot_status.get("bot_is_running", False)
            active_syms = bot_status.get("active_symbols", [])
            last_hb = bot_status.get("last_heartbeat", "---")
            cache_home = m_cache_home.load()
        except Exception:
            is_running = False
            active_syms = []
            last_hb = "---"
            cache_home = {}

        status_color = "#00ff88" if is_running else "#ef5350"
        status_txt = "🟢 BOT ACTIF" if is_running else "⚫ BOT ARRÊTÉ"

        # Récupération Configuration pour l'écran d'accueil
        from interface.bot_settings import load_config as get_cfg, PROFILE_LABELS, MODE_LABELS
        cfg_home = get_cfg()
        prof_id = cfg_home.get("profile", "DAY_TRADE")
        mode_id = cfg_home.get("op_mode", "PAPER")
        prof_txt = PROFILE_LABELS.get(prof_id, "Inconnu")
        mode_txt = "🟥 SIMULATION PAPER" if "PAPER" in mode_id else ("🟨 SEMI-AUTO" if "SEMI" in mode_id else "🟩 ORDRES RÉELS")

        st.html(f"""
<div style='text-align:center; padding:40px 20px;'>
    <h2 style='color:#4dabff; font-family:Outfit,sans-serif; margin-bottom:5px;'>
        🛡️ ICT Sentinel Pro
    </h2>
    <div style='color:#848e9c; margin-bottom: 20px; font-size:1.1rem;'>
        <b>{prof_txt}</b> &nbsp;|&nbsp; <span style='background:rgba(255,255,255,0.05); padding:3px 8px; border-radius:4px;'>{mode_txt}</span>
    </div>
    <div style='display:inline-block; background:#111; border:1px solid {status_color};
         border-radius:10px; padding:8px 24px; margin-bottom:20px; font-weight:700;
         color:{status_color}; font-size:1.0rem; letter-spacing:1px;'>
        {status_txt} &nbsp;|&nbsp; Dernier check : {last_hb}
    </div>
</div>
""")

        if active_syms and cache_home:
            # Afficher un mini résumé par symbole actif
            cols = st.columns(min(len(active_syms), 3))
            for i, sym in enumerate(active_syms[:3]):
                sym_data = cache_home.get(sym, {}).get("timeframes", {})
                best_score = 0
                best_tf = "-"
                best_dir = "-"
                best_verdict = "---"
                for tf_k, tf_v in sym_data.items():
                    d = tf_v.get("data", {})
                    sc = d.get("checklist", {}).get("score", 0) or 0
                    if sc > best_score:
                        best_score = sc
                        best_tf = tf_k
                        best_verdict = d.get("checklist", {}).get("verdict", "---")
                        sig = d.get("last_signal", {})
                        best_dir = sig.get("direction", "-") if sig else "-"
                dir_icon = "🔼" if best_dir == "BUY" else "🔽" if best_dir == "SELL" else "⬜"
                sc_color = "#00ff88" if best_score >= 80 else "#f0b429" if best_score >= 65 else "#ef5350"
                with cols[i]:
                    st.html(
                        f"<div style='background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1);"
                        f"border-radius:12px; padding:18px 14px; text-align:center;'>"
                        f"<div style='font-size:1.1rem; font-weight:800; color:#4dabff;'>{sym}</div>"
                        f"<div style='font-size:2.0rem; font-weight:900; color:{sc_color}; margin:8px 0;'>{dir_icon} {best_score}<span style='font-size:0.9rem;'>/100</span></div>"
                        f"<div style='font-size:0.8rem; color:#848e9c;'>{best_tf} &mdash; {best_verdict[:25]}</div>"
                        f"</div>"
                    )
        st.html("<br>")

        st.html("""
<div style='text-align:center; margin-top:30px;'>
    <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; max-width:960px; margin:0 auto;'>
        <div class='feature-card'>
            <h4>🛡️ MULTI-SÉLECTION</h4>
            <p>Analysez jusqu'à 9 paires en temps réel avec bascule instantanée via la barre latérale.</p>
        </div>
        <div class='feature-card'>
            <h4>🕒 ANALYSE TEMPORELLE</h4>
            <p>Killzones, Biais HTF, Midnight Open et CBDR (14h-20h NY) pour une précision absolue.</p>
        </div>
        <div class='feature-card'>
            <h4>🎯 PRECISION SUPRÊMe</h4>
            <p>Détection algorithmique ERL, BOS/MSS, FVGs, OB et SMT Divergences.</p>
        </div>
    </div>
    <div style="margin-top:40px; padding:20px; background:rgba(41,98,255,0.12); border-radius:14px;
         border:1px dashed #2962ff; display:inline-block;">
        <p style='color:#4dabff; font-weight:800; margin:0; font-size:1.05rem;'>
            🚀 SÉLECTIONNEZ VOS PAIRES DANS LA BARRE LATÉRALE ⬅️
        </p>
    </div>
</div>
""")

