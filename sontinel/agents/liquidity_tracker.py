import pandas as pd
import numpy as np
import datetime
import logging

log = logging.getLogger(__name__)

class LiquidityTracker:
    def __init__(self, symbol):
        self.symbol = symbol
        # AUDIT #10 FIX : fenêtre EQH/EQL adaptable selon le TF analysé
        # Sera mis à jour dans analyze() si le TF est précisé
        self._eqh_eql_window = 60  # valeur par défaut

    def analyze(self, df, tf: str = ""):
        if df is None or len(df) < 50: return None

        # AUDIT #10 FIX : fenêtre adaptative par TF pour EQH/EQL
        # Des TF longs (D1, W1) ont besoin de moins de bougies (le marché évolue lentement)
        # Des TF courts (M1, M5) ont besoin de plus de bougies pour capter les structures intraday
        eqh_window_by_tf = {
            "MN": 30, "W1": 40, "D1": 60,
            "H4": 80, "H1": 100,
            "M15": 120, "M5": 150, "M1": 200,
        }
        self._eqh_eql_window = eqh_window_by_tf.get(tf.upper(), 60) if tf else 60

        atr = (df['High'] - df['Low']).tail(20).mean()
        current_p = df['Close'].iloc[-1]

        # 1. EQH / EQL (Equal Highs / Lows) — Bible §14.1 Smooth vs Jagged
        eqh = self._find_eqh(df, atr, current_p)
        eql = self._find_eql(df, atr, current_p)

        # 2. ERL enrichi — PDH/PDL, PWH/PWL, Old Levels avec sweep status — Bible §4.1 + §15.1
        erl = self._find_erl_enriched(df, current_p)

        # 3. IRL (Internal Range Liquidity — FVG/imbalances internes)
        irl = self._find_irl(df)

        # 4. NDOG / NWOG — Bible §2.5
        ndog = self._find_ndog(df)
        nwog = self._find_nwog(df)

        # 5. Niveaux temporels structurés (PDH/PDL/PWH/PWL/PMH/PML) — Bible §4.2
        temporal = self._find_temporal_levels(df, current_p)

        # 6. DOL directionnel — Bible §4.1
        dol_bull = self._find_dol_directional(current_p, eqh, erl, temporal, direction='BULL')
        dol_bear = self._find_dol_directional(current_p, eql, erl, temporal, direction='BEAR')

        # 7. LRLR / HRLR — Bible §4.5
        lrlr_hrlr = self._detect_lrlr_hrlr(df, current_p, dol_bull, dol_bear)

        # 8. FIX-C: CBDR + Flout — Bible §5 (Central Bank Dealers Range 14h-20h EST)
        cbdr = self._compute_cbdr(df)

        # Proximal liquidity (nearest level)
        proximal = self._nearest(current_p, eqh, eql, erl)

        return {
            "eqh": eqh,
            "eql": eql,
            "erl": erl,
            "irl": irl,
            "ndog": ndog,
            "nwog": nwog,
            "temporal_levels": temporal,
            "dol_bull": dol_bull,
            "dol_bear": dol_bear,
            "lrlr_hrlr": lrlr_hrlr,
            "cbdr": cbdr,
            "proximal_liquidity": proximal,
        }

    # =====================================================
    # EQH — Equal Highs avec Smooth/Jagged + Proximal/Distal + Sweep Status
    # Bible §14.1
    # =====================================================
    def _find_eqh(self, df, atr, current_p):
        # AUDIT #10 FIX : utilise self._eqh_eql_window (adaptatif selon TF)
        highs_raw = df['High'].tail(self._eqh_eql_window)
        swing_highs = []
        vals = highs_raw.values
        idx_vals = highs_raw.index

        for i in range(2, len(vals) - 2):
            # Fractal 5-bougie pour swing high de qualité
            if vals[i] >= vals[i-1] and vals[i] >= vals[i-2] and vals[i] >= vals[i+1] and vals[i] >= vals[i+2]:
                swing_highs.append({"price": float(vals[i]), "index": idx_vals[i]})

        if not swing_highs:
            swing_highs = [{"price": float(highs_raw.max()), "index": highs_raw.idxmax()}]

        threshold = atr * 0.25
        smooth_threshold = atr * 0.12

        eqh_levels = []
        seen = set()
        for i in range(len(swing_highs)):
            for j in range(i + 1, len(swing_highs)):
                key = (i, j)
                if key in seen:
                    continue
                diff = abs(swing_highs[i]['price'] - swing_highs[j]['price'])
                if diff < threshold:
                    seen.add(key)
                    avg_price = (swing_highs[i]['price'] + swing_highs[j]['price']) / 2
                    is_smooth = diff < smooth_threshold
                    # Sweep status: le prix a-t-il déjà dépassé ce niveau?
                    swept = self._is_level_swept(df, avg_price, 'BSL')
                    # Proximal vs Distal
                    proximity = 'PROXIMAL' if abs(avg_price - current_p) < atr * 3 else 'DISTAL'
                    eqh_levels.append({
                        "price": round(avg_price, 5),
                        "quality": "SMOOTH" if is_smooth else "JAGGED",
                        "swept": swept,
                        "proximity": proximity,
                        "count": 2
                    })

        # Trier du plus proche au plus loin, garder les 4 plus proches au-dessus du prix
        above = [e for e in eqh_levels if e['price'] > current_p]
        below = [e for e in eqh_levels if e['price'] <= current_p]
        above_sorted = sorted(above, key=lambda x: x['price'])
        below_sorted = sorted(below, key=lambda x: x['price'], reverse=True)
        return (above_sorted + below_sorted)[:4]

    # =====================================================
    # EQL — Equal Lows avec Smooth/Jagged + Proximal/Distal + Sweep Status
    # Bible §14.1
    # =====================================================
    def _find_eql(self, df, atr, current_p):
        # AUDIT #10 FIX : utilise self._eqh_eql_window (adaptatif selon TF)
        lows_raw = df['Low'].tail(self._eqh_eql_window)
        swing_lows = []
        vals = lows_raw.values
        idx_vals = lows_raw.index

        for i in range(2, len(vals) - 2):
            if vals[i] <= vals[i-1] and vals[i] <= vals[i-2] and vals[i] <= vals[i+1] and vals[i] <= vals[i+2]:
                swing_lows.append({"price": float(vals[i]), "index": idx_vals[i]})

        if not swing_lows:
            swing_lows = [{"price": float(lows_raw.min()), "index": lows_raw.idxmin()}]

        threshold = atr * 0.25
        smooth_threshold = atr * 0.12

        eql_levels = []
        seen = set()
        for i in range(len(swing_lows)):
            for j in range(i + 1, len(swing_lows)):
                key = (i, j)
                if key in seen:
                    continue
                diff = abs(swing_lows[i]['price'] - swing_lows[j]['price'])
                if diff < threshold:
                    seen.add(key)
                    avg_price = (swing_lows[i]['price'] + swing_lows[j]['price']) / 2
                    is_smooth = diff < smooth_threshold
                    swept = self._is_level_swept(df, avg_price, 'SSL')
                    proximity = 'PROXIMAL' if abs(avg_price - current_p) < atr * 3 else 'DISTAL'
                    eql_levels.append({
                        "price": round(avg_price, 5),
                        "quality": "SMOOTH" if is_smooth else "JAGGED",
                        "swept": swept,
                        "proximity": proximity,
                        "count": 2
                    })

        below = [e for e in eql_levels if e['price'] < current_p]
        above = [e for e in eql_levels if e['price'] >= current_p]
        below_sorted = sorted(below, key=lambda x: x['price'], reverse=True)
        above_sorted = sorted(above, key=lambda x: x['price'])
        return (below_sorted + above_sorted)[:4]

    # =====================================================
    # IS LEVEL SWEPT — Vérifie si un niveau de liquidité a déjà été pris
    # Bible §3.3 (OB invalidé si revisité), §15.1 (ERL/IRL cycle)
    # =====================================================
    def _is_level_swept(self, df, level, direction):
        """
        BSL sweepé = prix a dépassé le niveau (mèche haute > level) ET a clôturé en dessous.
        SSL sweepé = prix a dépassé le niveau (mèche basse < level) ET a clôturé au-dessus.
        Scan les 30 dernières bougies.
        """
        scan = df.tail(30)
        if direction == 'BSL':
            # Quelqu'une des bougies a eu son High >= level et son Close < level
            swept_candles = scan[(scan['High'] >= level * 0.9999) & (scan['Close'] < level)]
            return len(swept_candles) > 0
        else:  # SSL
            swept_candles = scan[(scan['Low'] <= level * 1.0001) & (scan['Close'] > level)]
            return len(swept_candles) > 0

    # =====================================================
    # ERL ENRICHI — PDH/PDL, PWH/PWL + Old Levels + statut SWEPT/INTACT
    # Bible §4.1, §4.2, §15.1
    # =====================================================
    def _find_erl_enriched(self, df, current_p):
        """
        ERL inclut: High/Low du range complet (100 bougies), PDH/PDL, PWH/PWL.
        Chaque niveau est annoté SWEPT/INTACT selon _is_level_swept().
        """
        erl_high = df['High'].tail(100).max()
        erl_low = df['Low'].tail(100).min()

        h_swept = self._is_level_swept(df, erl_high, 'BSL')
        l_swept = self._is_level_swept(df, erl_low, 'SSL')

        return {
            "high": erl_high,
            "low": erl_low,
            "high_swept": h_swept,
            "low_swept": l_swept,
            "high_status": "SWEPT" if h_swept else "INTACT",
            "low_status": "SWEPT" if l_swept else "INTACT",
        }

    # =====================================================
    # NIVEAUX TEMPORELS STRUCTURÉS — PDH/PDL, PWH/PWL, PMH/PML
    # Bible §4.2
    # =====================================================
    def _find_temporal_levels(self, df, current_p):
        """
        Calcule PDH/PDL (yesterday), PWH/PWL (last week), PMH/PML (last month)
        depuis l'index datetime du df. Annote SWEPT/INTACT + ABOVE/BELOW vs prix actuel.
        """
        temporal = {}
        has_datetime = hasattr(df.index, 'date')

        if has_datetime:
            try:
                from datetime import timedelta
                last_ts = df.index[-1]

                # PDH/PDL — hier
                yesterday = (last_ts - timedelta(days=1)).date()
                prev_day_data = df[df.index.date == yesterday]
                if len(prev_day_data) > 0:
                    pdh = float(prev_day_data['High'].max())
                    pdl = float(prev_day_data['Low'].min())
                    temporal['PDH'] = {
                        "price": pdh,
                        "status": "SWEPT" if self._is_level_swept(df, pdh, 'BSL') else "INTACT",
                        "side": "ABOVE" if pdh > current_p else "BELOW"
                    }
                    temporal['PDL'] = {
                        "price": pdl,
                        "status": "SWEPT" if self._is_level_swept(df, pdl, 'SSL') else "INTACT",
                        "side": "ABOVE" if pdl > current_p else "BELOW"
                    }
            except Exception:
                pass

            try:
                # MOY-6 FIX: PWH/PWL — vraie semaine précédente via calendrier ISO au lieu d'une approximation de lignes
                if hasattr(df.index, 'isocalendar'):
                    current_week = df.index[-1].isocalendar().week
                    # Filtrer tout ce qui n'est pas la semaine courante
                    prev_data = df[df.index.isocalendar().week != current_week]
                    if len(prev_data) > 0:
                        last_prev_week = prev_data.index[-1].isocalendar().week
                        week_window = prev_data[prev_data.index.isocalendar().week == last_prev_week]
                        
                        if len(week_window) > 0:
                            pwh = float(week_window['High'].max())
                            pwl = float(week_window['Low'].min())
                            temporal['PWH'] = {
                                "price": pwh,
                                "status": "SWEPT" if self._is_level_swept(df, pwh, 'BSL') else "INTACT",
                                "side": "ABOVE" if pwh > current_p else "BELOW"
                            }
                            temporal['PWL'] = {
                                "price": pwl,
                                "status": "SWEPT" if self._is_level_swept(df, pwl, 'SSL') else "INTACT",
                                "side": "ABOVE" if pwl > current_p else "BELOW"
                            }
            except Exception as e:
                log.debug(f"PWH/PWL extraction failed: {e}")

        # Fallback: utiliser les ranges lookback fixes si pas de datetime
        if not temporal:
            lookback_20 = df.tail(20)
            lookback_60 = df.tail(60)
            temporal['PDH'] = {"price": float(lookback_20['High'].max()), "status": "INTACT", "side": "ABOVE"}
            temporal['PDL'] = {"price": float(lookback_20['Low'].min()), "status": "INTACT", "side": "BELOW"}
            temporal['PWH'] = {"price": float(lookback_60['High'].max()), "status": "INTACT", "side": "ABOVE"}
            temporal['PWL'] = {"price": float(lookback_60['Low'].min()), "status": "INTACT", "side": "BELOW"}

        return temporal

    # =====================================================
    # DOL DIRECTIONNEL — Bible §4.1
    # dol_bull = premier BSL INTACT au-dessus (pour biais BULL)
    # dol_bear = premier SSL INTACT en-dessous (pour biais BEAR)
    # =====================================================
    def _find_dol_directional(self, current_p, eq_levels, erl, temporal, direction):
        """
        Retourne le premier niveau de liquidité intact dans la direction du biais.
        Priorité: EQH > PDH > PWH (pour BULL) / EQL > PDL > PWL (pour BEAR)
        """
        candidates = []

        if direction == 'BULL':
            # EQH intacts au-dessus
            for e in eq_levels:
                if e['price'] > current_p and not e.get('swept', False):
                    candidates.append({"name": f"EQH ({e['quality']})", "price": e['price'], "type": "BSL"})
            # PDH intact
            if 'PDH' in temporal and temporal['PDH']['status'] == 'INTACT' and temporal['PDH']['price'] > current_p:
                candidates.append({"name": "PDH", "price": temporal['PDH']['price'], "type": "BSL"})
            # PWH intact
            if 'PWH' in temporal and temporal['PWH']['status'] == 'INTACT' and temporal['PWH']['price'] > current_p:
                candidates.append({"name": "PWH", "price": temporal['PWH']['price'], "type": "BSL"})
            # ERL high intact
            if not erl.get('high_swept', False) and erl['high'] > current_p:
                candidates.append({"name": "BSL MAX", "price": erl['high'], "type": "BSL"})
            # Trier du plus proche au plus loin
            candidates.sort(key=lambda x: x['price'])
            return candidates[0] if candidates else {"name": "N/A", "price": erl['high'], "type": "BSL"}

        else:  # BEAR
            for e in eq_levels:
                if e['price'] < current_p and not e.get('swept', False):
                    candidates.append({"name": f"EQL ({e['quality']})", "price": e['price'], "type": "SSL"})
            if 'PDL' in temporal and temporal['PDL']['status'] == 'INTACT' and temporal['PDL']['price'] < current_p:
                candidates.append({"name": "PDL", "price": temporal['PDL']['price'], "type": "SSL"})
            if 'PWL' in temporal and temporal['PWL']['status'] == 'INTACT' and temporal['PWL']['price'] < current_p:
                candidates.append({"name": "PWL", "price": temporal['PWL']['price'], "type": "SSL"})
            if not erl.get('low_swept', False) and erl['low'] < current_p:
                candidates.append({"name": "SSL MIN", "price": erl['low'], "type": "SSL"})
            candidates.sort(key=lambda x: x['price'], reverse=True)
            return candidates[0] if candidates else {"name": "N/A", "price": erl['low'], "type": "SSL"}

    # =====================================================
    # LRLR / HRLR — Bible §4.5
    # Low Resistance Liquidity Run = chemin dégagé vers la cible
    # High Resistance Liquidity Run = obstacles sur le chemin
    # =====================================================
    def _detect_lrlr_hrlr(self, df, current_p, dol_bull, dol_bear):
        """
        Compte les FVG (imbalances internes) non comblés entre le prix actuel
        et chaque cible directionnelle. 
        0-1 obstacle = LRLR (Low Resistance), 2+ = HRLR (High Resistance).
        """
        def count_obstacles(df, p_from, p_to):
            obstacles = 0
            lo, hi = min(p_from, p_to), max(p_from, p_to)
            # Scanner les imbalances internes dans cette zone en utilisant le pattern FVG
            for i in range(2, min(len(df) - 1, 80)):
                # FVG bullish (vide entre H[i-2] et L[i])
                if df['High'].iloc[i-2] < df['Low'].iloc[i]:
                    fvg_ce = (df['High'].iloc[i-2] + df['Low'].iloc[i]) / 2
                    if lo <= fvg_ce <= hi:
                        # Vérifier si ce FVG est non comblé (prix n'est pas revenu dessus)
                        future_min = df['Low'].iloc[i:].min() if i < len(df) - 1 else p_from
                        if future_min > df['High'].iloc[i-2]:
                            obstacles += 1
                # FVG bearish
                elif df['Low'].iloc[i-2] > df['High'].iloc[i]:
                    fvg_ce = (df['Low'].iloc[i-2] + df['High'].iloc[i]) / 2
                    if lo <= fvg_ce <= hi:
                        future_max = df['High'].iloc[i:].max() if i < len(df) - 1 else p_from
                        if future_max < df['Low'].iloc[i-2]:
                            obstacles += 1
            return obstacles

        bull_target = dol_bull.get('price', current_p) if dol_bull else current_p
        bear_target = dol_bear.get('price', current_p) if dol_bear else current_p

        bull_obstacles = count_obstacles(df, current_p, bull_target) if bull_target != current_p else 0
        bear_obstacles = count_obstacles(df, current_p, bear_target) if bear_target != current_p else 0

        return {
            "bull": {
                "type": "LRLR" if bull_obstacles <= 1 else "HRLR",
                "obstacles": bull_obstacles,
                "target": round(bull_target, 5),
                "label": f"{'LRLR ✅' if bull_obstacles <= 1 else 'HRLR ⚠️'} vers {round(bull_target, 5)} ({bull_obstacles} obstacle{'s' if bull_obstacles != 1 else ''})"
            },
            "bear": {
                "type": "LRLR" if bear_obstacles <= 1 else "HRLR",
                "obstacles": bear_obstacles,
                "target": round(bear_target, 5),
                "label": f"{'LRLR ✅' if bear_obstacles <= 1 else 'HRLR ⚠️'} vers {round(bear_target, 5)} ({bear_obstacles} obstacle{'s' if bear_obstacles != 1 else ''})"
            }
        }

    # =====================================================
    # IRL — Internal Range Liquidity (FVG internes)
    # =====================================================
    def _find_irl(self, df):
        gaps = []
        scan_start = max(2, len(df) - 20)
        for i in range(scan_start, len(df) - 1):
            if df['High'].iloc[i-1] < df['Low'].iloc[i+1]:
                gaps.append({"price": (df['High'].iloc[i-1] + df['Low'].iloc[i+1])/2, "type": "BISI"})
            if df['Low'].iloc[i-1] > df['High'].iloc[i+1]:
                gaps.append({"price": (df['Low'].iloc[i-1] + df['High'].iloc[i+1])/2, "type": "SIBI"})
        return gaps[-5:]

    # =====================================================
    # NDOG / NWOG — Bible §2.5
    # =====================================================
    # =====================================================
    # FIX-C: CBDR + FLOUT — Bible §5
    # CBDR = Central Bank Dealers Range (14h-20h EST la veille)
    # Flout = extension 15h-00h
    # CBDR_Explosive si range < 40 pips
    # =====================================================
    def _compute_cbdr(self, df):
        """
        Filtre les bougies entre 14h et 20h EST de la veille pour calculer le CBDR.
        Si pas d'index datetime, utilise les 12 dernières bougies comme approximation.
        Retourne: high, low, range_pips, explosive, projections SD, flout_high, flout_low.
        """
        try:
            if hasattr(df.index, 'hour'):
                import pytz
                ny_tz = pytz.timezone('America/New_York')
                # Convertir l'index en NY time si nécessaire
                if df.index.tzinfo is None:
                    df_tz = df.copy()
                    df_tz.index = df_tz.index.tz_localize('UTC').tz_convert(ny_tz)
                else:
                    df_tz = df.copy()
                    df_tz.index = df_tz.index.tz_convert(ny_tz)

                # Identifier toutes les bougies dans les heures CBDR
                cbdr_mask = (df_tz.index.hour >= 14) & (df_tz.index.hour < 20)
                cbdr_data = df_tz[cbdr_mask]
                
                if len(cbdr_data) > 0:
                    last_cbdr_date = cbdr_data.index[-1].date()
                    cbdr_window = cbdr_data[cbdr_data.index.date == last_cbdr_date]
                    cbdr_h = float(cbdr_window['High'].max())
                    cbdr_l = float(cbdr_window['Low'].min())
                else:
                    # Fallback si TF trop grand ou pas de données
                    cbdr_h = float(df['High'].tail(12).max())
                    cbdr_l = float(df['Low'].tail(12).min())

                # Fenêtre Flout: 15h-00h (on prend une fenêtre glissante des dernières 24h plutôt qu'un jour précis à cause du minuit)
                flout_mask = (df_tz.index.hour >= 15) | (df_tz.index.hour < 1)
                flout_data = df_tz[flout_mask]
                
                if len(flout_data) > 0:
                    # On approxime la dernière session en prenant les données depuis les 24 dernières heures du dernier tick flout
                    last_flout_time = flout_data.index[-1]
                    flout_window = flout_data[flout_data.index >= (last_flout_time - datetime.timedelta(hours=12))]
                    flout_h = float(flout_window['High'].max())
                    flout_l = float(flout_window['Low'].min())
                else:
                    flout_h = cbdr_h
                    flout_l = cbdr_l
            else:
                # Fallback sans timezone
                cbdr_h = float(df['High'].tail(12).max())
                cbdr_l = float(df['Low'].tail(12).min())
                flout_h = cbdr_h
                flout_l = cbdr_l

            cbdr_range = cbdr_h - cbdr_l
            # Calcul en pips (approximation pour Forex: 1 pip = 0.0001 pour les paires majeures)
            pip_val = 0.0001 if cbdr_h < 10 else (0.01 if cbdr_h < 100 else 1.0)
            cbdr_pips = cbdr_range / pip_val

            # Bible §5: CBDR < 40 pips = Explosive (déploiement tendanciel massif le lendemain)
            explosive = cbdr_pips < 40

            # Projections SD depuis CBDR (Bible §5: targets -1.0, -2.0, -2.5, -3.5)
            projections_bull = {
                "sd_1_0": round(cbdr_h + cbdr_range * 1.0, 5),
                "sd_2_0": round(cbdr_h + cbdr_range * 2.0, 5),
                "sd_2_5": round(cbdr_h + cbdr_range * 2.5, 5),
                "sd_3_5": round(cbdr_h + cbdr_range * 3.5, 5),
            }
            projections_bear = {
                "sd_1_0": round(cbdr_l - cbdr_range * 1.0, 5),
                "sd_2_0": round(cbdr_l - cbdr_range * 2.0, 5),
                "sd_2_5": round(cbdr_l - cbdr_range * 2.5, 5),
                "sd_3_5": round(cbdr_l - cbdr_range * 3.5, 5),
            }

            return {
                "cbdr_high": round(cbdr_h, 5),
                "cbdr_low": round(cbdr_l, 5),
                "cbdr_range_pips": round(cbdr_pips, 1),
                "cbdr_explosive": explosive,
                "flout_high": round(flout_h, 5),
                "flout_low": round(flout_l, 5),
                "projections_bull": projections_bull,
                "projections_bear": projections_bear,
            }
        except Exception as e:
            log.warning(f"CBDR Calculation error: {e}")  # MOY-1 FIX
            return {
                "cbdr_high": 0, "cbdr_low": 0, "cbdr_range_pips": 0,
                "cbdr_explosive": False, "flout_high": 0, "flout_low": 0,
                "projections_bull": {}, "projections_bear": {}
            }

    def _find_ndog(self, df):
        try:
            if hasattr(df.index, 'hour'):
                day_opens = df[df.index.hour == 0]['Open']
                if len(day_opens) >= 1:
                    return float(day_opens.iloc[-1])
            return float(df['Open'].iloc[-24]) if len(df) > 24 else 0
        except Exception as e:
            log.warning(f"NDOG Extraction error: {e}") # MOY-1 FIX
            return 0

    def _find_nwog(self, df):
        try:
            if hasattr(df.index, 'dayofweek'):
                mondays = df[df.index.dayofweek == 0]
                if len(mondays) >= 1:
                    return float(mondays['Open'].iloc[-1])
            return 0
        except Exception as e:
            log.warning(f"NWOG Extraction error: {e}") # MOY-1 FIX
            return 0

    # =====================================================
    # PROXIMAL LIQUIDITY — niveau le plus proche du prix actuel
    # =====================================================
    def _nearest(self, p, eqh, eql, erl):
        targets = []
        for item in eqh:
            targets.append(item['price'])
        for item in eql:
            targets.append(item['price'])
        targets.append(erl['high'])
        targets.append(erl['low'])
        if not targets:
            return 0
        return min(targets, key=lambda x: abs(x - p))
