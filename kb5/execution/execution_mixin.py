# execution/execution_mixin.py
"""
MIXIN pour EXECUTION (CapitalAllocator, BehaviourShield, OrderManager)

Permet aux modules d'exécution d'accéder facilement aux paramètres utilisateur.
"""

import logging

logger = logging.getLogger(__name__)


class ExecutionMixin:
    """Base pour tous les modules d'exécution."""
    
    def __init__(self, settings_integration=None):
        self._settings_integration = settings_integration
    
    # ========== RISK ==========
    def get_risk_per_trade(self) -> float:
        """Obtenir % risque par trade depuis settings."""
        if not self._settings_integration:
            return 1.0
        return self._settings_integration.get_risk_per_trade()
    
    def get_max_trades_per_day(self) -> int:
        """Obtenir max trades/jour depuis settings."""
        if not self._settings_integration:
            return 5
        return self._settings_integration.get_max_trades_per_day()
    
    def get_max_drawdown_daily(self) -> float:
        """Obtenir max drawdown journalier % depuis settings."""
        if not self._settings_integration:
            return 2.0
        return self._settings_integration.get_max_drawdown_daily()
    
    def get_max_drawdown_weekly(self) -> float:
        """Obtenir max drawdown hebdomadaire % depuis settings."""
        if not self._settings_integration:
            return 5.0
        return self._settings_integration.get_max_drawdown_weekly()
    
    # ========== TIME FILTERS ==========
    def can_trade_friday_pm(self) -> bool:
        """Vérifier si trading autorisé vendredi PM."""
        if not self._settings_integration:
            return False
        return self._settings_integration.can_trade_friday_pm()
    
    def can_trade_monday_am(self) -> bool:
        """Vérifier si trading autorisé lundi matin."""
        if not self._settings_integration:
            return False
        return self._settings_integration.can_trade_monday_am()
    
    def can_trade_before_news(self) -> bool:
        """Vérifier si trading autorisé avant news."""
        if not self._settings_integration:
            return False
        return self._settings_integration.can_trade_before_news()
    
    # ========== BEHAVIOUR SHIELD ==========
    def is_shield_enabled(self, shield_name: str) -> bool:
        """Vérifier si un comportement shield est activé."""
        # Validés: stop_hunt, fake_breakout, liquidity_grab, news_spike, 
        #          overextension, revenge_trade, duplicate, staleness
        if not self._settings_integration:
            return True  # Par défaut activé
        return self._settings_integration.is_behaviour_shield_enabled(shield_name)
    
    def get_all_shields_config(self) -> dict:
        """Obtenir config complète des shields."""
        if not self._settings_integration:
            shields = {
                'stop_hunt': True,
                'fake_breakout': True,
                'liquidity_grab': True,
                'news_spike': True,
                'overextension': True,
                'revenge_trade': True,
                'duplicate': True,
                'staleness': True,
            }
            return {name: {'active': True} for name in shields}
        
        return self._settings_integration.get_behaviour_shield_config()
    
    # ========== KILLSWITCHES ==========
    def is_killswitch_active(self, ks_id: str) -> bool:
        """Vérifier si killswitch est actif (pas désactivé)."""
        # ks_id format: 'ks1', 'ks2', ... 'ks9'
        if not self._settings_integration:
            return True
        return self._settings_integration.is_killswitch_enabled(ks_id)
    
    def get_disabled_killswitches(self) -> list:
        """Obtenir liste des killswitches désactivés."""
        if not self._settings_integration:
            return []
        return self._settings_integration.get_disabled_killswitches()
    
    # ========== MODE/PROFILE ==========
    def get_operation_mode(self) -> str:
        """Obtenir mode opération: demo, live, paper."""
        if not self._settings_integration:
            return 'demo'
        return self._settings_integration.get_operation_mode()
    
    def get_active_pairs(self) -> list:
        """Obtenir liste paires actives pour trading."""
        if not self._settings_integration:
            return []
        return self._settings_integration.get_active_pairs()
