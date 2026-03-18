"""
orchestrator.py — Cerveau d'Analyse ICT (ProOrchestrator)
Coordonne tous les agents d'analyse (SMC, Liquidité, MMXM, Biais, etc.)
pour produire une analyse complète d'un symbole et d'un timeframe.

Ce fichier est INDÉPENDANT de Streamlit. Il peut être importé
par le bot (bot_runner.py) ET par le tableau de bord (main.py)
sans aucun conflit.
"""
import pandas as pd
from datetime import datetime

# --- Agents d'analyse ---
from agents.temporal_clock     import TemporalClock
from agents.smc_specialist     import SMCSpecialist
from agents.liquidity_tracker  import LiquidityTracker
from agents.mmxm_logic         import MMXMLogic
from agents.execution_precision import ExecutionPrecision
from agents.bias_expert        import BiasExpert
from agents.checklist_expert   import ChecklistExpert
from agents.correlation_smt    import CorrelationSMT

# --- Import MetaTrader5 avec dégradation gracieuse ---
try:
    import MetaTrader5 as mt5
except ModuleNotFoundError:
    class DummyMT5:
        def __getattr__(self, name):
            if name == 'initialize': return lambda: True
            def dummy(*args, **kwargs): return None
            return dummy
    mt5 = DummyMT5()

# --- Import Plotly avec dégradation gracieuse ---
try:
    import plotly.graph_objects as go
except ModuleNotFoundError:
    class DummyPlotly:
        def __getattr__(self, name):
            def dummy(*args, **kwargs): return DummyPlotly()
            return dummy
    go = DummyPlotly()

import logging.handlers  # AUDIT #26 FIX


