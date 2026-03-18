"""
pa_feature_extractor.py — Extracteur de Données Price Action
============================================================
Module INDÉPENDANT du moteur ICT.
Lit uniquement les données OHLCV brutes et calcule les concepts PA issus
de la Bible Price Action (Chapitres 1 à 8).

Concept clé : Ce module ne sait RIEN de l'ICT (pas de FVG, pas d'OB, pas de Sweep).
Il ne connaît que les bougies, l'EMA, et la structure classique.
"""

import pandas as pd
import numpy as np


class PAFeatureExtractor:
    """
    Extrait toutes les features Price Action à partir d'un DataFrame OHLCV.
    Entrée  : pd.DataFrame avec colonnes ['open', 'high', 'low', 'close', 'tick_volume']
    Sortie  : dict structuré (pa_features)
    """

    # ── Paramètres (ajustables) ────────────────────────────────────────────
    EMA_PERIOD    = 20       # Ligne de Vie (Brooks)
    RSI_PERIOD    = 14       # RSI standard
    VOL_MA_PERIOD = 20       # MA du volume (référence)
    BODY_RATIO    = 0.50     # Corps > 50% du range → Trend Bar
    REVERSAL_WICK = 0.33     # Mèche > 1/3 du range → Signal Bar (Pin Bar)
    MICROCHANNEL_BARS = 3    # Nb barres min pour un Micro-Canal
    SR_LOOKBACK   = 50       # Nb bougies pour S/R horizontaux
    SR_TOLERANCE  = 0.0020   # Tolérance S/R (0.2%)
    OVERLAP_THRESH = 0.30    # Overlap de corps

    def extract(self, df: pd.DataFrame) -> dict:
        """
        Point d'entrée principal. Retourne le dictionnaire PA complet.
        """
        if df is None or len(df) < max(self.EMA_PERIOD + 5, 20):
            return self._empty_features()

        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        # ── EMA 20 ────────────────────────────────────────────────────────
        df["ema20"] = df["close"].ewm(span=self.EMA_PERIOD, adjust=False).mean()

        # ── Classification de chaque bougie ───────────────────────────────
        df = self._classify_bars(df)

        # ── Phase/Cycle du marché ─────────────────────────────────────────
        cycle = self._detect_cycle(df)

        # ── Dot EMA (position prix vs EMA) ───────────────────────────────
        ema_position = self._ema_position(df)

        # ── Bar Counting (H1/H2, L1/L2) ───────────────────────────────────
        bar_count = self._count_pullback_legs(df)

        # ── Dernière Signal Bar (Pin Bar, Reversal, Inside Bar) ──────────
        last_signal = self._detect_last_signal_bar(df)

        # ── Supports & Résistances horizontaux ───────────────────────────
        sr_levels = self._detect_support_resistance(df)

        # ── Measured Move (Leg 1 → Cible Leg 2) ──────────────────────────
        measured_move = self._compute_measured_move(df)

        # ── Micro-Canal (danger : inertie trop forte) ────────────────────
        microchannel = self._detect_microchannel(df)

        # ── Patterns Classiques (Double Top/Bottom, Flag, Triangle) ──────
        patterns = self._detect_patterns(df)

        # ── SECTION 10 — RSI (14) + Divergences ──────────────────────────
        rsi_data = self._compute_rsi(df)

        # ── SECTION 11 — Analyse Volumétrique ────────────────────────────
        volume_data = self._analyze_volume(df)

        return {
            "cycle":        cycle,
            "ema_position": ema_position,
            "bar_count":    bar_count,
            "last_signal":  last_signal,
            "sr_levels":    sr_levels,
            "measured_move": measured_move,
            "microchannel": microchannel,
            "patterns":     patterns,
            "rsi":          rsi_data,
            "volume":       volume_data,
            "df":           df,
        }

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 1 — Classification des Barres (Chapitre 2 — Bible PA)
    # ══════════════════════════════════════════════════════════════════════
    def _classify_bars(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ajoute colonnes : bar_type, body_pct, upper_wick_pct, lower_wick_pct,
                          is_bullish, is_bearish, is_inside, is_outside, overlap.
        """
        df["bar_range"]       = df["high"] - df["low"]
        df["body"]            = abs(df["close"] - df["open"])
        df["is_bullish"]      = df["close"] > df["open"]
        df["is_bearish"]      = df["close"] < df["open"]
        df["body_pct"]        = df["body"] / df["bar_range"].replace(0, np.nan)
        df["upper_wick_pct"]  = (df["high"] - df[["open", "close"]].max(axis=1)) / df["bar_range"].replace(0, np.nan)
        df["lower_wick_pct"]  = (df[["open", "close"]].min(axis=1) - df["low"]) / df["bar_range"].replace(0, np.nan)
        df["close_pct"]       = (df["close"] - df["low"]) / df["bar_range"].replace(0, np.nan)

        # Type de barre
        conditions = [
            df["body_pct"] > self.BODY_RATIO,                                         # Trend Bar
            (df["lower_wick_pct"] > self.REVERSAL_WICK) & df["is_bullish"],           # Bull Reversal / Pin Bar
            (df["upper_wick_pct"] > self.REVERSAL_WICK) & df["is_bearish"],           # Bear Reversal / Shooting Star
        ]
        choices = ["trend_bar", "bull_reversal", "bear_reversal"]
        df["bar_type"] = np.select(conditions, choices, default="doji")

        # Inside / Outside Bars (Chapitre 7 — Micro-structures)
        df["is_inside"]  = (df["high"] <= df["high"].shift(1)) & (df["low"] >= df["low"].shift(1))
        df["is_outside"] = (df["high"] >  df["high"].shift(1)) & (df["low"] <  df["low"].shift(1))

        # Gap de corps (Body Gap — signe de force)
        df["body_gap_bull"] = df["open"] > df["close"].shift(1)
        df["body_gap_bear"] = df["open"] < df["close"].shift(1)

        return df

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 2 — Cycle de Marché (Chapitre 1 — Bible PA)
    # ══════════════════════════════════════════════════════════════════════
    def _detect_cycle(self, df: pd.DataFrame) -> dict:
        """
        Détecte le cycle : Breakout / BullCanal / BearCanal / TradingRange / TightRange.
        Utilise les 20 dernières barres.
        """
        tail = df.tail(20)
        closes = tail["close"].values
        highs  = tail["high"].values
        lows   = tail["low"].values

        # Nombre de Trend Bars consécutives récentes
        bullTrend = tail[(tail["bar_type"] == "trend_bar") & tail["is_bullish"]].tail(5)
        bearTrend = tail[(tail["bar_type"] == "trend_bar") & tail["is_bearish"]].tail(5)
        nb_bull = len(bullTrend)
        nb_bear = len(bearTrend)

        # Détection Breakout : 3+ trend bars de même sens sans overlap
        def is_breakout(bars):
            if len(bars) < 3:
                return False
            gaps = bars["body_gap_bull"].sum() if bars["is_bullish"].all() else bars["body_gap_bear"].sum()
            return gaps >= 1 and bars["body_pct"].mean() > 0.6

        bull_breakout = (nb_bull >= 3 and is_breakout(bullTrend))
        bear_breakout = (nb_bear >= 3 and is_breakout(bearTrend))

        # Croisements de l'EMA (mesure de trading range)
        ema_crossings = 0
        for i in range(1, len(tail)):
            prev = tail["close"].iloc[i-1]
            curr = tail["close"].iloc[i]
            ema  = tail["ema20"].iloc[i]
            if (prev < ema and curr > ema) or (prev > ema and curr < ema):
                ema_crossings += 1

        # HH/HL pour direction du canal
        swing_highs = [highs[i] for i in range(2, len(highs)-2)
                       if highs[i] > highs[i-1] and highs[i] > highs[i+1]]
        swing_lows  = [lows[i]  for i in range(2, len(lows)-2)
                       if lows[i] < lows[i-1] and lows[i] < lows[i+1]]

        hh = len(swing_highs) >= 2 and swing_highs[-1] > swing_highs[-2]
        hl = len(swing_lows)  >= 2 and swing_lows[-1]  > swing_lows[-2]
        lh = len(swing_highs) >= 2 and swing_highs[-1] < swing_highs[-2]
        ll = len(swing_lows)  >= 2 and swing_lows[-1]  < swing_lows[-2]

        # Tight Range : 3+ doji/inside bars consécutifs
        tight_count = tail["is_inside"].tail(5).sum() + (tail["bar_type"] == "doji").tail(5).sum()
        tight_range = tight_count >= 3

        if tight_range:
            cycle_type = "TIGHT_RANGE"
        elif bull_breakout:
            cycle_type = "BREAKOUT_BULL"
        elif bear_breakout:
            cycle_type = "BREAKOUT_BEAR"
        elif ema_crossings >= 4:
            cycle_type = "TRADING_RANGE"
        elif hh and hl:
            cycle_type = "BULL_CANAL"
        elif lh and ll:
            cycle_type = "BEAR_CANAL"
        else:
            cycle_type = "TRADING_RANGE"

        return {
            "type":         cycle_type,
            "ema_crossings": ema_crossings,
            "hh": hh, "hl": hl, "lh": lh, "ll": ll,
            "bull_breakout": bull_breakout,
            "bear_breakout": bear_breakout,
            "tight_range":  tight_range,
        }

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 3 — Position EMA 20 (Chapitre 3)
    # ══════════════════════════════════════════════════════════════════════
    def _ema_position(self, df: pd.DataFrame) -> dict:
        last = df.iloc[-1]
        close  = last["close"]
        ema20  = last["ema20"]
        pct_from_ema = (close - ema20) / ema20 * 100

        # Test de l'EMA (le prix a-t-il touché l'EMA dans les 3 dernières barres ?)
        last3 = df.tail(3)
        ema_touch = any(
            row["low"] <= row["ema20"] <= row["high"]
            for _, row in last3.iterrows()
        )

        return {
            "close":          close,
            "ema20":          round(ema20, 5),
            "above_ema":      close > ema20,
            "pct_from_ema":   round(pct_from_ema, 3),
            "ema_touch_last3": ema_touch,
        }

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 4 — Bar Counting H1/H2, L1/L2 (Chapitre 3)
    # ══════════════════════════════════════════════════════════════════════
    def _count_pullback_legs(self, df: pd.DataFrame) -> dict:
        """
        Compte les 'High N' et 'Low N' en remontant depuis la dernière bougie.
        Un 'High' est une bougie dont le HIGH dépasse le HIGH de la précédente.
        """
        closes = df["close"].values
        highs  = df["high"].values
        lows   = df["low"].values

        n = len(closes)
        if n < 5:
            return {"h_count": 0, "l_count": 0, "bullish_setup": None, "bearish_setup": None}

        # Compter les H (tentatives haussières)
        h_count = 0
        for i in range(n-1, max(n-20, 0), -1):
            if highs[i] > highs[i-1]:
                h_count += 1
            else:
                break

        # Compter les L (tentatives baissières)
        l_count = 0
        for i in range(n-1, max(n-20, 0), -1):
            if lows[i] < lows[i-1]:
                l_count += 1
            else:
                break

        # Setup haussier : H2 = deuxième barre dont le high dépasse le précédent
        bullish_setup = None
        if h_count == 2:
            bullish_setup = "H2"
        elif h_count == 1:
            bullish_setup = "H1"
        elif h_count >= 3:
            bullish_setup = f"H{h_count} (Multiple)"

        # Setup baissier
        bearish_setup = None
        if l_count == 2:
            bearish_setup = "L2"
        elif l_count == 1:
            bearish_setup = "L1"
        elif l_count >= 3:
            bearish_setup = f"L{l_count} (Multiple)"

        return {
            "h_count":       h_count,
            "l_count":       l_count,
            "bullish_setup": bullish_setup,
            "bearish_setup": bearish_setup,
        }

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 5 — Signal Bar (Chapitre 2)
    # ══════════════════════════════════════════════════════════════════════
    def _detect_last_signal_bar(self, df: pd.DataFrame) -> dict:
        """Analyse la dernière bougie comme Signal Bar potentielle."""
        last = df.iloc[-1]
        bar_type   = last["bar_type"]
        is_bullish = last["is_bullish"]
        is_bearish = last["is_bearish"]
        is_inside  = last["is_inside"]
        is_outside = last["is_outside"]

        # Qualité de la signal bar
        quality = "FAIBLE"
        direction = None

        if bar_type == "bull_reversal":
            quality = "FORTE"
            direction = "BUY"
        elif bar_type == "bear_reversal":
            quality = "FORTE"
            direction = "SELL"
        elif bar_type == "trend_bar" and is_bullish:
            quality = "MODÉRÉE"
            direction = "BUY"
        elif bar_type == "trend_bar" and is_bearish:
            quality = "MODÉRÉE"
            direction = "SELL"
        elif is_inside:
            quality = "COMPRESSION"
            direction = "WAIT_BREAKOUT"
        elif bar_type == "doji":
            quality = "NEUTRE"
            direction = None

        # Body Gap (force de l'inertie institutionnelle)
        body_gap = last["body_gap_bull"] or last["body_gap_bear"]

        return {
            "bar_type":   bar_type,
            "quality":    quality,
            "direction":  direction,
            "is_inside":  is_inside,
            "is_outside": is_outside,
            "body_gap":   body_gap,
            "close_pct":  round(last.get("close_pct", 0.5), 3),
        }

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 6 — Supports & Résistances (Chapitre 4)
    # ══════════════════════════════════════════════════════════════════════
    def _detect_support_resistance(self, df: pd.DataFrame) -> list:
        """
        Identifie les niveaux horizontaux où le prix a rebondi plusieurs fois.
        Retourne une liste de prix clés.
        """
        tail = df.tail(self.SR_LOOKBACK)
        highs = tail["high"].values
        lows  = tail["low"].values
        levels = []

        # Swing Highs
        for i in range(2, len(highs)-2):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                levels.append(highs[i])

        # Swing Lows
        for i in range(2, len(lows)-2):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                levels.append(lows[i])

        # Regrouper les niveaux proches (tolérance 0.2%)
        if not levels:
            return []

        levels = sorted(set(levels))
        grouped = [levels[0]]
        for lvl in levels[1:]:
            if abs(lvl - grouped[-1]) / grouped[-1] > self.SR_TOLERANCE:
                grouped.append(lvl)

        return [round(l, 5) for l in grouped[-10:]]  # Max 10 niveaux

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 7 — Measured Move (Chapitre 4)
    # ══════════════════════════════════════════════════════════════════════
    def _compute_measured_move(self, df: pd.DataFrame) -> dict:
        """
        Calcule la cible Measured Move basée sur la taille du dernier Leg majeur.
        Si Leg 1 = 50 pips → Cible Leg 2 = prix actuel +/- 50 pips.
        """
        try:
            tail = df.tail(30)
            highs = tail["high"].values
            lows  = tail["low"].values
            closes = tail["close"].values

            # Trouver le dernier swing high et swing low
            sh_indices = [i for i in range(1, len(highs)-1)
                          if highs[i] > highs[i-1] and highs[i] > highs[i+1]]
            sl_indices = [i for i in range(1, len(lows)-1)
                          if lows[i] < lows[i-1] and lows[i] < lows[i+1]]

            if not sh_indices or not sl_indices:
                return {"valid": False}

            last_sh = highs[sh_indices[-1]]
            last_sl = lows[sl_indices[-1]]
            current = closes[-1]
            leg1_size = abs(last_sh - last_sl)

            # MM haussier (si au-dessus du dernier SL)
            mm_bull_target = current + leg1_size
            mm_bear_target = current - leg1_size

            return {
                "valid":         True,
                "leg1_size":     round(leg1_size, 5),
                "last_sh":       round(last_sh, 5),
                "last_sl":       round(last_sl, 5),
                "mm_bull_target": round(mm_bull_target, 5),
                "mm_bear_target": round(mm_bear_target, 5),
            }
        except Exception:
            return {"valid": False}

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 8 — Micro-Canal (Chapitre 7)
    # ══════════════════════════════════════════════════════════════════════
    def _detect_microchannel(self, df: pd.DataFrame) -> dict:
        """
        Détecte un micro-canal : série de N barres sans vrai pullback.
        Règle d'or : ne jamais acheter au 1er pullback contre un micro-canal baissier.
        """
        tail = df.tail(self.MICROCHANNEL_BARS + 2)
        highs  = tail["high"].values
        lows   = tail["low"].values
        closes = tail["close"].values

        # Micro-canal haussier : chaque low >= low précédent
        bull_mc = all(lows[i] >= lows[i-1] for i in range(1, len(lows)))
        # Micro-canal baissier : chaque high <= high précédent
        bear_mc = all(highs[i] <= highs[i-1] for i in range(1, len(highs)))

        active = bull_mc or bear_mc
        direction = "BULL" if bull_mc else ("BEAR" if bear_mc else None)

        return {
            "active":    active,
            "direction": direction,
            "danger":    bear_mc,  # Ne jamais acheter contre un micro-canal baissier
        }

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 9 — Patterns Classiques (Chapitre 8)
    # ══════════════════════════════════════════════════════════════════════
    def _detect_patterns(self, df: pd.DataFrame) -> dict:
        """
        Détecte les patterns chartistes classiques.
        """
        tail = df.tail(30)
        highs  = tail["high"].values
        lows   = tail["low"].values
        closes = tail["close"].values

        patterns_found = []

        # Double Bottom (W) : deux bas similaires avec un rebond entre les deux
        try:
            sl_idx = [i for i in range(1, len(lows)-1)
                      if lows[i] < lows[i-1] and lows[i] < lows[i+1]]
            if len(sl_idx) >= 2:
                l1, l2 = lows[sl_idx[-2]], lows[sl_idx[-1]]
                if abs(l1 - l2) / max(l1, l2) < 0.005:  # < 0.5% d'écart
                    patterns_found.append("DOUBLE_BOTTOM")
        except Exception:
            pass

        # Double Top (M) : deux hauts similaires avec une baisse entre les deux
        try:
            sh_idx = [i for i in range(1, len(highs)-1)
                      if highs[i] > highs[i-1] and highs[i] > highs[i+1]]
            if len(sh_idx) >= 2:
                h1, h2 = highs[sh_idx[-2]], highs[sh_idx[-1]]
                if abs(h1 - h2) / max(h1, h2) < 0.005:
                    patterns_found.append("DOUBLE_TOP")
        except Exception:
            pass

        # Triangle Symétrique : Lower Highs + Higher Lows
        try:
            if len(highs) >= 10:
                early_h = highs[:10].max()
                recent_h = highs[-5:].max()
                early_l  = lows[:10].min()
                recent_l  = lows[-5:].min()
                if recent_h < early_h and recent_l > early_l:
                    patterns_found.append("SYMMETRIC_TRIANGLE")
        except Exception:
            pass

        # Bull Flag : tendance forte suivie d'un canal baissier court
        try:
            first15  = closes[:15]
            last10   = closes[-10:]
            trend_up = first15[-1] > first15[0] * 1.002
            flag_down = last10[-1] < last10[0]
            if trend_up and flag_down:
                patterns_found.append("BULL_FLAG")
        except Exception:
            pass

        return {
            "detected": patterns_found,
            "count":    len(patterns_found),
        }

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 10 — RSI (14 périodes) + Divergences
    # ══════════════════════════════════════════════════════════════════════
    def _compute_rsi(self, df: pd.DataFrame) -> dict:
        """
        Calcule le RSI (14) à partir des prix de clôture MT5.
        Détecte les divergences haussières/baissières sur les 20 dernières barres.
        """
        try:
            closes = df["close"].copy()
            delta  = closes.diff()
            gain   = delta.clip(lower=0).rolling(self.RSI_PERIOD).mean()
            loss   = (-delta.clip(upper=0)).rolling(self.RSI_PERIOD).mean()
            rs     = gain / loss.replace(0, np.nan)
            df["rsi"] = (100 - (100 / (1 + rs))).fillna(50)

            rsi_now  = float(df["rsi"].iloc[-1])
            rsi_prev = float(df["rsi"].iloc[-2]) if len(df) > 2 else rsi_now

            # Biais RSI (proxy Always-In de Brooks)
            rsi_bias = "BULL" if rsi_now > 50 else "BEAR"

            # Zones extrêmes
            overbought  = rsi_now >= 70
            oversold    = rsi_now <= 30

            # ── Divergences sur les 20 dernières barres ─────────────────
            tail  = df.tail(20)
            highs = tail["high"].values
            lows  = tail["low"].values
            rsis  = tail["rsi"].values

            # Divergence Haussière : Prix LL mais RSI HL
            bull_div = (
                len(lows) >= 4
                and lows[-1] < lows[-4]    # prix : nouveau plus bas
                and rsis[-1] > rsis[-4]    # RSI : monte → divergence
            )

            # Divergence Baissière : Prix HH mais RSI LH
            bear_div = (
                len(highs) >= 4
                and highs[-1] > highs[-4]  # prix : nouveau plus haut
                and rsis[-1] < rsis[-4]    # RSI : baisse → divergence
            )

            # Série pour le graphique (80 dernières valeurs)
            rsi_series = [round(v, 1) for v in df["rsi"].tail(80).tolist()]

            return {
                "value":           round(rsi_now, 1),
                "prev":            round(rsi_prev, 1),
                "bias":            rsi_bias,
                "overbought":      overbought,
                "oversold":        oversold,
                "bull_divergence": bull_div,
                "bear_divergence": bear_div,
                "series":          rsi_series,
            }
        except Exception:
            return {
                "value": 50, "prev": 50, "bias": "NEUTRE",
                "overbought": False, "oversold": False,
                "bull_divergence": False, "bear_divergence": False,
                "series": [],
            }

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 11 — Analyse Volumétrique (tick_volume MT5/Exness)
    # ══════════════════════════════════════════════════════════════════════
    def _analyze_volume(self, df: pd.DataFrame) -> dict:
        """
        Analyse le tick_volume pour qualifier les mouvements :
        - Volume élevé sur Signal Bar → Force institutionnelle confirmée
        - Volume faible sur Breakout  → Faux Breakout probable (piège)
        - Volume décroissant sur Pullback → Pullback sain (trend va reprendre)
        - Climax de volume → Épuisement probable (MTR imminent)
        """
        try:
            vol_col = "tick_volume" if "tick_volume" in df.columns else (
                      "volume"      if "volume"       in df.columns else None)
            if vol_col is None:
                return {"available": False}

            vols = df[vol_col].copy().astype(float)

            # Moyenne mobile du volume comme référence
            vol_ma     = vols.rolling(self.VOL_MA_PERIOD).mean()
            df["vol_ma"] = vol_ma

            last_vol    = vols.iloc[-1]
            last_vol_ma = vol_ma.iloc[-1]
            vol_ratio   = (last_vol / last_vol_ma) if (last_vol_ma and not np.isnan(last_vol_ma) and last_vol_ma > 0) else 1.0

            # Qualification du volume actuel
            if vol_ratio >= 2.0:
                vol_label = "CLIMAX"          # Épuisement possible → alerte MTR
            elif vol_ratio >= 1.5:
                vol_label = "ÉLEVÉ"           # Confirmation institutionnelle forte
            elif vol_ratio >= 0.8:
                vol_label = "NORMAL"
            else:
                vol_label = "FAIBLE"          # Manque d'intérêt → méfiance

            # Signal Bar + Volume élevé = très puissant (confirmation PA)
            sig_bar_high_vol = (
                "bar_type" in df.columns
                and df["bar_type"].iloc[-1] in ("bull_reversal", "bear_reversal", "trend_bar")
                and vol_ratio >= 1.3
            )

            # Breakout + Volume faible = faux breakout probable
            breakout_low_vol = (
                "body_pct" in df.columns
                and df["body_pct"].iloc[-1] > 0.6
                and vol_ratio < 0.7
            )

            # Pullback décroissant (volume baisse sur 3 barres consécutives)
            tail3_vol = vols.tail(3).values
            pullback_healthy = (
                len(tail3_vol) == 3
                and tail3_vol[0] > tail3_vol[1] > tail3_vol[2]
            )

            # Climax → probable épuisement
            climax = vol_ratio >= 2.0

            # Séries pour le graphique (80 dernières bougies)
            vol_series    = [int(v) for v in vols.tail(80).tolist()]
            vol_ma_series = [round(v, 1) for v in vol_ma.tail(80).fillna(0).tolist()]

            return {
                "available":        True,
                "last_vol":         int(last_vol),
                "last_vol_ma":      int(last_vol_ma) if not np.isnan(last_vol_ma) else 0,
                "vol_ratio":        round(vol_ratio, 2),
                "label":            vol_label,
                "sig_bar_high_vol": sig_bar_high_vol,
                "breakout_low_vol": breakout_low_vol,
                "pullback_healthy": pullback_healthy,
                "climax":           climax,
                "series":           vol_series,
                "ma_series":        vol_ma_series,
            }
        except Exception:
            return {"available": False}

    # ══════════════════════════════════════════════════════════════════════
    # Retour vide si les données sont insuffisantes
    # ══════════════════════════════════════════════════════════════════════
    def _empty_features(self) -> dict:
        return {
            "cycle":        {"type": "UNKNOWN"},
            "ema_position": {"above_ema": None, "ema_touch_last3": False},
            "bar_count":    {"h_count": 0, "l_count": 0, "bullish_setup": None, "bearish_setup": None},
            "last_signal":  {"quality": "AUCUNE", "direction": None, "bar_type": "doji"},
            "sr_levels":    [],
            "measured_move": {"valid": False},
            "microchannel": {"active": False, "danger": False, "direction": None},
            "patterns":     {"detected": [], "count": 0},
            "rsi":          {"value": 50, "bias": "NEUTRE", "bull_divergence": False, "bear_divergence": False, "series": []},
            "volume":       {"available": False},
            "df":           pd.DataFrame(),
        }

