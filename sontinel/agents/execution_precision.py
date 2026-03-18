import pandas as pd
import numpy as np

class ExecutionPrecision:
    def __init__(self, symbol):
        self.symbol = symbol

    def analyze(self, df, smc, liq):
        if df is None or len(df) < 50: return None
        
        current_p = df['Close'].iloc[-1]
        sw_h = smc['structure']['swh']
        sw_l = smc['structure']['swl']
        
        # Déterminer le sens du dealing range pour OTE
        # Bible §8: Achat en Discount → retracement HAUSSIER, Vente en Premium → retracement BAISSIER
        is_bullish = current_p > (sw_h + sw_l) / 2
        
        ote = self._calculate_ote(sw_h, sw_l, is_bullish)
        pd_rank = self._rank_pd_arrays(smc, current_p)
        sd_projections = self._standard_deviations(df, sw_h, sw_l, is_bullish)
        eq_data = self._get_equilibrium_status(current_p, sw_h, sw_l)

        return {
            "ote": ote,
            "pd_hierarchy": pd_rank,
            "projections": sd_projections,
            "equilibrium": eq_data
        }

    def _calculate_ote(self, high, low, is_bullish):
        """
        Bible §8 CORRIGÉ: OTE bidirectionnel
        - Bullish: retracement depuis le haut → niveaux en dessous du high
        - Bearish: retracement depuis le bas → niveaux au-dessus du low
        """
        diff = high - low
        if is_bullish:
            # Retracement haussier (prix retrace VERS LE BAS depuis le high)
            return {
                "lvl_62": high - (diff * 0.62),
                "lvl_705": high - (diff * 0.705),
                "lvl_79": high - (diff * 0.79)
            }
        else:
            # Retracement baissier (prix retrace VERS LE HAUT depuis le low)
            return {
                "lvl_62": low + (diff * 0.62),
                "lvl_705": low + (diff * 0.705),
                "lvl_79": low + (diff * 0.79)
            }

    def _get_equilibrium_status(self, p, h, l):
        mid = (h + l) / 2
        pct = ((p - l) / (h - l)) * 100 if (h - l) != 0 else 50
        
        zone = "DISCOUNT"
        if pct > 75: zone = "DEEP_PREMIUM"
        elif pct > 50: zone = "PREMIUM"
        elif pct < 25: zone = "DEEP_DISCOUNT"
        
        return {
            "mid": mid,
            "zone": zone,
            "percent": pct
        }

    def _rank_pd_arrays(self, smc, p):
        """
        Bible §14 CORRIGÉ: Scoring combiné power + distance (pas seulement power)
        """
        scores = []
        
        for f in smc['fvgs']:
            dist = abs(p - f['ce'])
            # Bonus si Fresh
            power = 1
            if f.get('quality') == 'FRESH': power = 2
            if f.get('quality') == 'INVERTED': power = 2  # IFVG = important
            scores.append({"type": f['type'], "price": f['ce'], "power": power, "dist": dist})
            
        for bm in smc['institutional_blocks']:
            dist = abs(p - bm['level'])
            base_power = 3 if "BREAKER" in bm['type'] else 2
            # Bonus quality score
            base_power += bm.get('quality_score', 0) * 0.5
            scores.append({"type": bm['type'], "price": bm['level'], "power": base_power, "dist": dist})

        rb = smc['rejections']
        if rb['bull_wick_ce'] > 0: 
            scores.append({"type": "REJECTION_BULL", "price": rb['bull_wick_ce'], "power": 2, "dist": abs(p - rb['bull_wick_ce'])})
        if rb['bear_wick_ce'] > 0: 
            scores.append({"type": "REJECTION_BEAR", "price": rb['bear_wick_ce'], "power": 2, "dist": abs(p - rb['bear_wick_ce'])})
        
        # Tri combiné: power descendant PUIS distance ascendante
        return sorted(scores, key=lambda x: (-x['power'], x['dist']))

    def _standard_deviations(self, df, high, low, is_bullish):
        """
        Bible §5 CORRIGÉ: Projections SD bidirectionnelles
        """
        leg = high - low
        if leg == 0: return {}
        
        if is_bullish:
            return {
                "target_1_0": high + (leg * 1.0),
                "target_2_0": high + (leg * 2.0),
                "target_2_5": high + (leg * 2.5),
                "target_3_5": high + (leg * 3.5)
            }
        else:
            return {
                "target_1_0": low - (leg * 1.0),
                "target_2_0": low - (leg * 2.0),
                "target_2_5": low - (leg * 2.5),
                "target_3_5": low - (leg * 3.5)
            }

    def calculate_risk(self, entry, stop, balance, risk_percent=0.01, symbol=None):
        """
        Calcule la taille de lot pour un risque donné.
        Utilise les données MT5 réelles si disponibles (tick_value par symbole).
        Fallback sur des valeurs approchées si MT5 est hors ligne.
        """
        dist = abs(entry - stop)
        if entry == stop or dist == 0:
            return 0.01

        risk_amount = balance * risk_percent

        # Méthode précise : MT5 tick_value réel
        if symbol:
            try:
                import MetaTrader5 as mt5
                if mt5.initialize():
                    sym_info = mt5.symbol_info(symbol)
                    if sym_info and sym_info.trade_tick_size > 0 and sym_info.trade_tick_value > 0:
                        dist_ticks = dist / sym_info.trade_tick_size
                        lot = risk_amount / (dist_ticks * sym_info.trade_tick_value)
                        vol_step = sym_info.volume_step if sym_info.volume_step > 0 else 0.01
                        lot = round(lot / vol_step) * vol_step
                        lot = max(sym_info.volume_min, min(lot, sym_info.volume_max))
                        return round(min(lot, 5.0), 2)
            except Exception:
                pass

        # Fallback approché par type d'actif
        pip_values = {
            "XAUUSD": 1.0,   # Or : ~1$/pip/lot
            "EURUSD": 0.1,
            "GBPUSD": 0.1,
            "USDJPY": 0.09,
            "NAS100": 0.5,
            "US500":  0.5,
            "BTCUSD": 1.0,
        }
        sym_key = (symbol or "").upper()
        pip_val = pip_values.get(sym_key, 0.1)
        lot = risk_amount / (dist * pip_val * 100)
        return round(max(0.01, min(lot, 5.0)), 2)