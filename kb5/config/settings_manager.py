# config/settings_manager.py
"""
══════════════════════════════════════════════════════════════
Sentinel Pro KB5 — Gestionnaire de Paramètres Utilisateur
══════════════════════════════════════════════════════════════
Responsabilités :
  - Stocker et charger tous les paramètres configurables par l'utilisateur
  - Persister les préférences en JSON (user_settings.json)
  - Définir les "Écoles" de trading et leurs principes activables
  - Fournir des profils préconçus (Default, Conservateur, Agressif, ICT Pur)
  - Être consommé par le Dashboard, le Scoring Engine et le Supervisor

Structure :
  ┌─ PAIRES               → liste de paires actives choisies par l'utilisateur
  ├─ ÉCOLES               → ICT, SMC, Price Action, Analytics pur
  │   └─ Principes        → chaque principe activable individuellement
  ├─ RISQUE               → RR min, DD max, trades/jour, % par trade
  ├─ SCORING              → seuils EXECUTE / WATCH personnalisables
  └─ FILTRES GLOBAUX      → Killzone obligatoire, ERL requis, etc.
══════════════════════════════════════════════════════════════
"""

import json
import logging
import threading
import os
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SETTINGS_FILE = "user_settings.json"

# ══════════════════════════════════════════════════════════
# DÉFINITION DES ÉCOLES DE TRADING
# Chaque école a un nom, une description, et une liste de
# principes que l'utilisateur peut activer/désactiver un par un.
# ══════════════════════════════════════════════════════════

