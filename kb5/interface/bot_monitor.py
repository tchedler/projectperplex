"""
interface/bot_monitor.py — Dashboard de Monitoring Bot KB5
==========================================================
4 onglets temps réel :
  1. Analyses  — Radar ICT multi-temporel par paire
  2. Échanges  — Positions actives MT5 avec SL/TP/PnL
  3. Journal   — Historique trades + FailureLab
  4. Statistiques — Circuit Breaker, KillSwitches, équité

Lit les données depuis bridge/bridge.py (DataStore d'App2)
et directement depuis MT5 pour les positions.
Auto-refresh : bandeau 5s, analyses 10s, positions 5s.
"""

import datetime
import pytz
import streamlit as st

# ── Bridge vers DataStore App2 ───────────────────────────────
try:
    from bridge.bridge import get_dashboard_data_from_cache, CB_COLORS, CB_LABELS
    BRIDGE_OK = True
except ImportError:
    BRIDGE_OK = False
    CB_COLORS = {0: "#00ff88", 1: "#f0b429", 2: "#ef5350", 3: "#b71c1c"}
    CB_LABELS = {
        0: "✅ NOMINAL", 1: "⚠️ WARNING — Taille 50%",
        2: "🚫 PAUSE",   3: "🛑 HALT — Fermeture forcée",
    }

# ── Import contrôle bot ──────────────────────────────────────
try:
    from interface.bot_settings import (
        stop_bot_process, is_bot_running,
        load_config, PROFILE_LABELS, MODE_LABELS
    )
    BOT_CTRL_OK = True
except ImportError:
    BOT_CTRL_OK = False

# ── MT5 ─────────────────────────────────────────────────────
try:
    import MetaTrader5 as mt5
    MT5_OK = True
except ImportError:
    MT5_OK = False

TZ_NY = pytz.timezone("America/New_York")

CACHE_FILE = "market_state.pkl"

# ============================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================

def render_bot_monitor(journal=None, scheduler=None,
                       latest_signals: dict = None,
                       order_manager=None,
                       bot_active: bool = False):
    """
    Dashboard de monitoring principal.
    Appelé depuis main_streamlit.py page 'bot_monitor'.
    """

    # ── Bandeau statut (auto-refresh 5s) ────────────────────
    @st.fragment(run_every=5)
    def _status_banner():
        running     = is_bot_running() if BOT_CTRL_OK else bot_active
        now_ny      = datetime.datetime.now(TZ_NY).strftime("%H:%M:%S")
        dash_data   = _load_data()
        last_hb     = dash_data.get("bot_status", {}).get("last_heartbeat", "---")
        equity      = dash_data.get("equity", 0.0)
        cb          = dash_data.get("circuit_breaker", {})
        cb_lvl      = cb.get("level", 0)
        cb_color    = CB_COLORS.get(cb_lvl, "#00ff88")

        if running:
            col_s, col_eq, col_cb, col_stop = st.columns([4, 2, 3, 1.5])
            col_s.html(
                f"<div style='background:#1e3a2f;border:1px solid #00ff88;"
                f"border-radius:8px;padding:10px 16px;'>"
                f"🟢 <b style='color:#00ff88'>BOT ACTIF</b> — "
                f"Heure NY : <code>{now_ny}</code> | "
                f"Dernier check : <code>{str(last_hb)[:19]}</code></div>"
            )
            col_eq.html(
                f"<div style='background:#1a1f2c;border:1px solid #2962ff44;"
                f"border-radius:8px;padding:10px 16px;text-align:center;'>"
                f"<small style='color:#848e9c;'>Équité</small><br>"
                f"<b style='color:#4dabff;font-size:1.1rem;'>{equity:.2f} $</b></div>"
            )
            col_cb.html(
                f"<div style='background:#1a1f2c;border:1px solid {cb_color}44;"
                f"border-radius:8px;padding:10px 16px;text-align:center;'>"
                f"<b style='color:{cb_color};'>CB{cb_lvl} — {CB_LABELS.get(cb_lvl, '')}</b></div>"
            )
            if BOT_CTRL_OK:
                if col_stop.button("🔴 STOP", key="mon_stop_btn", use_container_width=True):
                    stop_bot_process()
                    st.rerun()
        else:
            st.html(
                "<div style='background:#2a1f1f;border:1px solid #ef5350;"
                "border-radius:8px;padding:10px 16px;'>"
                "⚫ <b style='color:#ef5350'>BOT ARRÊTÉ</b> — "
                "Allez dans ⚙️ Paramètres Bot pour le démarrer.</div>"
            )

    _status_banner()

    # ── Profil + Mode ────────────────────────────────────────
    if BOT_CTRL_OK:
        cfg   = load_config()
        p_lbl = PROFILE_LABELS.get(cfg.get("profile", ""), cfg.get("profile", ""))
        m_id  = cfg.get("op_mode", "PAPER")
        m_lbl = "🟥 Paper" if "PAPER" in m_id else ("🟨 Semi-Auto" if "SEMI" in m_id else "🟩 Full Auto")
        st.markdown(f"> **Profil :** `{p_lbl}` &nbsp;|&nbsp; **Mode :** `{m_lbl}`")

    # ── 4 onglets ────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📡 Analyses", "📊 Échanges", "📚 Journal", "📈 Statistiques"
    ])

    with tab1:
        @st.fragment(run_every=10)
        def _analyses():
            _render_analyses_tab()
        _analyses()

    with tab2:
        @st.fragment(run_every=5)
        def _positions():
            _render_positions_tab()
        _positions()

    with tab3:
        _render_journal_tab(journal)

    with tab4:
        _render_stats_tab()


