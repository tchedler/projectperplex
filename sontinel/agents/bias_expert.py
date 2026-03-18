import pandas as pd
import numpy as np

class BiasExpert:
    def __init__(self, symbol):
        self.symbol = symbol

    def analyze(self, d1_df, w1_df, mn_df):
        if d1_df is None or w1_df is None: return None
        
        current_p = d1_df['Close'].iloc[-1]
        
        pd_hl = {"pdh": d1_df['High'].iloc[-2], "pdl": d1_df['Low'].iloc[-2]}
        pw_hl = {"pwh": w1_df['High'].iloc[-2], "pwl": w1_df['Low'].iloc[-2]}
        pm_hl = {"pmh": mn_df['High'].iloc[-2], "pml": mn_df['Low'].iloc[-2]} if mn_df is not None and len(mn_df) > 1 else {}
        
        ipda_20 = self._get_lookback(d1_df, 20)
        ipda_40 = self._get_lookback(d1_df, 40)
        ipda_60 = self._get_lookback(d1_df, 60)
        
        # Bible §15 CORRIGÉ: Bias basé sur structure HTF + IPDA + momentum
        bias = self._determine_bias(d1_df, w1_df, current_p, ipda_20, ipda_40)
        
        dol = self._get_dol(current_p, pd_hl, pw_hl, ipda_20)

        return {
            "daily_levels": pd_hl,
            "weekly_levels": pw_hl,
            "monthly_levels": pm_hl,
            "ipda_ranges": {"r20": ipda_20, "r40": ipda_40, "r60": ipda_60},
            "htf_bias": bias,
            "draw_on_liquidity": dol
        }

    def _determine_bias(self, d1_df, w1_df, current_p, ipda_20, ipda_40):
        """
        Bible CORRIGÉ: Bias HTF multi-facteur
        1. Position vs IPDA ranges (20 et 40 jours)
        2. Momentum (EMA croisement)
        3. Weekly structure alignment
        """
        score_bull = 0
        score_bear = 0
        
        # Factor 1: Position vs IPDA 20 mid
        if current_p > ipda_20['mid']: score_bull += 1
        else: score_bear += 1
        
        # Factor 2: Position vs IPDA 40 mid
        if current_p > ipda_40['mid']: score_bull += 1
        else: score_bear += 1
        
        # Factor 3: Momentum — vraie EMA (expWeighted) au lieu de SMA
        ema5  = d1_df['Close'].ewm(span=5,  adjust=False).mean().iloc[-1]
        ema20 = d1_df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
        if ema5 > ema20: score_bull += 1
        else: score_bear += 1

        # Factor 4: Direction de la bougie hebdomadaire courante
        if len(w1_df) >= 2:
            w_current = w1_df['Close'].iloc[-1]
            w_open    = w1_df['Open'].iloc[-1]
            if w_current > w_open: score_bull += 1
            else: score_bear += 1

        # Factor 5 : Série de Higher Highs (HL) sur 3 derniers jours (BULL)
        #            ou série de Lower Lows (LL) sur 3 derniers jours (BEAR)
        #            → un seul facteur attribué selon la tendance dominante
        if len(d1_df) >= 4:
            hh = d1_df['High'].iloc[-1] > d1_df['High'].iloc[-2] > d1_df['High'].iloc[-3]
            ll = d1_df['Low'].iloc[-1]  < d1_df['Low'].iloc[-2]  < d1_df['Low'].iloc[-3]
            if hh and not ll: score_bull += 1
            elif ll and not hh: score_bear += 1
        
        # Verdict
        if score_bull >= 4: return "BULLISH_EXPANSION"
        if score_bear >= 4: return "BEARISH_EXPANSION"
        if score_bull >= 3: return "BULLISH_RETRACE"
        if score_bear >= 3: return "BEARISH_RETRACE"
        return "NEUTRAL"

    def _get_lookback(self, df, days):
        window = df.tail(days)
        h = window['High'].max()
        l = window['Low'].min()
        return {"high": h, "low": l, "mid": (h + l) / 2}

    def _get_dol(self, p, pd, pw, r20):
        """
        Bible §16 CORRIGÉ: Distance normalisée en pourcentage (pas en prix absolu)
        """
        targets = []
        targets.append({"name": "PDH", "price": pd['pdh'], "dist": abs(p - pd['pdh']) / p})
        targets.append({"name": "PDL", "price": pd['pdl'], "dist": abs(p - pd['pdl']) / p})
        targets.append({"name": "PWH", "price": pw['pwh'], "dist": abs(p - pw['pwh']) / p})
        targets.append({"name": "PWL", "price": pw['pwl'], "dist": abs(p - pw['pwl']) / p})
        targets.append({"name": "IPDA_20_H", "price": r20['high'], "dist": abs(p - r20['high']) / p})
        targets.append({"name": "IPDA_20_L", "price": r20['low'], "dist": abs(p - r20['low']) / p})
        
        sorted_targets = sorted(targets, key=lambda x: x['dist'])
        return sorted_targets[0]