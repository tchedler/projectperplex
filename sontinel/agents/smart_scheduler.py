"""
SmartScheduler — Boucle intelligente par TimeFrame
Bible ICT : Chaque TF a sa propre cadence de renouvellement.
Ne relance l'analyse que lorsque la bougie du TF vient de se fermer.
"""
import datetime
import pytz
import MetaTrader5 as mt5
from typing import List, Dict

# ============================================================
# CONFIGURATION DES TIMEFRAMES
# Durée de chaque TF en secondes (pour calcul de fermeture de bougie)
# ============================================================
TF_DURATIONS = {
    "MN":  60 * 60 * 24 * 30,  # ~1 mois (30 jours)
    "W1":  60 * 60 * 24 * 7,   # 1 semaine
    "D1":  60 * 60 * 24,        # 1 jour
    "H4":  60 * 60 * 4,         # 4 heures
    "H2":  60 * 60 * 2,         # 2 heures
    "H1":  60 * 60,              # 1 heure
    "M15": 60 * 15,              # 15 minutes
    "M5":  60 * 5,               # 5 minutes
    "M1":  60,                   # 1 minute
}

# Correspondances MT5
TF_MT5_MAP = {
    "MN":  mt5.TIMEFRAME_MN1,
    "W1":  mt5.TIMEFRAME_W1,
    "D1":  mt5.TIMEFRAME_D1,
    "H4":  mt5.TIMEFRAME_H4,
    "H2":  mt5.TIMEFRAME_H2,
    "H1":  mt5.TIMEFRAME_H1,
    "M15": mt5.TIMEFRAME_M15,
    "M5":  mt5.TIMEFRAME_M5,
    "M1":  mt5.TIMEFRAME_M1,
}

# TF actifs selon le profil de trading
PROFILE_TFS = {
    "SCALP":      ["H1", "M15", "M5", "M1"],
    "DAY_TRADE":  ["D1", "H4", "H1", "M15", "M5"],
    "SWING":      ["W1", "D1", "H4", "H2"],
    "LONG_TERM":  ["MN", "W1", "D1"],
}


class SmartScheduler:
    """
    Scheduler intelligent — ne déclenche l'analyse d'un TF
    que si la bougie de ce TF vient de se fermer.
    Maintient un cache des dernières analyses pour chaque TF.
    """

    def __init__(self, symbol: str, profile: str = "DAY_TRADE"):
        self.symbol = symbol
        self.profile = profile.upper()
        self.tz = pytz.timezone("America/New_York")

        # TF actifs selon le profil
        self.active_tfs: List[str] = PROFILE_TFS.get(self.profile, PROFILE_TFS["DAY_TRADE"])

        # Timestamp de la dernière analyse par TF
        self._last_analysis: Dict[str, datetime.datetime] = {}

        # Heure d'ouverture de la dernière bougie PROCESSÉE par TF (Bar Checking)
        self._last_candle_open: Dict[str, datetime.datetime] = {}

        # Cache des résultats d'analyse par TF
        self._cache: Dict[str, dict] = {}

    # ============================================================
    # MÉTHODE PRINCIPALE : Quels TF doivent être re-analysés ?
    # ============================================================
    def get_tfs_to_refresh(self) -> List[str]:
        """
        Retourne la liste des TF dont la bougie vient de se fermer
        et qui nécessitent une nouvelle analyse.
        """
        now = datetime.datetime.now(self.tz)
        to_refresh = []

        for tf in self.active_tfs:
            if self._candle_just_closed(tf, now):
                to_refresh.append(tf)

        return to_refresh

    def _candle_just_closed(self, tf: str, now: datetime.datetime) -> bool:
        """
        Détecte si une nouvelle bougie du TF vient de se fermer sur le broker.
        Utilise le 'Bar Checking' : on compare l'heure d'ouverture de la bougie
        actuelle MT5 avec celle de la dernière analyse effectuée.
        """
        # --- MÉTHODE 1 : Synchronisation réelle via MT5 (Broker) ---
        try:
            # Récupérer l'heure d'ouverture de la bougie actuelle (index 0)
            rates = mt5.copy_rates_from_pos(self.symbol, TF_MT5_MAP[tf], 0, 1)
            if rates is not None and len(rates) > 0:
                # L'heure d'ouverture de la bougie en cours chez le broker
                current_candle_open = datetime.datetime.fromtimestamp(rates[0]['time'], tz=pytz.UTC)
                
                # Première fois ou changement de bougie
                if tf not in self._last_candle_open:
                    self._last_candle_open[tf] = current_candle_open
                    return True
                
                if current_candle_open > self._last_candle_open[tf]:
                    self._last_candle_open[tf] = current_candle_open
                    return True
                
                # On a déjà analysé cette bougie
                return False
        except Exception:
            pass # Fallback sur la méthode par temps écoulé si MT5 échoue

        # --- MÉTHODE 2 : Fallback par calcul de durée (si MT5 indisponible) ---
        duration_s = TF_DURATIONS.get(tf, 60)
        if tf not in self._last_analysis:
            return True

        last = self._last_analysis[tf]
        elapsed = (now - last).total_seconds()

        # MN / W1 / D1 : On reste sur un refresh minimaliste si pas de MT5
        if tf in ["MN", "W1", "D1"]:
            return elapsed >= duration_s
            
        return elapsed >= duration_s

    # ============================================================
    # GESTION DU CACHE
    # ============================================================
    def update_analysis(self, tf: str, result: dict):
        """Enregistre le résultat d'une analyse et met à jour le timestamp."""
        now = datetime.datetime.now(self.tz)
        self._cache[tf] = result
        self._last_analysis[tf] = now

    def get_cached(self, tf: str) -> dict | None:
        """Retourne le résultat mis en cache pour un TF donné."""
        return self._cache.get(tf)

    def has_cache(self, tf: str) -> bool:
        return tf in self._cache

    def clear_cache(self, tf: str | None = None):
        """Vide le cache d'un TF ou de tous les TF."""
        if tf:
            self._cache.pop(tf, None)
            self._last_analysis.pop(tf, None)
        else:
            self._cache.clear()
            self._last_analysis.clear()

    # ============================================================
    # INFORMATIONS DE STATUT
    # ============================================================
    def get_status(self) -> Dict[str, dict]:
        """
        Retourne le statut de chaque TF actif :
        - Dernier refresh
        - Prochain refresh estimé
        - En cache?
        """
        now = datetime.datetime.now(self.tz)
        status = {}

        for tf in self.active_tfs:
            last = self._last_analysis.get(tf)
            duration_s = TF_DURATIONS.get(tf, 60)

            if last:
                elapsed = (now - last).total_seconds()
                remaining = max(0, duration_s - elapsed)
                next_refresh = now + datetime.timedelta(seconds=remaining)
            else:
                remaining = 0
                next_refresh = now

            status[tf] = {
                "last_refresh": last.strftime("%H:%M:%S") if last else "Jamais",
                "next_refresh": next_refresh.strftime("%H:%M:%S"),
                "seconds_remaining": int(remaining),
                "cached": self.has_cache(tf),
                "tf_duration_s": duration_s,
            }

        return status

    def set_profile(self, profile: str):
        """Change le profil de trading dynamiquement."""
        self.profile = profile.upper()
        self.active_tfs = PROFILE_TFS.get(self.profile, PROFILE_TFS["DAY_TRADE"])
        self.clear_cache()

    @property
    def active_timeframes(self) -> List[str]:
        return self.active_tfs
