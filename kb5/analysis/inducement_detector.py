# analysis/inducement_detector.py
"""
══════════════════════════════════════════════════════════════
Sentinel Pro KB5 — Détecteur Inducement (IDM)
══════════════════════════════════════════════════════════════
Responsabilités :
  - Détecter les Inducement (IDM) institutionnels ICT/SMC
  - Identifier les fausses cassures (Stop Hunt) avant POI
  - Valider la légitimité d'un OB / FVG par présence d'IDM

Logique ICT — Inducement :
  Un Inducement (IDM) est un point de liquidité interne mineur
  (Swing High / Low intermédiaire) qui est balayé PAR LE MARCHÉ
  AVANT que le prix ne touche la zone POI (OB / FVG) réelle.

  Exemple Bullish :
    - Tendance haussière en cours
    - Formation d'un Swing Low intermédiaire (IDM)
    - Prix descend, prélève l'IDM (stop hunt sous le low)
    - Puis remonte vers le POI (OB Bullish ou FVG Bullish)
    → Signal haute probabilité : les algos ont pris la liquidité
      côté vendeur avant d'accélérer à la hausse

  Exemple Bearish :
    - Tendance baissière en cours
    - Formation d'un Swing High intermédiaire (IDM)
    - Prix monte, prélève l'IDM (stop hunt au-dessus du high)
    - Puis descend vers le POI (OB Bearish ou FVG Bearish)
    → Signal haute probabilité : liquidity sweep BSL précédent

Consommé par :
  - kb5_engine.py  → bonus de confluence IDM (+12 pts)
  - scoring_engine.py → filtre de qualité setup
══════════════════════════════════════════════════════════════
"""

import logging
import threading
import pandas as pd
import numpy as np
from typing import Optional

from datastore.data_store import DataStore
from config.constants import Trading
from analysis.detector_mixin import DetectorMixin

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# CONSTANTES LOCALES
# ══════════════════════════════════════════════════════════════

IDM_SWING_LOOKBACK  = 10    # fenêtre pour localiser un Swing H/L interne
IDM_POI_PROXIMITY   = 0.5   # ratio ATR : POI doit être à moins de X×ATR du prix actuel
IDM_FRESH_CANDLES   = 6     # IDM "frais" si prélevé dans les 6 dernières bougies
IDM_TIMEFRAMES      = ["H4", "H1", "M15"]   # TF où l'IDM est pertinent

CONFLUENCE_IDM      = 12    # bonus de score si IDM confirmé

# ══════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE
# ══════════════════════════════════════════════════════════════

