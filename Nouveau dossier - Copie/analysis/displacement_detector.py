"""
Sentinel Pro KB5 — Displacement Detector (ICT)
"""
import logging
from datastore.data_store import DataStore

logger = logging.getLogger(__name__)

class DisplacementDetector:
    def __init__(self, data_store, fvg_detector, mss_detector):
        self._ds = data_store
        self._fvg = fvg_detector
        self._mss = mss_detector

    def detect(self, pair, tf):
        df = self._ds.get_candles(pair, tf)
        if len(df) < 10:
            return {"detected": False}
        
        mss = self._mss.has_mss(pair, tf)
        fvg = self._fvg.get_fresh_fvg(pair, tf)
        impulse = self._check_impulse_sequence(df)
        
        detected = mss and len(fvg) > 0 and impulse >= 3
        
        return {
            "detected": detected,
            "mss": mss,
            "fvg_count": len(fvg),
            "impulse_sequence": impulse
        }
    
    def _check_impulse_sequence(self, df):
        count = 0
        for i in range(1, min(10, len(df))):
            body = abs(df.close.iloc[-i] - df.open.iloc[-i])
            total = df.high.iloc[-i] - df.low.iloc[-i]
            if total > 0 and body / total > 0.6:
                count += 1
            else:
                break
        return count
