"""
main.py — Interface Streamlit pour SENTINEL PRO KB5
====================================================
Point d'entrée de l'interface visuelle.
Lit les données depuis le bridge.py (DataStore d'App2)
et affiche l'interface d'App1 adaptée au cerveau KB5.

Lancement : streamlit run main.py
"""

# ── Imports Streamlit ────────────────────────────────────────
try:
    import streamlit as st
except ModuleNotFoundError:
    raise SystemExit("Streamlit non installé. Lancez : pip install streamlit")

# ── Imports standard ─────────────────────────────────────────
import os
import sys
import pickle
import datetime

# Assurer que le dossier racine est dans le PATH
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ── Import Bridge (pont DataStore → Streamlit) ───────────────
try:
    from bridge.bridge import get_dashboard_data_from_cache, CB_COLORS, CB_LABELS, VERDICT_COLORS
    BRIDGE_OK = True
except ImportError:
    BRIDGE_OK = False

# ── Import interface Bot (portée depuis App1) ────────────────
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

# ── Import Plotly ────────────────────────────────────────────
try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

# ── Chemin cache pickle d'App2 ───────────────────────────────
CACHE_FILE = os.path.join(ROOT_DIR, "market_state.pkl")

# ============================================================
# CONFIG PAGE
# ============================================================
st.set_page_config(
    page_title="ICT SENTINEL KB5 — PRO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS GLASSMORPHISM (identique App1)
# ============================================================
st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Outfit:wght@500;700;900&display=swap');
.stApp {
    background: radial-gradient(circle at top right, #1a1f2c 0%, #0d1117 100%);
    color: #d1d4dc;
    font-family: 'Inter', sans-serif;
}
.report-card, .feature-card {
    background: rgba(30, 39, 58, 0.8);
    padding: 24px;
    border-radius: 16px;
    border: 1px solid rgba(41,98,255,0.25);
    margin-bottom: 16px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.metric-box {
    background: rgba(45, 55, 72, 0.7);
    padding: 18px;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.1);
    text-align: center;
    color: #fff;
}
.metric-box b { color: #4dabff; }
.stTabs [data-baseweb="tab-list"] { gap: 12px; background-color: transparent; }
.stTabs [data-baseweb="tab"] {
    background-color: rgba(30,34,45,0.5);
    border-radius: 8px;
    color: #848e9c;
    padding: 10px 20px;
    border: 1px solid transparent;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #2962ff 0%, #1c44b3 100%) !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(41,98,255,0.3);
}
[data-testid="stSidebar"] {
    background-color: #06090e;
    border-right: 1px solid rgba(255,255,255,0.05);
}
code { color: #00ff88 !important; background-color: rgba(0,255,136,0.1) !important; padding: 2px 7px !important; border-radius: 4px !important; }
</style>
""")

# ============================================================
# PAIRES CONFIGURÉES (symboles Exness)
# ============================================================
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
    "🥇 XAU/USD":    "XAUUSDm",
    "🥈 XAG/USD":    "XAGUSDm",
    "🛢️ WTI Oil":    "USOILm",
    "₿ BTC/USD":     "BTCUSDm",
    "🔷 ETH/USD":    "ETHUSDm",
    "💵 DXY":        "DXYm",
}

# ============================================================
# SESSION STATE
# ============================================================
defaults = {
    "pair_cache":     None,
    "active_pairs":   [],
    "last_analysis":  None,
    "scores_summary": {},
    "bot_is_running": False,
    "bot_page":       "analyse",
    "nav_state":      {"symbol": None, "tf": None, "consumed": False},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# LECTURE DES DONNÉES DEPUIS LE BRIDGE
# ============================================================
def load_dashboard_data() -> dict:
    """Charge les données depuis le cache pickle d'App2."""
    if BRIDGE_OK:
        return get_dashboard_data_from_cache(CACHE_FILE)
    return {}

# ============================================================
# SIDEBAR
# ============================================================
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

# Statut Bot
dash_data    = load_dashboard_data()
bot_status   = dash_data.get("bot_status", {})
bot_running  = bot_status.get("bot_is_running", False)
st.session_state["bot_is_running"] = bot_running

if bot_running:
    st.sidebar.success("🟢 BOT ACTIF")
else:
    st.sidebar.info("⚫ Bot arrêté")

# Pages non-analyse
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

# Boutons navigation Analyse
st.sidebar.markdown("---")
has_results = st.session_state["pair_cache"] is not None
nav1, nav2  = st.sidebar.columns(2)
retour  = nav1.button("🏠 Accueil",  use_container_width=True, disabled=not has_results)
refresh = nav2.button("🔄 Refresh",  use_container_width=True, disabled=not has_results)

if retour:
    st.session_state["pair_cache"]     = None
    st.session_state["active_pairs"]   = []
    st.session_state["scores_summary"] = {}
    st.session_state["last_analysis"]  = None
    st.rerun()

st.sidebar.markdown(f"<small style='color:#848e9c;'>🟢 MT5 connecté</small>", unsafe_allow_html=True)

# Scores dans sidebar
if st.session_state["scores_summary"]:
    st.sidebar.markdown("---")
    st.sidebar.markdown("<small style='color:#848e9c;font-weight:600;letter-spacing:1px;'>SCORES KB5</small>", unsafe_allow_html=True)
    for sym, sc in st.session_state["scores_summary"].items():
        if sc >= 80:
            bar_color = "#00c864"; verdict_txt = "🚀 EXEC A+"
        elif sc >= 65:
            bar_color = "#f0b429"; verdict_txt = "🔍 WATCH"
        else:
            bar_color = "#ef5350"; verdict_txt = "❌ NO TRADE"
        bar_w = max(int(sc), 3)
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

# Bouton lancer analyse
st.sidebar.markdown("---")
lancer = st.sidebar.button("🔬 LANCER L'ANALYSE", use_container_width=True, type="primary")

last_ok = st.session_state.get("last_analysis")
if last_ok:
    st.sidebar.markdown(
        f"<small style='color:#848e9c;'>🟢 Dernière analyse : <b>{last_ok}</b></small>",
        unsafe_allow_html=True
    )

# Sélection des paires
st.sidebar.markdown("")
selected_pairs = []
for label, symbol in PAIRS_CONFIG.items():
    has_state   = f"pair_{label}" in st.session_state
    default_val = False if not has_state else st.session_state[f"pair_{label}"]
    if st.sidebar.checkbox(label, value=default_val, key=f"pair_{label}"):
        selected_pairs.append((label, symbol))

col_sa, col_sc = st.sidebar.columns(2)
if col_sa.button("☑️ Tout",  use_container_width=True):
    for k in PAIRS_CONFIG:
        st.session_state[f"pair_{k}"] = True
if col_sc.button("⬜ Aucun", use_container_width=True):
    for k in PAIRS_CONFIG:
        st.session_state[f"pair_{k}"] = False

# ============================================================
# BANDEAU TRADES EN COURS (auto-refresh 5s)
# ============================================================
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
            f"<span style='font-size:0.7em;color:#4dabff;'>{profile_lbl}</span> "
            f"<span style='font-size:0.6em;background:rgba(255,255,255,0.1);padding:2px 6px;border-radius:4px;margin-left:10px;'>{mode_badge}</span>",
            unsafe_allow_html=True
        )

        cols = st.columns(min(len(positions), 4))
        for i, pos in enumerate(positions):
            col        = cols[i % 4]
            dir_color  = "#00c864" if pos.type == 0 else "#ef5350"
            dir_label  = "BUY 📈" if pos.type == 0 else "SELL 📉"
            pnl_color  = "#00c864" if pos.profit > 0 else "#ef5350"
            sl_display = pos.sl if pos.sl > 0 else "⚠️ ABSENT"
            sl_color   = "#ef5350" if pos.sl == 0 else "#ef5350"

            with col:
                st.html(f"""
                <div style="background:rgba(30,34,45,0.8);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:12px;margin-bottom:10px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <strong style="font-size:1.1em;color:#fff;">{pos.symbol}</strong>
                    <span style="color:{dir_color};font-weight:bold;font-size:0.9em;background:rgba(255,255,255,0.05);padding:2px 6px;border-radius:4px;">{dir_label} {pos.volume}</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;font-size:0.85em;color:#848e9c;margin-bottom:4px;">
                    <span>Entry: <span style="color:#fff;">{pos.price_open}</span></span>
                    <span>Now: <span style="color:#fff;">{pos.price_current}</span></span>
                  </div>
                  <div style="display:flex;justify-content:space-between;font-size:0.85em;color:#848e9c;margin-bottom:8px;">
                    <span>SL: <span style="color:{sl_color};">{sl_display}</span></span>
                    <span>TP: <span style="color:#00ff88;">{pos.tp if pos.tp > 0 else '-'}</span></span>
                  </div>
                  <div style="text-align:center;border-top:1px solid rgba(255,255,255,0.1);padding-top:8px;font-weight:bold;font-size:1.1em;color:{pnl_color};">
                    {pos.profit:.2f} $
                  </div>
                </div>
                """)
    except Exception:
        pass

_render_live_trades_banner()

# ============================================================
# PHASE DE CHARGEMENT
# ============================================================
do_load = lancer or refresh

if do_load and selected_pairs:
    temp_cache  = {}
    temp_scores = {}

    with st.spinner("⏳ Chargement des analyses KB5..."):
        prog = st.progress(0, text="Lecture en cours...")

        # Charger les données depuis le bridge
        all_data = load_dashboard_data()
        pairs_data_bridge = all_data.get("pairs", {})

        for idx, (label, symbol) in enumerate(selected_pairs):
            if symbol in pairs_data_bridge:
                temp_cache[symbol]  = {**pairs_data_bridge[symbol], "label": label}
                temp_scores[symbol] = pairs_data_bridge[symbol].get("best_score", 0)
            else:
                # Paire pas encore analysée par KB5
                temp_cache[symbol]  = {
                    "label":   label,
                    "pair":    symbol,
                    "error":   f"{symbol} : pas encore analysé par le cerveau KB5. Démarrez le bot.",
                }
                temp_scores[symbol] = 0

            prog.progress((idx + 1) / len(selected_pairs))

        prog.progress(1.0, text="✅ Chargement terminé !")

    st.session_state["pair_cache"]     = temp_cache
    st.session_state["active_pairs"]   = [s for _, s in selected_pairs]
    st.session_state["scores_summary"] = temp_scores
    st.session_state["last_analysis"]  = datetime.datetime.now().strftime("%H:%M:%S")
    st.rerun()

# ============================================================
# PHASE DE RENDU
# ============================================================

def render_pair_summary(symbol: str, cache: dict):
    """Affiche le résumé d'une paire depuis les données KB5."""
    label     = cache.get("label", symbol)
    htf_bias  = cache.get("htf_bias", "NEUTRAL")
    bias_color = cache.get("bias_color", "#848e9c")
    verdict   = cache.get("verdict", "NO_TRADE")
    score     = cache.get("best_score", 0)
    direction = cache.get("direction", "NEUTRAL")
    grade     = cache.get("grade", "C")
    rr        = cache.get("rr", 0.0)
    tf_scores = cache.get("tf_scores", {})

    # Boutons fermer / retour
    col_t, col_f, col_r = st.columns([8, 2, 2])
    with col_t:
        st.subheader(f"💎 {label}")
    with col_f:
        if st.button("❌ Fermer", key=f"close_{symbol}", type="primary", use_container_width=True):
            if symbol in st.session_state["active_pairs"]:
                st.session_state["active_pairs"].remove(symbol)
            if not st.session_state["active_pairs"]:
                st.session_state["pair_cache"] = None
            st.rerun()
    with col_r:
        if st.button("🏠 Retour", key=f"back_{symbol}", use_container_width=True):
            st.session_state["pair_cache"]   = None
            st.session_state["active_pairs"] = []
            st.rerun()

    if "error" in cache:
        st.error(f"⚠️ {cache['error']}")
        return

    # Métriques principales
    score_color = "#00ff88" if score >= 80 else ("#f0b429" if score >= 65 else "#ef5350")
    dir_icon    = "🔼 BULLISH" if "BULL" in direction else ("🔽 BEARISH" if "BEAR" in direction else "⬜ NEUTRE")

    m1, m2, m3, m4 = st.columns(4)
    m1.html(f"<div class='metric-box'>🌍 BIAIS HTF<br><b style='color:{bias_color}'>{htf_bias}</b></div>")
    m2.html(f"<div class='metric-box'>🎯 SCORE KB5<br><b style='color:{score_color};font-size:1.4rem;'>{score}/100 {grade}</b></div>")
    m3.html(f"<div class='metric-box'>📈 DIRECTION<br><b style='color:{bias_color}'>{dir_icon}</b></div>")
    m4.html(f"<div class='metric-box'>⚖️ R/R<br><b style='color:#4dabff'>{rr:.1f}x</b></div>")
    st.html("<br>")

    # Tableau des scores par timeframe
    st.markdown("#### 📊 Pyramide KB5 — Scores par Timeframe")

    tf_order = ["MN", "W1", "D1", "H4", "H1", "M15", "M5"]
    cols     = st.columns(len(tf_order))

    for i, tf in enumerate(tf_order):
        tf_data  = tf_scores.get(tf, {})
        sc       = tf_data.get("score", 0)
        vd       = tf_data.get("verdict", "NO_TRADE")
        sc_color = "#00ff88" if sc >= 80 else ("#f0b429" if sc >= 65 else "#ef5350")
        vd_short = {"EXECUTE": "🚀", "WATCH": "👁", "NO_TRADE": "⛔", "BLOCKED": "🔒"}.get(vd, "—")

        with cols[i]:
            st.html(
                f"<div style='background:rgba(30,34,45,0.8);border:1px solid rgba(255,255,255,0.1);"
                f"border-radius:8px;padding:10px;text-align:center;margin:2px;'>"
                f"<div style='font-size:0.7rem;color:#848e9c;'>{tf}</div>"
                f"<div style='font-size:1.3rem;font-weight:800;color:{sc_color};'>{sc}</div>"
                f"<div style='font-size:0.8rem;color:{sc_color};'>{vd_short}</div>"
                f"</div>"
            )

    st.html("<br>")

    # Niveaux entry / SL / TP
    entry = cache.get("entry")
    sl    = cache.get("sl")
    tp    = cache.get("tp")

    if entry and sl and tp:
        st.markdown("#### 🎯 Niveaux d'entrée KB5")
        n1, n2, n3 = st.columns(3)
        n1.html(
            f"<div style='background:#1a1a2e;border:1px solid #2962ff44;border-radius:10px;padding:12px;text-align:center;'>"
            f"<div style='font-size:0.65rem;color:#4dabff;text-transform:uppercase;'>Entry</div>"
            f"<div style='font-size:1.1rem;font-weight:700;color:#4dabff;'>{entry:.5f}</div></div>"
        )
        n2.html(
            f"<div style='background:#1a1a2e;border:1px solid #ef535044;border-radius:10px;padding:12px;text-align:center;'>"
            f"<div style='font-size:0.65rem;color:#ef5350;text-transform:uppercase;'>Stop Loss</div>"
            f"<div style='font-size:1.1rem;font-weight:700;color:#ef5350;'>{sl:.5f}</div></div>"
        )
        n3.html(
            f"<div style='background:#1a2e1a;border:1px solid #00ff8844;border-radius:10px;padding:12px;text-align:center;'>"
            f"<div style='font-size:0.65rem;color:#00ff88;text-transform:uppercase;'>Take Profit</div>"
            f"<div style='font-size:1.1rem;font-weight:700;color:#00ff88;'>{tp:.5f}</div></div>"
        )

    st.html("<div style='margin-bottom:40px;'></div>")


# ── Rendu principal ──────────────────────────────────────────
if st.session_state.get("pair_cache"):
    pairs_data  = st.session_state["pair_cache"]
    active_list = [p for p in st.session_state["active_pairs"] if p in pairs_data]

    if not active_list:
        st.session_state["pair_cache"] = None
        st.rerun()

    st.header(f"🔱 ICT SENTINEL KB5 — {len(active_list)} PAIRE(S)")

    # Circuit Breaker visible en haut
    cb_data = load_dashboard_data().get("circuit_breaker", {})
    cb_lvl  = cb_data.get("level", 0)
    if cb_lvl > 0:
        st.html(
            f"<div style='background:rgba(239,83,80,0.15);border:1px solid #ef5350;"
            f"border-radius:8px;padding:10px 16px;margin-bottom:16px;'>"
            f"🔴 <b>CIRCUIT BREAKER CB{cb_lvl}</b> — {CB_LABELS.get(cb_lvl, '')}</div>"
        )

    # Tabs par paire
    tab_labels = [pairs_data[s].get("label", s) for s in active_list]
    p_tabs     = st.tabs(tab_labels)

    for idx, sym in enumerate(active_list):
        with p_tabs[idx]:
            render_pair_summary(sym, pairs_data[sym])

else:
    # ── ÉCRAN D'ACCUEIL ─────────────────────────────────────
    all_data   = load_dashboard_data()
    bot_status = all_data.get("bot_status", {})
    is_running = bot_status.get("bot_is_running", False)
    last_hb    = bot_status.get("last_heartbeat", "---")
    equity     = all_data.get("equity", 0.0)
    cb_data    = all_data.get("circuit_breaker", {})
    cb_lvl     = cb_data.get("level", 0)

    status_color = "#00ff88" if is_running else "#ef5350"
    status_txt   = "🟢 BOT ACTIF" if is_running else "⚫ BOT ARRÊTÉ"
    cb_color     = CB_COLORS.get(cb_lvl, "#00ff88")

    st.html(f"""
    <div style='text-align:center;padding:40px 20px;'>
      <h2 style='color:#4dabff;font-family:Outfit,sans-serif;margin-bottom:5px;'>
        🛡️ ICT Sentinel KB5 Pro
      </h2>
      <div style='display:inline-block;background:#111;border:1px solid {status_color};
           border-radius:10px;padding:8px 24px;margin:10px;font-weight:700;
           color:{status_color};font-size:1.0rem;letter-spacing:1px;'>
        {status_txt} &nbsp;|&nbsp; Dernier check : {last_hb}
      </div>
      <div style='display:inline-block;background:#111;border:1px solid {cb_color};
           border-radius:10px;padding:8px 24px;margin:10px;font-weight:700;
           color:{cb_color};font-size:0.9rem;'>
        CB{cb_lvl} — {CB_LABELS.get(cb_lvl, 'NOMINAL')}
      </div>
      <div style='color:#848e9c;margin:10px;font-size:1rem;'>
        Équité : <b style='color:#4dabff;'>{equity:.2f} $</b>
      </div>
    </div>
    """)

    # Résumé scores si disponible
    scores_sum = all_data.get("scores_summary", {})
    if scores_sum:
        cols = st.columns(min(len(scores_sum), 4))
        for i, (sym, sc) in enumerate(list(scores_sum.items())[:4]):
            sc_color = "#00ff88" if sc >= 80 else ("#f0b429" if sc >= 65 else "#ef5350")
            with cols[i % 4]:
                st.html(
                    f"<div style='background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);"
                    f"border-radius:12px;padding:18px 14px;text-align:center;'>"
                    f"<div style='font-size:1rem;font-weight:800;color:#4dabff;'>{sym}</div>"
                    f"<div style='font-size:2rem;font-weight:900;color:{sc_color};margin:8px 0;'>{sc}<span style='font-size:0.9rem;'>/100</span></div>"
                    f"</div>"
                )

    st.html("""
    <div style='text-align:center;margin-top:30px;'>
      <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:24px;max-width:960px;margin:0 auto;'>
        <div class='feature-card'><h4 style='color:#00ff88;'>🛡️ CERVEAU KB5</h4>
          <p>Pyramide 6 niveaux MN→M15 avec cascade HTF, 10 confluences ICT, BooleanERL Gate §0.</p></div>
        <div class='feature-card'><h4 style='color:#00ff88;'>🔒 PROTECTION TOTALE</h4>
          <p>Circuit Breaker 4 niveaux, 9 KillSwitches, BehaviourShield 8 filtres anti-manipulation.</p></div>
        <div class='feature-card'><h4 style='color:#00ff88;'>🤖 TRIPLE IA</h4>
          <p>Groq (validation rapide) + Gemini (narratif War Room) + Perplexity (contexte macro).</p></div>
      </div>
      <div style='margin-top:40px;padding:20px;background:rgba(41,98,255,0.12);border-radius:14px;border:1px dashed #2962ff;display:inline-block;'>
        <p style='color:#4dabff;font-weight:800;margin:0;font-size:1.05rem;'>
          🚀 SÉLECTIONNEZ VOS PAIRES DANS LA BARRE LATÉRALE ⬅️
        </p>
      </div>
    </div>
    """)
