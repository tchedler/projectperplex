import pandas as pd
import numpy as np

class SMCSpecialist:
    def __init__(self, symbol):
        self.symbol = symbol

    def analyze(self, df, clock=None):
        """
        clock (optionnel) = données temporelles pour checker si on est en KZ/Macro.
        Requis pour le FIX-J (FVG créé en Killzone = institutionnel) et FIX-K (OB en KZ).
        """
        if df is None or len(df) < 60: return None

        data = df.tail(150).copy()

        # 1. DISPLACEMENT — requis par FVG
        displacement = self._calculate_displacement(data)

        # 2. MARKET STRUCTURE — BOS / CHoCH / MSS distincts (FIX-D)
        structure = self._market_structure(data, displacement['is_displaced'])

        # 3. FVG — filtrés par Displacement, priorisation High Probability (FIX-I + FIX-J)
        kz = clock['killzone'] if clock else 'NONE'
        macro = clock['macro'] if clock else 'NONE'
        in_kz = kz != 'NONE' or macro != 'NONE'
        fvgs = self._detect_fvgs_advanced(data, displacement['is_displaced'], in_kz)

        # 4. ORDER BLOCKS — Multi-bougies + bonus KZ (FIX-K)
        blocks = self._institutional_blocks(data, structure, displacement['is_displaced'], in_kz)

        # 5. REJECTION BLOCKS & WICK CE
        rejections = self._wick_analysis(data)

        # 6. PROTECTED LEVELS
        protected = self._protected_flow(data, structure)

        # 7. VOLUME IMBALANCES
        volume_imbalances = self._detect_volume_imbalances(data)

        # 8. Boolean_Sweep_ERL — FIX-B: variable d'état persistante
        #    True UNIQUEMENT si c.Low < PDL (avec réintégration) ou c.High > PDH (avec réintégration)
        sweep_erl = self._compute_boolean_sweep_erl(data)

        return {
            "displacement": displacement,
            "is_displaced": displacement['is_displaced'],
            "displacement_score": displacement['power_ratio'],
            "structure": structure,
            "fvgs": fvgs['all_fvgs'],
            "fvgs_pd_arrays": fvgs,
            "institutional_blocks": blocks,
            "rejections": rejections,
            "protected_levels": protected,
            "volume_imbalances": volume_imbalances,
            "boolean_sweep_erl": sweep_erl,
        }

    # =====================================================
    # FIX-B : Boolean_Sweep_ERL persistant
    # Bible §0: RÈGLE ABSOLUE — MSS valide seulement après sweep ERL (PDH/PDL)
    # =====================================================
    def _compute_boolean_sweep_erl(self, df):
        """
        Calcule Boolean_Sweep_ERL = True si dans les 30 dernières bougies:
        - Le Low d'une bougie est descendu sous le PDL (Low de l'avant-dernière session)
          ET le Close de cette bougie ou d'une suivante est remonté AU-DESSUS du PDL (réintégration)
        OU
        - Le High d'une bougie est monté au-dessus du PDH
          ET le Close de cette bougie ou d'une suivante est redescendu EN-DESSOUS du PDH
        """
        try:
            if not hasattr(df.index, 'date'):
                # Fallback: utiliser le range sur 20 bougies
                pdh = float(df['High'].iloc[:-10].max()) if len(df) > 20 else df['High'].max()
                pdl = float(df['Low'].iloc[:-10].min()) if len(df) > 20 else df['Low'].min()
            else:
                from datetime import timedelta
                last_date = df.index[-1].date()
                # I3 FIX : Remonter jusqu'à 3 jours pour gérer le lundi (weekend = aucune donnée)
                prev_day_data = pd.DataFrame()
                for days_back in range(1, 4):
                    candidate = last_date - timedelta(days=days_back)
                    # Ignorer samedi (5) et dimanche (6)
                    if candidate.weekday() >= 5:
                        continue
                    prev_day_data = df[df.index.date == candidate]
                    if len(prev_day_data) > 0:
                        break

                if len(prev_day_data) == 0:
                    # Fallback : utiliser les 10 premières bougies de la fenêtre visible
                    pdh = float(df['High'].iloc[:-5].max())
                    pdl = float(df['Low'].iloc[:-5].min())
                else:
                    pdh = float(prev_day_data['High'].max())
                    pdl = float(prev_day_data['Low'].min())

            scan = df.tail(30)
            bullish_sweep = False
            bearish_sweep = False

            for i in range(1, len(scan) - 1):
                # Bullish Sweep ERL: Low descend sous PDL + réintégration (Close remonte > PDL)
                if scan['Low'].iloc[i] < pdl:
                    # Chercher réintégration dans les 3 bougies suivantes
                    for r in range(i, min(i + 4, len(scan))):
                        if scan['Close'].iloc[r] > pdl:
                            bullish_sweep = True
                            break

                # Bearish Sweep ERL: High monte au-dessus PDH + réintégration (Close descend < PDH)
                if scan['High'].iloc[i] > pdh:
                    for r in range(i, min(i + 4, len(scan))):
                        if scan['Close'].iloc[r] < pdh:
                            bearish_sweep = True
                            break

            return {
                "value": bullish_sweep or bearish_sweep,
                "bullish_sweep": bullish_sweep,   # SSL sweepé → setup BULL valide
                "bearish_sweep": bearish_sweep,   # BSL sweepé → setup BEAR valide
                "pdh": round(pdh, 5),
                "pdl": round(pdl, 5),
            }
        except Exception:
            return {"value": False, "bullish_sweep": False, "bearish_sweep": False, "pdh": 0.0, "pdl": 0.0}

    # =====================================================
    # FIX-D : CHoCH distinct de BOS (Bible §3)
    # CHoCH = alerte uniquement (premier bris contre-tendance sans sweep ERL)
    # MSS = BOS + Displacement + Boolean_Sweep_ERL = True → SEUL signal d'exécution valide
    # =====================================================
    def _market_structure(self, df, is_displaced):
        highs = df['High'].rolling(window=5, center=True).apply(lambda x: x[2] == max(x), raw=True)
        lows = df['Low'].rolling(window=5, center=True).apply(lambda x: x[2] == min(x), raw=True)

        sh_series = df[highs == 1]['High']
        sl_series = df[lows == 1]['Low']

        last_swh = float(sh_series.tail(1).values[0]) if not sh_series.empty else df['High'].max()
        last_swl = float(sl_series.tail(1).values[0]) if not sl_series.empty else df['Low'].min()
        prev_swh = float(sh_series.tail(2).values[0]) if len(sh_series) >= 2 else last_swh
        prev_swl = float(sl_series.tail(2).values[0]) if len(sl_series) >= 2 else last_swl

        curr_close = df['Close'].iloc[-1]
        curr_high = df['High'].iloc[-1]
        curr_low = df['Low'].iloc[-1]
        mid = (last_swh + last_swl) / 2

        mode = "CONSOLIDATION"
        choch = "NONE"

        # MSS (FIX-D): BOS validé + Displacement = Market Structure Shift
        if curr_close > last_swh:
            if is_displaced:
                mode = "MSS_BULL"    # Seul signal autorisant l'exécution
            else:
                mode = "BOS_BULL"   # BOS sans displacement = continuation simple

        elif curr_close < last_swl:
            if is_displaced:
                mode = "MSS_BEAR"
            else:
                mode = "BOS_BEAR"

        # CHoCH (FIX-D): premier bris contre-tendance = ALERTE uniquement, pas d'exécution
        # Détecté: bougie casse le swing interne sans encore casser le dernier vrai swing
        if mode == "CONSOLIDATION" or mode in ["BOS_BULL", "BOS_BEAR"]:
            # CHoCH haussier: prix casse un Lower High interne (dans une tendance baissière)
            if curr_high > prev_swh and curr_close < last_swh:
                choch = "CHoCH_BULL_ALERT"   # Alerte retournement potentiel haussier
            # CHoCH baissier: prix casse un Higher Low interne (dans une tendance haussière)
            elif curr_low < prev_swl and curr_close > last_swl:
                choch = "CHoCH_BEAR_ALERT"   # Alerte retournement potentiel baissier

        if mode == "CONSOLIDATION":
            recent_ema = df['Close'].tail(10).mean()
            if curr_close > mid * 1.002 and recent_ema > df['Close'].iloc[-10]:
                mode = "EXPANSION_BULL"
            elif curr_close < mid * 0.998 and recent_ema < df['Close'].iloc[-10]:
                mode = "EXPANSION_BEAR"

        # FIX-E : Swings internal vs external nommés explicitement
        # Internal swings = les 2 derniers swings récents (pour entrée LTF)
        # External swings = les plus anciens (pour cible HTF)
        external_swh = float(df['High'].max())
        external_swl = float(df['Low'].min())

        return {
            "mode": mode,
            "choch": choch,       # FIX-D: CHoCH alerte distincte de BOS/MSS
            "swh": last_swh,      # Swing interne (entrée)
            "swl": last_swl,
            "prev_swh": prev_swh,   # Swing précédent
            "prev_swl": prev_swl,
            "ext_swh": external_swh,  # FIX-E: Swing externe (cible HTF)
            "ext_swl": external_swl,
        }

    # =====================================================
    # DISPLACEMENT (inchangé mais enrichi)
    # =====================================================
    def _calculate_displacement(self, df):
        lookback = 5
        max_score = 0
        velocity = "NORMAL"
        is_displaced = False

        avg_body = abs(df['Close'] - df['Open']).tail(20).mean()
        atr = (df['High'] - df['Low']).tail(20).mean()

        for i in range(1, lookback + 1):
            idx = -i
            candle_body = abs(df['Close'].iloc[idx] - df['Open'].iloc[idx])
            candle_range = df['High'].iloc[idx] - df['Low'].iloc[idx]
            score = candle_body / avg_body if avg_body > 0 else 1.0

            body_ratio = candle_body / candle_range if candle_range > 0 else 0
            is_momentum = score > 1.5 and body_ratio > 0.70
            is_atr_break = candle_body > atr * 1.5

            if is_momentum or is_atr_break:
                is_displaced = True
                max_score = max(max_score, score)
                if score > 2.5: velocity = "EXTREME"
                elif score > 2.0: velocity = "HIGH"
                elif score > 1.5: velocity = "ELEVATED"

        return {
            "is_displaced": is_displaced,
            "power_ratio": round(max_score if is_displaced else (abs(df['Close'].iloc[-1] - df['Open'].iloc[-1]) / avg_body if avg_body > 0 else 1), 2),
            "velocity": velocity
        }

    # =====================================================
    # FIX-I + FIX-J : FVG High Probability (premier FVG de jambe) + bonus Killzone
    # Bible §1: "n'accepter que le PREMIER FVG créé depuis l'origine"
    # Bible §1: FVG créé en Macro/KZ = institutionnel
    # =====================================================
    def _detect_fvgs_advanced(self, df, displacement_active, in_kz=False):
        fvgs = []
        swing_h = df['High'].max()
        swing_l = df['Low'].min()
        swing_range = swing_h - swing_l if swing_h != swing_l else 1

        # Indices d'origine des jambes (pour prioriser le PREMIER FVG)
        bull_origin_idx = None
        bear_origin_idx = None

        for i in range(2, len(df) - 1):
            # BULLISH (BISI)
            if df['High'].iloc[i-2] < df['Low'].iloc[i]:
                body = abs(df['Close'].iloc[i-1] - df['Open'].iloc[i-1])
                rng = df['High'].iloc[i-1] - df['Low'].iloc[i-1]
                is_local_disp = body > rng * 0.70 if rng > 0 else False

                if displacement_active or is_local_disp:
                    top = df['Low'].iloc[i]
                    bot = df['High'].iloc[i-2]
                    ce = (top + bot) / 2

                    # Quality State
                    future = df.iloc[i+1:] if i+1 < len(df) else pd.DataFrame()
                    if len(future) > 0:
                        if future['Close'].min() < bot:
                            quality = "USED"
                        elif future['Low'].min() < top:
                            quality = "MITIGATED"
                        else:
                            quality = "FRESH"
                    else:
                        quality = "FRESH"

                    # FIX-I: Position dans le swing (> 65% = LOW quality, épuisement)
                    fvg_pos = (ce - swing_l) / swing_range * 100
                    pos_quality = "LOW" if fvg_pos > 65 else "HIGH"

                    # FIX-I: Premier FVG de la jambe haussière = prioriser
                    if bull_origin_idx is None or i < bull_origin_idx + 5:
                        if bull_origin_idx is None:
                            bull_origin_idx = i
                        is_first_fvg = True
                    else:
                        is_first_fvg = False

                    # FIX-J: Bonus institutionnel si créé en Killzone/Macro
                    institutional = in_kz or is_first_fvg

                    fvgs.append({
                        "type": "BISI", "top": top, "bot": bot, "ce": ce,
                        "index": df.index[i-1],
                        "mitigated": quality != "FRESH",
                        "quality": quality,
                        "position_quality": pos_quality,
                        "position_pct": round(fvg_pos, 1),
                        "is_first_fvg": is_first_fvg,       # FIX-I
                        "institutional": institutional,       # FIX-J
                    })

            # BEARISH (SIBI)
            elif df['Low'].iloc[i-2] > df['High'].iloc[i]:
                body = abs(df['Close'].iloc[i-1] - df['Open'].iloc[i-1])
                rng = df['High'].iloc[i-1] - df['Low'].iloc[i-1]
                is_local_disp = body > rng * 0.70 if rng > 0 else False

                if displacement_active or is_local_disp:
                    top = df['Low'].iloc[i-2]
                    bot = df['High'].iloc[i]
                    ce = (top + bot) / 2

                    future = df.iloc[i+1:] if i+1 < len(df) else pd.DataFrame()
                    if len(future) > 0:
                        if future['Close'].max() > top:
                            quality = "USED"
                        elif future['High'].max() > bot:
                            quality = "MITIGATED"
                        else:
                            quality = "FRESH"
                    else:
                        quality = "FRESH"

                    fvg_pos = (ce - swing_l) / swing_range * 100
                    pos_quality = "LOW" if fvg_pos < 35 else "HIGH"

                    if bear_origin_idx is None or i < bear_origin_idx + 5:
                        if bear_origin_idx is None:
                            bear_origin_idx = i
                        is_first_fvg = True
                    else:
                        is_first_fvg = False

                    institutional = in_kz or is_first_fvg

                    fvgs.append({
                        "type": "SIBI", "top": top, "bot": bot, "ce": ce,
                        "index": df.index[i-1],
                        "mitigated": quality != "FRESH",
                        "quality": quality,
                        "position_quality": pos_quality,
                        "position_pct": round(fvg_pos, 1),
                        "is_first_fvg": is_first_fvg,
                        "institutional": institutional,
                    })

        # IFVG
        ifvgs = []
        for f in fvgs:
            if f['quality'] == 'USED':
                inv_type = "SIBI" if f['type'] == "BISI" else "BISI"
                ifvgs.append({**f, "type": f"IFVG_{inv_type}", "quality": "INVERTED"})

        # BPR — timing ≤ 20 bougies = INSTITUTIONAL
        bprs = []
        for fi, f in enumerate(fvgs):
            for fj, ff in enumerate(fvgs):
                if f['type'] != ff['type'] and f['type'] in ['BISI', 'SIBI'] and ff['type'] in ['BISI', 'SIBI']:
                    overlap_top = min(f['top'], ff['top'])
                    overlap_bot = max(f['bot'], ff['bot'])
                    if overlap_top > overlap_bot:
                        gap = abs(fi - fj)
                        strength = "INSTITUTIONAL" if gap <= 20 else "DILUTED"
                        bprs.append({"level": (overlap_top + overlap_bot) / 2, "zone": [overlap_bot, overlap_top], "strength": strength})

        return {"all_fvgs": (fvgs + ifvgs)[-8:], "bprs": bprs[-2:]}

    # =====================================================
    # FIX-K : OB Quality score +1 si créé en Killzone/Macro (Bible §2 scoring OB)
    # =====================================================
    def _institutional_blocks(self, df, struct, is_displaced, in_kz=False):
        blocks = []
        atr = (df['High'] - df['Low']).tail(20).mean()

        for i in range(len(df)-20, len(df)-2):
            if i < 5: continue

            # Bullish OB
            if df['Close'].iloc[i+1] > df['High'].iloc[i] and df['Close'].iloc[i] < df['Open'].iloc[i]:
                ob_start = i
                while ob_start > max(0, i-10) and df['Close'].iloc[ob_start-1] < df['Open'].iloc[ob_start-1]:
                    ob_start -= 1

                ob_low = df['Low'].iloc[ob_start:i+1].min()
                ob_high = max(df['Open'].iloc[ob_start:i+1].max(), df['High'].iloc[ob_start:i+1].max())
                ob_count = i - ob_start + 1

                pre_high = df['High'].iloc[max(0, ob_start-5):ob_start].max() if ob_start > 5 else 0
                is_breaker = ob_high > 0 and df['High'].iloc[i] > pre_high and df['Close'].iloc[-1] < ob_low

                quality = 0
                if df['High'].iloc[i+1] > df['High'].iloc[:i].tail(20).max(): quality += 1
                has_fvg_after = any(
                    i+j+1 < len(df) and df['High'].iloc[i+j-1] < df['Low'].iloc[i+j+1]
                    for j in range(1, min(4, len(df)-i-1))
                )
                if has_fvg_after: quality += 1
                mid = (struct['swh'] + struct['swl']) / 2
                if ob_low < mid: quality += 1
                if df['Low'].iloc[i+1:].min() > ob_low: quality += 1
                if is_displaced: quality += 1
                if in_kz: quality += 1  # FIX-K: bonus si créé en Killzone

                blocks.append({
                    "type": "BREAKER_BEAR" if is_breaker else "BULLISH_OB",
                    "level": df['Open'].iloc[i],
                    "index": df.index[ob_start],
                    "refined_zone": [ob_low, ob_high],
                    "candle_count": ob_count,
                    "quality_score": min(quality, 5),
                    "in_killzone": in_kz,   # FIX-K
                })

            # Bearish OB
            if df['Close'].iloc[i+1] < df['Low'].iloc[i] and df['Close'].iloc[i] > df['Open'].iloc[i]:
                ob_start = i
                while ob_start > max(0, i-10) and df['Close'].iloc[ob_start-1] > df['Open'].iloc[ob_start-1]:
                    ob_start -= 1

                ob_high = df['High'].iloc[ob_start:i+1].max()
                ob_low = min(df['Open'].iloc[ob_start:i+1].min(), df['Low'].iloc[ob_start:i+1].min())
                ob_count = i - ob_start + 1

                pre_low = df['Low'].iloc[max(0, ob_start-5):ob_start].min() if ob_start > 5 else 0
                is_breaker = df['Low'].iloc[i] < pre_low and df['Close'].iloc[-1] > ob_high

                quality = 0
                if df['Low'].iloc[i+1] < df['Low'].iloc[:i].tail(20).min(): quality += 1
                has_fvg_after = any(
                    i+j+1 < len(df) and df['Low'].iloc[i+j-1] > df['High'].iloc[i+j+1]
                    for j in range(1, min(4, len(df)-i-1))
                )
                if has_fvg_after: quality += 1
                mid = (struct['swh'] + struct['swl']) / 2
                if ob_high > mid: quality += 1
                if df['High'].iloc[i+1:].max() < ob_high: quality += 1
                if is_displaced: quality += 1
                if in_kz: quality += 1  # FIX-K

                blocks.append({
                    "type": "BREAKER_BULL" if is_breaker else "BEARISH_OB",
                    "level": df['Open'].iloc[i],
                    "index": df.index[ob_start],
                    "refined_zone": [ob_low, ob_high],
                    "candle_count": ob_count,
                    "quality_score": min(quality, 5),
                    "in_killzone": in_kz,
                })

        return blocks[-4:]

    def _detect_volume_imbalances(self, df):
        vis = []
        for i in range(1, len(df)-1):
            prev_close = df['Close'].iloc[i-1]
            curr_open = df['Open'].iloc[i]
            if curr_open > prev_close:
                vis.append({"type": "VI_BULL", "top": curr_open, "bot": prev_close, "ce": (curr_open + prev_close)/2, "index": df.index[i]})
            elif curr_open < prev_close:
                vis.append({"type": "VI_BEAR", "top": prev_close, "bot": curr_open, "ce": (prev_close + curr_open)/2, "index": df.index[i]})
        return vis[-5:]

    def _wick_analysis(self, df):
        last_h = df.tail(30)
        h_idx = last_h['High'].idxmax()
        h_candle = last_h.loc[h_idx]
        rejection_bear = 0
        if (h_candle['High'] - max(h_candle['Open'], h_candle['Close'])) > (h_candle['High'] - h_candle['Low']) * 0.5:
            rejection_bear = h_candle['High'] - (h_candle['High'] - max(h_candle['Open'], h_candle['Close']))/2

        last_l = df.tail(30)
        l_idx = last_l['Low'].idxmin()
        l_candle = last_l.loc[l_idx]
        rejection_bull = 0
        if (min(l_candle['Open'], l_candle['Close']) - l_candle['Low']) > (l_candle['High'] - l_candle['Low']) * 0.5:
            rejection_bull = l_candle['Low'] + (min(l_candle['Open'], l_candle['Close']) - l_candle['Low'])/2

        return {"bear_wick_ce": rejection_bear, "bull_wick_ce": rejection_bull}

    def _protected_flow(self, df, struct):
        p_low = df['Low'].tail(25).min()
        p_high = df['High'].tail(25).max()
        is_low_protected = "BULL" in struct['mode']
        is_high_protected = "BEAR" in struct['mode']
        return {
            "low": {"price": p_low, "status": "PROTECTED" if is_low_protected else "TARGET"},
            "high": {"price": p_high, "status": "PROTECTED" if is_high_protected else "TARGET"}
        }