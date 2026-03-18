"""
bot_monitor.py — Dashboard de Monitoring du Bot ICT
4 onglets : Analyses en cours, Trades, Journal d'apprentissage, Statistiques.
"""
import streamlit as st
import datetime
import pytz
import pandas as pd
import json


def render_bot_monitor(journal=None, scheduler=None, latest_signals: dict = None,
                       order_manager=None, bot_active: bool = False):
    """
    Dashboard principal de monitoring.
    Appelée depuis main.py avec les instances des modules du bot.
    Lit l'état persistant via MarketStateCache.
    """
    # Fragment auto-refresh pour le bandeau supérieur (Statut + Heartbeat)
    @st.fragment(run_every=5)
    def status_header_fragment():
        # Re-lire le statut pour le fragment
        from core.market_state_cache import MarketStateCache
        import pytz
        import datetime
        tz  = pytz.timezone("America/New_York")
        m_cache = MarketStateCache()
        c_status = m_cache.get_bot_status()
        is_running = c_status.get("bot_is_running", False)
        last_hb = c_status.get("last_heartbeat", "N/A")
        # Double check heartbeat
        if is_running and last_hb != "N/A":
            try:
                hb_t = datetime.datetime.strptime(last_hb, "%Y-%m-%d %H:%M:%S")
                ny_now = datetime.datetime.now(tz).replace(tzinfo=None)
                if abs((ny_now - hb_t).total_seconds()) > 120:
                    is_running = False
            except: pass

        if is_running or bot_active:
            col_status, col_stop = st.columns([4, 1])
            with col_status:
                st.html(
                    f"<div style='background:#1e3a2f; border:1px solid #00ff88; border-radius:8px; "
                    f"padding:10px 16px; margin-bottom:16px;'>"
                    f"🟢 <b style='color:#00ff88'>BOT ACTIF</b> — "
                    f"Heure Locale : <code>{datetime.datetime.now(tz).strftime('%H:%M:%S')}</code> | "
                    f"Dernier check : <code>{last_hb}</code> | "
                    f"</div>"
                )
            with col_stop:
                from interface.bot_settings import stop_bot_process
                if st.button("🔴 STOPPER LE BOT", use_container_width=True, 
                             key="dashboard_stop_bot_btn_frag"):
                    stop_bot_process()
                    st.rerun()
        else:
            st.html(
                "<div style='background:#2a1f1f; border:1px solid #ef5350; border-radius:8px; "
                "padding:10px 16px; margin-bottom:16px;'>"
                "⚫ <b style='color:#ef5350'>BOT ARRÊTÉ</b> — "
                "Allez dans ⚙️ Paramètres Bot pour le démarrer."
                "</div>"
            )

    # Lancement du fragment de statut
    status_header_fragment()

    # Configuration du Bot (Profil + Mode)
    from interface.bot_settings import load_config, PROFILE_LABELS, MODE_LABELS
    b_cfg = load_config()
    p_id = b_cfg.get("profile", "DAY_TRADE")
    m_id = b_cfg.get("op_mode", "PAPER")
    p_lbl = PROFILE_LABELS.get(p_id, "Inconnu")
    m_lbl = "🟥 Simulation (Paper)" if "PAPER" in m_id else ("🟨 Semi-Auto" if "SEMI" in m_id else "🟩 Mode Réel (Auto)")
    
    st.markdown(f"> **Profil :** `{p_lbl}` &nbsp;|&nbsp; **Mode :** `{m_lbl}`")

    # 4 onglets de monitoring
    tab1, tab2, tab3, tab4 = st.tabs([
        "📡 Analyses", "📊 Trades", "📚 Journal", "📈 Statistiques"
    ])

    # ============================================================
    # ONGLET 1 : ANALYSES EN COURS (Auto-Refresh 10s)
    # ============================================================
    with tab1:
        @st.fragment(run_every=10)
        def live_analyses_fragment():
            from core.market_state_cache import MarketStateCache
            m_cache = MarketStateCache()
            _render_analyses_tab(scheduler, latest_signals, m_cache)
        
        live_analyses_fragment()

    # ============================================================
    # ONGLET 2 : TRADES
    # ============================================================
    with tab2:
        _render_trades_tab(journal, order_manager)

    # ============================================================
    # ONGLET 3 : JOURNAL D'APPRENTISSAGE
    # ============================================================
    with tab3:
        _render_journal_tab(journal)

    # ============================================================
    # ONGLET 4 : STATISTIQUES
    # ============================================================
    with tab4:
        _render_stats_tab(journal)