SCHOOLS = {
    "ICT": {
        "name":        "ICT (Inner Circle Trader)",
        "description": "Concepts institutionnels : Power of 3, SMT, PD Arrays, Macros.",
        "color":       "#00d4ff",
        "principles": {
            "killzone":       {"label": "Killzones ICT",            "desc": "Londres / NY / Asie",                   "default": True},
            "fvg":            {"label": "Fair Value Gap (FVG)",      "desc": "BISI / SIBI — zones de déséquilibre",   "default": True},
            "order_blocks":   {"label": "Order Blocks (OB)",         "desc": "Bullish / Bearish / Breaker Blocks",    "default": True},
            "liquidity":      {"label": "Prise de Liquidité (Sweep)","desc": "PDH/PDL, EQH/EQL, Turtle Soup",        "default": True},
            "mss":            {"label": "Market Structure Shift",    "desc": "Cassure de structure avec momentum",    "default": True},
            "choch":          {"label": "Change of Character",       "desc": "Premier signe de retournement LTF",     "default": True},
            "smt":            {"label": "SMT Divergence",            "desc": "Corrélation intermarché inversée",      "default": True},
            "amd":            {"label": "AMD / Power of 3",          "desc": "Accum → Manipulation → Distribution",  "default": True},
            "silver_bullet":  {"label": "Silver Bullet",             "desc": "Fenêtre 10h-11h/14h-15h NY",           "default": True},
            "macros_ict":     {"label": "Macros ICT",                "desc": "Fenêtres algorithmiques 20-27 min",     "default": True},
            "midnight_open":  {"label": "Midnight Open",             "desc": "Pivot institutionnel 00h00 UTC",        "default": True},
            "irl":            {"label": "IRL (Internal Liquidity)",  "desc": "Cibles TP internes (FVG / Swings)",     "default": True},
            "pd_zone":        {"label": "Premium / Discount",        "desc": "Entrée en Discount (BULL) / Premium",  "default": True},
            "ote":            {"label": "OTE (Fibonacci 62-79%)",     "desc": "Zone d'entrée optimale ICT",           "default": True},
            "cisd":           {"label": "CISD",                      "desc": "Change in State of Delivery",          "default": False},
            "cbdr":           {"label": "CBDR",                      "desc": "Central Bank Dealers Range (17h-20h)",  "default": True},
        }
    },
    "SMC": {
        "name":        "SMC (Smart Money Concepts)",
        "description": "Structure, BOS, CHoCH, volumes institutionnels.",
        "color":       "#7c3aed",
        "principles": {
            "bos":            {"label": "Break of Structure (BOS)",  "desc": "Cassure de structure directionnelle",  "default": True},
            "choch_smc":      {"label": "Change of Character",       "desc": "Retournement précoce (SMC)",           "default": True},
            "inducement":     {"label": "Inducement",                "desc": "Piège liquidité avant le vrai move",   "default": True},
            "ob_smc":         {"label": "Order Blocks SMC",          "desc": "Zones d'offre/demande institutionnelles", "default": True},
            "fvg_smc":        {"label": "FVG / Imbalances",          "desc": "Déséquilibres de prix SMC",            "default": True},
            "equal_hl":       {"label": "Equal Highs / Equal Lows",  "desc": "Faux supports/résistances (pools)",    "default": True},
            "premium_discount":{"label":"Premium / Discount Zone",   "desc": "Positionnement par rapport au range",  "default": True},
        }
    },
    "PA": {
        "name":        "Price Action (PA)",
        "description": "Trading au chandeliers, tendances, supports/résistances.",
        "color":       "#10b981",
        "principles": {
            "engulfing":      {"label": "Bougie Engulfing",          "desc": "Engulfing Bull / Bear (confirmation)",  "default": True},
            "trendlines":     {"label": "Lignes de tendance",        "desc": "Trendlines validées (3 touches min)",   "default": True},
            "round_numbers":  {"label": "Chiffres Ronds",            "desc": "Niveaux .00 / .20 / .50 / .80",        "default": True},
            "pin_bar":        {"label": "Pin Bar / Doji",            "desc": "Mèches de rejet longues",              "default": False},
            "inside_bar":     {"label": "Inside Bar",                "desc": "Consolidation avant expansion",        "default": False},
            "sr_levels":      {"label": "Support / Résistance",      "desc": "Niveaux S/R classiques",               "default": True},
        }
    },
    "RISK": {
        "name":        "Gestion du Risque (Propriétaire)",
        "description": "Circuit Breakers, Killswitches, Behaviour Shield.",
        "color":       "#ef4444",
        "principles": {
            "circuit_breaker":{"label": "Circuit Breaker (CB)",      "desc": "Stop auto si DD > seuil",              "default": True},
            "killswitches":   {"label": "Killswitches (×9)",         "desc": "Règles d'arrêt absolu KB5",            "default": True},
            "behaviour_shield":{"label":"Behaviour Shield",          "desc": "Anti-revenge, anti-news, anti-spike",  "default": True},
            "news_filter":    {"label": "Filtre Actualités",         "desc": "Bloquer trades avant NFP/FOMC",        "default": True},
            "friday_filter":  {"label": "Filtre Vendredi PM",        "desc": "Pas de trades après 14h NY vendredi",  "default": True},
            "monday_filter":  {"label": "Filtre Lundi Matin",        "desc": "Seek & Destroy requis avant 10h NY",   "default": True},
            "spread_filter":  {"label": "Filtre Spread",             "desc": "Rejeter si spread > seuil paire",      "default": True},
        }
    }
}

# ══════════════════════════════════════════════════════════
# PAIRES DISPONIBLES (groupées par catégorie)
# ══════════════════════════════════════════════════════════

AVAILABLE_PAIRS = {
    "Forex Majeurs":  ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"],
    "Forex Majeurs m": ["EURUSDm", "GBPUSDm", "USDJPYm", "USDCHFm", "USDCADm", "AUDUSDm", "NZDUSDm"],
    "Forex Croisés":  ["EURGBP", "EURJPY", "GBPJPY"],
    "Métaux":         ["XAUUSD", "XAUUSDm", "XAGUSD"],
    "Indices":        ["US30", "NAS100", "SPX500", "DE30m", "UK100m", "USTECm", "US500m"],
    "Crypto":         ["BTCUSD", "BTCUSDm", "ETHUSD", "ETHUSDm"],
    "Energie":        ["USOILm", "UKOILm"],
}

# ══════════════════════════════════════════════════════════
# PROFILS PRÉ-CONFIGURÉS
# ══════════════════════════════════════════════════════════