# ============================================================
# UTILITAIRE — chargement données
# ============================================================

def _load_data() -> dict:
    if BRIDGE_OK:
        return get_dashboard_data_from_cache(CACHE_FILE)
    return {}


# ============================================================
# ONGLET 1 — ANALYSES ICT MULTI-TEMPOREL
# ============================================================

def _render_analyses_tab():
    st.markdown("#### 📡 Radar ICT Multi-Temporel")

    data       = _load_data()
    pairs_data = data.get("pairs", {})

    if not pairs_data:
        st.info(
            "Aucune analyse disponible. "
            "Lancez le bot et sélectionnez vos paires dans l'interface principale."
        )
        return

    # Sélecteur de paire
    pairs = list(pairs_data.keys())
    if len(pairs) > 1:
        pair_tabs = st.tabs([f"📊 {p}" for p in pairs])
    else:
        pair_tabs = [st.container()]

    TF_ORDER = ["MN", "W1", "D1", "H4", "H1", "M15", "M5"]

    for i, pair in enumerate(pairs):
        with pair_tabs[i]:
            pdata      = pairs_data.get(pair, {})
            htf_bias   = pdata.get("htf_bias", "NEUTRAL")
            bias_color = pdata.get("bias_color", "#848e9c")
            verdict    = pdata.get("verdict", "NO_TRADE")
            score      = pdata.get("best_score", 0)
            direction  = pdata.get("direction", "NEUTRAL")
            tf_scores  = pdata.get("tf_scores", {})

            # En-tête paire
            dir_icon = "🔼" if "BULL" in direction else ("🔽" if "BEAR" in direction else "⬜")
            sc_color = "#00ff88" if score >= 80 else ("#f0b429" if score >= 65 else "#ef5350")

            c1, c2, c3 = st.columns(3)
            c1.html(
                f"<div style='background:#1a1f2c;border:1px solid {bias_color}44;"
                f"border-radius:8px;padding:10px;text-align:center;'>"
                f"<small style='color:#848e9c;'>BIAIS HTF</small><br>"
                f"<b style='color:{bias_color};'>{htf_bias}</b></div>"
            )
            c2.html(
                f"<div style='background:#1a1f2c;border:1px solid {sc_color}44;"
                f"border-radius:8px;padding:10px;text-align:center;'>"
                f"<small style='color:#848e9c;'>MEILLEUR SCORE</small><br>"
                f"<b style='color:{sc_color};font-size:1.4rem;'>{score}/100</b></div>"
            )
            c3.html(
                f"<div style='background:#1a1f2c;border:1px solid {bias_color}44;"
                f"border-radius:8px;padding:10px;text-align:center;'>"
                f"<small style='color:#848e9c;'>DIRECTION</small><br>"
                f"<b style='color:{bias_color};'>{dir_icon} {direction}</b></div>"
            )

            st.markdown("")

            # Tableau par timeframe
            st.markdown("**Pyramide KB5 — Scores par Timeframe**")
            for tf in TF_ORDER:
                tf_data  = tf_scores.get(tf, {})
                sc       = tf_data.get("score", 0)
                vd       = tf_data.get("verdict", "NO_TRADE")
                dir_tf   = tf_data.get("direction", "NEUTRAL")
                rr       = tf_data.get("rr", 0.0)

                sc_c   = "#00ff88" if sc >= 80 else ("#f0b429" if sc >= 65 else "#ef5350")
                vd_map = {
                    "EXECUTE":  ("🚀 EXÉCUTION",      "status-ok"),
                    "WATCH":    ("👁 SURVEILLER",      "status-wait"),
                    "NO_TRADE": ("⛔ NO TRADE",        "status-no"),
                    "BLOCKED":  ("🔒 BLOQUÉ",          "status-no"),
                }
                vd_lbl, vd_cls = vd_map.get(vd, (vd, "status-wait"))

                col_tf, col_sc, col_vd, col_dir, col_rr, col_btn = st.columns([1, 1.5, 2.5, 1.5, 1, 1.5])

                col_tf.html(
                    f"<div style='padding:8px 0;'>"
                    f"<b style='color:#4dabff;font-size:1rem;'>{tf}</b></div>"
                )
                col_sc.html(
                    f"<div style='padding:8px 0;'>"
                    f"<span style='background:#111;padding:3px 8px;border-radius:16px;"
                    f"font-weight:700;color:{sc_c};border:1px solid {sc_c}33;'>{sc}/100</span></div>"
                )

                if sc > 0:
                    if vd_cls == "status-ok":
                        vd_bg, vd_color, vd_border = "#00ff8822", "#00ff88", "#00ff8844"
                    elif vd_cls == "status-wait":
                        vd_bg, vd_color, vd_border = "#f0b42922", "#f0b429", "#f0b42944"
                    else:
                        vd_bg, vd_color, vd_border = "#ef535022", "#ef5350", "#ef535044"
                    col_vd.html(
                        f"<div style='padding:6px 0;'>"
                        f"<span style='padding:3px 10px;border-radius:6px;font-size:0.82rem;"
                        f"font-weight:600;"
                        f"background:{vd_bg};"
                        f"color:{vd_color};"
                        f"border:1px solid {vd_border};'>"
                        f"{vd_lbl}</span></div>"
                    )
                    col_dir.html(
                        f"<div style='padding:8px 0;color:#848e9c;font-size:0.85rem;'>"
                        f"{'🔼' if 'BULL' in dir_tf else '🔽' if 'BEAR' in dir_tf else '⬜'} "
                        f"{dir_tf[:4]}</div>"
                    )
                    col_rr.html(
                        f"<div style='padding:8px 0;color:#4dabff;font-size:0.85rem;'>"
                        f"RR {rr:.1f}x</div>"
                    )
                    with col_btn:
                        if st.button("🔍 Détails", key=f"det_{pair}_{tf}",
                                     use_container_width=True):
                            st.session_state[f"detail_{pair}_{tf}"] = True
                else:
                    col_vd.html(
                        "<div style='padding:8px 0;'>"
                        "<span style='color:#555;font-size:0.85rem;'>En attente…</span></div>"
                    )

                # Détails expandables
                if st.session_state.get(f"detail_{pair}_{tf}"):
                    with st.expander(f"📋 Détails {pair} {tf}", expanded=True):
                        confluences = tf_data.get("confluences", [])
                        if confluences:
                            st.markdown("**Confluences actives :**")
                            for c in confluences:
                                bonus = c.get("bonus", 0)
                                b_col = "#00ff88" if bonus > 0 else "#ef5350"
                                st.html(
                                    f"<div style='background:#1a1f2c;border-left:3px solid {b_col};"
                                    f"padding:6px 10px;margin:3px 0;border-radius:4px;'>"
                                    f"<b style='color:{b_col};'>{c.get('name','')}</b>"
                                    f"<span style='color:#848e9c;font-size:0.8rem;'> +{bonus}pts</span><br>"
                                    f"<small style='color:#aaa;'>{c.get('description','')}</small></div>"
                                )
                        else:
                            st.info("Aucune confluence détectée pour ce timeframe.")
                        if st.button("✖ Fermer", key=f"close_{pair}_{tf}"):
                            del st.session_state[f"detail_{pair}_{tf}"]


