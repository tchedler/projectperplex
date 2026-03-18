"""
pa_orchestrator.py — Coordinateur de l'Analyse Price Action
============================================================
Orchestre le PAFeatureExtractor et le PAChecklistExpert pour produire
une analyse Price Action complète, indépendante du moteur ICT.

ISOLATION : Ce fichier ne peut pas importer quoi que ce soit depuis
            orchestrator.py, smc_specialist.py, liquidity_tracker.py, etc.
"""

import pandas as pd
import logging

# Nos agents PA (et uniquement eux)
from agents.pa_feature_extractor import PAFeatureExtractor
from agents.pa_checklist_expert  import PAChecklistExpert

# MT5 avec dégradation gracieuse (idem orchestrator.py ICT)
try:
    import MetaTrader5 as mt5
except ModuleNotFoundError:
    class _DummyMT5:
        def __getattr__(self, name):
            def dummy(*a, **kw): return None
            return dummy
    mt5 = _DummyMT5()


# ── TimeFrame Map ────────────────────────────────────────────────────────
TF_MAP = {
    "MN":  "TIMEFRAME_MN1", "W1": "TIMEFRAME_W1",
    "D1":  "TIMEFRAME_D1",  "H4": "TIMEFRAME_H4",
    "H1":  "TIMEFRAME_H1",  "M15": "TIMEFRAME_M15",
    "M5":  "TIMEFRAME_M5",  "M1": "TIMEFRAME_M1",
}

BARS_BY_TF = {
    "MN": 60, "W1": 104, "D1": 200, "H4": 250,
    "H1": 350, "M15": 480, "M5": 576, "M1": 720,
}


