# supervisor/supervisor_mixin.py
"""
MIXIN pour SUPERVISOR (heartbeat_monitor, supervisor)

Permet au supervisor de gérer le cycle de reload des paramètres.
"""

import logging
import time
from threading import Thread, Event

logger = logging.getLogger(__name__)


class SupervisorMixin:
    """Base pour supervisor avec cycle de reload des paramètres."""
    
    def __init__(self, settings_manager=None, settings_integration=None):
        self._settings_manager = settings_manager
        self._settings_integration = settings_integration
        self._reload_thread = None
        self._reload_stop_event = Event()
        self._last_reload = time.time()
        self._reload_interval = 10  # secondes
    
    def start_settings_reload_cycle(self):
        """Démarrer le cycle de reload des settings (10s)."""
        if not self._settings_manager or not self._settings_integration:
            logger.warning("SettingsManager/Integration non disponible - reload désactivé")
            return
        
        if self._reload_thread is not None and self._reload_thread.is_alive():
            logger.info("Cycle de reload déjà en cours")
            return
        
        self._reload_stop_event.clear()
        self._reload_thread = Thread(target=self._reload_loop, daemon=True)
        self._reload_thread.start()
        logger.info("Cycle de reload des paramètres démarré (10s)")
    
    def stop_settings_reload_cycle(self):
        """Arrêter le cycle de reload."""
        if self._reload_thread is None:
            return
        
        self._reload_stop_event.set()
        if self._reload_thread.is_alive():
            self._reload_thread.join(timeout=5)
        logger.info("Cycle de reload arrêté")
    
    def _reload_loop(self):
        """Boucle de reload - run toutes les 10 secondes."""
        logger.info("Boucle de reload démarrée")
        
        while not self._reload_stop_event.is_set():
            try:
                # Attendre 10 secondes
                if self._reload_stop_event.wait(self._reload_interval):
                    # Signal d'arrêt reçu
                    break
                
                # Reload settings
                self._reload_settings()
                
            except Exception as e:
                logger.error(f"Erreur dans cycle reload: {e}", exc_info=True)
                # Continuer plutôt que de crash
    
    def _reload_settings(self):
        """Recharger settings depuis JSON."""
        try:
            if not self._settings_manager:
                return
            
            self._settings_manager.reload()
            self._last_reload = time.time()
            
            # Log optionnel
            logger.debug(f"Settings reloadés avec succès à {self._last_reload}")
            
        except Exception as e:
            logger.error(f"Erreur reload settings: {e}", exc_info=True)
    
    def get_last_reload_time(self) -> float:
        """Obtenir timestamp du dernier reload."""
        return self._last_reload
    
    def set_reload_interval(self, seconds: int):
        """Changer l'intervalle de reload."""
        if seconds < 5:
            seconds = 5
            logger.warning("Intervalle minimum = 5s, ajusté à 5s")
        self._reload_interval = seconds
        logger.info(f"Intervalle de reload = {self._reload_interval}s")
    
    def force_reload_now(self):
        """Forcer reload immédiat des settings."""
        self._reload_settings()
        logger.info("Reload forcé des settings")