# ============================================================
# ONGLET 2 — POSITIONS ACTIVES
# ============================================================

def _render_positions_tab():
    st.markdown("#### 📊 Positions Actives (MT5)")

    if not MT5_OK:
        st.error("MetaTrader5 non disponible.")
        return

    try:
        if not mt5.initialize():
            st.warning("MT5 non connecté.")
            return
        positions = mt5.positions_get()
    except Exception as e:
        st.error(f"Erreur MT5 : {e}")
        return

    if not positions:
        st.html(
            "<div style='text-align:center;padding:40px;color:#848e9c;'>"
            "📭 Aucune position ouverte en ce moment.</div>"
        )
        return

    total_pnl = sum(p.profit for p in positions)
    pnl_color = "#00ff88" if total_pnl >= 0 else "#ef5350"

    st.html(
        f"<div style='background:#1a1f2c;border:1px solid #2962ff44;"
        f"border-radius:8px;padding:10px 16px;margin-bottom:16px;'>"
        f"<b style='color:#4dabff;'>{len(positions)} position(s) ouverte(s)</b> | "
        f"PnL total : <b style='color:{pnl_color};'>{total_pnl:+.2f} $</b></div>"
    )

    cols = st.columns(min(len(positions), 3))
    for i, pos in enumerate(positions):
        with cols[i % 3]:
            dir_lbl   = "📈 BUY"  if pos.type == 0 else "📉 SELL"
            dir_color = "#00ff88" if pos.type == 0 else "#ef5350"
            pnl_c     = "#00ff88" if pos.profit >= 0 else "#ef5350"
            sl_c      = "#ef5350" if pos.sl == 0 else "#ef5350"
            sl_txt    = f"{pos.sl:.5f}" if pos.sl > 0 else "⚠️ ABSENT"
            tp_txt    = f"{pos.tp:.5f}" if pos.tp > 0 else "—"

            # Calcul PnL en pips approximatif
            pip_diff = abs(pos.price_current - pos.price_open)

            st.html(
                f"<div style='background:rgba(30,34,45,0.9);border:1px solid "
                f"rgba(255,255,255,0.1);border-radius:10px;padding:14px;margin-bottom:10px;'>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:8px;'>"
                f"<b style='color:#fff;font-size:1.05rem;'>{pos.symbol}</b>"
                f"<span style='color:{dir_color};font-weight:700;background:rgba(255,255,255,0.05);"
                f"padding:2px 8px;border-radius:4px;'>{dir_lbl} {pos.volume}</span></div>"
                f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:0.83rem;color:#848e9c;'>"
                f"<span>Entry: <b style='color:#fff;'>{pos.price_open:.5f}</b></span>"
                f"<span>Now: <b style='color:#fff;'>{pos.price_current:.5f}</b></span>"
                f"<span>SL: <b style='color:{sl_c};'>{sl_txt}</b></span>"
                f"<span>TP: <b style='color:#00ff88;'>{tp_txt}</b></span>"
                f"<span>Ticket: <b style='color:#4dabff;'>#{pos.ticket}</b></span>"
                f"<span>Δ: <b style='color:#aaa;'>{pip_diff:.5f}</b></span>"
                f"</div>"
                f"<div style='border-top:1px solid rgba(255,255,255,0.1);margin-top:10px;"
                f"padding-top:8px;text-align:center;font-weight:700;font-size:1.15rem;"
                f"color:{pnl_c};'>{pos.profit:+.2f} $</div></div>"
            )