# ============================================================
# ONGLET 1 — ANALYSES
# ============================================================

def _render_analyses_tab(scheduler, latest_signals: dict = None, market_cache = None):
    st.markdown("#### 📡 Radar ICT Multi-Timeframe")

    if market_cache is None:
        st.info("Initialisation du cache...")
        return

    cache_data = market_cache.load()
    bot_status = market_cache.get_bot_status()
    active_symbols = bot_status.get("active_symbols", ["XAUUSD"])

    if not active_symbols:
        st.warning("Aucun symbole actif. Configurez vos paires dans les Paramètres Bot.")
        return

    # CSS commun pour le tableau
    st.html("""
        <style>
        .tf-label { font-weight: 800; color: #4dabff; font-size: 1.0rem; }
        .score-badge {
            background: #111; padding: 4px 10px; border-radius: 20px;
            font-weight: bold; color: #ffff00; border: 1px solid #ffff0033;
            font-size: 0.9rem;
        }
        .status-pill { padding: 3px 8px; border-radius: 6px; font-size: 0.82rem; font-weight: 600; }
        .status-ok   { background: #00ff8822; color: #00ff88; border: 1px solid #00ff8844; }
        .status-wait { background: #f0b42922; color: #f0b429; border: 1px solid #f0b42944; }
        .status-no   { background: #ef535022; color: #ef5350; border: 1px solid #ef535044; }
        </style>
    """)

    tf_order = ["MN", "W1", "D1", "H4", "H1", "M15", "M5", "M1"]

    # --- Un Radar par symbole actif ---
    sym_tabs = st.tabs([f"📊 {sym}" for sym in active_symbols]) if len(active_symbols) > 1 else [st.container()]

    for idx, symbol in enumerate(active_symbols):
        ctx = sym_tabs[idx]
        with ctx:
            symbol_data = cache_data.get(symbol, {}).get("timeframes", {})
            gbias = market_cache.get_global_bias(symbol)
            bias_txt = gbias.get("htf_bias", "---") if gbias else "---"
            bias_color = "#00ff88" if "BULL" in bias_txt else "#ef5350" if "BEAR" in bias_txt else "#848e9c"

            title_html = ""
            if len(active_symbols) == 1:
                title_html = f"<div style='font-size:1.3rem; font-weight:800; color:#4dabff; margin-bottom:8px;'>📊 Radar {symbol}</div>"

            st.html(
                f"{title_html}"
                f"<div style='margin-bottom:10px; font-size:0.9rem;'>"
                f"Biais HTF : <b style='color:{bias_color}'>{bias_txt}</b></div>"
            )

            for tf in tf_order:
                data_wrapper = symbol_data.get(tf, {})
                data = data_wrapper.get("data", {})
                last_upd = data_wrapper.get("last_updated", "N/A")

                score = data.get("checklist", {}).get("score", "-")
                verdict = data.get("checklist", {}).get("verdict", "En attente")

                # M5 FIX : Lire la direction depuis le dernier signal
                signal_data = data.get("last_signal", {})
                direction = signal_data.get("direction", "")
                dir_icon = ""
                if direction == "BUY":
                    dir_icon = "🔼"
                elif direction == "SELL":
                    dir_icon = "🔽"

                pill_class = "status-wait"
                if "EXECUT" in str(verdict).upper(): pill_class = "status-ok"
                elif "INTERDIT" in str(verdict).upper(): pill_class = "status-no"

                # M2 FIX : Afficher le score en /100 (pas en %)
                score_val = f"{score}/100" if score != "-" else "---"
                time_clean = last_upd.split("T")[-1][:5] if "T" in str(last_upd) else "--:--"
                has_data = bool(data)

                # Colonnes Streamlit natives pour permettre le bouton interactif
                col_tf, col_sc, col_st, col_hr, col_ic, col_btn = st.columns([1, 1.2, 2.5, 1.2, 0.6, 1.2])

                with col_tf:
                    st.html(f"<div class='tf-label' style='padding-top:6px;'>{tf}</div>")
                with col_sc:
                    st.html(f"<div class='score-badge' style='margin-top:4px; display:inline-block;'>{dir_icon} {score_val}</div>")
                with col_st:
                    st.html(f"<div class='status-pill {pill_class}' style='margin-top:6px; display:inline-block;'>{verdict}</div>")
                with col_hr:
                    st.html(f"<div style='color:#848e9c; font-size:0.8rem; padding-top:8px;'>🕒 {time_clean}</div>")
                with col_ic:
                    st.html(f"<div style='font-size:1rem; padding-top:6px;'>{'\u2705' if has_data else '\u23f3'}</div>")
                with col_btn:
                    if has_data:
                        link_url = f"/?symbol={symbol}&tf={tf}"
                        st.html(
                            f"<a href='{link_url}' target='_blank' "
                            f"style='display:inline-block; padding:4px 12px; border-radius:6px; "
                            f"background:#2962ff; color:white; text-decoration:none; font-size:0.82rem; "
                            f"font-weight:600; text-align:center; width:100%;'>"
                            f"🔍 Détails</a>"
                        )

                st.html("<hr style='margin:4px 0; border-color:rgba(255,255,255,0.05);'>")

    if st.button("🔄 Forcer le rafraîchissement", key="btn_ref"):
        st.rerun()


