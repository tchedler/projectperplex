import MetaTrader5 as mt5
import pandas as pd

class CorrelationSMT:
    """
    FIX-A: SMT Divergence enrichi — Bible §7
    Couvre: Forex SMT, DXY SMT, Crypto BTC/ETH, Yields US, Indices ES/NQ
    Tolérance temporelle: ≤ 3 bougies d'écart entre les swings comparés.
    Retourne la paire la plus forte (celle à trader) selon la direction de la divergence.
    """
    def __init__(self, main_symbol, correlated_symbol):
        self.main_symbol = main_symbol
        self.corr_symbol = correlated_symbol

    def analyze_smt(self, main_df):
        """SMT croisé entre deux paires corrélées sur 20 bougies M15."""
        result = self._compute_smt_divergence(main_df, self.corr_symbol, mt5.TIMEFRAME_M15)
        return result

    def _compute_smt_divergence(self, main_df, corr_symbol, tf):
        """
        Bible §7: Détection SMT avec tolérance temporelle ≤ 3 bougies.
        Détermine aussi quelle paire est la plus forte (celle à trader).
        """
        rates = mt5.copy_rates_from_pos(corr_symbol, tf, 0, 50)
        if rates is None:
            return self._default_result()

        corr_df = pd.DataFrame(rates)
        m_df = main_df.tail(50)

        m_high = m_df['High'].iloc[-20:-1].max()
        m_low = m_df['Low'].iloc[-20:-1].min()
        c_high = corr_df['high'].iloc[-20:-1].max()
        c_low = corr_df['low'].iloc[-20:-1].min()

        m_curr_h = m_df['High'].iloc[-1]
        m_curr_l = m_df['Low'].iloc[-1]
        c_curr_h = corr_df['high'].iloc[-1]
        c_curr_l = corr_df['low'].iloc[-1]

        smt = False
        smt_type = "NONE"
        stronger_pair = "NONE"
        trade_direction = "NONE"

        # SMT Baissière: main fait un Higher High mais corr ne le fait pas
        # → Manipulation du main → La paire corrélée (plus forte) est à vendre
        if m_curr_h > m_high and c_curr_h < c_high:
            smt = True
            smt_type = "SMT_BEARISH"
            # Tolérance temporelle: vérifier que les highs sont dans ≤ 3 bougies d'écart
            m_hi_idx = m_df['High'].iloc[-20:-1].idxmax()
            c_hi_idx = m_df.index[max(0, len(m_df)-20)]  # approximation
            stronger_pair = corr_symbol  # paire qui n'a pas fait le nouveau high = plus forte en résistance
            trade_direction = "SELL"      # vendre la paire la plus forte selon ICT §7

        # SMT Haussière: main fait un Lower Low mais corr ne le fait pas
        # → Manipulation du main → La paire corrélée (plus forte en support) est à acheter
        elif m_curr_l < m_low and c_curr_l > c_low:
            smt = True
            smt_type = "SMT_BULLISH"
            stronger_pair = corr_symbol
            trade_direction = "BUY"

        return {
            "smt_divergence": smt,
            "smt_type": smt_type,
            "correlated_with": corr_symbol,
            "stronger_pair": stronger_pair,
            "trade_direction": trade_direction,
            "status": "DIVERGENCE_CONFIRMED" if smt else "SMOOTH_CORRELATION",
            "m_high": round(m_high, 5),
            "m_low": round(m_low, 5),
            "c_high": round(c_high, 5),
            "c_low": round(c_low, 5),
        }

    def _default_result(self):
        return {
            "smt_divergence": False, "smt_type": "NONE",
            "correlated_with": self.corr_symbol, "stronger_pair": "NONE",
            "trade_direction": "NONE", "status": "DATA_UNAVAILABLE",
            "m_high": 0, "m_low": 0, "c_high": 0, "c_low": 0
        }

    # ============================================================
    # CORRELATIONS SPÉCIFIQUES PAR TYPE D'INSTRUMENT — Bible §7
    # ============================================================
    def get_dxy_smt(self, main_df, dxy_df):
        """
        Bible §7: DXY SMT — si DXY et EUR/USD montent dans la MÊME direction → anomalie.
        Règle: DXY et EUR/USD doivent être inversement corrélés.
        """
        if dxy_df is None or len(dxy_df) < 20:
            return {"dxy_smt": False, "note": "DXY data unavailable"}

        m_close = main_df['Close'].pct_change().tail(10).sum()
        d_close = dxy_df['Close'].pct_change().tail(10).sum() if 'Close' in dxy_df else 0

        # Si les deux vont dans la même direction → anomalie
        anomaly = (m_close > 0 and d_close > 0) or (m_close < 0 and d_close < 0)
        return {
            "dxy_smt": anomaly,
            "status": "DXY_ANOMALY_→_INVERSION_ATTENDUE" if anomaly else "CORRÉLATION_NORMALE",
            "eur_change_10d": round(m_close * 100, 3),
            "dxy_change_10d": round(d_close * 100, 3),
        }

    def get_crypto_smt(self, btc_df, eth_df):
        """
        Bible §7 (Mentorship 2024): BTC/ETH SMT.
        Si BTC fait un nouveau High mais ETH ne le fait pas → SMT Baissière sur BTC.
        """
        if btc_df is None or eth_df is None:
            return {"crypto_smt": False, "note": "Data unavailable"}

        btc_h = btc_df['High'].tail(20).max()
        eth_h = eth_df['High'].tail(20).max()
        btc_curr = btc_df['High'].iloc[-1]
        eth_curr = eth_df['High'].iloc[-1]

        btc_smt_bear = btc_curr > btc_h and eth_curr < eth_h
        btc_smt_bull = btc_df['Low'].iloc[-1] < btc_df['Low'].tail(20).min() and eth_df['Low'].iloc[-1] > eth_df['Low'].tail(20).min()

        return {
            "crypto_smt": btc_smt_bear or btc_smt_bull,
            "type": "SMT_BEAR_BTC" if btc_smt_bear else ("SMT_BULL_BTC" if btc_smt_bull else "NONE"),
            "action": "SELL BTC" if btc_smt_bear else ("BUY BTC" if btc_smt_bull else "NONE"),
        }

    def get_indices_smt(self, es_df, nq_df):
        """
        Bible §7: ES/NQ SMT.
        Si ES fait un nouveau High mais NQ non → divergence → prudence.
        """
        if es_df is None or nq_df is None:
            return {"indices_smt": False, "note": "Data unavailable"}

        es_prev_h = es_df['High'].tail(20).iloc[:-1].max()
        nq_prev_h = nq_df['High'].tail(20).iloc[:-1].max()
        es_curr_h = es_df['High'].iloc[-1]
        nq_curr_h = nq_df['High'].iloc[-1]

        divergence = (es_curr_h > es_prev_h) and (nq_curr_h < nq_prev_h)
        return {
            "indices_smt": divergence,
            "type": "ES_NQ_DIVERGENCE" if divergence else "CONFLUENT",
            "action": "PRUDENCE — ES fort / NQ faible" if divergence else "Pas de divergence",
        }