# ============================================================
# ONGLET 3 — JOURNAL DES TRADES
# ============================================================

def _render_journal_tab(journal=None):
    st.markdown("#### 📚 Journal des Trades & FailureLab")

    # ── Statistiques depuis journal App2 ────────────────────
    if journal is not None:
        try:
            stats = journal.get_stats(last_n=100)
            total  = stats.get("total", 0)
            wins   = stats.get("wins", 0)
            losses = stats.get("losses", 0)
            wr     = stats.get("winrate", 0)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Trades totaux", total)
            col2.metric("Wins",   wins,   delta=None)
            col3.metric("Losses", losses, delta=None)
            wr_color = "#00ff88" if wr >= 55 else ("#f0b429" if wr >= 45 else "#ef5350")
            col4.html(
                f"<div style='text-align:center;'>"
                f"<small style='color:#848e9c;'>Win Rate</small><br>"
                f"<b style='color:{wr_color};font-size:1.5rem;'>{wr:.1f}%</b></div>"
            )

            # Erreurs les plus fréquentes
            errors = stats.get("errors", {})
            if errors:
                st.markdown("**Erreurs les plus fréquentes :**")
                for cat, count in sorted(errors.items(), key=lambda x: -x[1])[:5]:
                    pct = int(count / total * 100) if total > 0 else 0
                    st.html(
                        f"<div style='display:flex;align-items:center;gap:10px;margin:4px 0;'>"
                        f"<span style='color:#848e9c;min-width:180px;font-size:0.85rem;'>{cat}</span>"
                        f"<div style='flex:1;background:#1a1f2c;border-radius:4px;height:8px;'>"
                        f"<div style='width:{pct}%;background:#ef5350;border-radius:4px;height:8px;'></div></div>"
                        f"<span style='color:#ef5350;font-size:0.85rem;min-width:40px;'>{count}x</span>"
                        f"</div>"
                    )
        except Exception as e:
            st.warning(f"Impossible de lire le journal : {e}")
    else:
        # Lecture depuis le cache pickle
        data       = _load_data()
        bot_status = data.get("bot_status", {})
        cycles     = bot_status.get("cycles", 0)
        exec_count = bot_status.get("execute_count", 0)

        col1, col2, col3 = st.columns(3)
        col1.metric("Cycles KB5",     cycles)
        col2.metric("Signaux EXECUTE", exec_count)
        col3.metric("Source",         "Cache PKL")

    st.markdown("---")

    # ── FailureLab ───────────────────────────────────────────
    st.markdown("**🔬 FailureLab — Autopsy des pertes**")
    st.html(
        "<div style='background:rgba(239,83,80,0.08);border:1px solid #ef535033;"
        "border-radius:8px;padding:12px 16px;'>"
        "<b style='color:#ef5350;'>FailureLab KB5</b><br>"
        "<small style='color:#aaa;'>Le bot analyse automatiquement chaque perte pour "
        "identifier les erreurs récurrentes et adapter son scoring. "
        "Si le Regret Rate dépasse 40%, le bot bloque les nouveaux trades "
        "jusqu'à la prochaine session.</small></div>"
    )

    if journal is not None:
        try:
            recent_losses = journal.get_recent_losses(5)
            if recent_losses:
                st.markdown("**5 dernières pertes :**")
                for loss in recent_losses:
                    pair   = loss.get("pair", "?")
                    rr     = loss.get("rr", 0)
                    cat    = loss.get("error_category", "INCONNU")
                    score  = loss.get("score", 0)
                    st.html(
                        f"<div style='background:#1a1f2c;border-left:3px solid #ef5350;"
                        f"padding:8px 12px;margin:4px 0;border-radius:4px;'>"
                        f"<b style='color:#ef5350;'>{pair}</b>"
                        f" | Score: <b style='color:#f0b429;'>{score}</b>"
                        f" | RR: <b style='color:#848e9c;'>{rr:.1f}x</b>"
                        f" | Erreur: <b style='color:#aaa;'>{cat}</b></div>"
                    )
            else:
                st.success("✅ Aucune perte récente enregistrée.")
        except Exception:
            st.info("Journal non disponible — le bot n'a pas encore tourné.")
    else:
        st.info("Journal disponible après le premier cycle du bot.")