PROFILES = {
    "ICT Pur": {
        "description": "Uniquement les principes ICT officiels. Approche institutionnelle stricte.",
        "schools_enabled": ["ICT", "RISK"],
        "score_execute":   80,
        "score_watch":     65,
        "rr_min":          2.0,
        "max_trades_day":  3,
        "max_dd_day_pct":  2.0,
        "max_dd_week_pct": 5.0,
        "risk_per_trade":  1.0,
        "require_killzone":True,
        "require_erl":     True,
    },
    "SMC + ICT": {
        "description": "Combinaison SMC et ICT pour plus de setups.",
        "schools_enabled": ["ICT", "SMC", "RISK"],
        "score_execute":   75,
        "score_watch":     60,
        "rr_min":          1.8,
        "max_trades_day":  5,
        "max_dd_day_pct":  2.5,
        "max_dd_week_pct": 6.0,
        "risk_per_trade":  1.0,
        "require_killzone":True,
        "require_erl":     True,
    },
    "Conservateur": {
        "description": "Risque minimal, seuils élevés. Idéal pour compte réel débutant.",
        "schools_enabled": ["ICT", "RISK"],
        "score_execute":   85,
        "score_watch":     70,
        "rr_min":          3.0,
        "max_trades_day":  2,
        "max_dd_day_pct":  1.0,
        "max_dd_week_pct": 3.0,
        "risk_per_trade":  0.5,
        "require_killzone":True,
        "require_erl":     True,
    },
    "Agressif": {
        "description": "Plus de trades, seuils bas. Réservé aux comptes de prop firm.",
        "schools_enabled": ["ICT", "SMC", "PA", "RISK"],
        "score_execute":   70,
        "score_watch":     55,
        "rr_min":          1.5,
        "max_trades_day":  10,
        "max_dd_day_pct":  4.0,
        "max_dd_week_pct": 8.0,
        "risk_per_trade":  2.0,
        "require_killzone":False,
        "require_erl":     False,
    },
    "Custom": {
        "description": "Configuration entièrement personnalisée.",
        "schools_enabled": ["ICT", "RISK"],
        "score_execute":   78,
        "score_watch":     63,
        "rr_min":          2.0,
        "max_trades_day":  5,
        "max_dd_day_pct":  2.0,
        "max_dd_week_pct": 5.0,
        "risk_per_trade":  1.0,
        "require_killzone":True,
        "require_erl":     True,
    },
}

# ══════════════════════════════════════════════════════════
# VALEURS PAR DÉFAUT (profil Custom au démarrage)
# ══════════════════════════════════════════════════════════

def _build_default_principles() -> dict:
    """Construit le dict principles_enabled depuis les defaults SCHOOLS."""
    enabled = {}
    for school_id, school_data in SCHOOLS.items():
        for principle_id, pdata in school_data["principles"].items():
            key = f"{school_id}:{principle_id}"
            enabled[key] = pdata["default"]
    return enabled


DEFAULT_SETTINGS = {
    # --- Profil actif ---
    "profile": "Custom",

    # --- Paires actives ---
    "active_pairs": ["EURUSDm", "GBPUSDm", "XAUUSDm", "USTECm"],

    # --- Écoles actives ---
    "schools_enabled": ["ICT", "RISK"],

    # --- Principes individuels ---
    "principles_enabled": _build_default_principles(),

    # --- Risque ---
    "risk_per_trade":   1.0,    # % du capital par trade
    "max_trades_day":   5,      # Nombre max de trades par jour
    "max_dd_day_pct":   2.0,    # Drawdown max par jour (%)
    "max_dd_week_pct":  5.0,    # Drawdown max par semaine (%)
    "rr_min":           2.0,    # Risk/Reward minimum accepté
    "rr_target":        3.0,    # Risk/Reward cible (TP1 intermédiaire)

    # --- Seuils de scoring ---
    "score_execute":    78,     # Score minimum pour EXECUTE
    "score_watch":      63,     # Score minimum pour WATCH

    # --- Filtres globaux ---
    "require_killzone": True,   # Forcer Killzone pour entrée
    "require_erl":      True,   # Forcer ERL sweepé avant entrée
    "require_mss":      False,  # Exiger MSS confirmé
    "require_choch":    False,  # Exiger CHoCH confirmé
    "use_partial_tp":   True,   # TP partiel sur IRL avant cible finale

    # --- Paramètres IA (Narratif) ---
    "llm_provider":     "Gemini", # Gemini ou Grok
    "llm_api_key":      "",

    # --- Meta ---
    "last_updated": None,
    "version": "1.0",
}


