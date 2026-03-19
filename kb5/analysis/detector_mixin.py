# analysis/detector_mixin.py
"""
MIXIN UNIVERSEL POUR TOUS LES DÉTECTEURS

Fournit une base commune pour que TOUS les détecteurs KB5 respectent
les paramètres utilisateur sans modification massive du code existant.

Utilisation:
    class FVGDetector(DetectorMixin):
        def __init__(self, data_store, settings_integration=None):
            super().__init__(settings_integration)
            self._ds = data_store
        
        def scan_pair(self, pair):
            # Vérifie AUTOMATIQUEMENT si ce détecteur est activé
            if not self.is_active():
                return {}
            # ... Le reste du code ne change pas
"""

import logging

logger = logging.getLogger(__name__)


class DetectorMixin:
    """
    Base commune UNIVERSELLE pour TOUS les détecteurs.
    
    Permet à n'importe quel détecteur de:
      - Vérifier s'il est activé via les paramètres utilisateur
      - Accéder aux settings globalement
      - Gérer le logging cohérent
    
    Cette classe:
      - Ne modifie PAS la logique existante
      - Permet la rétrocompatibilité (pas de break)
      - Fournit juste des vérifications simples
    """
    
    def __init__(self, settings_integration=None):
        """Initialiser le mixin avec l'intégration settings."""
        self._settings_integration = settings_integration
        self._detector_name = self.__class__.__name__
    
    def _is_detector_active(self) -> bool:
        """
        Vérifier si CETTE instance de détecteur est activée par l'utilisateur.
        
        Détecteur → Nom court → Paramètre utilisateur
        Exemple : FVGDetector → 'fvg' → settings.is_principle_active('ICT', 'fvg')
        
        Default: True (rétrocompatibilité)
        """
        if not self._settings_integration:
            return True  # Si pas de settings, accepter tous
        
        # Mapping automatique: nom classe → clé court
        detector_mappings = {
            'FVGDetector':           'fvg',
            'OBDetector':            'ob',
            'LiquidityDetector':     'liquidity',
            'SMTDetector':           'smt',
            'MSSDetector':           'mss',
            'CHoCHDetector':         'choch',
            'AMDDetector':           'amd',
            'BiasDetector':          'bias',       # Note: bias → pd_zone dans settings
            'IRLDetector':           'irl',
            'InducementDetector':    'inducement',
            'PADetector':            'pa',
            'CISDDetector':          'cisd',
            'TemporalClock':         'temporal',
            'COTSeasonality':        'cot',
        }
        
        short_name = detector_mappings.get(self._detector_name)
        
        if not short_name:
            # Détecteur inconnu → autoriser par défaut
            logger.warning(f"Détecteur inconnu: {self._detector_name} — activé par défaut")
            return True
        
        # Pour BiasDetector, la clé est pd_zone
        if short_name == 'bias':
            active = self._settings_integration.is_detector_active('bias')
        else:
            active = self._settings_integration.is_detector_active(short_name)
        
        if not active:
            logger.debug(f"✓ {self._detector_name} DÉSACTIVÉ (user settings)")
        
        return active
    
    def is_active(self) -> bool:
        """Raccourci: is_active() au lieu de _is_detector_active()"""
        return self._is_detector_active()
    
    def _get_setting(self, key: str, default=None):
        """Obtenir un paramètre depuis l'intégration settings."""
        if not self._settings_integration:
            return default
        return self._settings_integration._settings.get(key, default) if self._settings_integration._settings else default
