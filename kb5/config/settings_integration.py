# config/settings_integration.py
"""
COUCHE D'INTÉGRATION UNIVERSELLE DES PARAMÈTRES

Fournit à CHAQUE module accès simple et transparent aux paramètres utilisateur.
Cela supprime le besoin de modifier chaque module individuellement.

Utilisé par:
  - Tous les détecteurs (FVG, OB, SMT, etc.)
  - Tous les moteurs (KB5Engine, ScoringEngine)
  - Toute l'exécution (BehaviourShield, OrderManager)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SettingsIntegration:
    """
    Wrapper universel pour accéder aux paramètres du bot.
    
    Utilisé par tous les modules pour:
      - Vérifier si un concept est activé
      - Obtenir les seuils de risque
      - Vérifier les filtres temporels
      - etc.
    """
    
    def __init__(self, settings_manager: Optional['SettingsManager'] = None):
        """
        Initialise l'intégration avec un SettingsManager.
        Si None, utilise les defaults.
        """
        self._settings = settings_manager
    
    # ══════════════════════════════════════════════════════
    # CONCEPTS / ANALYSES
    # ══════════════════════════════════════════════════════
    
    def is_detector_active(self, detector_name: str) -> bool:
        """Vérifier si un détecteur est actif par rapport aux concepts activés."""
        if not self._settings:
            return True  # Default: tous actifs si pas de settings
        
        # Mapping: nom détecteur → (école, concept)
        mapping = {
            'fvg':         ('ICT', 'fvg'),
            'ob':          ('ICT', 'order_blocks'),
            'liquidity':   ('ICT', 'liquidity'),
            'smt':         ('ICT', 'smt'),
            'mss':         ('ICT', 'mss'),
            'choch':       ('ICT', 'choch'),
            'amd':         ('ICT', 'amd'),
            'irl':         ('ICT', 'irl'),
            'bias':        ('ICT', 'pd_zone'),
            'pa':          ('PA', 'engulfing'),
            'inducement':  ('SMC', 'inducement'),
            'cisd':        ('ICT', 'cisd'),
        }
        
        if detector_name not in mapping:
            return True  # Unknown detector → allow
        
        school, concept = mapping[detector_name]
        active = self._settings.is_principle_active(school, concept)
        
        if not active:
            logger.debug(f"Detector '{detector_name}' désactivé (user setting)")
        
        return active
    
    # ══════════════════════════════════════════════════════
    # SESSIONS / TEMPORALITÉ
    # ══════════════════════════════════════════════════════
    
    def is_session_active(self, session_name: str) -> bool:
        """Vérifier si une session de trading est activée."""
        if not self._settings:
            return True
        
        sessions = self._settings.get('sessions_actives', [
            'session_london', 'session_ny', 'overlap_lnny'
        ])
        
        return session_name in sessions
    
    def get_active_sessions(self) -> list:
        """Retourner liste des sessions actives."""
        if not self._settings:
            return ['session_london', 'session_ny', 'overlap_lnny']
        
        return self._settings.get('sessions_actives', [])
    
    # ══════════════════════════════════════════════════════
    # RISQUE / GESTION
    # ══════════════════════════════════════════════════════
    
    def get_risk_per_trade(self) -> float:
        """Obtenir % risque par trade."""
        if not self._settings:
            return 1.0
        return self._settings.get('risk_per_trade', 1.0)
    
    def get_max_trades_per_day(self) -> int:
        """Obtenir nombre max de trades par jour."""
        if not self._settings:
            return 5
        return self._settings.get('max_trades_day', 5)
    
    def get_max_drawdown_daily(self) -> float:
        """Obtenir drawdown max par jour (%)."""
        if not self._settings:
            return 2.0
        return self._settings.get('max_dd_day_pct', 2.0)
    
    def get_max_drawdown_weekly(self) -> float:
        """Obtenir drawdown max par semaine (%)."""
        if not self._settings:
            return 5.0
        return self._settings.get('max_dd_week_pct', 5.0)
    
    def get_rr_minimum(self) -> float:
        """Obtenir RR minimum accepté."""
        if not self._settings:
            return 2.0
        return self._settings.get('rr_min', 2.0)
    
    def get_rr_target(self) -> float:
        """Obtenir RR cible pour TP1."""
        if not self._settings:
            return 3.0
        return self._settings.get('rr_target', 3.0)
    
    # ══════════════════════════════════════════════════════
    # SCORING
    # ══════════════════════════════════════════════════════
    
    def get_score_execute_threshold(self) -> int:
        """Score minimum pour EXECUTE."""
        if not self._settings:
            return 75
        return self._settings.get('score_execute', 75)
    
    def get_score_watch_threshold(self) -> int:
        """Score minimum pour WATCH."""
        if not self._settings:
            return 15
        return self._settings.get('score_watch', 15)
    
    # ══════════════════════════════════════════════════════
    # FILTRES GLOBAUX
    # ══════════════════════════════════════════════════════
    
    def require_killzone(self) -> bool:
        """Killzone obligatoire?"""
        if not self._settings:
            return True
        return self._settings.get('require_killzone', True)
    
    def require_erl(self) -> bool:
        """ERL sweep obligatoire?"""
        if not self._settings:
            return True
        return self._settings.get('require_erl', True)
    
    def require_mss(self) -> bool:
        """MSS confirmé obligatoire?"""
        if not self._settings:
            return False
        return self._settings.get('require_mss', False)
    
    def require_choch(self) -> bool:
        """CHoCH confirmé obligatoire?"""
        if not self._settings:
            return False
        return self._settings.get('require_choch', False)
    
    def use_partial_tp(self) -> bool:
        """TP partiel activé?"""
        if not self._settings:
            return True
        return self._settings.get('use_partial_tp', True)
    
    # ══════════════════════════════════════════════════════
    # KILLSWITCHES
    # ══════════════════════════════════════════════════════
    
    def is_killswitch_enabled(self, ks_id: str) -> bool:
        """Vérifier si un killswitch est activé (pas dans disabled_ks)."""
        if not self._settings:
            return True
        
        disabled = self._settings.get('disabled_ks', [])
        is_enabled = ks_id not in disabled
        
        if not is_enabled:
            logger.debug(f"KS {ks_id} DÉSACTIVÉ par utilisateur")
        
        return is_enabled
    
    def get_disabled_killswitches(self) -> list:
        """Obtenir liste des KS désactivés."""
        if not self._settings:
            return []
        return self._settings.get('disabled_ks', [])
    
    # ══════════════════════════════════════════════════════
    # BEHAVIOUR SHIELD
    # ══════════════════════════════════════════════════════
    
    def is_behaviour_shield_enabled(self, shield_name: str) -> bool:
        """Vérifier si un filtre de behaviour_shield est activé."""
        if not self._settings:
            return True
        
        behaviour_shields = self._settings.get('behaviour_shield', {})
        return behaviour_shields.get(shield_name, True)  # Default=True
    
    def get_behaviour_shield_config(self) -> dict:
        """Obtenir config complète behaviour_shield."""
        if not self._settings:
            return {}
        return self._settings.get('behaviour_shield', {})
    
    # ══════════════════════════════════════════════════════
    # TIME FILTERS
    # ══════════════════════════════════════════════════════
    
    def is_time_filter_enabled(self, filter_name: str) -> bool:
        """Vérifier si un filtre temporel est activé."""
        if not self._settings:
            return True
        
        time_filters = self._settings.get('time_filters', {})
        return time_filters.get(filter_name, True)  # Default=True
    
    def can_trade_friday_pm(self) -> bool:
        """Peut-on trader le vendredi PM?"""
        if not self._settings:
            return False  # Par défaut: NON
        
        filters = self._settings.get('time_filters', {})
        friday_pm_blocked = filters.get('friday_pm', True)
        return not friday_pm_blocked
    
    def can_trade_monday_am(self) -> bool:
        """Peut-on trader le lundi AM?"""
        if not self._settings:
            return False
        
        filters = self._settings.get('time_filters', {})
        monday_am_blocked = filters.get('monday_morning', True)
        return not monday_am_blocked
    
    def can_trade_before_news(self) -> bool:
        """Peut-on trader avant les news?"""
        if not self._settings:
            return False
        
        filters = self._settings.get('time_filters', {})
        before_news_blocked = filters.get('before_news', True)
        return not before_news_blocked
    
    # ══════════════════════════════════════════════════════
    # PAIRES
    # ══════════════════════════════════════════════════════
    
    def get_active_pairs(self) -> list:
        """Obtenir liste des paires actives."""
        if not self._settings:
            return []
        return self._settings.get_active_pairs()
    
    # ══════════════════════════════════════════════════════
    # MODE OPÉRATION
    # ══════════════════════════════════════════════════════
    
    def get_operation_mode(self) -> str:
        """Obtenir mode opération: PAPER / SEMI_AUTO / FULL_AUTO."""
        if not self._settings:
            return "PAPER"
        return self._settings.get('op_mode', 'PAPER')
    
    def is_paper_trading(self) -> bool:
        """Est-on en paper trading?"""
        return self.get_operation_mode() == "PAPER"
    
    def is_semi_auto(self) -> bool:
        """Est-on en semi-automatique?"""
        return self.get_operation_mode() == "SEMI_AUTO"
    
    def is_full_auto(self) -> bool:
        """Est-on en full automatique?"""
        return self.get_operation_mode() == "FULL_AUTO"
    
    # ══════════════════════════════════════════════════════
    # IA / LLM
    # ══════════════════════════════════════════════════════
    
    def get_llm_provider(self) -> str:
        """Obtenir fournisseur LLM: Gemini / Grok, etc."""
        if not self._settings:
            return "Gemini"
        return self._settings.get('llm_provider', 'Gemini')
    
    def get_llm_api_key(self) -> str:
        """Obtenir clé API LLM."""
        if not self._settings:
            return ""
        return self._settings.get('llm_api_key', '')


# ══════════════════════════════════════════════════════════════
# INSTANCE GLOBALE (optionnelle pour compatibility)
# ══════════════════════════════════════════════════════════════

_global_integration: Optional[SettingsIntegration] = None


def set_global_integration(integration: SettingsIntegration) -> None:
    """Définir l'instance globale d'intégration."""
    global _global_integration
    _global_integration = integration
    logger.debug("Global SettingsIntegration définie")


def get_global_integration() -> SettingsIntegration:
    """Obtenir l'instance globale (fallback si non définie)."""
    global _global_integration
    if _global_integration is None:
        _global_integration = SettingsIntegration(None)
    return _global_integration