def log_diag(msg):
    """Log de diagnostic vers sentinel_pro.log avec rotation (max 5Mo, 3 fichiers)."""
    try:
        import os
        # AUDIT #26 FIX : RotatingFileHandler pour éviter saturation disque
        logger = logging.getLogger("sentinel_pro")
        if not logger.handlers:
            handler = logging.handlers.RotatingFileHandler(
                "sentinel_pro.log",
                maxBytes=5 * 1024 * 1024,  # 5 Mo
                backupCount=3,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d %H:%M:%S"))
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        logger.debug(msg)
    except Exception:
        pass


class ProOrchestrator:
    """
    Orchestrateur principal d'analyse ICT.
    Instancie et coordonne tous les agents pour un symbole donné.
    Utilisé par :
      - Le tableau de bord (main.py) pour afficher les analyses
      - Le bot (bot_runner.py) pour générer les signaux de trading
    """

    def __init__(self, symbol, config: dict = None):
        self.symbol  = symbol
        self.config  = config or {}
        self.time_ac = TemporalClock(self.config)
        self.smc_ac  = SMCSpecialist(symbol)
        self.liq_ac  = LiquidityTracker(symbol)
        self.mmxm_ac = MMXMLogic(symbol)
        self.exe_ac  = ExecutionPrecision(symbol)
        self.bias_ac = BiasExpert(symbol)
        self.chk_ac  = ChecklistExpert()
        self.smt_ac  = self._get_smt_agent(symbol)

    # ============================================================
    # AGENT SMT — Paire corrélée selon le symbole
    # ============================================================
    def _get_smt_agent(self, symbol):
        """Détermine la paire corrélée selon le symbole pour SMT."""
        corr_map = {
            "EURUSD": "GBPUSD", "GBPUSD": "EURUSD",
            "XAUUSD": "XAGUSD", "XAGUSD": "XAUUSD",
            "USDJPY": "EURJPY", "EURJPY": "USDJPY",
            "NAS100": "US500",  "US500":  "NAS100",
            "BTCUSD": "ETHUSD", "ETHUSD": "BTCUSD",
            "USDX":   "EURUSD", # MIN-3 FIX: DXY est corrélé inversement à sa composante majeure
        }
        if symbol is None:
            return CorrelationSMT("XAUUSD", "XAGUSD")
        prefix = symbol[:6].upper()
        base   = symbol.upper()
        corr   = corr_map.get(base, corr_map.get(prefix, "GBPUSD"))
        return CorrelationSMT(symbol, corr)

    # ============================================================
    # FETCH — Récupération des données MT5
    # ============================================================
    def _fetch_pro(self, tf):
        """Récupère les données OHLCV depuis MT5 pour un timeframe donné."""
        tf_map = {
            "MN": mt5.TIMEFRAME_MN1, "W1": mt5.TIMEFRAME_W1,
            "D1": mt5.TIMEFRAME_D1,  "H4": mt5.TIMEFRAME_H4,
            "H1": mt5.TIMEFRAME_H1,  "M15": mt5.TIMEFRAME_M15,
            "M5": mt5.TIMEFRAME_M5,  "M1":  mt5.TIMEFRAME_M1,
        }
        # AUDIT #3 FIX — Nombre de bougies adapté au TF.
        # M1/M5 : besoin de + de bougies pour avoir PDH/PDL du jour précédent.
        # MN/W1 : 250 bougies = trop (20 ans!) — on limite à l'essentiel.
        bars_by_tf = {
            "MN": 60,   # 5 ans de données mensuelles
            "W1": 104,  # 2 ans de données hebdomadaires
            "D1": 200,  # ~10 mois de données journalières
            "H4": 250,  # ~6 semaines de données H4
            "H1": 350,  # ~2 semaines de données H1
            "M15": 480, # ~5 jours en M15 (pdh/pdl/pwh/pwl visibles)
            "M5": 576,  # ~2 jours complets en M5
            "M1": 720,  # ~12 heures en M1 (1 session complète)
        }
        n_bars = bars_by_tf.get(tf, 250)
        try:
            rates = mt5.copy_rates_from_pos(self.symbol, tf_map[tf], 0, n_bars)
            if rates is None or len(rates) < 10:
                log_diag(f"FETCH FAIL {tf}: {mt5.last_error()}")
                return None
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df.rename(columns={
                'open': 'Open', 'high': 'High',
                'low':  'Low',  'close': 'Close'
            }, inplace=True)
            return df
        except Exception as e:
            log_diag(f"FETCH ERROR {tf}: {e}")
            return None

    # ============================================================
    # BUILD CHART — Construction du graphique Plotly
    # ============================================================
    def build_chart_pro(self, df, smc, liq, exe, mmxm, tf,
                        clock=None, smt_result=None):
        """Construit le graphique candlestick Plotly enrichi avec les concepts ICT."""
        try:
            # ── Nombre de bougies affichées selon le TF ──────────────────────
            n_candles = {
                "MN": 24, "W1": 52, "D1": 90,
                "H4": 100, "H1": 120, "M15": 150, "M5": 180, "M1": 200,
            }.get(tf, 120)
            df_p = df.tail(n_candles).copy()

            # ── Timezone NY ──────────────────────────────────────────────────
            import pytz
            if df_p.index.tzinfo is None:
                df_p.index = df_p.index.tz_localize('UTC').tz_convert('America/New_York')
            else:
                df_p.index = df_p.index.tz_convert('America/New_York')

            fig = go.Figure()

            # ════════════════════════════════════════════════════════════════
            # COUCHE 1 : FOND — Sessions ICT (discret, en arrière-plan)
            # ════════════════════════════════════════════════════════════════
            if tf not in ["MN", "W1", "D1"]:
                unique_dates = pd.Series(df_p.index.date).unique()
                recent_dates = unique_dates[-4:] if len(unique_dates) > 4 else unique_dates
                session_colors = {
                    "asia":   "rgba(100,100,180,0.04)",
                    "london": "rgba(41,98,255,0.06)",
                    "ny_am":  "rgba(0,200,100,0.06)",
                    "ny_pm":  "rgba(255,160,0,0.05)",
                }
                for d in recent_dates:
                    try:
                        d_str  = str(d)
                        prev_d = str(pd.Timestamp(d) - pd.Timedelta(days=1))
                        fig.add_vrect(x0=f"{prev_d} 20:00", x1=f"{d_str} 02:00",
                            fillcolor=session_colors["asia"],   line_width=0, layer="below")
                        fig.add_vrect(x0=f"{d_str} 02:00", x1=f"{d_str} 05:00",
                            fillcolor=session_colors["london"], line_width=0, layer="below")
                        fig.add_vrect(x0=f"{d_str} 07:00", x1=f"{d_str} 10:00",
                            fillcolor=session_colors["ny_am"],  line_width=0, layer="below")
                        fig.add_vrect(x0=f"{d_str} 13:00", x1=f"{d_str} 16:00",
                            fillcolor=session_colors["ny_pm"],  line_width=0, layer="below")
                    except Exception:
                        pass

            # ════════════════════════════════════════════════════════════════
            # COUCHE 2 : DEALING RANGE (Premium / EQ / Discount)
            # ════════════════════════════════════════════════════════════════
            swh = smc['structure']['swh']
            swl = smc['structure']['swl']
            mid = (swh + swl) / 2
            last_x = df_p.index[-1]
            first_x = df_p.index[0]

            # Zone Premium (rouge très translucide)
            fig.add_hrect(y0=mid, y1=swh,
                fillcolor="rgba(239,83,80,0.04)", line_width=0, layer="below")
            # Zone Discount (vert très translucide)
            fig.add_hrect(y0=swl, y1=mid,
                fillcolor="rgba(38,166,154,0.04)", line_width=0, layer="below")
            # Ligne EQ (pointillée fine)
            fig.add_shape(type="line", x0=first_x, y0=mid, x1=last_x, y1=mid,
                line=dict(color="rgba(180,180,180,0.35)", width=1, dash="dot"),
                xref="x", yref="y", layer="below")
            fig.add_annotation(
                x=last_x, y=mid, text="EQ 50%", showarrow=False,
                font=dict(size=9, color="rgba(180,180,180,0.6)"),
                xanchor="left", yanchor="middle", xref="x", yref="y",
                xshift=6
            )

            # ════════════════════════════════════════════════════════════════
            # COUCHE 3 : FVGs (Fair Value Gaps)
            # Zone colorée + ligne CE pointillée + label compact
            # ════════════════════════════════════════════════════════════════
            def _normalize_ts(ts):
                t = pd.to_datetime(ts)
                if t.tzinfo is None:
                    return t.tz_localize('UTC').tz_convert('America/New_York')
                return t.tz_convert('America/New_York')

            df_p_start = _normalize_ts(df_p.index[0])

            for f in smc['fvgs_pd_arrays']['all_fvgs'][-5:]:
                f_idx = _normalize_ts(f['index'])
                if f_idx < df_p_start:
                    continue
                is_bull = "BISI" in f['type']
                fc  = "rgba(0,200,100,0.12)"  if is_bull else "rgba(239,83,80,0.12)"
                lc  = "#00c864"               if is_bull else "#ef5350"
                label = "BISI FVG" if is_bull else "SIBI FVG"
                # Rectangle FVG
                fig.add_shape(type="rect", x0=f_idx, y0=f['bot'], x1=last_x, y1=f['top'],
                    fillcolor=fc, line=dict(color=lc, width=0.8, dash="dot"),
                    xref="x", yref="y", layer="above")
                # Ligne CE (50% du FVG)
                fig.add_shape(type="line", x0=f_idx, y0=f['ce'], x1=last_x, y1=f['ce'],
                    line=dict(color=lc, width=0.6, dash="dash"),
                    xref="x", yref="y")
                # Label à droite
                fig.add_annotation(
                    x=last_x, y=f['ce'], text=f"  {label}",
                    showarrow=False, font=dict(size=8, color=lc),
                    xanchor="left", yanchor="middle", xref="x", yref="y",
                    xshift=4
                )

            # ════════════════════════════════════════════════════════════════
            # COUCHE 4 : ORDER BLOCKS
            # Rectangle solide avec label net à droite
            # ════════════════════════════════════════════════════════════════
            for b in smc['institutional_blocks'][-3:]:
                b_idx = _normalize_ts(b['index'])
                if b_idx < df_p_start:
                    continue
                is_bull_ob = "BULL" in b['type']
                bc    = "rgba(41,98,255,0.18)"  if is_bull_ob else "rgba(239,83,80,0.18)"
                lc_ob = "#2962ff"               if is_bull_ob else "#ef5350"
                label_ob = "BULL OB" if is_bull_ob else "BEAR OB"
                if "BREAKER" in b['type']:
                    label_ob = "BRK ↑" if is_bull_ob else "BRK ↓"
                    bc    = "rgba(240,180,40,0.15)"
                    lc_ob = "#f0b429"

                z0, z1 = b['refined_zone'][0], b['refined_zone'][1]
                fig.add_shape(type="rect", x0=b_idx, y0=z0, x1=last_x, y1=z1,
                    fillcolor=bc, line=dict(color=lc_ob, width=1.2),
                    xref="x", yref="y", layer="above")
                # Label à droite de l'OB
                fig.add_annotation(
                    x=last_x, y=(z0 + z1) / 2, text=f"  {label_ob}",
                    showarrow=False, font=dict(size=9, color=lc_ob, family="monospace"),
                    xanchor="left", yanchor="middle", xref="x", yref="y",
                    bgcolor="rgba(6,9,14,0.6)", xshift=4
                )

            # ════════════════════════════════════════════════════════════════
            # COUCHE 5 : LIQUIDITÉ (BSL / SSL / EQH / EQL)
            # Lignes nettes avec labels à droite (style MT5/TradingView)
            # ════════════════════════════════════════════════════════════════
            erl_h = liq['erl']['high']
            erl_l = liq['erl']['low']

            # BSL (liquidity en haut — cible BULL)
            fig.add_shape(type="line", x0=first_x, y0=erl_h, x1=last_x, y1=erl_h,
                line=dict(color="#ef5350", width=1.8, dash="dash"),
                xref="x", yref="y")
            fig.add_annotation(x=last_x, y=erl_h,
                text=f"  🔴 BSL", showarrow=False,
                font=dict(size=10, color="#ef5350", family="monospace"),
                xanchor="left", yanchor="middle", xref="x", yref="y",
                bgcolor="rgba(239,83,80,0.15)", bordercolor="#ef5350",
                borderwidth=1, xshift=4)

            # SSL (liquidity en bas — cible BEAR)
            fig.add_shape(type="line", x0=first_x, y0=erl_l, x1=last_x, y1=erl_l,
                line=dict(color="#26a69a", width=1.8, dash="dash"),
                xref="x", yref="y")
            fig.add_annotation(x=last_x, y=erl_l,
                text=f"  🟢 SSL", showarrow=False,
                font=dict(size=10, color="#26a69a", family="monospace"),
                xanchor="left", yanchor="middle", xref="x", yref="y",
                bgcolor="rgba(38,166,154,0.15)", bordercolor="#26a69a",
                borderwidth=1, xshift=4)

            # EQH (Equal Highs — SMOOTH seulement)
            for eq in [e for e in liq['eqh'] if e['quality'] == 'SMOOTH' and not e.get('swept')][:2]:
                fig.add_shape(type="line", x0=first_x, y0=eq['price'], x1=last_x, y1=eq['price'],
                    line=dict(color="rgba(239,83,80,0.6)", width=1, dash="dot"),
                    xref="x", yref="y")
                fig.add_annotation(x=last_x, y=eq['price'], text="  EQH",
                    showarrow=False, font=dict(size=8, color="rgba(239,83,80,0.8)"),
                    xanchor="left", yanchor="middle", xref="x", yref="y", xshift=4)

            # EQL (Equal Lows — SMOOTH seulement)
            for eq in [e for e in liq['eql'] if e['quality'] == 'SMOOTH' and not e.get('swept')][:2]:
                fig.add_shape(type="line", x0=first_x, y0=eq['price'], x1=last_x, y1=eq['price'],
                    line=dict(color="rgba(38,166,154,0.6)", width=1, dash="dot"),
                    xref="x", yref="y")
                fig.add_annotation(x=last_x, y=eq['price'], text="  EQL",
                    showarrow=False, font=dict(size=8, color="rgba(38,166,154,0.8)"),
                    xanchor="left", yanchor="middle", xref="x", yref="y", xshift=4)

            # ════════════════════════════════════════════════════════════════
            # COUCHE 6 : MIDNIGHT OPEN
            # ════════════════════════════════════════════════════════════════
            mo = mmxm.get('midnight_open', 0)
            if mo > 0 and tf not in ["MN", "W1", "D1"]:
                fig.add_shape(type="line", x0=first_x, y0=mo, x1=last_x, y1=mo,
                    line=dict(color="rgba(209,212,220,0.5)", width=1, dash="dashdot"),
                    xref="x", yref="y")
                fig.add_annotation(x=last_x, y=mo, text="  MO",
                    showarrow=False, font=dict(size=9, color="rgba(209,212,220,0.7)"),
                    xanchor="left", yanchor="middle", xref="x", yref="y", xshift=4)

            # ════════════════════════════════════════════════════════════════
            # COUCHE 7 : STRUCTURE BOS / MSS
            # Triangle discret sur le swing concerné
            # ════════════════════════════════════════════════════════════════
            mode = smc['structure']['mode']
            if "MSS" in mode or "BOS" in mode:
                struct_color = "#00c864" if "BULL" in mode else "#ef5350"
                struct_y     = swh       if "BULL" in mode else swl
                fig.add_annotation(
                    x=df_p.index[int(len(df_p) * 0.75)],
                    y=struct_y,
                    text=f"◀ {mode}",
                    showarrow=False,
                    font=dict(size=10, color=struct_color, family="monospace"),
                    xref="x", yref="y",
                    bgcolor="rgba(6,9,14,0.8)",
                    bordercolor=struct_color, borderwidth=1,
                    borderpad=3
                )

            # ════════════════════════════════════════════════════════════════
            # COUCHE 8 : SMT DIVERGENCE
            # ════════════════════════════════════════════════════════════════
            if smt_result and smt_result.get('smt_divergence'):
                smt_type = smt_result.get('smt_type', 'SMT DIV')
                fig.add_annotation(
                    x=df_p.index[-3], y=df_p['High'].iloc[-3],
                    text=f"🔗 {smt_type}",
                    showarrow=True, arrowhead=2, arrowcolor="#f0b429",
                    font=dict(size=11, color="#f0b429"),
                    bgcolor="rgba(6,9,14,0.85)", bordercolor="#f0b429",
                    borderwidth=1
                )

            # ════════════════════════════════════════════════════════════════
            # COUCHE 9 : POSITIONS ACTIVES (Entry / SL / TP)
            # ════════════════════════════════════════════════════════════════
            try:
                symbol_positions = exe.get('active_positions', []) if isinstance(exe, dict) else []
                for pos in symbol_positions:
                    if pos.get("state") not in ("ACTIVE", "PENDING"):
                        continue
                    direction = pos.get("direction", "")
                    arrow     = "▲" if direction == "BUY" else "▼"
                    for level, color, label in [
                        (pos.get("entry", 0), "#4dabff", f"{arrow} ENTRY"),
                        (pos.get("sl",    0), "#ef5350", "⛔ SL"),
                        (pos.get("tp1",   0), "#f0b429", "🎯 TP1"),
                        (pos.get("tp2",   0), "#00c864", "🏆 TP2"),
                    ]:
                        if level > 0:
                            fig.add_shape(type="line",
                                x0=first_x, y0=level, x1=last_x, y1=level,
                                line=dict(color=color, width=1.5, dash="dash"),
                                xref="x", yref="y")
                            fig.add_annotation(x=last_x, y=level,
                                text=f"  {label}",
                                showarrow=False,
                                font=dict(size=9, color=color, family="monospace"),
                                xanchor="left", yanchor="middle",
                                xref="x", yref="y",
                                bgcolor="rgba(6,9,14,0.7)", xshift=4)
            except Exception:
                pass

            # ════════════════════════════════════════════════════════════════
            # COUCHE 10 : BOUGIES (au-dessus de tout le reste)
            # ════════════════════════════════════════════════════════════════
            fig.add_trace(go.Candlestick(
                x=df_p.index,
                open=df_p['Open'], high=df_p['High'],
                low=df_p['Low'],   close=df_p['Close'],
                name=self.symbol,
                increasing=dict(line=dict(color='#26a69a', width=1.5), fillcolor='#26a69a'),
                decreasing=dict(line=dict(color='#ef5350', width=1.5), fillcolor='#ef5350'),
                whiskerwidth=0.3,
            ))

            # ════════════════════════════════════════════════════════════════
            # COUCHE 11 : PRIX ACTUEL (dernière bougie MT5)
            # Ligne blanche visible avec étiquette prix à droite
            # ════════════════════════════════════════════════════════════════
            try:
                import MetaTrader5 as mt5
                tick = mt5.symbol_info_tick(self.symbol)
                live_price = tick.bid if tick else None
            except Exception:
                live_price = None

            current_price = live_price if live_price else float(df_p['Close'].iloc[-1])

            # Ligne prix actuel
            fig.add_shape(type="line", x0=first_x, y0=current_price, x1=last_x, y1=current_price,
                line=dict(color="rgba(255,255,255,0.85)", width=1.2, dash="solid"),
                xref="x", yref="y")

            # Nombre de décimales selon l'instrument
            sym_u = self.symbol.upper()
            if any(x in sym_u for x in ['BTC', 'ETH', 'NAS', 'US30', 'US500']):
                price_fmt = f"{current_price:,.2f}"
            elif 'JPY' in sym_u:
                price_fmt = f"{current_price:.3f}"
            elif 'XAU' in sym_u or 'XAG' in sym_u:
                price_fmt = f"{current_price:.2f}"
            else:
                price_fmt = f"{current_price:.5f}"

            # Étiquette prix (style MT5 — fond coloré selon sens)
            last_open  = float(df_p['Open'].iloc[-1])
            price_bg   = "rgba(38,166,154,0.9)"  if current_price >= last_open else "rgba(239,83,80,0.9)"
            fig.add_annotation(
                x=last_x, y=current_price,
                text=f"  {price_fmt}  ",
                showarrow=False,
                font=dict(size=11, color="white", family="monospace"),
                xanchor="left", yanchor="middle",
                xref="x", yref="y",
                bgcolor=price_bg, bordercolor="rgba(255,255,255,0.3)",
                borderwidth=1, xshift=4
            )

            # ════════════════════════════════════════════════════════════════
            # RANGEBREAKS — Forex/Indices uniquement (pas Crypto 24/7)
            # ════════════════════════════════════════════════════════════════
            if tf not in ["MN", "W1"]:
                is_crypto = any(x in sym_u for x in ['BTC','ETH','XRP','SOL','BNB'])
                if not is_crypto:
                    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])

            # ════════════════════════════════════════════════════════════════
            # LAYOUT FINAL — Style TradingView sombre épuré
            # ════════════════════════════════════════════════════════════════

            # Titre du graphique avec info TF + symbole
            tf_labels = {"MN":"1M","W1":"1W","D1":"1D","H4":"4H","H1":"1H","M15":"15","M5":"5","M1":"1"}
            tf_badge  = tf_labels.get(tf, tf)

            # Couleur du biais HTF
            bias_str = ""
            if smc['structure']:
                bias_str = "🟢" if "BULL" in mode else ("🔴" if "BEAR" in mode else "⚪")

            fig.update_layout(
                template="plotly_dark",
                height=680,
                margin=dict(l=10, r=120, b=25, t=36),  # r=120 pour les labels droite
                xaxis_rangeslider_visible=False,
                showlegend=False,       # Légende désactivée (trop de bruit — infos en annotations)
                paper_bgcolor="#131722",
                plot_bgcolor="#131722",
                dragmode='pan',
                uirevision=self.symbol + tf,
                hovermode='x unified',
                title=dict(
                    text=f"<b>{self.symbol}</b>  <span style='color:#848e9c'>{tf_badge}</span>  {bias_str}",
                    font=dict(size=14, color="#d1d4dc"),
                    x=0.01, y=0.99, xanchor="left", yanchor="top"
                ),
                yaxis=dict(
                    gridcolor="rgba(42,46,57,0.4)",
                    side="right",
                    fixedrange=False, zeroline=False,
                    tickfont=dict(size=10, color="#848e9c"),
                    tickformat=",",
                ),
                xaxis=dict(
                    gridcolor="rgba(42,46,57,0.25)",
                    fixedrange=False,
                    type='date',
                    tickmode='auto',
                    nticks=7,
                    showgrid=True,
                    tickfont=dict(size=10, color="#848e9c"),
                    tickformat="%d %b\n%H:%M" if tf not in ["MN","W1","D1"] else "%b %Y",
                ),
                hoverlabel=dict(
                    bgcolor="#1e222d",
                    bordercolor="#2a2e39",
                    font=dict(size=11, color="#d1d4dc"),
                ),
            )
            return fig

        except Exception as e:
            log_diag(f"CHART ERROR {tf}: {e}")
            return go.Figure()