class InducementDetector(DetectorMixin):
    """
    Détecte les Inducements (IDM) institutionnels sur H4, H1 et M15.

    Un IDM est validé si :
      1. Un Swing High/Low interne mineur est identifiable
      2. Le prix DÉPASSE ce point (sweep de liquidité interne)
      3. La clôture de la bougie revient DANS la range précédente
         (le dépassement = prise de liquidité, pas une vraie cassure)
      4. Un POI (OB ou FVG) dans la direction du biais se trouve
         dans une zone proche après le sweep

    Le sweep d'IDM augmente la probabilité institutionnelle du setup.
    """

    def __init__(self, data_store: DataStore,
                 ob_detector=None,
                 fvg_detector=None,
                 bias_detector=None,
                 settings_integration=None):
        super().__init__(settings_integration)
        self._ds    = data_store
        self._ob    = ob_detector
        self._fvg   = fvg_detector
        self._bias  = bias_detector
        self._lock  = threading.RLock()
        self._cache: dict[str, dict] = {}
        # _cache[pair][tf] = list of IDM dicts
        logger.info("InducementDetector initialisé — IDM / Stop Hunt surveillance active")

    # ══════════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE
    # ══════════════════════════════════════════════════════════

    def scan_pair(self, pair: str) -> dict:
        """
        Scan tous les TF actifs pour détecter les IDM sur la paire.

        Args:
            pair: ex. "EURUSD"

        Returns:
            dict {tf: [idm_list]}
        """
        if not self.is_active():
            return {}
        
        results: dict[str, list] = {}

        # Récupérer le biais directional HTF pour contextualiser
        bias_dir = "NEUTRAL"
        if self._bias:
            bias_data = self._bias.get_bias(pair)
            if bias_data:
                bias_dir = bias_data.get("direction", "NEUTRAL")

        for tf in IDM_TIMEFRAMES:
            df = self._ds.get_candles(pair, tf)
            if df is None or len(df) < IDM_SWING_LOOKBACK + 5:
                logger.debug(f"IDM scan ignoré — {pair} {tf} | données insuffisantes")
                continue

            atr     = self._calculate_atr(df)
            idm_list = self._detect_idm(pair, tf, df, atr, bias_dir)
            results[tf] = idm_list

            logger.debug(
                f"IDM scan — {pair} {tf} | "
                f"idm_détectés={len(idm_list)} | biais={bias_dir}"
            )

        with self._lock:
            self._cache[pair] = results

        return results

    # ══════════════════════════════════════════════════════════
    # DÉTECTION INDUCEMENT
    # ══════════════════════════════════════════════════════════

    def _detect_idm(self, pair: str, tf: str,
                    df: pd.DataFrame, atr: float,
                    bias_dir: str) -> list:
        """
        Détecte les IDM (Inducements) selon le biais HTF.

          - Biais BULLISH → chercher IDM bearish (sweep de SSL interne avant POI haussier)
          - Biais BEARISH → chercher IDM bullish (sweep de BSL interne avant POI baissier)

        Condition de validation IDM :
          1. Identifier un Swing Low interne (bullish) ou High interne (bearish) dans les N dernières bougies
          2. Vérifier que le prix a dépassé ce point puis est revenu (clôture au-delà du point = non valide)
          3. Vérifier qu'un POI (OB/FVG) dans la direction principale existe après le sweep

        Returns:
            liste de dicts IDM
        """
        idm_list = []
        highs    = df["high"].values
        lows     = df["low"].values
        closes   = df["close"].values
        opens    = df["open"].values
        times    = df.index if hasattr(df.index, '__iter__') else df["time"].values

        lookback = min(IDM_SWING_LOOKBACK, len(df) - 4)
        scan_start = max(0, len(df) - lookback - IDM_FRESH_CANDLES - 4)

        for i in range(scan_start, len(df) - IDM_FRESH_CANDLES - 1):
            # ── IDM Bullish context (biais BULLISH) : sweep de SSL interne
            #    Le marché crée un Swing Low interne, l'invalide temporairement,
            #    puis remonte vers l'OB/FVG bullish.
            if bias_dir in ("BULLISH", "NEUTRAL"):
                # Chercher un Swing Low interne dans la fenêtre
                # Low[i] doit être inférieur aux lows voisins
                if i >= 2 and lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                    swing_low = lows[i]
                    idm_level = swing_low

                    # Vérifier si une bougie dans les IDM_FRESH_CANDLES suivantes a :
                    # 1. Un Low qui dépasse le swing (dépasse l'IDM)
                    # 2. Mais CLÔTURE au-dessus de l'IDM (rejet = sweep confirmé)
                    for j in range(i + 1, min(i + IDM_FRESH_CANDLES + 1, len(df))):
                        if lows[j] < idm_level and closes[j] > idm_level:
                            # ✅ Sweep confirmé : la mèche est descendue sous l'IDM
                            # mais la clôture est revenue au-dessus.
                            # Vérifier la présence d'un POI bullish à portée
                            poi_exists = self._check_poi_nearby(
                                pair, tf, closes[-1], "BULLISH", atr
                            )

                            idm_list.append({
                                "id":          f"IDM_BULL_{pair}_{tf}_{str(times[i])}",
                                "pair":        pair,
                                "tf":          tf,
                                "type":        "BULL_IDM",
                                "direction":   "BULLISH",
                                "idm_level":   round(idm_level, 6),
                                "swing_idx":   i,
                                "sweep_idx":   j,
                                "sweep_low":   round(lows[j], 6),
                                "sweep_close": round(closes[j], 6),
                                "poi_nearby":  poi_exists,
                                "formed_at":   str(times[i]),
                                "swept_at":    str(times[j]),
                                "candles_ago": len(df) - 1 - j,  # fraîcheur
                                "status":      "FRESH" if (len(df) - 1 - j) <= IDM_FRESH_CANDLES else "USED",
                            })
                            break  # un seul IDM par swing

            # ── IDM Bearish context (biais BEARISH) : sweep de BSL interne
            if bias_dir in ("BEARISH", "NEUTRAL"):
                # Chercher un Swing High interne
                if i >= 2 and highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                    swing_high = highs[i]
                    idm_level  = swing_high

                    for j in range(i + 1, min(i + IDM_FRESH_CANDLES + 1, len(df))):
                        if highs[j] > idm_level and closes[j] < idm_level:
                            # ✅ Sweep BSL confirmé
                            poi_exists = self._check_poi_nearby(
                                pair, tf, closes[-1], "BEARISH", atr
                            )

                            idm_list.append({
                                "id":           f"IDM_BEAR_{pair}_{tf}_{str(times[i])}",
                                "pair":         pair,
                                "tf":           tf,
                                "type":         "BEAR_IDM",
                                "direction":    "BEARISH",
                                "idm_level":    round(idm_level, 6),
                                "swing_idx":    i,
                                "sweep_idx":    j,
                                "sweep_high":   round(highs[j], 6),
                                "sweep_close":  round(closes[j], 6),
                                "poi_nearby":   poi_exists,
                                "formed_at":    str(times[i]),
                                "swept_at":     str(times[j]),
                                "candles_ago":  len(df) - 1 - j,
                                "status":       "FRESH" if (len(df) - 1 - j) <= IDM_FRESH_CANDLES else "USED",
                            })
                            break

        return idm_list

    # ══════════════════════════════════════════════════════════
    # VÉRIFICATION POI À PORTÉE
    # ══════════════════════════════════════════════════════════

    def _check_poi_nearby(self, pair: str, tf: str,
                           current_price: float,
                           direction: str,
                           atr: float) -> bool:
        """
        Vérifie qu'un POI (OB ou FVG) dans la direction donnée
        se trouve dans un rayon de IDM_POI_PROXIMITY × ATR.

        Returns:
            True si un POI proche existe dans la direction
        """
        proximity = IDM_POI_PROXIMITY * atr

        # Vérifier OB
        if self._ob:
            obs = self._ob.get_valid_ob(pair, tf, direction=direction)
            for ob in obs:
                mid_ob = (ob["top"] + ob["bottom"]) / 2
                if abs(mid_ob - current_price) <= proximity * 5:  # 5× ATR max
                    return True

        # Vérifier FVG
        if self._fvg:
            fvgs = self._fvg.get_fresh_fvg(pair, tf, direction=direction)
            for fvg in fvgs:
                if abs(fvg["midpoint"] - current_price) <= proximity * 5:
                    return True

        return False

    # ══════════════════════════════════════════════════════════
    # CALCUL ATR
    # ══════════════════════════════════════════════════════════

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """ATR Wilder sur `period` bougies. Fallback 0.0001."""
        if len(df) < period + 1:
            return 0.0001

        high  = df["high"].values
        low   = df["low"].values
        close = df["close"].values

        tr_list = [
            max(high[i] - low[i],
                abs(high[i]  - close[i - 1]),
                abs(low[i]   - close[i - 1]))
            for i in range(1, len(df))
        ]

        atr = float(np.mean(tr_list[:period]))
        for tr in tr_list[period:]:
            atr = (atr * (period - 1) + tr) / period

        return atr if atr > 0 else 0.0001

    # ══════════════════════════════════════════════════════════
    # API PUBLIQUE
    # ══════════════════════════════════════════════════════════

    def get_fresh_idm(self, pair: str, tf: str,
                      direction: Optional[str] = None) -> list:
        """
        Retourne les IDM FRESH (récents) pour une paire/TF.

        Un IDM frais indique que la prise de liquidité interne vient
        tout juste de se produire — le setup suivant est haute probabilité.

        Args:
            pair:      ex. "EURUSD"
            tf:        ex. "H1"
            direction: "BULLISH", "BEARISH", ou None

        Returns:
            liste de IDM dicts avec status=FRESH
        """
        with self._lock:
            tf_data = self._cache.get(pair, {}).get(tf, [])

        fresh = [idm for idm in tf_data if idm.get("status") == "FRESH"]

        if direction:
            fresh = [idm for idm in fresh if idm["direction"] == direction]

        return fresh

    def get_dominant_idm(self, pair: str,
                          direction: Optional[str] = None) -> Optional[dict]:
        """
        Retourne l'IDM le plus récent et le plus prioritaire toutes TF.
        Priorité : H1 > H4 > M15 (IDM H1 = confirmation LTF suffisante).

        Returns:
            dict IDM dominant, ou None si aucun IDM frais trouvé
        """
        priority = ["H1", "H4", "M15"]
        for tf in priority:
            fresh = self.get_fresh_idm(pair, tf, direction)
            with_poi = [idm for idm in fresh if idm.get("poi_nearby")]
            if with_poi:
                # Le plus récent = candles_ago le plus petit
                return min(with_poi, key=lambda x: x.get("candles_ago", 999))

        return None

    def has_fresh_idm(self, pair: str,
                       direction: Optional[str] = None) -> bool:
        """
        Retourne True si au moins un IDM frais existe pour cette paire.
        Utilisé par kb5_engine pour filtrer les setups.
        """
        for tf in IDM_TIMEFRAMES:
            if self.get_fresh_idm(pair, tf, direction):
                return True
        return False

    def get_idm_score_bonus(self, pair: str, direction: str) -> int:
        """
        Calcule le bonus de score lié à l'IDM.

        Returns:
            int : CONFLUENCE_IDM si IDM frais avec POI proche, sinon 0
        """
        dom = self.get_dominant_idm(pair, direction)
        if dom and dom.get("poi_nearby") and dom.get("status") == "FRESH":
            return CONFLUENCE_IDM
        return 0

    def clear_cache(self, pair: Optional[str] = None) -> None:
        """Vide le cache IDM."""
        with self._lock:
            if pair:
                self._cache.pop(pair, None)
                logger.info(f"IDM cache vidé — Paire : {pair}")
            else:
                self._cache.clear()
                logger.info("IDM cache vidé — toutes les paires")

    def __repr__(self) -> str:
        pairs = list(self._cache.keys())
        return f"InducementDetector(pairs={pairs}, tf={IDM_TIMEFRAMES})"
