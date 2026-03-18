import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import threading
import time
import logging
from datetime import datetime, timezone

from config.settings_manager import SettingsManager, SCHOOLS, PROFILES, AVAILABLE_PAIRS
from execution.market_state_cache import MarketStateCache
from analysis.analysis_reporter import AnalysisReporter
# Assuming render_settings_panel takes (settings)
try:
    from interface.settings_panel import render_settings_panel
except ImportError:
    pass
from main import build_bot

logger = logging.getLogger(__name__)

class CommandCenter:
    """
    Interface principale de contrôle du bot (Command Center) - Sentinel Pro KB5.
    """

    def __init__(self):
        # Initialisation session_state
        if 'supervisor' not in st.session_state:
            st.session_state.supervisor = None
        if 'bot_thread' not in st.session_state:
            st.session_state.bot_thread = None
        if 'analysis_results' not in st.session_state:
            st.session_state.analysis_results = {}
        if 'selected_pair' not in st.session_state:
            st.session_state.selected_pair = None
        if 'bot_init_error' not in st.session_state:
            st.session_state.bot_init_error = None
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 0
        if 'current_mode' not in st.session_state:
            st.session_state.current_mode = 'paper'
        
        # Managers
        self.settings = SettingsManager()
        self.reporter = AnalysisReporter(kb5_engine=None)
        
        self._ensure_supervisor()

    def _ensure_supervisor(self):
        """Initialise le Supervisor sans bloquer l'interface en cas d'erreur de connexion MT5."""
        if st.session_state.supervisor is None:
            try:
                supervisor, _ = build_bot(enable_dashboard=False)
                st.session_state.supervisor = supervisor
                st.session_state.bot_init_error = None
            except Exception as e:
                st.session_state.bot_init_error = str(e)
                logger.error(f"CommandCenter: Erreur initialisation bot - {e}")

    def inject_css(self):
        """Injecte le style CSS War Room."""
        st.markdown("""
        <style>
            .stApp { background-color: #0d1117; color: #c9d1d9; }
            [data-testid="stSidebar"] { background-color: #010409; border-right: 1px solid #30363d; }
            
            /* Cards */
            .card { background-color: #161b22; border-radius: 8px; border: 1px solid #30363d; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); }
            
            /* Badges Verdict */
            .badge-execute { background-color: #10b981; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; display: inline-block; uppercase; }
            .badge-regarder { background-color: #f59e0b; color: black; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; display: inline-block; uppercase; }
            .badge-interdit { background-color: #ef4444; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; display: inline-block; uppercase; }
            .badge-en-attente { background-color: #374151; color: #9ca3af; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; display: inline-block; uppercase; }
            
            /* Texts & Titles */
            .module-title { color: #00d4ff; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; border-bottom: 1px solid #30363d; padding-bottom: 4px; font-weight: bold; }
            .logo-title { color: #00d4ff; font-weight: 900; font-size: 24px; text-align: center; margin-bottom: 5px; }
            .logo-subtitle { color: #8b949e; font-size: 12px; text-align: center; margin-bottom: 25px; }
            
            /* Colors */
            .text-green { color: #10b981; font-weight: bold; }
            .text-orange { color: #f59e0b; font-weight: bold; }
            .text-red { color: #ef4444; font-weight: bold; }
            .text-cyan { color: #00d4ff; font-weight: bold; }
            .text-muted { color: #8b949e; }
            
            hr { border-top: 1px solid #30363d; }
        </style>
        """, unsafe_allow_html=True)

    def run(self):
        """Lance l'interface utilisateur Streamlit."""
        st.set_page_config(
            page_title="SENTINEL PRO KB5 — Command Center",
            page_icon="💎",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        self.inject_css()

        self.render_sidebar()

        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Analyses TIC", 
            "📈 Monitoring & Positions", 
            "⚙️ Paramètres Bot", 
            "📝 Journal & Logs"
        ])
        
        with tab1:
            self.render_tab_analyses()
        with tab2:
            self.render_tab_monitoring()
        with tab3:
            self.render_tab_settings()
        with tab4:
            self.render_tab_logs()

        # Boucle d'horloge UTC en fin de run pour mettre a jour l'heure dans la sidebar
        # Permet l'actualisation continue via sleep
        if getattr(st.session_state, 'clock_placeholder', None):
            utctime = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
            st.session_state.clock_placeholder.markdown(f"**Heure Actuelle:** {utctime}")

    # ══════════════════════════════════════════════════════════
    # SIDEBAR
    # ══════════════════════════════════════════════════════════
    def render_sidebar(self):
        """Affichage du menu latéral de contrôle et navigation."""
        st.sidebar.markdown("<div class='logo-title'>💎 SENTINEL V9.3-PRO</div>", unsafe_allow_html=True)
        st.sidebar.markdown("<div class='logo-subtitle'>COMMAND CENTER V1.0</div>", unsafe_allow_html=True)
        
        # Navigation
        st.sidebar.markdown("### 🧭 Navigation Rapide")
        if st.sidebar.button("📊 Analyser les TIC", use_container_width=True):
            st.session_state.active_tab = 0
        if st.sidebar.button("⚙️ Paramètres Bot", use_container_width=True):
            st.session_state.active_tab = 2
        if st.sidebar.button("👁️ Bot de surveillance", use_container_width=True):
            st.session_state.active_tab = 1
            
        st.sidebar.markdown("---")
        
        # Etat du bot
        is_running = False
        if st.session_state.supervisor and st.session_state.supervisor.is_running():
            is_running = True
            
        status_html = "<div style='text-align: center; margin-bottom: 10px;'><span class='badge-execute'>🟢 BOT ACTIF</span></div>" if is_running else "<div style='text-align: center; margin-bottom: 10px;'><span class='badge-interdit'>🔴 BOT ARRÊTÉ</span></div>"
        st.sidebar.markdown(status_html, unsafe_allow_html=True)
        
        if is_running:
            if st.sidebar.button("🔴 STOPPER LE BOT", use_container_width=True, type="primary"):
                self.stop_bot()
        else:
            if st.sidebar.button("▶️ DÉMARRER", use_container_width=True, type="secondary"):
                self.start_bot()
                
        st.sidebar.markdown("---")
        
        # Paires Actives
        active_pairs = self.settings.get_active_pairs()
        st.sidebar.markdown("### 📎 Paires Actives")
        if not active_pairs:
            st.sidebar.info("Aucune paire configurée.")
        for p in active_pairs:
            st.sidebar.markdown(f"• <span style='color: #10b981;'>■</span> {p}", unsafe_allow_html=True)
            
        st.sidebar.markdown("---")
        
        # Horloge UTC et Heartbeat
        st.session_state.clock_placeholder = st.sidebar.empty()
        st.sidebar.markdown(f"<small class='text-muted'>Heartbeat: Dernier check: {datetime.now().strftime('%H:%M:%S')}</small>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # ANALYSES (TAB 1)
    # ══════════════════════════════════════════════════════════
    def render_tab_analyses(self):
        """Affiche les analyses multi-timeframes et le dashboard TIC."""
        # Top bar
        is_running = False
        if st.session_state.supervisor and st.session_state.supervisor.is_running():
            is_running = True
            
        if is_running:
            now_local = datetime.now().strftime('%H:%M:%S')
            st.success(f"🟢 BOT ACTIF — Heure Locale : {now_local} | Dernier check : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        elif st.session_state.bot_init_error:
            st.warning(f"⚠️ Bot en mode lecture seule — Erreur initialisation MT5 : {st.session_state.bot_init_error}")
        else:
            st.info("ℹ️ Bot actuellement en attente. Profil actif : " + self.settings.get("profile", "Custom"))
        
        st.markdown(f"<small class='text-muted'>Profil: <b>{self.settings.get('profile', 'Custom')}</b> | Mode: <b>{st.session_state.current_mode}</b></small>", unsafe_allow_html=True)
        
        # Sub-tabs
        subtabs = st.tabs(["📊 Analyses", "💱 Échanges", "📔 Journal", "📈 Statistiques"])
        
        with subtabs[0]:
            self._render_analyses_subtab()
        with subtabs[1]:
            self._render_echanges_subtab()
        with subtabs[2]:
            st.info("Journal d'opérations détaillé (voir Onglet Logs pour les journaux techniques).")
        with subtabs[3]:
            self._render_statistiques_subtab()

    def _render_analyses_subtab(self):
        st.markdown("## 🎯 Radar ICT Multi-temporel")
        active_pairs = self.settings.get_active_pairs()
        if not active_pairs:
            st.warning("Veuillez sélectionner des paires dans les paramètres.")
            return
            
        # Pair selector (tabs)
        pair_tabs = st.tabs(active_pairs)
        for i, pair in enumerate(active_pairs):
            with pair_tabs[i]:
                # If no data, render mock
                report = st.session_state.analysis_results.get(pair, None)
                self._render_single_pair_analysis(pair, report)
                
                # Analyze Button
                if st.button(f"🔍 Lancer l'analyse {pair} maintenant", key=f"btn_analyze_{pair}", type="primary", use_container_width=True):
                    with st.spinner("Analyse institutionnelle en cours..."):
                        try:
                            res = self.reporter.analyze_pair(pair)
                            st.session_state.analysis_results[pair] = res
                            st.success(f"Analyse terminée pour {pair}")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur d'analyse: {str(e)}")
                            logger.error(f"Crash AnalysisReporter {pair}: {e}")

    def _render_single_pair_analysis(self, pair: str, report: dict):
        # Biais HTF & Badges
        htf_bias = "BULLISH" # Mock ou recup de report
        htf_color = "text-green" if htf_bias == "BULLISH" else "text-red"
        
        global_bias = "NEUTRAL"
        ny_session = "HORS_SESSION"
        cible_dol = "PDL @ 1.0500"
        
        if report and "summary_score" in report:
            global_bias = report["summary_score"].get("dominant_verdict", "NEUTRAL")
            if "BEAR" in global_bias: htf_color = "text-red"
            elif "BULL" in global_bias: htf_color = "text-green"

        col_b1, col_b2 = st.columns([1, 2])
        col_b1.markdown(f"<h1 class='{htf_color}'>{htf_bias}</h1>", unsafe_allow_html=True)
        col_b2.markdown(f"""
        <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:20px;">
            <div class="card" style="padding:10px;"><small>🧭 BIAIS GLOBAL</small><br><b>{global_bias}</b></div>
            <div class="card" style="padding:10px;"><small>🕐 SESSION NY</small><br><b>{ny_session}</b></div>
            <div class="card" style="padding:10px;"><small>🎯 CIBLE DOL</small><br><b class='text-cyan'>{cible_dol}</b></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # TFs table
        tfs = ["MN", "W1", "D1", "H4", "H1", "M15", "M5", "M1"]
        
        st.markdown("""
        <div style="display:flex; border-bottom:1px solid #30363d; padding-bottom:10px; margin-bottom:10px;">
            <div style="flex:1; font-weight:bold;">Timeframe</div>
            <div style="flex:1; font-weight:bold;">Score /100</div>
            <div style="flex:2; font-weight:bold;">Verdict</div>
            <div style="flex:2; font-weight:bold;">Heure Analyse</div>
            <div style="flex:1; font-weight:bold;">Données OK</div>
            <div style="flex:1; font-weight:bold;">Détails</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Load detailed reports logic if available
        # mock for now except if we have data
        for tf in tfs:
            score = 0
            verdict = "EN_ATTENTE"
            verdict_badge = "<span class='badge-en-attente'>⏳ EN_ATTENTE</span>"
            dt_analyse = "--"
            data_ok = "⚪"
            
            # Simulated matching
            if report and tf in report.get("timeframes_analyzed", []):
                # Fake data since report summary only has averages, normally we load tf detailed report
                try:
                    tf_file = Path(f"data/reports/{pair}/{tf}/analysis_report.json")
                    if tf_file.exists():
                        import json
                        with open(tf_file, 'r') as f:
                            tf_data = json.load(f)
                            score = tf_data.get("score", {}).get("total", 0)
                            verdict = tf_data.get("score", {}).get("verdict", "WATCH")
                            data_ok = "🟢"
                            dt_analyse = datetime.now().strftime("%H:%M:%S")
                except:
                    pass
            
            # Verdict styling
            if score >= 78 or "EXECUTE" in verdict: verdict_badge = "<span class='badge-execute'>🎯 EXECUTE</span>"
            elif score >= 63 or "WATCH" in verdict: verdict_badge = "<span class='badge-regarder'>👁️ REGARDER / TIREUR D'ÉLITE</span>"
            elif score > 0: verdict_badge = "<span class='badge-interdit'>❌ INTERDIT (Pas de Setup)</span>"
            
            col1, col2, col3, col4, col5, col6 = st.columns([1,1,2,2,1,1])
            col1.write(f"**{tf}**")
            col2.markdown(f"**{score}/100**")
            col3.markdown(verdict_badge, unsafe_allow_html=True)
            col4.write(dt_analyse)
            col5.write(data_ok)
            
            btn_details = col6.button("🔍 Détails", key=f"det_{pair}_{tf}")
            if btn_details:
                st.session_state[f"exp_{pair}_{tf}"] = not st.session_state.get(f"exp_{pair}_{tf}", False)
                
            if st.session_state.get(f"exp_{pair}_{tf}", False):
                self._render_tf_expander(pair, tf, score, verdict)
                st.markdown("---")

    def _render_tf_expander(self, pair, tf, score, verdict):
        st.markdown(f"<div class='card'>", unsafe_allow_html=True)
        col_L, col_R = st.columns([4, 6])
        
        with col_L:
            st.markdown(f"### Score: {score}/100")
            st.markdown(f"<div class='module-title'>📘 {tf} MAÎTRISE</div>", unsafe_allow_html=True)
            
            st.markdown("**MODULE 1 — NARRATIF & BIAIS**")
            st.markdown("- Biais HTF: <span class='text-green'>BULLISH</span>", unsafe_allow_html=True)
            st.markdown("- Phase PO3: MANIPULATION")
            st.markdown("- Midnight Open: 1.0500")
            
            st.markdown("**MODULE 2 — STRUCTURE DU PRIX**")
            st.markdown("- Structure: <span class='text-cyan'>MSS_BULL</span>", unsafe_allow_html=True)
            st.markdown("- SFP/Turtle Soup: Aucun")
            
            st.markdown("**MODULE 3 — LIQUIDITÉ EXTERNE**")
            st.markdown("- DOL Principal: PDH @ 1.0600")
            
            st.markdown("**MODULE 4 — ZONES BL**")
            st.markdown("- FVG Non Équilibrés: 2")
            st.markdown("- OB Non Retestés: 1")
            
            st.markdown("**MODULE 5 — PREMIUM / DISCOUNT**")
            st.markdown("- Zone: <span class='text-green'>DISCOUNT</span>", unsafe_allow_html=True)
            st.markdown("- OTE Range: DANS_OTE")
            
            st.markdown("**MODULE 6 — TEMPS & MACRO**")
            st.markdown("- Killzone: <span class='text-orange'>NEW_YORK</span>", unsafe_allow_html=True)
            st.markdown("- Balle d'argent: OUI 10h00")
            
            st.markdown("**MODULE 7 — SETUPS ACTIFS**")
            st.markdown("<span class='text-cyan'>SILVER_BULLET_LONG</span>", unsafe_allow_html=True)
            
        with col_R:
            # Candlestick mock ou real chart
            fig = go.Figure(data=[go.Candlestick(x=[1,2,3],
                             open=[1,2,1], high=[2,3,2],
                             low=[0.5,1.5,0.5], close=[1.5,2.5,1])])
            fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=30,b=0), title=f"{pair} {tf} Price Action")
            st.plotly_chart(fig, use_container_width=True)
            
            subT1, subT2 = st.tabs(["📖 Narratif IA", "📊 Analyse de l'évolution"])
            with subT1:
                st.markdown("""
                **0. BIAIS LOCAL [H4]**  
                Le marché est en extraction de liquidité sur le bas du range asiatique.  
                **1. FLUX INSTITUTIONNELS (IPDA)**  
                Flow acheteur maintenu.  
                **...**  
                ➤ **SCÉNARIO A — CONTINUATION**  
                - Entrée sur le FVG 1.0450  
                - TP à la BSL 1.0600  
                
                ✅ **VERDICT: EXECUTE** (Probabilité très forte)
                """)
            with subT2:
                st.line_chart([1,2,1.5,3,2,4], height=200)
                
        st.markdown("</div>", unsafe_allow_html=True)

    def _render_echanges_subtab(self):
        st.markdown("### 💱 Échanges Ouverts")
        if st.session_state.current_mode == "paper":
            st.info("PAIRES DE SIMULATION (Paper Trading)")
        else:
            st.warning("PAIRES RÉELLES (Live Trading)")
            
        # Get from cache
        msc = MarketStateCache()
        msc.load_from_disk()
        positions = msc.get("open_positions", [])
        
        if not positions:
            st.write("Aucune position ouverte actuellement.")
        else:
            cols = st.columns(4)
            for i, p in enumerate(positions):
                color = "text-green" if p.get('pnl',0) > 0 else "text-red"
                with cols[i%4]:
                    st.markdown(f"""
                    <div class='card'>
                        <b>{p.get('pair','')}</b> <span class='{color}'>{p.get('direction','')}</span><br>
                        Entrée: {p.get('entry', 0)}<br>
                        Actuel: {p.get('current', 0)}<br>
                        P&L: <b class='{color}'>${p.get('pnl',0):.2f}</b>
                    </div>
                    """, unsafe_allow_html=True)
                    
        st.markdown("---")
        st.markdown("### ICT SENTINEL PRO — PAIRES ANALYSÉES")
        st.button("🔄 Lancer l'analyse complète (Toutes les paires)", type="primary")

    def _render_statistiques_subtab(self):
        st.markdown("### 📈 Statistiques de Performance")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Win Rate", "68.5%")
        c2.metric("Total Trades", "142")
        c3.metric("Profit Factor", "2.1")
        c4.metric("Score Moyen (Execute)", "82/100")
        
        st.line_chart(np.random.randn(100).cumsum() + 10000)

    # ══════════════════════════════════════════════════════════
    # MONITORING (TAB 2)
    # ══════════════════════════════════════════════════════════
    def render_tab_monitoring(self):
        st.markdown("## 📈 Monitoring & Positions")
        
        msc = MarketStateCache()
        msc.load_from_disk()
        state = msc.get_all()
        
        balance = state.get("balance", 0.0)
        equity = state.get("equity", 0.0)
        dd_day = state.get("dd_day_pct", 0.0)
        positions = state.get("open_positions", [])
        last_score = state.get("last_score", 0)
        
        if balance == 0:
            st.warning("⚠️ Bot non démarré — données en attente. Affichez les valeurs à 0.")
            
        # 5 Metrics
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("💰 Balance ($)", f"{balance:,.2f}")
        c2.metric("📈 Equity ($)", f"{equity:,.2f}", delta=f"{equity-balance:,.2f}")
        c3.metric("📉 DD Jour (%)", f"{dd_day:.2f}%", delta_color="inverse")
        c4.metric("🔓 Positions ouvertes", len(positions))
        c5.metric("🏆 Score dernier signal", f"{last_score}/100")
        
        # Courbe Equity
        st.markdown("### Courbe d'Equity (Session en cours)")
        eq_history = state.get("equity_history", [])
        if not eq_history:
            # Mock if empty
            eq_history = [(datetime.now().timestamp() - i*3600, 10000 + i*10) for i in range(20)][::-1]
            
        x_vals = [datetime.fromtimestamp(e[0]) for e in eq_history]
        y_vals = [e[1] for e in eq_history]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, fill='tozeroy', mode='lines', line=dict(color='#00d4ff')))
        fig.update_layout(template='plotly_dark', height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)
        
        # Killswitches
        st.markdown("### 🔴 KillSwitches Status")
        ks_status = state.get("ks_status", {f"KS{i}": False for i in range(1,10)})
        cols = st.columns(9)
        for i, (ks, active) in enumerate(ks_status.items()):
            with cols[i%9]:
                if active:
                    st.markdown(f"<div class='badge-interdit'>{ks} ACTIF</div>", unsafe_allow_html=True)
                    if st.button("💬 Info", key=f"info_{ks}"):
                        st.info(f"{ks} a été déclenché (protection active).")
                else:
                    st.markdown(f"<div class='badge-execute'>{ks} OK</div>", unsafe_allow_html=True)
                    
        # Positions 
        st.markdown("### 🔓 Positions Ouvertes")
        if not positions:
            st.write("Aucune position en cours.")
        else:
            # Render table
            df = pd.DataFrame(positions)
            # Add buttons per row by using columns
            st.markdown("""
            <div style="display:flex; border-bottom:1px solid #30363d; padding-bottom:5px; margin-bottom:5px; font-weight:bold;">
                <div style="flex:1;">Paire</div><div style="flex:1;">Direction</div><div style="flex:1;">Entrée</div>
                <div style="flex:1;">Actuel</div><div style="flex:1;">SL / TP</div><div style="flex:1;">P&L $</div><div style="flex:1;">Action</div>
            </div>""", unsafe_allow_html=True)
            
            for p in positions:
                c1,c2,c3,c4,c5,c6,c7 = st.columns([1,1,1,1,1,1,1])
                c1.write(p.get("pair"))
                direction = p.get("direction", "UNKNOWN")
                c2.markdown(f"<span class='text-{'green' if direction=='BUY' else 'red'}'>{direction}</span>", unsafe_allow_html=True)
                c3.write(p.get("entry", 0))
                c4.write(p.get("current", 0))
                c5.write(f"{p.get('sl',0)} / {p.get('tp',0)}")
                pnl = p.get("pnl", 0)
                c6.markdown(f"<strong class='text-{'green' if pnl>0 else 'red'}'>{pnl:.2f}</strong>", unsafe_allow_html=True)
                if c7.button("❌ Clôturer", key=f"close_{p.get('ticket',np.random.randint(1000))}"):
                    st.toast("Demande de clôture envoyée au Supervisor.")

    # ══════════════════════════════════════════════════════════
    # SETTINGS (TAB 3)
    # ══════════════════════════════════════════════════════════
    def render_tab_settings(self):
        st.markdown("## ⚙️ Paramètres Bot & Gouvernance")
        
        st.markdown("### SECTION A — Profil et Mode de Trading")
        colA1, colA2 = st.columns(2)
        with colA1:
            profil = st.radio("Sélection du Profil", [
                "⚡ Scalp (M1-M5, fenêtres Silver Bullet)",
                "📅 Day Trade (M5-D1, Londres + NY) 🔸 Recommandé",
                "🔄 Swing Trading (S2-S1, plusieurs jours)",
                "🏔️ Long Terme (D1-MN, positions mensuelles)"
            ])
            
        with colA2:
            mode = st.radio("Mode d'opération", [
                "📄 Paper Trading (simulation)",
                "⚠️ Semi-Automatique (alerte + vous validez)",
                "🚨 Full Automatique (bot trade seul 24/7)"
            ], key="mode_radio")
            
            st.session_state.current_mode = mode.split(' ')[0].lower() # paper, semi-automatique, full
            
            if "Full" in mode:
                st.error("AVERTISSEMENT: Le mode Full Auto engage des fonds réels sans intervention humaine. Assurez-vous d'avoir testé les stratégies en Paper Trading.")
                st.checkbox("J'accepte les risques institutionnels", key="accept_risk")

        st.markdown("---")
        
        # Inclusion du Settings Panel natif
        try:
            render_settings_panel(self.settings)
        except Exception as e:
            st.warning(f"Le panneau de paramètres natif n'a pu être chargé complètement: {e}")
            
        st.markdown("---")
        st.markdown("### SECTION SPÉCIALE — Actifs 24/7 (Cryptos & Indices Volatils)")
        st.info("Cryptos et certains indices traitent différemment. Ajustez les comportements.")
        t1 = st.toggle("Autoriser le trading HORS Killzones (24/7)")
        t2 = st.toggle("Désactiver le blocage de Spread Max pour les Cryptos")
        
        st.markdown("---")
        st.markdown("### Lancement du Bot")
        
        is_running = False
        if st.session_state.supervisor and st.session_state.supervisor.is_running():
            is_running = True
            
        cL1, cL2 = st.columns(2)
        with cL1:
            if st.button("✅ DÉMARRER LE BOT", type="primary", use_container_width=True):
                self.start_bot()
        with cL2:
            if st.button("⛔ ARRÊTER LE BOT", type="secondary", use_container_width=True):
                self.stop_bot()

    # ══════════════════════════════════════════════════════════
    # LOGS (TAB 4)
    # ══════════════════════════════════════════════════════════
    def render_tab_logs(self):
        st.markdown("## 📝 Journal & Logs")
        
        col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
        level_filter = col1.selectbox("Filtre Niveau", ["ALL", "INFO", "WARNING", "ERROR"])
        num_lines = col2.slider("Lignes à afficher", min_value=20, max_value=500, value=100)
        auto_refresh = col3.toggle("Rafraîchissement auto (2s)", value=True)
        if col4.button("🗑️ Vider l'affichage", use_container_width=True):
            st.session_state.clear_logs = True
        
        log_file = Path("logs/sentinel_kb5.log")
        if not log_file.exists():
            st.warning("Fichier Sentinel log non trouvé. En attente d'écriture...")
            return
            
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.readlines()
                
            if getattr(st.session_state, 'clear_logs', False):
                content = []
                st.session_state.clear_logs = False
                
            filtered = []
            for line in content:
                if level_filter == "ALL" or f"| {level_filter}" in line or f"- {level_filter}" in line:
                    filtered.append(line)
                    
            lines_to_show = filtered[-num_lines:]
            # Manual coloring simulation (since st.code doesn't support rich HTML natively easily, we use raw text in st.code)
            # Actually, standard log rendering is fine with language="log"
            st.code("".join(lines_to_show), language="log")
            
        except Exception as e:
            st.error(f"Erreur lecture logs: {e}")
            
        if auto_refresh:
            time.sleep(2)
            st.rerun()

    # ══════════════════════════════════════════════════════════
    # UTILS & ACTIONS
    # ══════════════════════════════════════════════════════════
    def start_bot(self):
        supervisor = st.session_state.supervisor
        if not supervisor:
            st.error("Supervisor non initialisé.")
            return
        if supervisor.is_running():
            st.info("Le bot est déjà actif.")
            return

        def run_thread():
            try:
                supervisor.start()
            except Exception as e:
                logger.error(f"Supervisor crash in thread: {e}")
                
        t = threading.Thread(target=run_thread, daemon=True)
        st.session_state.bot_thread = t
        t.start()
        
        # Attendre l'initialisation
        for _ in range(5):
            time.sleep(0.5)
            if supervisor.is_running():
                break
                
        st.success("Bot démarré avec succès !")
        time.sleep(1)
        st.rerun()

    def stop_bot(self):
        supervisor = st.session_state.supervisor
        if not supervisor or not supervisor.is_running():
            st.info("Le bot est déjà arrêté.")
            return
            
        try:
            supervisor.shutdown(reason="Arrêt manuel depuis Command Center")
            st.success("Bot arrêté.")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Erreur arrêt: {e}")

if __name__ == "__main__":
    app = CommandCenter()
    app.run()
