"""
market_state_cache.py — Pont Central d'État du Marché (Event-Driven)
Permet d'écrire et de lire l'état actuel des analyses de marché (HTF, SMC, Liquidité)
sans recalculer ni solliciter MT5 inutilement. Utilisé par le bot pour écrire,
et par le dashboard (interface) pour lire en temps réel.
"""
import pickle
import os
import logging
import datetime
import threading
import time
from typing import Dict, Any

# Initialiser le logger local
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("MarketStateCache")


class MarketStateCache:
    def __init__(self, cache_file: str = "data/market_state_cache.pkl"):
        self.cache_file = cache_file
        self.state: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._last_save_time = 0.0
        self._save_interval = 3.0  # max 1 save toutes les 3s (IMP-5)
        self._ensure_dir()
        self.load()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.cache_file) or ".", exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Charge l'état depuis le fichier pickle."""
        with self._lock:
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, "rb") as f:
                        self.state = pickle.load(f)
                except Exception as e:
                    log.warning(f"Erreur de lecture du cache HTF: {e}")
                    self.state = {}
            else:
                self.state = {}
            return self.state

    def save(self, force=False):
        """Sauvegarde l'état actuel dans le fichier pickle de manière sécurisée (atomique et thread-safe)."""
        with self._lock:
            now = time.time()
            if not force and (now - self._last_save_time < self._save_interval):
                return  # Throttle d'écriture (IMP-5 FIX)

            try:
                tmp_file = self.cache_file + ".tmp"
                with open(tmp_file, "wb") as f:
                    pickle.dump(self.state, f, protocol=pickle.HIGHEST_PROTOCOL)
                
                # Remplacement atomique (gestion des collisions sur Windows)
                for attempt in range(5):
                    try:
                        os.replace(tmp_file, self.cache_file)
                        self._last_save_time = time.time()
                        break
                    except PermissionError:
                        time.sleep(0.05)
                else:
                    log.warning("Impossible de remplacer le fichier cache (Verrouillé par un autre processus).")
            except Exception as e:
                log.warning(f"Erreur d'écriture du cache HTF: {e}")

    def update_symbol_tf(self, symbol: str, tf: str, data: dict):
        """
        Met à jour les données calculées pour un symbole et un timeframe précis.
        `data` est généralement le dictionnaire retourné par `ProOrchestrator`.
        """
        with self._lock:
            if symbol not in self.state:
                self.state[symbol] = {"timeframes": {}, "global_bias": {}}
                
            self.state[symbol]["timeframes"][tf] = {
                "last_updated": datetime.datetime.now().isoformat(),
                "data": data
            }
            self.save()
        
    def update_global_bias(self, symbol: str, bias_data: dict):
        """
        Met à jour le biais global HTF (provenant du Monthly/Weekly/Daily).
        """
        with self._lock:
            if symbol not in self.state:
                self.state[symbol] = {"timeframes": {}, "global_bias": {}}
                
            self.state[symbol]["global_bias"] = {
                "last_updated": datetime.datetime.now().isoformat(),
                "data": bias_data
            }
            self.save()

    def get_symbol_tf(self, symbol: str, tf: str) -> dict | None:
        """Récupère les données en cache d'un timeframe spécifique."""
        with self._lock:
            try:
                return self.state[symbol]["timeframes"][tf]["data"]
            except KeyError:
                return None
            
    def get_global_bias(self, symbol: str) -> dict | None:
        """Récupère le biais global HTF mis en cache."""
        with self._lock:
            try:
                return self.state[symbol]["global_bias"]["data"]
            except KeyError:
                return None

    def update_bot_status(self, is_running: bool, current_time: str, active_symbols: list):
        """Met à jour l'état global du bot (pour le dashboard)."""
        with self._lock:
            self.state["_SYSTEM"] = {
                "bot_is_running": is_running,
                "last_heartbeat": current_time,
                "active_symbols": active_symbols
            }
            self.save()
        
    def get_bot_status(self) -> dict:
        """Retourne l'état du système."""
        with self._lock:
            return self.state.get("_SYSTEM", {"bot_is_running": False, "last_heartbeat": "N/A"})