# ============================================================
# ONGLET 2 — TRADES
# ============================================================
def _render_trades_tab(journal, order_manager):
    st.markdown("#### 📊 Gestion des Trades")

    sub1, sub2, sub3 = st.tabs(["🔥 Actifs", "⏳ En Attente", "✅ Fermés"])

    active_list  = []
    pending_list = []

    if order_manager:
        active_list  = [p.to_dict() for p in order_manager.get_active_positions()]
        pending_list = [p.to_dict() for p in order_manager.get_pending_positions()]

    with sub1:
        if active_list:
            df = pd.DataFrame(active_list)
            _display_trade_table(df, status_color="#00ff88")
        else:
            st.info("Aucune position active en ce moment.")

        # Bouton fermeture urgence
        if active_list and order_manager:
            if st.button("⛔ FERMER TOUTES LES POSITIONS (urgence)", type="secondary", key="close_all"):
                order_manager.close_all_positions("MANUAL")
                st.warning("Toutes les positions fermées manuellement.")
                st.rerun()

    with sub2:
        if pending_list:
            df = pd.DataFrame(pending_list)
            _display_trade_table(df, status_color="#f0b429")
        else:
            st.info("Aucun ordre limite en attente.")

    with sub3:
        if journal:
            closed = journal.get_closed_trades(limit=50)
            if closed:
                df = pd.DataFrame(closed)
                cols_to_show = ["symbol", "direction", "entry", "close_price", "close_reason",
                                "pnl_pips", "pnl_money", "status", "setup_name", "score",
                                "open_time", "close_time"]
                cols_to_show = [c for c in cols_to_show if c in df.columns]
                st.dataframe(df[cols_to_show], use_container_width=True, hide_index=True)
            else:
                st.info("Aucun trade fermé pour l'instant.")
        else:
            st.info("Journal non disponible.")


def _display_trade_table(df: pd.DataFrame, status_color: str = "#00ff88"):
    cols = ["symbol", "direction", "entry", "sl", "tp1", "tp2",
            "lot_size", "score", "setup", "partial_done", "paper", "open_time"]
    cols = [c for c in cols if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)


