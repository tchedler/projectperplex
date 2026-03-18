# analysis/cot_seasonality.py
"""
══════════════════════════════════════════════════════════════
Sentinel Pro KB5 — COT (Commitment of Traders) & Seasonality
══════════════════════════════════════════════════════════════
Responsabilités :
  - Fournir un biais directionnel basé sur les données COT
    (positions des Large Speculators vs Commercials)
  - Identifier les patterns de saisonnalité historique
    (mois bullish / bearish sur chaque paire)
  - Ajuster le Monthly Bias (MN) du BiasDetector

Logique COT (Commitment of Traders) :
  Les trois catégories de traders CFTC :
    - Commercial Hedgers  : vendent quand le marché monte (hedging)
    - Large Speculators  : suivent la tendance (trend-following funds)
    - Small Speculators  : gros souvent dans le mauvais sens

  Signal haussier COT :
    - Large Specs sont NET LONG (positions longues > shorts)
    - Commercials deviennent NET LONG après une période de couverture extrême
    - Small Specs sont NET SHORT (signal contrarian)

  Signal baissier COT :
    - Large Specs sont NET SHORT
    - Commercials NET SHORT massivement
    - Small Specs NET LONG (signal contrarian)

Note :
  - Les données COT sont publiées chaque vendredi (avec délai 3 jours).
  - En l'absence d'API dédiée, ce module utilise des données structurées
    manuellement et un mécanisme d'override JSON configurable.
  - Structure extensible : l'utilisateur peut brancher une API CFTC/Quandl.

Consommé par :
  - bias_detector.py → ajustement du Monthly Bias
  - kb5_engine.py    → bonus/malus selon le signal COT
══════════════════════════════════════════════════════════════
"""

import logging
import json
import threading
from datetime import datetime, timezone, date
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════

# Bonus/Malus appliqué au score si signal COT aligné
CONFLUENCE_COT_ALIGNED   = 10   # COT aligné avec la direction du trade
CONFLUENCE_COT_OPPOSED   = -10  # COT opposé à la direction du trade

# Bonus si in-season (période historiquement favorable à la direction)
CONFLUENCE_SEASONAL_BULL = 7
CONFLUENCE_SEASONAL_BEAR = 7

# ── Saisonnalité historique (basée sur les statistiques Forex long-terme)
#    Clé : (paire, mois 1-12) → biais attendu "BULLISH" / "BEARISH" / "NEUTRAL"
#    Source : études saisonnières Gold / Forex (données 1990-2024)
HISTORICAL_SEASONALITY: dict[tuple, str] = {
    # EURUSD : Saisonnalité classique
    ("EURUSD",  1): "BEARISH",   # Janvier : USD fort post-FOMC
    ("EURUSD",  2): "BULLISH",
    ("EURUSD",  3): "BEARISH",
    ("EURUSD",  4): "BULLISH",
    ("EURUSD",  5): "NEUTRAL",
    ("EURUSD",  6): "BEARISH",
    ("EURUSD",  7): "BULLISH",
    ("EURUSD",  8): "BEARISH",   # Août : faible liquidité
    ("EURUSD",  9): "BEARISH",
    ("EURUSD", 10): "BULLISH",
    ("EURUSD", 11): "BULLISH",
    ("EURUSD", 12): "BEARISH",
    # GBPUSD : Corrélée EUR mais plus volatile
    ("GBPUSD",  1): "BEARISH",
    ("GBPUSD",  2): "BULLISH",
    ("GBPUSD",  3): "BULLISH",
    ("GBPUSD",  4): "BULLISH",
    ("GBPUSD",  5): "NEUTRAL",
    ("GBPUSD",  6): "BEARISH",
    ("GBPUSD",  7): "NEUTRAL",
    ("GBPUSD",  8): "BEARISH",
    ("GBPUSD",  9): "BEARISH",
    ("GBPUSD", 10): "NEUTRAL",
    ("GBPUSD", 11): "BULLISH",
    ("GBPUSD", 12): "BEARISH",
    # XAUUSD (Gold) : Saisonnalité très forte
    ("XAUUSD",  1): "BULLISH",   # Demande asiatique / CNY
    ("XAUUSD",  2): "BULLISH",
    ("XAUUSD",  3): "NEUTRAL",
    ("XAUUSD",  4): "BEARISH",
    ("XAUUSD",  5): "NEUTRAL",
    ("XAUUSD",  6): "BEARISH",
    ("XAUUSD",  7): "BEARISH",
    ("XAUUSD",  8): "BULLISH",   # Demande indienne (mariages)
    ("XAUUSD",  9): "BULLISH",
    ("XAUUSD", 10): "BEARISH",
    ("XAUUSD", 11): "BULLISH",
    ("XAUUSD", 12): "BULLISH",
    # NAS100 / US100
    ("NAS100",  1): "BULLISH",
    ("NAS100",  2): "BEARISH",
    ("NAS100",  3): "BULLISH",
    ("NAS100",  4): "BULLISH",
    ("NAS100",  5): "NEUTRAL",
    ("NAS100",  6): "BULLISH",
    ("NAS100",  7): "BULLISH",
    ("NAS100",  8): "NEUTRAL",
    ("NAS100",  9): "BEARISH",   # "Sell in September"
    ("NAS100", 10): "BEARISH",
    ("NAS100", 11): "BULLISH",
    ("NAS100", 12): "BULLISH",   # "Santa Rally"
    # US30 (Dow Jones)
    ("US30",  1): "BULLISH",
    ("US30",  9): "BEARISH",
    ("US30", 10): "BEARISH",
    ("US30", 11): "BULLISH",
    ("US30", 12): "BULLISH",
}

