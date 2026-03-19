# analysis/engine_mixin.py
"""
MIXIN pour MOTEURS (KB5Engine, ScoringEngine, KillSwitchEngine)

Permet aux moteurs d'accéder facilement aux paramètres utilisateur.
"""

import logging

logger = logging.getLogger(__name__)


class EngineMixin:
    """Base pour tous les moteurs d'analyse."""
    
    def __init__(self, settings_integration=None):
        self._settings_integration = settings_integration
    
    def check_requirement(self, requirement_name: str) -> bool:
        """
        Vérifier un requirement global (require_killzone, require_erl, etc).
        
        Args:
            requirement_name: 'killzone', 'erl', 'mss', 'choch'
        
        Returns:
            True si le requirement est actif (doit être respecté)
        """
        if not self._settings_integration:
            return False
        
        mapping = {
            'killzone': lambda: self._settings_integration.require_killzone(),
            'erl': lambda: self._settings_integration.require_erl(),
            'mss': lambda: self._settings_integration.require_mss(),
            'choch': lambda: self._settings_integration.require_choch(),
        }
        
        func = mapping.get(requirement_name)
        if not func:
            logger.warning(f"Requirement inconnu: {requirement_name}")
            return False
        
        return func()
    
    def get_scoring_thresholds(self) -> dict:
        """Obtenir les seuils de scoring depuis settings."""
        if not self._settings_integration:
            return {'execute': 75, 'watch': 65}
        
        return {
            'execute': self._settings_integration.get_score_execute_threshold(),
            'watch': self._settings_integration.get_score_watch_threshold(),
        }
    
    def get_risk_config(self) -> dict:
        """Obtenir config risque depuis settings."""
        if not self._settings_integration:
            return {
                'risk_per_trade': 1.0,
                'rr_min': 2.0,
                'rr_target': 3.0,
                'max_dd_daily': 2.0,
                'max_dd_weekly': 5.0,
            }
        
        return {
            'risk_per_trade': self._settings_integration.get_risk_per_trade(),
            'rr_min': self._settings_integration.get_rr_minimum(),
            'rr_target': self._settings_integration.get_rr_target(),
            'max_dd_daily': self._settings_integration.get_max_drawdown_daily(),
            'max_dd_weekly': self._settings_integration.get_max_drawdown_weekly(),
        }