# ══════════════════════════════════════════════════════════
# CLASSE PRINCIPALE
# ══════════════════════════════════════════════════════════

class SettingsManager:
    """
    Gestionnaire de paramètres utilisateur pour Sentinel Pro KB5.

    Permet à l'utilisateur de configurer via le Dashboard :
      - Les paires actives
      - Les écoles de trading à utiliser
      - Chaque principe ICT/SMC/PA activable individuellement
      - Les paramètres de risque (RR, DD, trades/jour, %)
      - Les seuils de scoring
      - Les filtres globaux

    Persistance JSON automatique à chaque modification.
    Thread-safe via RLock.
    """

    def __init__(self, settings_file: str = SETTINGS_FILE):
        self._file   = Path(settings_file)
        self._lock   = threading.RLock()
        self._data   = deepcopy(DEFAULT_SETTINGS)
        self._last_ui_sync = 0.0
        self.reload()
        logger.info(f"SettingsManager initialise — profil: {self._data['profile']}")

    # ══════════════════════════════════════════════════
    # CHARGEMENT / SAUVEGARDE
    # ══════════════════════════════════════════════════

    def _load(self) -> None:
        """Charge les settings depuis le fichier JSON. Fallback sur DEFAULT si absent."""
        with self._lock:
            if not self._file.exists():
                logger.info("SettingsManager — pas de fichier settings, defaults utilises")
                return
            try:
                with open(self._file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Fusion douce : on garde les defaults pour les clés manquantes
                self._merge(loaded)
                logger.info(f"SettingsManager — chargé depuis {self._file}")
            except Exception as e:
                logger.error(f"SettingsManager — erreur chargement : {e}. Defaults utilisés.")

    def _merge(self, loaded: dict) -> None:
        """Fusionne settings chargés avec défaults pour gérer les nouvelles clés."""
        for key, default_val in DEFAULT_SETTINGS.items():
            if key == "principles_enabled":
                # Fusion spéciale : garder les defaults pour nouveaux principes
                loaded_p = loaded.get("principles_enabled", {})
                merged_p = deepcopy(_build_default_principles())
                merged_p.update(loaded_p)
                self._data["principles_enabled"] = merged_p
            elif key in loaded:
                self._data[key] = loaded[key]
            else:
                self._data[key] = deepcopy(default_val)

    def reload(self) -> None:
        """Recharge les paramètres en vérifiant d'abord les mises à jour de l'UI."""
        # 1. Vérifier si bot_config.json (UI) a été modifié
        # On cherche bot_config.json dans le dossier 'data' relatif au dossier parent de ce fichier
        bot_cfg_path = Path(__file__).parent.parent / "data" / "bot_config.json"
        
        if bot_cfg_path.exists():
            try:
                mtime = os.path.getmtime(bot_cfg_path)
                if mtime > self._last_ui_sync:
                    with open(bot_cfg_path, "r", encoding="utf-8") as f:
                        bot_cfg = json.load(f)
                    self.sync_from_bot_config(bot_cfg)
                    self._last_ui_sync = mtime
                    logger.info(f"SettingsManager — synchronisé avec {bot_cfg_path} (mtime: {mtime})")
            except Exception as e:
                logger.error(f"SettingsManager — erreur sync UI : {e}")

        # 2. Recharger depuis user_settings.json
        self._load()

    def save(self) -> bool:
        """Sauvegarde les settings sur disque."""
        with self._lock:
            try:
                self._data["last_updated"] = datetime.now(timezone.utc).isoformat()
                tmp = str(self._file) + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2, ensure_ascii=False)
                Path(tmp).replace(self._file)
                logger.info("SettingsManager — sauvegarde OK")
                return True
            except Exception as e:
                logger.error(f"SettingsManager — erreur sauvegarde : {e}")
                return False

    # ══════════════════════════════════════════════════
    # ACCÈS GÉNÉRAL
    # ══════════════════════════════════════════════════

    def get(self, key: str, default=None):
        """Lecture thread-safe d'une clé."""
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        """Écriture + sauvegarde automatique."""
        with self._lock:
            self._data[key] = value
        self.save()

    def get_all(self) -> dict:
        """Retourne une copie complète."""
        with self._lock:
            return deepcopy(self._data)

    def update_bulk(self, updates: dict) -> None:
        """Met à jour plusieurs clés en une seule opération + sauvegarde."""
        with self._lock:
            self._data.update(updates)
        self.save()

    # ══════════════════════════════════════════════════
    # PROFILS
    # ══════════════════════════════════════════════════

    def apply_profile(self, profile_name: str) -> None:
        """
        Applique un profil préconfiguré.
        Ne modifie pas les principes individuels (préserve la personnalisation).
        """
        profile = PROFILES.get(profile_name)
        if not profile:
            logger.warning(f"Profil inconnu: {profile_name}")
            return

        with self._lock:
            self._data["profile"]          = profile_name
            self._data["schools_enabled"]  = profile.get("schools_enabled", self._data["schools_enabled"])
            self._data["score_execute"]    = profile.get("score_execute",   self._data["score_execute"])
            self._data["score_watch"]      = profile.get("score_watch",     self._data["score_watch"])
            self._data["rr_min"]           = profile.get("rr_min",          self._data["rr_min"])
            self._data["max_trades_day"]   = profile.get("max_trades_day",  self._data["max_trades_day"])
            self._data["max_dd_day_pct"]   = profile.get("max_dd_day_pct",  self._data["max_dd_day_pct"])
            self._data["max_dd_week_pct"]  = profile.get("max_dd_week_pct", self._data["max_dd_week_pct"])
            self._data["risk_per_trade"]   = profile.get("risk_per_trade",  self._data["risk_per_trade"])
            self._data["require_killzone"] = profile.get("require_killzone",self._data["require_killzone"])
            self._data["require_erl"]      = profile.get("require_erl",     self._data["require_erl"])
        self.save()
        logger.info(f"Profil appliqué : {profile_name}")

    def get_profile_list(self) -> list:
        """Retourne la liste des profils disponibles."""
        return list(PROFILES.keys())

    # ══════════════════════════════════════════════════
    # ÉCOLES & PRINCIPES
    # ══════════════════════════════════════════════════

    def is_school_active(self, school_id: str) -> bool:
        """Vérifie si une école est activée."""
        return school_id in self.get("schools_enabled", [])

    def is_principle_active(self, school_id: str, principle_id: str) -> bool:
        """
        Vérifie si un principe est actif.
        Le principe doit être activé ET son école doit être activée.
        """
        if not self.is_school_active(school_id):
            return False
        key = f"{school_id}:{principle_id}"
        return self.get("principles_enabled", {}).get(key, False)

    def set_principle(self, school_id: str, principle_id: str, value: bool) -> None:
        """Active ou désactive un principe individuel."""
        key = f"{school_id}:{principle_id}"
        with self._lock:
            self._data["principles_enabled"][key] = value
        self.save()

    def get_active_principles(self, school_id: str) -> list:
        """Retourne la liste des principes actifs pour une école."""
        if not self.is_school_active(school_id):
            return []
        school = SCHOOLS.get(school_id, {})
        return [
            pid for pid in school.get("principles", {})
            if self.is_principle_active(school_id, pid)
        ]

    # ══════════════════════════════════════════════════
    # PAIRES
    # ══════════════════════════════════════════════════

    def get_active_pairs(self) -> list:
        """Retourne les paires actives."""
        return list(self.get("active_pairs", []))

    def set_active_pairs(self, pairs: list) -> None:
        """Définit les paires actives."""
        self.set("active_pairs", pairs)

    # ══════════════════════════════════════════════════
    # RACCOURCIS RISQUE
    # ══════════════════════════════════════════════════

    def get_risk_config(self) -> dict:
        """Retourne la config risque complète."""
        with self._lock:
            return {
                "risk_per_trade":   self._data.get("risk_per_trade",  1.0),
                "max_trades_day":   self._data.get("max_trades_day",  5),
                "max_dd_day_pct":   self._data.get("max_dd_day_pct",  2.0),
                "max_dd_week_pct":  self._data.get("max_dd_week_pct", 5.0),
                "rr_min":           self._data.get("rr_min",          2.0),
                "rr_target":        self._data.get("rr_target",       3.0),
                "score_execute":    self._data.get("score_execute",   78),
                "score_watch":      self._data.get("score_watch",     63),
                "require_killzone": self._data.get("require_killzone",True),
                "require_erl":      self._data.get("require_erl",     True),
                "require_mss":      self._data.get("require_mss",     False),
                "require_choch":    self._data.get("require_choch",   False),
                "use_partial_tp":   self._data.get("use_partial_tp",  True),
            }

    def get_llm_config(self) -> dict:
        """Retourne la configuration IA."""
        with self._lock:
            return {
                "llm_provider": self._data.get("llm_provider", "Gemini"),
                "llm_api_key":  self._data.get("llm_api_key", ""),
            }

    def reset_to_defaults(self) -> None:
        """Remet tous les settings aux valeurs par défaut."""
        with self._lock:
            self._data = deepcopy(DEFAULT_SETTINGS)
        self.save()
        logger.info("SettingsManager — reset aux defaults effectué")

    # ══════════════════════════════════════════════════
    # MÉTHODES POUR LE COMMAND CENTER
    # ══════════════════════════════════════════════════

    def get_all_settings(self) -> dict:
        """Retourne tous les paramètres organisés pour l'interface."""
        with self._lock:
            return {
                'profile': self._data.get('profile', 'Custom'),
                'active_pairs': self._data.get('active_pairs', ['BTCUSDm']),
                'bot_running': self._data.get('bot_running', False),
                'schools_enabled': self._data.get('schools_enabled', ['ICT', 'RISK']),
                'principles_enabled': self._data.get('principles_enabled', {}),
                'risk_config': {
                    'risk_per_trade': self._data.get('risk_per_trade', 1.0),
                    'rr_min': self._data.get('rr_min', 2.0),
                    'max_trades_day': self._data.get('max_trades_day', 5),
                    'max_dd_day_pct': self._data.get('max_dd_day_pct', 2.0),
                    'max_dd_week_pct': self._data.get('max_dd_week_pct', 5.0)
                },
                'scoring_config': {
                    'score_execute': self._data.get('score_execute', 78),
                    'score_watch': self._data.get('score_watch', 63)
                },
                'global_filters': {
                    'require_killzone': self._data.get('require_killzone', True),
                    'require_erl': self._data.get('require_erl', True)
                }
            }

    def load_profile(self, profile_name: str) -> None:
        """Alias pour apply_profile pour compatibilité avec l'interface."""
        self.apply_profile(profile_name)

    def update_risk_config(self, risk_settings: dict) -> None:
        """Met à jour la configuration de risque."""
        with self._lock:
            for key, value in risk_settings.items():
                self._data[key] = value
        self.save()
        logger.info("Configuration de risque mise à jour")

    def update_scoring_config(self, scoring_settings: dict) -> None:
        """Met à jour la configuration de scoring."""
        with self._lock:
            for key, value in scoring_settings.items():
                self._data[key] = value
        self.save()
        logger.info("Configuration de scoring mise à jour")

    def set_active_pairs(self, pairs: list) -> None:
        """Met à jour les paires actives."""
        with self._lock:
            self._data['active_pairs'] = pairs
        self.save()
        logger.info(f"Paires actives mises à jour: {pairs}")

    def set_schools_enabled(self, schools: list) -> None:
        """Met à jour les écoles activées."""
        with self._lock:
            self._data['schools_enabled'] = schools
        self.save()
        logger.info(f"Écoles activées mises à jour: {schools}")

    def set_principles_enabled(self, principles: dict) -> None:
        """Met à jour les principes activés."""
        with self._lock:
            self._data['principles_enabled'] = principles
        self.save()
        logger.info("Principes activés mis à jour")

    def set_global_filters(self, filters: dict) -> None:
        """Met à jour les filtres globaux."""
        with self._lock:
            for key, value in filters.items():
                self._data[key] = value
        self.save()
        logger.info("Filtres globaux mis à jour")

    # ══════════════════════════════════════════════════
    # INFORMATIONS STATIQUES
    # ══════════════════════════════════════════════════

    @staticmethod
    def get_schools_definition() -> dict:
        """Retourne la définition complète des écoles (immuable)."""
        return SCHOOLS

    @staticmethod
    def get_profiles_definition() -> dict:
        """Retourne la définition complète des profils."""
        return PROFILES

    @staticmethod
    def get_available_pairs() -> dict:
        """Retourne les paires disponibles groupées par catégorie."""
        return AVAILABLE_PAIRS
    # ══════════════════════════════════════════════════
    # PONT UI → CERVEAU (synchronisation bot_config.json)
    # ══════════════════════════════════════════════════

    def sync_from_bot_config(self, bot_config: dict) -> None:
        """
        Lit bot_config.json (sauvé par l'interface Streamlit)
        et injecte les valeurs dans user_settings.json (lu par le cerveau).
        Appelée au démarrage de main.py.
        """
        mapping = {
            "score_execute":          "score_execute",
            "score_limit":            "score_watch",
            "risk_pct":               "risk_per_trade",
            "drawdown_max_pct":       "max_dd_day_pct",
            "drawdown_max_week_pct":  "max_dd_week_pct",
            "rr_min":                 "rr_min",
            "rr_target":              "rr_target",
            "max_positions":          "max_trades_day",
            "max_session_trades":     "max_trades_day",
            "require_killzone":       "require_killzone",
            "require_erl":            "require_erl",
            "require_mss":            "require_mss",
            "require_choch":          "require_choch",
            "partial_tp":             "use_partial_tp",
            "llm_provider":           "llm_provider",
            "llm_api_key":            "llm_api_key",
        }
        updates = {}

        # Copie directe des clés avec mapping de noms
        for ui_key, sm_key in mapping.items():
            if ui_key in bot_config:
                updates[sm_key] = bot_config[ui_key]

        # Paires actives (symbols_watched → active_pairs)
        if "symbols_watched" in bot_config:
            updates["active_pairs"] = bot_config["symbols_watched"]

        # Mode opération (PAPER / SEMI_AUTO / FULL_AUTO)
        if "op_mode" in bot_config:
            updates["op_mode"] = bot_config["op_mode"]

        # Sessions actives
        if "sessions_actives" in bot_config:
            updates["sessions_actives"] = bot_config["sessions_actives"]

        # KillSwitches désactivés
        if "disabled_ks" in bot_config:
            updates["disabled_ks"] = bot_config["disabled_ks"]

        # Behaviour Shield (dict de flags)
        if "behaviour_shield" in bot_config:
            updates["behaviour_shield"] = bot_config["behaviour_shield"]

        # Filtres temporels
        if "time_filters" in bot_config:
            updates["time_filters"] = bot_config["time_filters"]

        # active_concepts (liste plate) → principles_enabled (dict hiérarchique)
        if "active_concepts" in bot_config:
            concepts = bot_config["active_concepts"]
            principles = deepcopy(self.get("principles_enabled", {}))
            for k in principles:
                short_key = k.split(":")[-1]
                principles[k] = short_key in concepts
            updates["principles_enabled"] = principles

        self.update_bulk(updates)
        logger.info(
            f"[SYNC UI→BOT] {len(updates)} paramètres synchronisés "
            f"depuis bot_config.json vers user_settings.json"
        )
