"""
══════════════════════════════════════════════════════════════
Sentinel Pro KB5 — Dashboard Plotly 10 Couches ICT
══════════════════════════════════════════════════════════════
Interface Streamlit avec :
- Graphique Plotly 10 couches annotées ICT
- 5 espaces : Monitoring, Analyse ICT, Scalp Output, Stats, Paramètres
- Temps réel via cache market_state_cache.py
══════════════════════════════════════════════════════════════
"""

import sys
import os
from pathlib import Path

# Ajouter la racine du projet au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time
import logging

logger = logging.getLogger(__name__)
# Imports des modules du bot
from execution.market_state_cache import MarketStateCache
from analysis.scoring_engine import ScoringEngine
from learning.trade_journal import TradeJournal
from learning.failure_lab import FailureLab
from learning.performance_memory import PerformanceMemory
from interface.telegram_notifier import TelegramNotifier
from config.settings_manager import SettingsManager
from interface.settings_panel import render_settings_panel
from analysis.llm_narrative import generate_narrative

# Config
REFRESH_INTERVAL = 5  # secondes
PYRAMID_ORDER = ["MN", "W1", "D1", "H4", "H1", "M15", "M5", "M1"]

st.set_page_config(
    page_title="Sentinel Pro KB5 Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── État global ──
@st.cache_resource
def init_components():
    """Initialise tous les composants."""
    cache    = MarketStateCache()
    journal  = TradeJournal()
    failure_lab = FailureLab(journal)
    perf_mem = PerformanceMemory()
    settings = SettingsManager()    # <-- gestionnaire de paramètres utilisateur
    # Telegram optionnel
    notifier = None
    try:
        if st.secrets.get("TELEGRAM_TOKEN"):
            notifier = TelegramNotifier(
                st.secrets["TELEGRAM_TOKEN"],
                st.secrets["TELEGRAM_CHAT_ID"]
            )
    except Exception as e:
        logger.warning(f"No secrets.toml or error loading secrets: {e}. Telegram notifier disabled.")
    return cache, journal, failure_lab, perf_mem, notifier, settings

cache, journal, failure_lab, perf_mem, notifier, settings = init_components()

# Paires dynamiques depuis les settings utilisateur
PAIRES = settings.get_active_pairs() or ["EURUSDm", "GBPUSDm", "XAUUSDm", "USTECm"]

# ── Sidebar ──
st.sidebar.title("🔧 Paramètres")
selected_pair = st.sidebar.selectbox("Paire", PAIRES)
mode = st.sidebar.radio("Mode", ["Analyse", "Monitoring", "Stats"])
force_refresh = st.sidebar.button("🔄 Refresh forcé")

st.sidebar.markdown("---")

# Récap settings dans la sidebar
rc = settings.get_risk_config()
current_profile = settings.get("profile", "Custom")
st.sidebar.markdown(f"**Profil : `{current_profile}`**")
st.sidebar.markdown(
    f"RR min: **{rc['rr_min']}x** | DD/j: **{rc['max_dd_day_pct']}%**\n\n"
    f"Trades/j max: **{rc['max_trades_day']}** | Risque/trade: **{rc['risk_per_trade']}%**"
)

st.sidebar.info(f"Paires actives : {len(PAIRES)}")

st.sidebar.markdown("---")
# --- Bot Controls ---
st.sidebar.markdown("### 🎛️ Contrôle du Bot")
bot_status = cache.get("bot_status", "Arrêté")
if bot_status == "Actif":
    st.sidebar.success("🟢 BOT ACTIF")
    if st.sidebar.button("🟥 STOPPER LE BOT", width="stretch"):
        cache.set("bot_status", "Arrêté")
        st.rerun()
else:
    st.sidebar.error("🔴 BOT ARRÊTÉ")
    if st.sidebar.button("🟩 DÉMARRER LE BOT", width="stretch"):
        cache.set("bot_status", "Actif")
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("⚙️ Ouvrir les Paramètres", width="stretch"):
    st.query_params["tab"] = "settings"
    st.rerun()

# ── Header ──
# ── Fragments temps réel (Streamlit 1.37+) ──
@st.fragment(run_every=REFRESH_INTERVAL)
def render_live_header():
    # Recharger le cache et les réglages depuis le disque pour synchro avec le moteur
    cache.load_from_disk()
    settings._load()
    st.title("📈 Sentinel Pro KB5 — Dashboard ICT")

    with st.container():
        col1, col2, col3 = st.columns(3)
        
        # Score : meilleur score parmi les paires actives
        best_score = 0
        for p in PAIRES:
            state = cache.get(p, {})
            if state:
                s = state.get("scoring_output", {}).get("score", 0)
                if s > best_score:
                    best_score = s
        
        # Stats du journal
        stats = journal.get_stats()
        total_trades = stats.get("total", 0)
        winrate = stats.get("winrate", 0.0)
        
        with col1:
            score_label = "TOP SIGNAL" if best_score >= 78 else ("WATCH" if best_score >= 63 else "---")
            st.metric("Meilleur Score", f"{best_score}/100" if best_score > 0 else "En attente...", score_label)
        with col2:
            st.metric("Trades total", str(total_trades))
        with col3:
            st.metric("Winrate", f"{winrate:.1f}%")

    st.markdown("### ⚔️ Positions Ouvertes Actives")
    open_positions = cache.get("open_positions", [])
    
    # Rendre TOUJOURS le dataframe pour stabiliser le DOM React
    if not open_positions:
        empty_df = pd.DataFrame(columns=["Ticket", "Symbol", "Type", "Entry", "PnL"])
        st.dataframe(empty_df, width="stretch", hide_index=True)
    else:
        pos_df = pd.DataFrame(open_positions)
        st.dataframe(pos_df, width="stretch", hide_index=True)

def _get_count(val):
    """Convertit une valeur (int, dict, etc) en entier pour les counts."""
    if isinstance(val, dict):
        return len(val) if val else 0
    try:
        return int(val) if val else 0
    except (ValueError, TypeError):
        return 0

def _enrich_tf_details(kb5_result):
    """Enrichit les détails TF avec toutes les informations disponibles."""
    tf_details = kb5_result.get("tf_details", {})
    direction = kb5_result.get("direction", "NEUTRAL")
    entry_model = kb5_result.get("entry_model", {})
    
    # Enrichir chaque TF avec plus d'infos
    for tf in PYRAMID_ORDER:
        if tf not in tf_details:
            tf_details[tf] = {"score": 0, "components": {}}
        
        # Copier les données globales si pas de données TF-spécifiques
        tf_data = tf_details[tf]
        
        # Ajouter direction et RR
        if "direction" not in tf_data:
            tf_data["direction"] = direction
        if "rr" not in tf_data:
            tf_data["rr"] = entry_model.get("rr", 0)
        
        # Ajouter confluences pour ce TF
        if "confluences" not in tf_data:
            tf_data["confluences"] = [c for c in kb5_result.get("confluences", []) 
                                     if c.get("tf", "").upper() == tf or not c.get("tf")]
        
        # Ajouter structures (FVG, OB, etc.)
        if "fvgs" not in tf_data:
            tf_data["fvgs"] = kb5_result.get("fvgs", [])
        if "fvg_count" not in tf_data:
            tf_data["fvg_count"] = len(tf_data.get("fvgs", []))
        
        if "order_blocks" not in tf_data:
            tf_data["order_blocks"] = kb5_result.get("order_blocks", [])
        if "ob_count" not in tf_data:
            tf_data["ob_count"] = len(tf_data.get("order_blocks", []))
        
        # Ajouter liquidity zones
        if "liquidity" not in tf_data:
            tf_data["liquidity"] = kb5_result.get("liquidity", {})
        
        # Ajouter sessions
        if "sessions" not in tf_data:
            tf_data["sessions"] = kb5_result.get("sessions", [])
        
        # Ajouter smart money structure
        if "smt" not in tf_data:
            tf_data["smt"] = kb5_result.get("smt", {})
        
        # Ajouter DOL
        if "dol" not in tf_data:
            tf_data["dol"] = kb5_result.get("dol", {})
        
        # Ajouter composants du score
        if "components" not in tf_data:
            tf_data["components"] = {}
        
        tf_details[tf] = tf_data
    
    return tf_details

@st.fragment(run_every=REFRESH_INTERVAL)
def render_tab1_live(selected_pair):
    cache.load_from_disk()  # Sync avec le moteur
    state = cache.get(selected_pair, {})
    
    kb5_result = state.get("kb5_result", {}) if state else {}
    scoring_output = state.get("scoring_output", {}) if state else {}
    entry_model = kb5_result.get("entry_model", {}) if kb5_result else {}

    st.markdown("### 📡 Radar ICT Multi-Temporel")
    pyramid = kb5_result.get("pyramid_scores", {})
    confluences = kb5_result.get("confluences", [])
    
    # Sécuriser les accès
    has_mss = "MSS" in " ".join([c.get("name", "") for c in confluences if isinstance(c, dict)]).upper()
    has_choch = "CHOCH" in " ".join([c.get("name", "") for c in confluences if isinstance(c, dict)]).upper()
    
    radar_data = []
    for tf in PYRAMID_ORDER:
        score = pyramid.get(tf, 0)
        tf_data = kb5_result.get("tf_details", {}).get(tf, {})
        direction = tf_data.get("direction", "NEUTRAL") if tf_data.get("score", 0) > 0 else "NEUTRAL"
        
        # Getter sécurisé pour les counts
        fvg_count = _get_count(tf_data.get("fvg_count", 0))
        ob_count = _get_count(tf_data.get("ob_count", 0))
        
        status = "⚫ En attente"
        if score >= 80: 
            status = "🔥 Exécution A+"
        elif score >= 65: 
            status = "🎯 Tireur d'élite"
        elif score > 15: 
            status = "⏳ Regarder (WATCH)"
        
        # Icônes direction
        dir_icon = "📈" if direction == "BULLISH" else "📉" if direction == "BEARISH" else "➡️"
        
        radar_data.append({
            "TF": f"**{tf}**",
            "Score": f"{score}/100" if score > 0 else "---",
            "Direction": f"{dir_icon} {direction}",
            "Statut": status,
            "FVG": f"✅" if fvg_count > 0 else "---",
            "OB": f"✅" if ob_count > 0 else "---",
            "Status Grid": "🟢" if score >= 65 else "🟡" if score >= 15 else "🔴"
        })
    
    st.dataframe(
        pd.DataFrame(radar_data),
        width="stretch",
        hide_index=True,
        key=f"radar_df_{selected_pair}",
        column_config={
            "TF": st.column_config.TextColumn("Timeframe", width="small"),
            "Score": st.column_config.TextColumn("Verdict ICT", width="medium"),
            "Direction": st.column_config.TextColumn("Direction", width="medium"),
            "Statut": st.column_config.TextColumn("Statut Opérationnel", width="medium"),
            "FVG": st.column_config.TextColumn("FVG", width="small"),
            "OB": st.column_config.TextColumn("OB", width="small"),
            "Status Grid": st.column_config.TextColumn("Signal", width="small"),
        }
    )

    st.markdown("---")
    st.markdown("### 📊 Métriques Globales")
    
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
    
    with metric_col1:
        st.metric(
            "🎯 Score Final", 
            f"{scoring_output.get('score', 0)}/100",
            delta=None
        )
    with metric_col2:
        verdict = scoring_output.get("verdict", "En attente...")
        verdict_icon = "✅" if verdict == "EXECUTE" else "👁️" if verdict == "WATCH" else "⛔"
        st.metric(f"{verdict_icon} Verdict", verdict)
    with metric_col3:
        grade = scoring_output.get("grade", "-")
        st.metric("📈 Grade", grade)
    with metric_col4:
        direction = scoring_output.get("direction", "NEUTRAL")
        dir_icon = "📈" if direction == "BULLISH" else "📉" if direction == "BEARISH" else "➡️"
        st.metric(f"{dir_icon} Direction", direction)
    with metric_col5:
        rr = entry_model.get("rr", 0) if entry_model else 0
        st.metric("💰 RR", f"{rr:.2f}x" if rr > 0 else "---")

    st.markdown("---")
    
    # Enrichir tf_details AVANT de l'utiliser
    tf_details = _enrich_tf_details(kb5_result)
    
    st.markdown("### 🏗️ Structures ICT Globales Détectées")
    
    struct_col1, struct_col2, struct_col3, struct_col4, struct_col5 = st.columns(5)
    
    # Compiler les totaux
    total_fvgs = sum(_get_count(tf_details.get(tf, {}).get("fvg_count", 0)) for tf in PYRAMID_ORDER)
    total_obs = sum(_get_count(tf_details.get(tf, {}).get("ob_count", 0)) for tf in PYRAMID_ORDER)
    total_confluences = len(kb5_result.get("confluences", []))
    
    with struct_col1:
        st.metric("📈 FVG Totaux", f"{total_fvgs}")
    with struct_col2:
        st.metric("🎯 OB Totaux", f"{total_obs}")
    with struct_col3:
        st.metric("🎪 Confluences", f"{total_confluences}")
    with struct_col4:
        dol = kb5_result.get("dol", {})
        st.metric("🎲 DOL", "✅ Actif" if dol else "---")
    with struct_col5:
        sessions = kb5_result.get("sessions", [])
        st.metric("📍 Sessions", f"{len(sessions)}")
    
    st.markdown("---")
    
    # ── SÉLECTEUR DE TIMEFRAME (DOIT ÊTRE EN PREMIER!) ────────────────────────────
    st.markdown("## 🔍 ANALYSEUR PAR TIMEFRAME")
    st.markdown("*Sélectionnez un timeframe pour voir les structures détaillées*")
    
    selected_tf = st.selectbox(
        "📊 Sélectionnez un Timeframe à analyser:",
        options=PYRAMID_ORDER,
        format_func=lambda x: f"🎯 {x}",
        key=f"tf_selector_{selected_pair}"
    )
    
    st.markdown("---")
    
    # ── GET DATA FOR SELECTED TIMEFRAME ────────────────────────────
    tf_data = tf_details.get(selected_tf, {})
    tf_fvgs = tf_data.get("fvgs", [])
    tf_obs = tf_data.get("order_blocks", [])
    tf_liquidity = tf_data.get("liquidity", {})
    tf_sessions = tf_data.get("sessions", [])
    tf_dol = tf_data.get("dol", {})
    tf_score = tf_data.get("score", 0)
    tf_direction = tf_data.get("direction", "NEUTRAL")
    tf_components = tf_data.get("components", {})
    tf_rr = tf_data.get("rr", 0)
    
    fig = make_subplots(
        rows=1, cols=1,
        subplot_titles=[f"Analyse ICT ({selected_tf}) — Bougies + Structures du Timeframe"],
        specs=[[{"secondary_y": False}]],
        vertical_spacing=0.1
    )

    # CHARGER LES BOUGIES DU TF SÉLECTIONNÉ
    candles = None
    
    # Essayer d'abord d'obtenir les candles organisées par TF
    state_candles = state.get("candles", {}) if state else {}
    if isinstance(state_candles, dict):
        candles = state_candles.get(selected_tf, [])
    elif isinstance(state_candles, list):
        # Si c'est une liste, utiliser directement (fallback)
        candles = state_candles
    
    # Fallback si aucune donnée
    if not candles:
        st.warning(f"⚠️ Pas de bougies pour {selected_tf} — données manquantes", icon="⚠️")
        candles = []
    
    if candles:
        df = pd.DataFrame(candles)
        fig.add_trace(go.Candlestick(
            x=df["time"], open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            name=f"Prix {selected_tf}", 
            increasing=dict(line=dict(color="green")),
            decreasing=dict(line=dict(color="red")),
            line=dict(width=1)
        ))
    else:
         # Empty axes if no data
         fig.add_scatter(x=[], y=[])

    # ── SESSIONS ICT (DU TF SÉLECTIONNÉ) ──────────────────────────────────
    for s in tf_sessions:
        session_name = s.get("name", "Session")
        fig.add_hrect(
            y0=s["low"], y1=s["high"], x0=s["start"], x1=s["end"],
            fillcolor="rgba(100,150,255,0.08)", line_width=1, line_color="rgba(100,150,255,0.3)",
            annotation_text=f"<b>{session_name}</b>", 
            annotation_position="top left",
            annotation_font=dict(size=10, color="blue")
        )

    # ── FVG : Fair Value Gaps (DU TF SÉLECTIONNÉ) ────────────────────────
    for i, fvg in enumerate(tf_fvgs):
        is_bullish = fvg.get("direction") == "BULLISH"
        color = "rgba(0,255,100,0.15)" if is_bullish else "rgba(255,100,0,0.15)"
        line_color = "green" if is_bullish else "red"
        direction_label = "📈 FVG↑" if is_bullish else "📉 FVG↓"
        
        fig.add_hrect(
            y0=fvg.get("low", 0), y1=fvg.get("high", 0), 
            x0=fvg.get("start", 0), x1=fvg.get("end", 0),
            fillcolor=color, line_width=2, line_color=line_color,
            annotation_text=f"{direction_label} {fvg.get('quality', 'Normal')}", 
            annotation_position="top right",
            annotation_font=dict(size=9, color=line_color)
        )

    # ── ORDER BLOCKS (DU TF SÉLECTIONNÉ) ──────────
    for ob in tf_obs:
        is_valid = ob.get("status") == "VALID"
        color = "rgba(255,165,0,0.2)" if is_valid else "rgba(200,200,200,0.1)"
        line_color = "darkorange" if is_valid else "gray"
        status_label = f"🎯 OB [{ob.get('quality', 'N')}]"
        
        fig.add_hrect(
            y0=ob.get("low", 0), y1=ob.get("high", 0), 
            x0=ob.get("start", 0), x1=ob.get("end", 0),
            fillcolor=color, line_width=2, line_dash="dash",
            line_color=line_color,
            annotation_text=status_label, 
            annotation_position="bottom right",
            annotation_font=dict(size=8, color=line_color)
        )

    # ── LIQUIDITY ZONES (DU TF SÉLECTIONNÉ) ──────────────
    if isinstance(tf_liquidity, dict):
        for level, data in tf_liquidity.items():
            price = data.get("price", 0) if isinstance(data, dict) else data
            color_map = {
                "SUPPORT": "green",
                "RESISTANCE": "red",
                "EQUAL_LOW": "blue",
                "EQUAL_HIGH": "orange"
            }
            color = color_map.get(level, "gray")
            fig.add_hline(
                y=price, line_dash="dash", line_width=1, line_color=color,
                annotation_text=f"💧 {level}: {price:.4f}", 
                annotation_position="right",
                annotation_font=dict(size=8, color=color)
            )

    # ── DELIVERY OPENING LEVEL (DU TF SÉLECTIONNÉ) ──────────────────────
    if tf_dol and tf_dol.get("target_price"):
        fig.add_hline(
            y=tf_dol.get("target_price", 0), line_dash="dot", line_width=2, line_color="purple",
            annotation_text=f"🎲 DOL {tf_dol.get('direction', '?')}", 
            annotation_position="right",
            annotation_font=dict(size=9, color="purple")
        )

    # ── SMART MONEY (MSS) ─────────────────────────────────
    smt_data = kb5_result.get("smt", {})
    if smt_data:
        if smt_data.get("has_choch"):
            st.markdown(f"🔄 **CHoCH détecté** — Changement de character détecté", unsafe_allow_html=True)
        if smt_data.get("has_mss"):
            st.markdown(f"💨 **MSS actif** — Variable structure validée", unsafe_allow_html=True)

    fig.update_layout(
        title=f"<b>Sentinel Pro KB5 — {selected_pair} @ {selected_tf}</b> | "
              f"Score TF: {tf_data.get('score', 0)}/100 | "
              f"FVG: {len(tf_fvgs)} | OB: {len(tf_obs)} | "
              f"Direction: {tf_direction}",
        xaxis_title="Temps (UTC)", 
        yaxis_title="Prix",
        height=700, 
        showlegend=False,
        hovermode="x unified",
        template="plotly_dark"
    )

    st.plotly_chart(fig, width="stretch", key=f"main_chart_{selected_pair}")
    
    # ── NARRATION EXPERT IA ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🤖 NARRATION EXPERT — Analyse Détaillée")
    
    # Générer narration complète
    try:
        llm_config = settings.get_llm_config()
        llm_provider = llm_config.get("llm_provider", "Gemini")
        api_key = llm_config.get("llm_api_key", "")
        
        narrative = generate_narrative(
            llm_provider=llm_provider,
            api_key=api_key,
            pair=selected_pair,
            kb5_result=kb5_result,
            scoring_output=scoring_output
        )
        
        if narrative and "⚠️ Clé API non configurée" not in narrative:
            # Afficher la narration dans un expander
            with st.expander("📖 Cliquez pour lire l'analyse complète", expanded=True):
                st.markdown(narrative, unsafe_allow_html=True)
        else:
            with st.expander("📖 Configuration de l'IA requise", expanded=False):
                st.warning(narrative or "⚠️ Impossible de générer la narration")
    except Exception as e:
        with st.expander("📖 Narration (Erreur)", expanded=False):
            st.warning(f"⚠️ Narration indisponible — {str(e)}")
        logger.error(f"Narrative generation error: {e}")

    # ── BUILD TIMEFRAME-SPECIFIC DATA ──────────────────────────────
    tf_data = tf_details.get(selected_tf, {})
    tf_score = tf_data.get("score", 0)
    tf_direction = tf_data.get("direction", "NEUTRAL")
    tf_components = tf_data.get("components", {})
    tf_rr = tf_data.get("rr", 0)
    
    # Display header
    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
    with col_h1:
        st.metric("📈 Score TF", f"{tf_score}/100", delta=None)
    with col_h2:
        dir_icon = "📈" if tf_direction == "BULLISH" else "📉" if tf_direction == "BEARISH" else "➡️"
        st.metric(f"{dir_icon} Direction", tf_direction)
    with col_h3:
        st.metric("💰 Risk/Reward", f"{tf_components.get('rr', 0):.2f}x" if tf_components.get('rr', 0) > 0 else "---")
    with col_h4:
        confluence_count = len(tf_data.get("confluences", []))
        st.metric("🎯 Confluences", confluence_count)
    
    st.plotly_chart(fig, width="stretch", key=None)  # Pas de clé fixe pour éviter duplication dans fragments
    
    # ── CHECKLIST ICT COMPLÈTE ──────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### ✅ Checklist ICT Complète — {selected_tf}")
    
    checklist_col1, checklist_col2 = st.columns(2)
    
    with checklist_col1:
        st.markdown("#### 🟢 STRUCTURES DÉTECTÉES")
        
        # FVG Checklist
        fvg_list = tf_data.get("fvgs", [])
        fvg_count = _get_count(tf_data.get("fvg_count", len(fvg_list)))
        
        st.markdown(f"**📊 Fair Value Gaps (FVG)** — {fvg_count} détectés")
        if fvg_list:
            for i, fvg in enumerate(fvg_list[:5], 1):
                direction_emoji = "📈" if fvg.get("direction") == "BULLISH" else "📉"
                quality = fvg.get("quality", "Normal")
                price_low = fvg.get("low", 0)
                price_high = fvg.get("high", 0)
                gap_size = price_high - price_low
                filled = fvg.get("filled", False)
                filled_icon = "✅" if filled else "⏳"
                
                with st.container(border=True):
                    st.markdown(
                        f"**{direction_emoji} [{i}] {quality}** — {filled_icon}\n"
                        f"• Range: `{price_low:.4f}` → `{price_high:.4f}` (Δ {gap_size:.4f})\n"
                        f"• Type: {fvg.get('type', 'Normal FVG')}\n"
                        f"• Status: {'REMPLI' if filled else 'ACTIF'}"
                    )
        else:
            st.info("✅ Aucun FVG — Marché cohérent")
        
        st.markdown("---")
        
        # Order Blocks Checklist
        ob_list = tf_data.get("order_blocks", [])
        ob_count = _get_count(tf_data.get("ob_count", len(ob_list)))
        
        st.markdown(f"**🎯 Order Blocks (OB)** — {ob_count} détectés")
        if ob_list:
            for i, ob in enumerate(ob_list[:5], 1):
                status = ob.get("status", "PENDING")
                quality = ob.get("quality", "N/A")
                price_low = ob.get("low", 0)
                price_high = ob.get("high", 0)
                ob_size = price_high - price_low
                status_emoji = "🎯" if status == "VALID" else "⏳"
                
                with st.container(border=True):
                    st.markdown(
                        f"**{status_emoji} [{i}] {quality}** ({status})\n"
                        f"• Range: `{price_low:.4f}` → `{price_high:.4f}` (Δ {ob_size:.4f})\n"
                        f"• Imbalance: {ob.get('imbalance', 'N/A')}\n"
                        f"• Confluence: {ob.get('confluence_count', 0)} niveaux"
                    )
        else:
            st.info("✅ Pas de concentration institutionnelle détectée")
        
        st.markdown("---")
        
        # Liquidity Zones
        liquidity = tf_data.get("liquidity", {})
        liq_count = 0
        if isinstance(liquidity, dict):
            liq_count = len(liquidity)
        
        st.markdown(f"**💧 Zones de Liquidité** — {liq_count} niveaux")
        if isinstance(liquidity, dict):
            for level, data in list(liquidity.items())[:8]:
                price = data.get("price", 0) if isinstance(data, dict) else data
                level_emoji = "🔴" if "SUPPORT" in level else "🔵" if "RESISTANCE" in level else "🟠"
                liquidity_strength = "Strong" if "SUPPORT" in level or "RESISTANCE" in level else "Normal"
                
                st.markdown(f"  {level_emoji} **{level}**: `{price:.4f}` — {liquidity_strength}")
        else:
            st.info("✅ Aucune liquidité extrême détectée")
    
    with checklist_col2:
        st.markdown("#### 🔵 SMART MONEY & SESSIONS")
        
        # Smart Money Structure
        smt_data = tf_data.get("smt", {})
        st.markdown("**🎪 Smart Money Structure**")
        has_choch = smt_data.get("has_choch", False) if isinstance(smt_data, dict) else False
        has_mss = smt_data.get("has_mss", False) if isinstance(smt_data, dict) else False
        
        with st.container(border=True):
            choch_status = "✅ ACTIF" if has_choch else "❌ INACTIF"
            mss_status = "✅ ACTIF" if has_mss else "❌ INACTIF"
            
            st.markdown(
                f"**🔄 Change of Character (CHoCH)**\n"
                f"• Status: {choch_status}\n"
                f"• Signification: {'Structure de marché confirmée' if has_choch else 'Pas de changement structurel'}\n\n"
                f"**💨 Market Structure Shift (MSS)**\n"
                f"• Status: {mss_status}\n"
                f"• Signification: {'Variable structure détectée' if has_mss else 'Structure stable'}"
            )
        
        st.markdown("---")
        
        # Sessions détaillées
        sessions = tf_data.get("sessions", [])
        session_count = len(sessions) if isinstance(sessions, list) else 0
        st.markdown(f"**📍 Sessions ICT** — {session_count} sessions")
        
        if sessions:
            for i, session in enumerate(sessions[:3], 1):
                session_name = session.get("name", "Session")
                session_low = session.get("low", 0)
                session_high = session.get("high", 0)
                session_range = (session_high - session_low) / session_low * 100 if session_low > 0 else 0
                
                with st.container(border=True):
                    st.markdown(
                        f"**📌 [{i}] {session_name}**\n"
                        f"• Range: `{session_low:.4f}` → `{session_high:.4f}`\n"
                        f"• Amplitude: **+{session_range:.2f}%**\n"
                        f"• Type: {session.get('type', 'ICT Session')}"
                    )
        else:
            st.info("Aucune session spécifique détectée")
        
        st.markdown("---")
        
        # DOL avec plus de détails
        dol = tf_data.get("dol", {})
        st.markdown("**🎲 Delivery Opening Level (DOL)**")
        if dol and dol.get("target_price"):
            dol_price = dol.get("target_price", 0)
            dol_direction = dol.get("direction", "UNKNOWN")
            dol_strength = dol.get("strength", "Normal")
            icon = "📈" if dol_direction == "BULLISH" else "📉"
            
            with st.container(border=True):
                st.markdown(
                    f"{icon} **Direction**: {dol_direction}\n"
                    f"💰 **Price Target**: `{dol_price:.4f}`\n"
                    f"🔥 **Strength**: {dol_strength}\n"
                    f"📊 **Type**: {dol.get('type', 'Standard DOL')}"
                )
        else:
            st.warning("❌ Pas de DOL significatif détecté")
        
        st.markdown("---")
        
        # Confluences avec détails
        confluences = tf_data.get("confluences", [])
        conf_count = len(confluences) if isinstance(confluences, list) else 0
        st.markdown(f"**🎯 Confluences Actives** — {conf_count} niveaux")
        
        if confluences:
            for i, conf in enumerate(confluences[:5], 1):
                conf_price = conf.get("price", 0)
                conf_type = conf.get("type", "Unknown")
                confluence_strength = conf.get("strength", 1)
                
                st.markdown(
                    f"  **[{i}]** `{conf_price:.4f}` — "
                    f"**{conf_type}** "
                    f"({'🔴' * min(int(confluence_strength), 5) if confluence_strength else '⚪'})"
                )
        else:
            st.info("✅ Pas de confluences détectées (marché limpide)")
    
    # ── ANALYSE DÉTAILLÉE PAR TIMEFRAME ──────────────────────────
    st.markdown("---")
    st.markdown("## � TABLEAU COMPARATIF — Tous les Timeframes")
    
    # Construire un dataframe de comparaison
    comparison_data = []
    for tf in PYRAMID_ORDER:
        tf_detail = tf_details.get(tf, {})
        comparison_data.append({
            "🎯 TF": f"**{tf}**",
            "📈 Score": f"{tf_detail.get('score', 0)}/100",
            "🔍 Direction": tf_detail.get("direction", "N/A"),
            "🎯 Conf.": len(tf_detail.get("confluences", [])),
            "📊 FVG": _get_count(tf_detail.get("fvg_count", 0)),
            "🎪 OB": _get_count(tf_detail.get("ob_count", 0)),
            "💰 RR": f"{tf_detail.get('rr', 0):.2f}x" if tf_detail.get('rr', 0) > 0 else "---"
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, width="stretch", hide_index=True, use_container_width=True)
    
    # ── STATISTIQUES GLOBALES ──────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🔢 STATISTIQUES GLOBALES")
    
    stats_col1, stats_col2, stats_col3, stats_col4, stats_col5 = st.columns(5)
    
    # Calculer stats globales
    total_scores = sum(_get_count(tf_details.get(tf, {}).get("score", 0)) for tf in PYRAMID_ORDER)
    avg_score = total_scores / len(PYRAMID_ORDER) if PYRAMID_ORDER else 0
    
    bullish_count = sum(1 for tf in PYRAMID_ORDER if tf_details.get(tf, {}).get("direction") == "BULLISH")
    bearish_count = sum(1 for tf in PYRAMID_ORDER if tf_details.get(tf, {}).get("direction") == "BEARISH")
    
    total_fvgs_all = sum(_get_count(tf_details.get(tf, {}).get("fvg_count", 0)) for tf in PYRAMID_ORDER)
    total_obs_all = sum(_get_count(tf_details.get(tf, {}).get("ob_count", 0)) for tf in PYRAMID_ORDER)
    total_confluences_all = len(kb5_result.get("confluences", []))
    
    with stats_col1:
        st.metric("📊 Score Moyen", f"{avg_score:.1f}")
    with stats_col2:
        st.metric("📈 Bullish TF", f"{bullish_count}/{len(PYRAMID_ORDER)}")
    with stats_col3:
        st.metric("📉 Bearish TF", f"{bearish_count}/{len(PYRAMID_ORDER)}")
    with stats_col4:
        st.metric("🔄 Total Structures", f"{total_fvgs_all + total_obs_all}")
    with stats_col5:
        st.metric("🎯 Confluences", total_confluences_all)
    
    # ── ANALYSE DÉTAILLÉE PAR TIMEFRAME ──────────────────────────
    st.markdown("---")
    st.markdown("## 📋 Détails Expandables — Tous les Timeframes")
    st.markdown("*Cliquez pour voir les détails*")
    
    # Afficher 2 colonnes par ligne pour chaque TF
    for i in range(0, len(PYRAMID_ORDER), 2):
        cols = st.columns(2)
        
        for col_idx, col in enumerate(cols):
            tf_idx = i + col_idx
            if tf_idx >= len(PYRAMID_ORDER):
                break
                
            tf = PYRAMID_ORDER[tf_idx]
            tf_data = tf_details.get(tf, {})
            tf_score = tf_data.get("score", 0)
            components = tf_data.get("components", {})
            
            with col:
                st.markdown(f"### 📊 **{tf}**")
                
                # Afficher 3 metrics
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric(
                        "Score",
                        f"{tf_score}/100",
                        delta=None
                    )
                with m2:
                    direction = tf_data.get("direction", "NEUTRAL")
                    icon = "📈" if direction == "BULLISH" else "📉" if direction == "BEARISH" else "➡️"
                    st.metric(f"{icon} Direction", direction)
                with m3:
                    rr = tf_data.get("rr", 0)
                    st.metric("RR", f"{rr:.2f}x" if rr > 0 else "---")
                
                # Bouton pour expandable details
                with st.expander(f"🔍 Détails Complets {tf}", expanded=False):
                    st.markdown("#### 🎯 Composants du Score")
                    
                    # Score breakdown
                    if components:
                        comp_col1, comp_col2, comp_col3, comp_col4 = st.columns(4)
                        with comp_col1:
                            st.metric("FVG", f"{components.get('fvg', 0)} pts")
                        with comp_col2:
                            st.metric("OB", f"{components.get('ob', 0)} pts")
                        with comp_col3:
                            st.metric("Structure", f"{components.get('structure', 0)} pts")
                        with comp_col4:
                            st.metric("SMT", f"{components.get('smt', 0)} pts")
                    
                    st.markdown("---")
                    st.markdown("#### 📈 Structures Détectées")
                    
                    # FVG Details
                    st.write("**Fair Value Gaps (FVG)**")
                    fvg_list = tf_data.get("fvgs", [])
                    fvg_count = _get_count(tf_data.get("fvg_count", 0))
                    if fvg_count > 0 or fvg_list:
                        st.write(f"  • Détectés: **{max(fvg_count, len(fvg_list))}**")
                        if fvg_list:
                            for fvg in fvg_list[:3]:
                                direction_icon = "📈" if fvg.get("direction") == "BULLISH" else "📉"
                                st.write(f"    {direction_icon} {fvg.get('quality', 'Normal').upper()}")
                    else:
                        st.write("  • Aucun FVG détecté")
                    
                    # OB Details
                    st.write("\n**Order Blocks (OB)**")
                    ob_list = tf_data.get("order_blocks", [])
                    ob_count = _get_count(tf_data.get("ob_count", 0))
                    if ob_count > 0 or ob_list:
                        st.write(f"  • Détectés: **{max(ob_count, len(ob_list))}**")
                        if ob_list:
                            for ob in ob_list[:3]:
                                status = "✅" if ob.get("status") == "VALID" else "⚠️"
                                st.write(f"    {status} {ob.get('quality', 'Normal').upper()} - {ob.get('status', '?')}")
                    else:
                        st.write("  • Aucun OB détecté")
                    
                    st.markdown("---")
                    st.markdown("#### 🎪 Confluences")
                    
                    conf_list = tf_data.get("confluences", [])
                    if conf_list:
                        st.write(f"  **{len(conf_list)} confluences actives**")
                        for conf in conf_list[:5]:
                            st.write(f"  • {conf.get('name', '?')} (+{conf.get('bonus', conf.get('score', 0))} pts)")
                    else:
                        st.write("  Aucune confluence pour ce TF")
                    
                    st.markdown("---")
                    st.markdown("#### 💧 Zones de Liquidité")
                    
                    liq_data = tf_data.get("liquidity", {})
                    if liq_data:
                        for level, price in liq_data.items():
                            price_val = price if isinstance(price, (int, float)) else price.get("price", "?")
                            st.write(f"  • **{level}**: {price_val}")
                    else:
                        st.write("  Pas de données de liquidité pour ce TF")

    st.subheader("🎯 Confluences Actives")
    
    confluences = kb5_result.get("confluences", [])
    if not confluences:
        st.info("❌ Aucune confluence majeure à afficher")
    else:
        # Afficher les confluences dans des colonnes
        cols_conf = st.columns(min(3, len(confluences)))
        for i, conf in enumerate(confluences[:6]):
            with cols_conf[i % len(cols_conf)]:
                bonus = conf.get("bonus", conf.get("score", 0))
                name = conf.get("name", "?")
                st.success(f"✅ **{name}**\n+{bonus} pts")
        
        # Afficher la liste complète
        if len(confluences) > 6:
            with st.expander(f"📋 Voir toutes les confluences ({len(confluences)})"):
                for conf in confluences:
                    st.write(f"• {conf.get('name', '?')} — +{conf.get('bonus', conf.get('score', 0))} pts")

@st.fragment(run_every=REFRESH_INTERVAL)
def render_tab2_live():
    cache.load_from_disk()  # Sync avec le moteur
    outputs = cache.get("recent_outputs", [])
    
    # Rendre TOUJOURS le dataframe pour stabiliser le DOM React
    if not outputs:
        empty_df = pd.DataFrame(columns=["Paire", "Verdict", "Score", "Direction", "Détails"])
        st.dataframe(empty_df, width="stretch", hide_index=True, key="scalp_outputs_table")
    else:
        # Extraire les infos clés pour un tableau propre au lieu de gros expanders JSON
        clean_outputs = []
        for out in outputs:
            clean_outputs.append({
                "Paire": out.get("pair", "?"),
                "Verdict": out.get("verdict", "?"),
                "Score": f"{out.get('score', 0)}/100",
                "Direction": out.get("direction", "?"),
                "Détails": str(out.get("confluences_count", 0)) + " confluences"
            })
        out_df = pd.DataFrame(clean_outputs)
        st.dataframe(out_df, width="stretch", hide_index=True, key="scalp_outputs_table")

def render_tab3_stats():
    perf_mem._load()  # Recharger la mémoire de performance depuis disque
    col1, col2 = st.columns(2)
    with col1:
        stats = journal.get_stats()
        st.metric("Total trades", stats.get("total", 0))
        st.metric("Winrate", f"{stats.get('winrate', 0):.1f}%")
        st.metric("Erreurs évitables", stats.get("errors", {}).get("UNKNOWN", 0))
    
    with col2:
        regret_rate = failure_lab.get_regret_rate()
        st.metric("Regret Rate", f"{regret_rate:.1%}")
        snapshot = perf_mem.get_snapshot()
        st.metric("Malus actifs", snapshot.get("malus_count", 0))
    
    st.subheader("Top erreurs récentes")
    errors = journal.get_stats().get("errors", {})
    if errors:
        df_errors = pd.DataFrame([{"Erreur": k, "Count": v} for k, v in errors.items()]).sort_values("Count", ascending=False)
        st.bar_chart(df_errors.set_index("Erreur"))
    else:
        st.info("Aucune erreur enregistrée.")

# ── Rendu de la page principale ──

render_live_header()
st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📊 Analyse ICT", "⚡ Scalp Output", "📚 Stats", "🔧 Contrôles", "⚙️ Paramètres", "🔍 DIAGNOSTIC"]
)

with tab1:
    st.header(f"🎯 Analyse {selected_pair}")
    if force_refresh:
        st.rerun()
        
    render_tab1_live(selected_pair)
    
    # ── NARRATIF IA EXPERT (HORS FRAGMENT) ──
    st.markdown("---")
    st.markdown("### 🧠 Narratif Expert IA")
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("✨ Générer l'Analyse IA", width="stretch"):
            st.session_state[f"ai_narrative_{selected_pair}"] = "GENERATING"
            
    narrative_key = f"ai_narrative_{selected_pair}"
    if narrative_key in st.session_state:
        if st.session_state[narrative_key] == "GENERATING":
            with st.spinner("Analyse approfondie en cours par l'IA..."):
                state = cache.get(selected_pair, {})
                kb5_result = state.get("kb5_result", {})
                scoring_output = state.get("scoring_output", {})
                llm_conf = settings.get_llm_config()
                narrative = generate_narrative(
                    llm_provider=llm_conf["llm_provider"],
                    api_key=llm_conf["llm_api_key"],
                    pair=selected_pair,
                    kb5_result=kb5_result,
                    scoring_output=scoring_output
                )
                st.session_state[narrative_key] = narrative
            st.rerun()
        else:
            st.info(st.session_state[narrative_key], icon="🤖")

with tab2:
    st.header("⚡ Derniers Scalp Outputs")
    render_tab2_live()

with tab3:
    st.header("📚 Statistiques")
    render_tab3_stats()

with tab4:
    st.header("🔧 Contrôles avancés")

    # ── Statut Circuit Breaker ──
    st.markdown("### ⚡ Circuit Breaker")
    # Lire l'état CB directement depuis le fichier DataStore (pas le MarketStateCache)
    _cb_state = {"level": 0, "status": "CB_CLEAR", "pct_drop": 0.0}
    _ds_path = Path("data/datastore_state.json")
    if _ds_path.exists():
        try:
            with open(_ds_path, "r", encoding="utf-8") as _f:
                _ds_data = json.load(_f)
            _cb_state = _ds_data.get("cb_state", _cb_state)
        except Exception:
            pass

    cb_level = _cb_state.get("level", 0)
    cb_name  = _cb_state.get("status", "CB_CLEAR")
    cb_dd    = _cb_state.get("pct_drop", 0.0)
    cb_labels = {0: "🟢 CB0 — NOMINAL", 1: "🟡 CB1 — WARNING", 2: "🟠 CB2 — PAUSE", 3: "🔴 CB3 — HALT"}
    cb_col1, cb_col2 = st.columns([2, 1])
    with cb_col1:
        st.metric("Niveau Circuit Breaker", cb_labels.get(cb_level, f"CB{cb_level} {cb_name}"), f"DD : {cb_dd:.2f}%")
    with cb_col2:
        if cb_level >= 2:
            st.warning("⚠️ CB en mode HALT — aucun trade autorisé.")
            if st.button("🔓 Réinitialiser Circuit Breaker", type="primary"):
                # Écrire le reset dans le fichier DataStore — le moteur relira au prochain cycle
                if _ds_path.exists():
                    try:
                        with open(_ds_path, "r", encoding="utf-8") as _f:
                            _ds_reset = json.load(_f)
                        _ds_reset["cb_state"] = {"level": 0, "status": "CB_CLEAR", "pct_drop": 0.0, "triggered_at": None}
                        with open(_ds_path, "w", encoding="utf-8") as _f:
                            json.dump(_ds_reset, _f, indent=2)
                    except Exception as e:
                        st.error(f"Erreur reset CB : {e}")
                st.success("✅ Circuit Breaker réinitialisé à CB0 NOMINAL. Le bot reprendra au prochain cycle.")
                st.rerun()
        else:
            st.success("Circuit Breaker OK — trading autorisé")


    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 Vider cache"):
            cache.clear()
            st.success("Cache vidé !")
            st.rerun()
        if st.button("📊 Autopsie quotidienne"):
            report = failure_lab.run_daily_autopsy()
            st.json(report)
    with col2:
        if notifier and st.button("📱 Test Telegram"):
            notifier.send_execute({"pair": "EURUSD", "score": 85, "verdict": "EXECUTE"})
            st.success("Test Telegram envoyé !")
        if st.button("🔄 Reset Performance Memory"):
            perf_mem.reset()
            st.success("Mémoire performance reset !")

with tab5:
    render_settings_panel(settings)

with tab6:
    st.header("🔍 DIAGNOSTIC & DONNÉES COMPLÈTES")
    st.markdown("*Affiche TOUT ce que le bot analyse — toutes les étapes, tous les détecteurs*")
    
    cache.load_from_disk()
    state = cache.get(selected_pair, {})
    kb5_result = state.get("kb5_result", {}) if state else {}
    scoring_output = state.get("scoring_output", {}) if state else {}
    
    # ── SECTION 1: RÉSUMÉ DES ANALYSES ──
    st.markdown("### 📋 Résumé des Analyses Effectuées")
    
    diag_col1, diag_col2, diag_col3, diag_col4, diag_col5 = st.columns(5)
    with diag_col1:
        st.metric("📊 KB5 Score", kb5_result.get("final_score", "N/A"), "/100")
    with diag_col2:
        st.metric("🎯 Direction", kb5_result.get("direction", "N/A"))
    with diag_col3:
        st.metric("✅ Verdict", scoring_output.get("verdict", "N/A"))
    with diag_col4:
        confluences_count = len(kb5_result.get("confluences", []))
        st.metric("🎪 Confluences", confluences_count)
    with diag_col5:
        timestamp = kb5_result.get("timestamp", "N/A")
        if timestamp and "T" in str(timestamp):
            time_display = timestamp.split("T")[1][:8]
        else:
            time_display = "N/A"
        st.metric("⏰ Analysé à", time_display)
    
    # ── SECTION 2: PYRAMIDE DES SCORES ──
    st.markdown("---")
    st.markdown("### 📈 Pyramide de Scores (MN→W1→D1→H4→H1→M15→M5→M1)")
    
    pyramid_scores = kb5_result.get("pyramid_scores", {})
    tf_details_data = kb5_result.get("tf_details", {})
    
    pyramid_cols = st.columns(len(PYRAMID_ORDER))
    for i, tf in enumerate(PYRAMID_ORDER):
        with pyramid_cols[i]:
            score = pyramid_scores.get(tf, 0)
            tf_direction = tf_details_data.get(tf, {}).get("direction", "?")
            dir_emoji = "📈" if tf_direction == "BULLISH" else "📉" if tf_direction == "BEARISH" else "➡️"
            
            color = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"
            st.metric(
                f"{tf}",
                f"{score}/100",
                delta=f"{dir_emoji} {tf_direction}",
            )
            st.caption(f"{color} Score")
    
    # ── SECTION 3: DÉTECTEURS ACTIFS ──
    st.markdown("---")
    st.markdown("### 🔍 Détecteurs Actifs & Structures Détectées")
    
    det_col1, det_col2 = st.columns(2)
    
    with det_col1:
        st.markdown("#### 📊 **Structures ICT**")
        
        fvgs = kb5_result.get("fvgs", [])
        fvg_count = len(fvgs) if isinstance(fvgs, list) else 0
        st.markdown(f"✅ **FVG Detector** — {fvg_count} détectés")
        if fvgs:
            for fvg in fvgs[:3]:
                st.write(f"  • {fvg.get('direction', '?')} {fvg.get('quality', '?')} @ {fvg.get('low', 0):.4f}-{fvg.get('high', 0):.4f}")
        
        obs = kb5_result.get("order_blocks", [])
        ob_count = len(obs) if isinstance(obs, list) else 0
        st.markdown(f"✅ **OB Detector** — {ob_count} détectés")
        if obs:
            for ob in obs[:3]:
                st.write(f"  • {ob.get('status', '?')} [{ob.get('quality', '?')}] @ {ob.get('low', 0):.4f}-{ob.get('high', 0):.4f}")
        
        liquidity = kb5_result.get("liquidity", {})
        liq_count = len(liquidity) if isinstance(liquidity, dict) else 0
        st.markdown(f"✅ **Liquidity Detector** — {liq_count} zones")
        if isinstance(liquidity, dict):
            for level, data in list(liquidity.items())[:3]:
                price = data.get("price", 0) if isinstance(data, dict) else data
                st.write(f"  • {level}: {price:.4f}")
    
    with det_col2:
        st.markdown("#### 🎪 **Smart Money Concepts**")
        
        smt_data = kb5_result.get("smt", {})
        has_choch = smt_data.get("has_choch", False) if isinstance(smt_data, dict) else False
        has_mss = smt_data.get("has_mss", False) if isinstance(smt_data, dict) else False
        
        st.markdown(f"✅ **SMT Detector**")
        st.write(f"  • CHoCH: {'✅ ACTIF' if has_choch else '❌ inactif'}")
        st.write(f"  • MSS: {'✅ ACTIF' if has_mss else '❌ inactif'}")
        
        choch_detector = (
            f"  • Changement structurel: {'Confirmé' if has_choch else 'Non confirmé'}"
        )
        st.write(choch_detector)
        
        st.markdown(f"✅ **Sessions Detector**")
        sessions = kb5_result.get("sessions", [])
        session_count = len(sessions) if isinstance(sessions, list) else 0
        st.write(f"  • Sessions actives: {session_count}")
        
        st.markdown(f"✅ **Bias Detector**")
        bias_score = kb5_result.get("bias_score", 0)
        bias_aligned = kb5_result.get("bias_aligned", False)
        st.write(f"  • Score biais: {bias_score}")
        st.write(f"  • Aligné: {'✅ OUI' if bias_aligned else '❌ NON'}")
    
    # ── SECTION 4: CONFLUENCES DÉTAILLÉES ──
    st.markdown("---")
    st.markdown("### 🎯 Confluences Détectées (Bonus de Score)")
    
    confluences = kb5_result.get("confluences", [])
    if confluences:
        conf_df_data = []
        for conf in confluences:
            conf_df_data.append({
                "Nom": conf.get("name", "?"),
                "Bonus": f"+{conf.get('bonus', conf.get('score', 0))} pts",
                "Description": conf.get("description", ""),
            })
        conf_df = pd.DataFrame(conf_df_data)
        st.dataframe(conf_df, width="stretch", hide_index=True)
    else:
        st.info("Aucune confluence détectée")
    
    # ── SECTION 5: ENTRY MODEL ──
    st.markdown("---")
    st.markdown("### 💰 Entry Model Calculé")
    
    entry_model = kb5_result.get("entry_model", {})
    entry_cols = st.columns(5)
    
    with entry_cols[0]:
        st.metric("Entry", f"{entry_model.get('entry_price', 0):.4f}")
    with entry_cols[1]:
        st.metric("SL", f"{entry_model.get('sl', 0):.4f}")
    with entry_cols[2]:
        st.metric("TP", f"{entry_model.get('tp', 0):.4f}")
    with entry_cols[3]:
        rr = entry_model.get("rr", 0)
        st.metric("RR", f"{rr:.2f}x" if rr > 0 else "N/A")
    with entry_cols[4]:
        invalidation = kb5_result.get("invalidation", {})
        inv_price = invalidation.get("price", 0) if isinstance(invalidation, dict) else 0
        st.metric("Invalidation", f"{inv_price:.4f}" if inv_price > 0 else "N/A")
    
    # ── SECTION 6: DONNÉES JSON BRUTES ──
    st.markdown("---")
    st.markdown("### 📄 Données JSON Brutes (Debug)")
    
    json_view_tab1, json_view_tab2 = st.tabs(["KB5 Result", "Scoring Output"])
    
    with json_view_tab1:
        st.json(kb5_result if kb5_result else {"status": "Aucune donnée KB5 disponible"})
    
    with json_view_tab2:
        st.json(scoring_output if scoring_output else {"status": "Aucune donnée Scoring disponible"})
    
    # ── SECTION BONUS: STRUCTURE DES DONNÉES (DEBUG) ──
    st.markdown("---")
    st.markdown("#### 🔧 Structure des Données Cache (DEBUG)")
    
    debug_col1, debug_col2 = st.columns(2)
    
    with debug_col1:
        st.markdown("**Type de state.candles**")
        state_candles_type = type(state.get("candles", {})).__name__
        st.code(f"Type: {state_candles_type}", language="text")
        
        if isinstance(state.get("candles", {}), dict):
            st.markdown("**Clés de candles (par TF)**")
            candles_keys = list(state.get("candles", {}).keys())
            st.write(f"Timeframes disponibles: {candles_keys}")
        else:
            st.markdown("**Candles: structure LIST (global)**")
            st.write(f"Nombre de bougies: {len(state.get('candles', []))}")
    
    with debug_col2:
        st.markdown("**Vérification tf_details**")
        if kb5_result.get("tf_details"):
            st.success(f"✅ tf_details existe ({len(kb5_result.get('tf_details', {}))} TF)")
            for tf in PYRAMID_ORDER:
                if tf in kb5_result.get("tf_details", {}):
                    tf_detail = kb5_result["tf_details"][tf]
                    fvg_c = len(tf_detail.get("fvgs", []))
                    ob_c = len(tf_detail.get("order_blocks", []))
                    st.caption(f"  {tf}: {fvg_c} FVG, {ob_c} OB")
        else:
            st.error("❌ tf_details MANQUANT!")
    
    # ── SECTION 7: HISTORIQUE DES CHANGEMENTS ──
    st.markdown("---")
    st.markdown("### 📊 Suivi en Temps Réel (Toutes les 5 Secondes)")
    st.markdown("*Les données se mettent à jour automatiquement — observez les changements de score, direction, confluences*")
    
    st.warning(
        "💡 **Conseil**: Gardez cet onglet ouvert pour monitorer les changements en temps réel. "
        "Si le score ou la direction change, vous le verrez ici immédiatement.",
        icon="💡"
    )
    
    # Bouton pour forcer réanalyse
    force_col1, force_col2 = st.columns([3, 1])
    with force_col2:
        if st.button("🔄 Réanalyser maintenant"):
            st.info("✅ Réanalyse demandée — vérifiez le pipeline du supervisor")
    
    with force_col1:
        # Afficher le timestamp de dernière analyse
        last_ts = kb5_result.get("timestamp", "N/A")
        if last_ts and "T" in str(last_ts):
            ts_formatted = last_ts.split(".")[0].replace("T", " @ ")
        else:
            ts_formatted = "N/A"
        st.caption(f"⏰ Dernière analyse: {ts_formatted} UTC")
    
    # Afficher les métriques clés qui pourraient changer
    st.markdown("#### 🎯 Métriques Clés en Suivi")
    
    metric_row1 = st.columns(4)
    
    with metric_row1[0]:
        score_val = kb5_result.get("final_score", 0)
        st.metric(
            "Score ICT",
            f"{score_val}/100",
            delta="🔄 Suivi temps réel",
            delta_color="off"
        )
    
    with metric_row1[1]:
        direction_val = kb5_result.get("direction", "NEUTRAL")
        dir_icon = "📈" if direction_val == "BULLISH" else "📉" if direction_val == "BEARISH" else "➡️"
        st.metric(
            "Direction",
            f"{dir_icon} {direction_val}",
            delta="Pyramide ICT",
            delta_color="off"
        )
    
    with metric_row1[2]:
        conf_count = len(kb5_result.get("confluences", []))
        st.metric(
            "Confluences Actives",
            conf_count,
            delta="Bonus en pts",
            delta_color="off"
        )
    
    with metric_row1[3]:
        bias_aligned = kb5_result.get("bias_aligned", False)
        bias_icon = "✅" if bias_aligned else "❌"
        st.metric(
            "Biais Aligné",
            f"{bias_icon}",
            delta=f"Score biais: {kb5_result.get('bias_score', 0)}",
            delta_color="off"
        )
    
    # Afficher les scores TF importants
    st.markdown("#### 📊 Scores par Timeframe (Suivi)")
    
    tf_scores = kb5_result.get("pyramid_scores", {})
    important_tfs = ["W1", "D1", "H4", "H1"]
    
    important_tfs_cols = st.columns(len(important_tfs))
    for i, tf in enumerate(important_tfs):
        with important_tfs_cols[i]:
            score_tf = tf_scores.get(tf, 0)
            color = "🟢" if score_tf >= 70 else "🟡" if score_tf >= 50 else "🔴"
            st.metric(
                f"{tf}",
                f"{color} {score_tf}/100",
                delta=None
            )
    
    # Afficher les structures majeures
    st.markdown("#### 🔍 Structures Majeures")
    
    struct_row1 = st.columns(3)
    
    with struct_row1[0]:
        fvgs = kb5_result.get("fvgs", [])
        fvg_bullish = sum(1 for f in fvgs if f.get("direction") == "BULLISH")
        fvg_bearish = sum(1 for f in fvgs if f.get("direction") == "BEARISH")
        st.markdown(
            f"**📊 Fair Value Gaps**\n"
            f"• Bullish: {fvg_bullish}\n"
            f"• Bearish: {fvg_bearish}\n"
            f"• Total: {len(fvgs)}"
        )
    
    with struct_row1[1]:
        obs = kb5_result.get("order_blocks", [])
        ob_valid = sum(1 for ob in obs if ob.get("status") == "VALID")
        st.markdown(
            f"**🎯 Order Blocks**\n"
            f"• Valides: {ob_valid}\n"
            f"• Total: {len(obs)}"
        )
    
    with struct_row1[2]:
        sessions = kb5_result.get("sessions", [])
        smt_data = kb5_result.get("smt", {})
        choch = smt_data.get("has_choch", False) if isinstance(smt_data, dict) else False
        st.markdown(
            f"**🎪 Smart Money**\n"
            f"• Sessions: {len(sessions)}\n"
            f"• CHoCH: {'✅ Actif' if choch else '❌ Inactif'}"
        )
    
    st.markdown("---")
    st.markdown("#### 📝 Notes")
    st.info(
        "Les données affichées ici se rafraîchissent toutes les **5 secondes**. "
        "Le bot réanalyse continuellement toutes les paires et tous les timeframes. "
        "Si les conditions du marché changent, les scores et confluences se mettront à jour automatiquement."
    )

st.markdown("---")
@st.fragment(run_every=REFRESH_INTERVAL)
def render_footer():
    st.caption(f"🕐 Dernière mise à jour live : {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")

render_footer()