# ============================================================
# ONGLET 3 — JOURNAL D'APPRENTISSAGE
# ============================================================
def _render_journal_tab(journal):
    st.markdown("#### 📚 Journal d'Apprentissage ICT")
    st.caption("Analyse des trades échoués pour améliorer la performance.")

    if journal is None:
        st.info("Journal non disponible. Démarrez le bot pour commencer à enregistrer.")
        return

    # Filtre
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_status = st.selectbox("Filtrer par résultat", ["Tous", "WIN", "LOSS", "BREAKEVEN"], key="filter_status")
    with col_f2:
        filter_error = st.selectbox(
            "Filtrer par erreur",
            ["Toutes", "EARLY_ENTRY", "WRONG_BIAS", "BAD_TIMING", "INDUCEMENT",
             "WRONG_ZONE", "FRIDAY_TRADE", "NONE"],
            key="filter_error"
        )

    trades = journal.get_all_trades(limit=100)

    if filter_status != "Tous":
        trades = [t for t in trades if t.get("status") == filter_status]
    if filter_error != "Toutes":
        trades = [t for t in trades if t.get("error_category") == filter_error]

    if not trades:
        st.info("Aucun trade correspondant aux filtres.")
        return

    df = pd.DataFrame(trades)
    cols = ["symbol", "direction", "entry", "close_price", "status",
            "error_category", "setup_name", "score", "killzone", "htf_bias", "open_time"]
    cols = [c for c in cols if c in df.columns]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)

    # Cas d'échec
    st.markdown("##### ⚠️ Cas d'Échec Analysés")
    failures = journal.get_failure_cases(limit=20)
    if failures:
        for fc in failures:
            with st.expander(f"❌ {fc.get('error_type', '?')} — {fc.get('date', '?')}"):
                st.markdown(f"**Erreur :** `{fc.get('error_type')}`")
                st.markdown(f"**Description :** {fc.get('error_desc', '')}")
                st.markdown(f"**Leçon :** {fc.get('lesson_learned', '')}")
                ctx = fc.get("context_json", "{}")
                try:
                    ctx_dict = json.loads(ctx)
                    st.json(ctx_dict)
                except Exception:
                    st.text(ctx)
    else:
        st.success("✅ Aucun cas d'échec enregistré pour l'instant — excellent !")


# ============================================================
# ONGLET 4 — STATISTIQUES
# ============================================================
def _render_stats_tab(journal):
    st.markdown("#### 📈 Statistiques de Performance")

    if journal is None:
        st.info("Journal non disponible.")
        return

    # Sélecteur de date
    selected_date = st.date_input("Date de session", value=datetime.date.today(), key="stats_date")
    stats = journal.get_session_stats(str(selected_date))

    if stats.get("no_data"):
        st.info(f"Aucun trade enregistré pour le {selected_date}.")
        return

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Total Trades", stats["total_trades"])
    with col2:
        wr_color = "normal" if stats["win_rate"] >= 50 else "inverse"
        st.metric("🏆 Win Rate", f"{stats['win_rate']}%",
                  delta=f"{stats['win_count']}W / {stats['loss_count']}L")
    with col3:
        pnl = stats["total_pnl"]
        st.metric("💰 PnL Session", f"{pnl:+.2f}$",
                  delta=f"{stats['total_pips']:+.1f} pips")
    with col4:
        st.metric("📉 Avg/Trade", f"{stats['avg_per_trade']:+.2f}$")

    # Barre W/L/BE
    w = stats["win_count"]
    l = stats["loss_count"]
    be = stats["be_count"]
    if w + l + be > 0:
        st.progress(w / (w + l + be))
        st.caption(f"✅ {w} Wins | ❌ {l} Losses | ➡️ {be} Breakeven")

    # Erreurs top
    if stats.get("top_errors"):
        st.markdown("##### ⚠️ Erreurs de session les plus fréquentes")
        for err, count in stats["top_errors"].items():
            st.warning(f"**{err}** : {count}x")

    # Rapport texte
    st.markdown("##### 📋 Rapport Complet")
    report = journal.generate_session_report(str(selected_date))
    st.code(report, language=None)