class PAOrchestrator:
    """
    Coordinateur Price Action pour un symbole donné.
    Méthode principale : analyze(tf) → dict d'analyse PA complète.
    """

    def __init__(self, symbol: str):
        self.symbol    = symbol
        self.extractor = PAFeatureExtractor()
        self.expert    = PAChecklistExpert()

    # ════════════════════════════════════════════════════════════════════
    # POINT D'ENTRÉE PRINCIPAL
    # ════════════════════════════════════════════════════════════════════
    def analyze(self, tf: str, score_execute: int = 80, score_limit: int = 65) -> dict:
        """
        Analyse Price Action complète pour self.symbol sur le timeframe `tf`.
        Retourne un dict avec : html_checklist, score, verdict, direction,
                                narratif, features, dernière mise à jour.
        """
        try:
            df = self._fetch(tf)
            if df is None or df.empty:
                return self._empty_result(tf, "Données MT5 indisponibles")

            # 1. Extraction des features PA
            features = self.extractor.extract(df)

            # 2. Checklist Expert PA (score + HTML)
            html, score, verdict, direction = self.expert.generate(
                tf, features, score_execute=score_execute, score_limit=score_limit
            )

            # 3. Narratif textuel PA (en français)
            narratif = self._build_narrative(tf, features, direction, score, verdict)

            # 4. Niveaux clés pour affichage (SL/TP)
            levels = self._build_key_levels(features, direction)

            from datetime import datetime
            return {
                "ok":           True,
                "tf":           tf,
                "symbol":       self.symbol,
                "score":        score,
                "verdict":      verdict,
                "direction":    direction,
                "html":         html,
                "narratif":     narratif,
                "levels":       levels,
                "features":     features,
                "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
            }

        except Exception as e:
            logging.getLogger("pa_orch").exception("PA analyze error: %s", e)
            return self._empty_result(tf, str(e))

    # ════════════════════════════════════════════════════════════════════
    # FETCH — Récupération bougies MT5
    # ════════════════════════════════════════════════════════════════════
    def _fetch(self, tf: str) -> pd.DataFrame:
        """Récupère les bougies OHLCV depuis MT5 pour le symbole et le TF."""
        tf_attr = TF_MAP.get(tf)
        if tf_attr is None:
            return None
        mt5_tf = getattr(mt5, tf_attr, None)
        if mt5_tf is None:
            return None

        nb_bars = BARS_BY_TF.get(tf, 300)
        rates = mt5.copy_rates_from_pos(self.symbol, mt5_tf, 0, nb_bars)
        if rates is None or len(rates) == 0:
            return None

        df = pd.DataFrame(rates)
        df.rename(columns={"time": "time", "open": "open", "high": "high",
                            "low": "low", "close": "close",
                            "tick_volume": "tick_volume"}, inplace=True)
        return df

    # ════════════════════════════════════════════════════════════════════
    # NARRATIF — Résumé PA en français
    # ════════════════════════════════════════════════════════════════════
    def _build_narrative(self, tf: str, features: dict,
                          direction: str, score: int, verdict: str) -> str:
        cycle    = features.get("cycle", {})
        ema_pos  = features.get("ema_position", {})
        bar_cnt  = features.get("bar_count", {})
        last_sig = features.get("last_signal", {})
        mc       = features.get("microchannel", {})
        patterns = features.get("patterns", {})
        mm       = features.get("measured_move", {})

        cycle_type = cycle.get("type", "INCONNU")
        b_setup    = bar_cnt.get("bullish_setup", "")
        s_setup    = bar_cnt.get("bearish_setup", "")
        setup_lbl  = b_setup or s_setup or "Aucun setup"

        ema_txt = "au-dessus" if ema_pos.get("above_ema") else "en dessous"
        ema_touch = ema_pos.get("ema_touch_last3")

        # Narratif cycle
        cycle_msgs = {
            "BULL_CANAL":    "en Canal Haussier — Always In Long",
            "BEAR_CANAL":    "en Canal Baissier — Always In Short",
            "BREAKOUT_BULL": "en Breakout Haussier Fort — Urgence absolue (Ne pas vendre !)",
            "BREAKOUT_BEAR": "en Breakout Baissier Fort — Urgence absolue (Ne pas acheter !)",
            "TRADING_RANGE": "dans un Trading Range — Scalping uniquement (Buy Low / Sell High)",
            "TIGHT_RANGE":   "dans un Tight Range (Barb Wire) — ZONE INTERDITE",
        }
        cycle_msg = cycle_msgs.get(cycle_type, f"dans un cycle {cycle_type}")

        # Narratif EMA
        ema_msg = ""
        if ema_touch:
            ema_msg = "La dernière bougie a touché et rejeté l'EMA 20 (Pullback validé). "
        else:
            pct = abs(ema_pos.get("pct_from_ema", 0))
            ema_msg = f"Le prix est {ema_txt} de l'EMA 20 ({pct:.3f}% de distance). "

        # Narratif Signal Bar
        sig_quality = last_sig.get("quality", "FAIBLE")
        sig_type    = last_sig.get("bar_type", "doji")
        sig_msgs = {
            "FORTE":        f"Signal Bar puissante ({sig_type}) identifiée. ",
            "MODÉRÉE":      f"Présence d'une Trend Bar ({sig_type}). ",
            "COMPRESSION":  "Inside Bar de compression — Attendre la cassure directionnelle. ",
            "NEUTRE":       "Doji sans confirmation — Setup insuffisant. ",
            "FAIBLE":       "Aucun signal bar clair sur la dernière bougie. ",
        }
        sig_msg = sig_msgs.get(sig_quality, "")

        # Narratif Patterns
        pts_detected = patterns.get("detected", [])
        pts_msg = ""
        if "DOUBLE_BOTTOM" in pts_detected:
            pts_msg = "Double Bottom (W) détecté : pullback haussier probable sur cassure du neckline. "
        elif "DOUBLE_TOP" in pts_detected:
            pts_msg = "Double Top (M) détecté : retournement baissier probable. "
        elif "BULL_FLAG" in pts_detected:
            pts_msg = "Bull Flag identifiée : continuation haussière probable. "
        elif "SYMMETRIC_TRIANGLE" in pts_detected:
            pts_msg = "Triangle Symétrique : compression forte — breakout imminent (direction inconnue). "

        # Narratif Micro-Canal
        mc_msg = ""
        if mc.get("danger"):
            mc_msg = "⚠️ ATTENTION : Micro-Canal Baissier actif — Ne pas acheter le premier pullback. "

        # Narratif Measured Move
        mm_msg = ""
        if mm.get("valid"):
            target = mm.get("mm_bull_target") if direction == "BUY" else mm.get("mm_bear_target")
            mm_msg = f"Cible Measured Move projetée à {target}. "

        # Composition finale
        parts = [
            f"Sur le timeframe {tf}, le marché {self.symbol} est {cycle_msg}. ",
            f"Setup détecté : {setup_lbl}. ",
            ema_msg,
            sig_msg,
            mc_msg,
            pts_msg,
            mm_msg,
            f"VERDICT PA : {verdict}.",
        ]
        return "".join(p for p in parts if p.strip())

    # ════════════════════════════════════════════════════════════════════
    # NIVEAUX CLÉS (SL / TP suggérés)
    # ════════════════════════════════════════════════════════════════════
    def _build_key_levels(self, features: dict, direction: str) -> dict:
        sr     = features.get("sr_levels", [])
        mm     = features.get("measured_move", {})
        last   = features.get("last_signal", {})
        df_raw = features.get("df", pd.DataFrame())

        sl, tp1, tp2 = None, None, None

        try:
            if not df_raw.empty:
                last_bar = df_raw.iloc[-1]
                if direction == "BUY":
                    sl  = round(last_bar["low"], 5)
                    tp1 = round(sr[-1], 5) if sr else None
                    tp2 = mm.get("mm_bull_target")
                elif direction == "SELL":
                    sl  = round(last_bar["high"], 5)
                    tp1 = round(sr[0], 5) if sr else None
                    tp2 = mm.get("mm_bear_target")
        except Exception:
            pass

        return {"sl": sl, "tp1": tp1, "tp2": tp2}

    # ════════════════════════════════════════════════════════════════════
    # GRAPHIQUE PRICE ACTION ANNOTÉ (Plotly)
    # ════════════════════════════════════════════════════════════════════
    def build_pa_chart(self, tf: str, features: dict, direction: str, levels: dict):
        """
        Construit un graphique Plotly annoté avec tous les marqueurs Price Action :
        - Bougies japonaises (OHLC)
        - EMA 20 (Ligne de Vie)
        - Niveaux S/R horizontaux
        - Labels H1/H2/L1/L2 sur les bougies
        - Marqueurs Signal Bar (flèches)
        - Ligne Measured Move (cible)
        - Zone Micro-Canal (fond coloré)
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            import pandas as pd

            df = features.get("df", pd.DataFrame())
            if df is None or df.empty or "time" not in df.columns:
                return None
            df = df.tail(80).copy()

            times = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_convert("Europe/Paris")

            # ── Figure de base : Subplots (3 lignes) ────────────────────
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True,
                vertical_spacing=0.04, row_heights=[0.6, 0.2, 0.2]
            )

            # [Row 1] Chandeliers
            fig.add_trace(go.Candlestick(
                x=times, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
                name="Prix", increasing_line_color="#00ff88", decreasing_line_color="#ef5350",
                increasing_fillcolor="#004d2a", decreasing_fillcolor="#4d0000",
            ), row=1, col=1)

            # [Row 1] EMA 20
            if "ema20" in df.columns:
                fig.add_trace(go.Scatter(
                    x=times, y=df["ema20"], mode="lines", name="EMA 20",
                    line=dict(color="#f0b429", width=1.5, dash="dot"), opacity=0.85,
                ), row=1, col=1)

            # Niveaux S/R
            sr_levels = features.get("sr_levels", [])
            for lvl in sr_levels[-6:]:
                fig.add_hline(y=lvl, line=dict(color="#4dabff", width=1, dash="dash"), opacity=0.5, row=1, col=1)

            # SL et MM
            if levels.get("sl"):
                fig.add_hline(y=levels["sl"], line=dict(color="#ef5350", width=1, dash="dot"), opacity=0.6, row=1, col=1)
            
            mm = features.get("measured_move", {})
            if mm.get("valid"):
                mm_target = mm.get("mm_bull_target") if direction == "BUY" else mm.get("mm_bear_target")
                if mm_target:
                    fig.add_hline(y=mm_target, line=dict(color="#d4a017", width=1.5, dash="longdash"), opacity=0.7, row=1, col=1)

            # Annotations Row 1
            bar_count = features.get("bar_count", {})
            h_count = bar_count.get("h_count", 0)
            l_count = bar_count.get("l_count", 0)
            last_bar = df.iloc[-1]
            last_time = times.iloc[-1]

            if h_count >= 1:
                label = f"H{min(h_count, 2)}"
                fig.add_annotation(x=last_time, y=last_bar["low"], text=f"▲ {label}", showarrow=True, arrowhead=2, arrowcolor="#00ff88", ax=0, ay=30, row=1, col=1)
            elif l_count >= 1:
                label = f"L{min(l_count, 2)}"
                fig.add_annotation(x=last_time, y=last_bar["high"], text=f"▼ {label}", showarrow=True, arrowhead=2, arrowcolor="#ef5350", ax=0, ay=-30, row=1, col=1)

            last_sig = features.get("last_signal", {})
            if last_sig.get("quality") == "FORTE":
                arrow_y = last_bar["low"] if direction == "BUY" else last_bar["high"]
                arrow_color = "#00ff88" if direction == "BUY" else "#ef5350"
                fig.add_annotation(x=last_time, y=arrow_y, text="SIGNAL", showarrow=True, arrowhead=3, arrowcolor=arrow_color, ax=0, ay=40 if direction=="BUY" else -40, row=1, col=1)

            # [Row 2] Volume
            vol_col = "tick_volume" if "tick_volume" in df.columns else ("volume" if "volume" in df.columns else None)
            if vol_col:
                colors = ["#00ff88" if c > o else "#ef5350" for c, o in zip(df["close"], df["open"])]
                fig.add_trace(go.Bar(
                    x=times, y=df[vol_col], name="Volume", marker_color=colors, opacity=0.7
                ), row=2, col=1)
                
                if "vol_ma" in df.columns:
                    fig.add_trace(go.Scatter(
                        x=times, y=df["vol_ma"], mode="lines", name="Vol MA(20)",
                        line=dict(color="#d4a017", width=1.5), opacity=0.9
                    ), row=2, col=1)

            # [Row 3] RSI
            if "rsi" in df.columns:
                fig.add_trace(go.Scatter(
                    x=times, y=df["rsi"], mode="lines", name="RSI(14)",
                    line=dict(color="#4dabff", width=1.5)
                ), row=3, col=1)
                
                # Lignes 70, 30, 50
                fig.add_hline(y=70, line=dict(color="#ef5350", width=1, dash="dot"), opacity=0.5, row=3, col=1)
                fig.add_hline(y=30, line=dict(color="#00ff88", width=1, dash="dot"), opacity=0.5, row=3, col=1)
                fig.add_hline(y=50, line=dict(color="#f0b429", width=1, dash="dash"), opacity=0.3, row=3, col=1)

            # Style global
            cycle_type = features.get("cycle", {}).get("type", "?")
            cyc_color = "#f0b429" if "CANAL" in cycle_type else ("#00ff88" if "BREAKOUT" in cycle_type else ("#ef5350" if "TIGHT" in cycle_type else "#848e9c"))
            
            fig.update_layout(
                title=dict(text=f"📊 {self.symbol} — {tf} | Cycle : {cycle_type.replace('_',' ')} | {direction}", font=dict(color=cyc_color, size=13)),
                paper_bgcolor="#0e1117", plot_bgcolor="#000000",
                font=dict(color="#d4d4d4", size=10),
                height=750, margin=dict(l=10, r=10, t=40, b=10),
                showlegend=False, xaxis_rangeslider_visible=False
            )
            
            # Grilles
            fig.update_xaxes(gridcolor="#1e2130", showgrid=True)
            fig.update_yaxes(gridcolor="#1e2130", showgrid=True, side="right")

            return fig

        except Exception as e:
            logging.getLogger("pa_orch").warning("PA chart error: %s", e)
            return None

    # ════════════════════════════════════════════════════════════════════
    # Résultat vide en cas d'erreur
    # ════════════════════════════════════════════════════════════════════
    def _empty_result(self, tf: str, reason: str) -> dict:
        return {
            "ok":        False,
            "tf":        tf,
            "symbol":    self.symbol,
            "score":     0,
            "verdict":   "EN ATTENTE",
            "direction": "NEUTRE",
            "html":      f"<p style='color:#848e9c'>⏳ Analyse PA en attente — {reason}</p>",
            "narratif":  f"Analyse PA indisponible : {reason}",
            "levels":    {"sl": None, "tp1": None, "tp2": None},
            "features":  {},
            "last_updated": None,
        }