# ============================================================
# ONGLET 4 — STATISTIQUES GLOBALES
# ============================================================

def _render_stats_tab():
    st.markdown("#### 📈 Statistiques Globales")

    data = _load_data()
    cb   = data.get("circuit_breaker", {})
    ks   = data.get("killswitches", [])
    eq   = data.get("equity", 0.0)
    bs   = data.get("bot_status", {})

    # ── Circuit Breaker ──────────────────────────────────────
    st.markdown("**🔌 Circuit Breaker**")
    cb_lvl   = cb.get("level", 0)
    cb_color = CB_COLORS.get(cb_lvl, "#00ff88")
    cb_pct   = cb.get("pct_drop", 0.0)

    col1, col2, col3, col4 = st.columns(4)
    col1.html(
        f"<div style='background:#1a1f2c;border:2px solid {cb_color};"
        f"border-radius:10px;padding:14px;text-align:center;'>"
        f"<div style='font-size:0.7rem;color:#848e9c;text-transform:uppercase;'>Niveau CB</div>"
        f"<div style='font-size:2rem;font-weight:900;color:{cb_color};'>CB{cb_lvl}</div>"
        f"<div style='font-size:0.75rem;color:{cb_color};'>{CB_LABELS.get(cb_lvl,'')}</div></div>"
    )
    col2.metric("Drawdown actuel",  f"{cb_pct:.2f}%")
    col3.metric("Équité compte",    f"{eq:.2f} $")
    col4.metric("Cycles effectués", bs.get("cycles", 0))

    st.markdown("")

    # Barre de drawdown
    dd_pct_display = min(cb_pct, 10.0)
    bar_w  = int(dd_pct_display / 10 * 100)
    bar_c  = "#00ff88" if cb_lvl == 0 else ("#f0b429" if cb_lvl == 1 else "#ef5350")
    st.html(
        f"<div style='margin:8px 0;'>"
        f"<div style='display:flex;justify-content:space-between;font-size:0.8rem;color:#848e9c;margin-bottom:4px;'>"
        f"<span>Drawdown</span><span>{cb_pct:.2f}% / 10%</span></div>"
        f"<div style='background:#1a1f2c;border-radius:6px;height:12px;'>"
        f"<div style='width:{bar_w}%;background:{bar_c};border-radius:6px;height:12px;"
        f"transition:width 0.5s;'></div></div></div>"
    )

    st.markdown("---")

    # ── KillSwitches ─────────────────────────────────────────
    st.markdown("**🔴 KillSwitches actifs**")
    KS_NAMES = {
        1: "Spread excessif",    2: "Volatilité extrême",
        3: "News haute impact",  4: "Hors Killzone",
        5: "DD journalier max",  6: "Contre-tendance HTF",
        7: "Trop de positions",  8: "Corrélation exposée",
        9: "Phase Accumulation",
    }

    if ks:
        cols = st.columns(3)
        for i, ks_item in enumerate(ks):
            ks_id = ks_item.get("id", ks_item) if isinstance(ks_item, dict) else int(ks_item)
            reason = ks_item.get("reason", "") if isinstance(ks_item, dict) else ""
            with cols[i % 3]:
                st.html(
                    f"<div style='background:rgba(239,83,80,0.12);border:1px solid #ef535044;"
                    f"border-radius:8px;padding:8px 12px;margin:4px 0;'>"
                    f"<b style='color:#ef5350;'>🔴 KS{ks_id} — {KS_NAMES.get(ks_id,'?')}</b><br>"
                    f"<small style='color:#aaa;'>{reason}</small></div>"
                )
    else:
        st.success("✅ Aucun KillSwitch actif — toutes les paires autorisées")

    st.markdown("---")

    # ── Statistiques session ─────────────────────────────────
    st.markdown("**📊 Statistiques de session**")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Signaux EXECUTE", bs.get("execute_count", 0))
    col2.metric("Erreurs",         bs.get("error_count", 0))
    col3.metric("Session active",  bs.get("session", "---"))
    col4.metric("Statut",
                "🟢 Actif" if bs.get("bot_is_running") else "⚫ Arrêté")

    # ── Paires actives ───────────────────────────────────────
    pairs_data = data.get("pairs", {})
    if pairs_data:
        st.markdown("---")
        st.markdown("**🌐 Scores en temps réel — toutes les paires**")
        scores = {
            pair: pdata.get("best_score", 0)
            for pair, pdata in pairs_data.items()
        }
        scores_sorted = dict(sorted(scores.items(), key=lambda x: -x[1]))
        cols = st.columns(min(len(scores_sorted), 5))
        for i, (pair, sc) in enumerate(list(scores_sorted.items())[:10]):
            sc_c = "#00ff88" if sc >= 80 else ("#f0b429" if sc >= 65 else "#ef5350")
            with cols[i % 5]:
                st.html(
                    f"<div style='background:#1a1f2c;border:1px solid {sc_c}44;"
                    f"border-radius:8px;padding:10px;text-align:center;margin:4px 0;'>"
                    f"<div style='font-size:0.75rem;color:#848e9c;'>{pair}</div>"
                    f"<div style='font-size:1.4rem;font-weight:800;color:{sc_c};'>{sc}</div>"
                    f"<div style='font-size:0.65rem;color:{sc_c};'>/100</div></div>"
                )