# ── COT Snapshot statique (exemple de structure)
#    En production, charger depuis data/cot_data.json
#    Structure : {pair: {large_specs_net: int, commercials_net: int, date: str}}
DEFAULT_COT_DATA: dict[str, dict] = {
    "EURUSD": {"large_specs_net": 0,    "commercials_net": 0,    "date": "N/A"},
    "GBPUSD": {"large_specs_net": 0,    "commercials_net": 0,    "date": "N/A"},
    "XAUUSD": {"large_specs_net": 0,    "commercials_net": 0,    "date": "N/A"},
    "NAS100": {"large_specs_net": 0,    "commercials_net": 0,    "date": "N/A"},
    "US30":   {"large_specs_net": 0,    "commercials_net": 0,    "date": "N/A"},
}

# ══════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE
# ══════════════════════════════════════════════════════════════

class COTSeasonality:
    """
    Fournit deux signaux complémentaires pour le Monthly Bias :
      1. Saisonnalité historique (statique, par mois et paire)
      2. Positionnement COT (dynamique, chargeable depuis JSON)

    Ces signaux enrichissent le bias MN et permettent d'éviter
    de trader contre les flux institutionnels hebdomadaires réels.
    """

    def __init__(self, cot_data_path: Optional[str] = None):
        self._lock      = threading.RLock()
        self._cot_data  = dict(DEFAULT_COT_DATA)
        self._data_path = cot_data_path

        # Charger les données COT depuis le fichier si disponible
        if cot_data_path:
            self._load_cot_from_file(cot_data_path)

        logger.info(
            "COTSeasonality initialisé — "
            f"saisonnalité {len(HISTORICAL_SEASONALITY)} paires×mois | "
            f"COT {'chargé' if cot_data_path else 'par défaut (non configuré)'}"
        )

    # ══════════════════════════════════════════════════════════
    # CHARGEMENT DONNÉES COT
    # ══════════════════════════════════════════════════════════

    def _load_cot_from_file(self, path: str) -> None:
        """
        Charge les données COT depuis un fichier JSON.
        Format attendu :
        {
          "EURUSD": {
            "large_specs_net": 85000,
            "commercials_net": -72000,
            "date": "2026-03-14"
          },
          ...
        }
        """
        try:
            p = Path(path)
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with self._lock:
                    self._cot_data.update(data)
                logger.info(f"COT data chargé depuis {path} — {len(data)} paires")
            else:
                logger.warning(f"Fichier COT non trouvé : {path} — utilisation des données par défaut")
        except Exception as e:
            logger.error(f"Erreur chargement COT : {e}")

    def update_cot(self, pair: str, large_specs_net: int,
                   commercials_net: int, date_str: str) -> None:
        """
        Met à jour manuellement les données COT pour une paire.
        Peut être appelé depuis un scheduler hebdomadaire ou une API CFTC.

        Args:
            pair:            ex. "EURUSD"
            large_specs_net: positions nettes des Large Speculators (+ = long, - = short)
            commercials_net: positions nettes des Commercials (+ = long, - = short)
            date_str:        date de publication CFTC "YYYY-MM-DD"
        """
        with self._lock:
            self._cot_data[pair] = {
                "large_specs_net": large_specs_net,
                "commercials_net": commercials_net,
                "date":            date_str,
            }
        logger.info(
            f"COT mis à jour — {pair} | "
            f"LS_NET={large_specs_net:+d} | COMM_NET={commercials_net:+d} | date={date_str}"
        )

    # ══════════════════════════════════════════════════════════
    # SIGNAL SAISONNALITÉ
    # ══════════════════════════════════════════════════════════

    def get_seasonal_bias(self, pair: str,
                           month: Optional[int] = None) -> dict:
        """
        Retourne le biais saisonnier historique pour une paire/mois.

        Args:
            pair:  ex. "EURUSD"
            month: mois 1-12 (None = mois actuel UTC)

        Returns:
            dict {bias, month, pair, confidence}
        """
        if month is None:
            month = datetime.now(timezone.utc).month

        bias = HISTORICAL_SEASONALITY.get((pair, month), "NEUTRAL")

        return {
            "pair":       pair,
            "month":      month,
            "bias":       bias,
            "confidence": "HIGH" if bias != "NEUTRAL" else "LOW",
            "source":     "HISTORICAL_SEASONALITY",
        }

    # ══════════════════════════════════════════════════════════
    # SIGNAL COT
    # ══════════════════════════════════════════════════════════

    def get_cot_bias(self, pair: str) -> dict:
        """
        Calcule le biais directionnel basé sur les positions COT.

        Logique :
          - Large Specs NET LONG fortement (> 80k) = Signal BULLISH
          - Large Specs NET SHORT fortement (< -80k) = Signal BEARISH
          - Neutralité : entre -40k et +40k
          - Commercials inversement corrélés (ils hedgent) : si NET LONG = signal de fond baissier
            car ils couvrent des actifs physiques en vendant les futures

        Returns:
            dict {bias, large_specs_net, commercials_net, date, strength}
        """
        with self._lock:
            data = self._cot_data.get(pair, {})

        ls_net   = data.get("large_specs_net", 0)
        comm_net = data.get("commercials_net", 0)
        cot_date = data.get("date", "N/A")

        # Signal Large Speculators (momentum institutionnel)
        if ls_net > 40000:
            bias     = "BULLISH"
            strength = "STRONG" if ls_net > 80000 else "MODERATE"
        elif ls_net < -40000:
            bias     = "BEARISH"
            strength = "STRONG" if ls_net < -80000 else "MODERATE"
        else:
            bias     = "NEUTRAL"
            strength = "WEAK"

        # Confirmation : si Commercials vont dans le même sens que LS = rare et fort
        comm_confirms = (bias == "BULLISH" and comm_net > 0) or \
                        (bias == "BEARISH" and comm_net < 0)

        if comm_confirms and bias != "NEUTRAL":
            strength = "VERY_STRONG"  # Rare = très institutionnel

        return {
            "pair":            pair,
            "bias":            bias,
            "strength":        strength,
            "large_specs_net": ls_net,
            "commercials_net": comm_net,
            "date":            cot_date,
            "comm_confirms":   comm_confirms,
            "source":          "COT_CFTC",
        }

    # ══════════════════════════════════════════════════════════
    # SIGNAL COMPOSITE COT + SAISONNALITÉ
    # ══════════════════════════════════════════════════════════

    def get_macro_bias(self, pair: str,
                        month: Optional[int] = None) -> dict:
        """
        Retourne un biais macro combining COT + Saisonnalité.
        Utilisé par bias_detector ou kb5_engine pour le Level MN.

        Returns:
            dict {bias, score_bonus, cot, seasonal, aligned}
        """
        cot      = self.get_cot_bias(pair)
        seasonal = self.get_seasonal_bias(pair, month)

        cot_bias  = cot["bias"]
        seas_bias = seasonal["bias"]

        # Alignement COT + Saisonnalité
        if cot_bias == seas_bias and cot_bias != "NEUTRAL":
            macro_bias = cot_bias
            aligned    = True
            confidence = "HIGH"
        elif cot_bias != "NEUTRAL":
            macro_bias = cot_bias
            aligned    = (cot_bias == seas_bias)
            confidence = "MODERATE"
        elif seas_bias != "NEUTRAL":
            macro_bias = seas_bias
            aligned    = False
            confidence = "LOW"
        else:
            macro_bias = "NEUTRAL"
            aligned    = False
            confidence = "VERY_LOW"

        return {
            "pair":       pair,
            "bias":       macro_bias,
            "aligned":    aligned,
            "confidence": confidence,
            "cot":        cot,
            "seasonal":   seasonal,
        }

    def get_confluence_bonus(self, pair: str,
                              direction: str,
                              month: Optional[int] = None) -> dict:
        """
        Retourne le bonus/malus de score ICT basé sur COT + Saisonnalité.

        Args:
            pair:      ex. "EURUSD"
            direction: direction du trade ("BULLISH" / "BEARISH")
            month:     mois 1-12 (None = actuel)

        Returns:
            dict {bonus, details}
        """
        macro  = self.get_macro_bias(pair, month)
        bonus  = 0
        detail = []

        if macro["cot"]["bias"] == direction:
            bonus += CONFLUENCE_COT_ALIGNED
            detail.append(
                f"COT aligné ({macro['cot']['strength']}) "
                f"LS_NET={macro['cot']['large_specs_net']:+d} (+{CONFLUENCE_COT_ALIGNED})"
            )
        elif macro["cot"]["bias"] != "NEUTRAL" and macro["cot"]["bias"] != direction:
            bonus += CONFLUENCE_COT_OPPOSED
            detail.append(
                f"COT opposé ({macro['cot']['bias']}) "
                f"({CONFLUENCE_COT_OPPOSED})"
            )

        if macro["seasonal"]["bias"] == direction:
            seas_bonus = CONFLUENCE_SEASONAL_BULL if direction == "BULLISH" else CONFLUENCE_SEASONAL_BEAR
            bonus  += seas_bonus
            detail.append(
                f"Saisonnalité {direction} en mois {macro['seasonal']['month']} "
                f"(+{seas_bonus})"
            )

        return {
            "bonus":      bonus,
            "details":    detail,
            "macro_bias": macro["bias"],
            "aligned":    macro["aligned"],
        }

    def get_snapshot(self, pair: str) -> dict:
        """Snapshot complet pour le dashboard."""
        return {
            "pair":    pair,
            "cot":     self.get_cot_bias(pair),
            "seasonal": self.get_seasonal_bias(pair),
            "macro":   self.get_macro_bias(pair),
        }
