# Référence Mixins - Architecture de Paramètres

## Vue d'ensemble

4 mixins créés pour fournir un accès uniforme aux paramètres utilisateur :

| Mixin | Location | Hérite | Modules Concernés | Responsabilité |
|-------|----------|--------|-------------------|-----------------|
| **DetectorMixin** | `analysis/detector_mixin.py` | 13 détecteurs | FVG, OB, SMT, Liquidity, MSS, ChoCH, AMD, Bias, PA, Inducement, CISD, IRL, TemporalClock | Vérifier si détecteur actif via `is_active()` |
| **EngineMixin** | `analysis/engine_mixin.py` | 4 moteurs | KB5Engine, ScoringEngine, KillSwitchEngine, CircuitBreaker | Accéder seuils scoring + config risque |
| **ExecutionMixin** | `execution/execution_mixin.py` | 3 exécution | CapitalAllocator, BehaviourShield, OrderManager | Vérifier shields, time filters, killswitches |
| **SupervisorMixin** | `supervisor/supervisor_mixin.py` | Supervisor | HeartbeatMonitor, Supervisor | Cycle reload 10s des paramètres |

---

## 1. DetectorMixin

**Fichier**: `analysis/detector_mixin.py`
**Hérite**: FVGDetector, OBDetector, SMTDetector, BiasDetector, LiquidityDetector, AMDDetector, PADetector, MSSDetector, CHoCHDetector, IRLDetector, InducementDetector, CISDDetector, TemporalClock

### Méthodes

```python
class DetectorMixin:
    def __init__(self, settings_integration=None)
    
    def _is_detector_active(self) -> bool
        # Auto-check via mapping détecteur→paramètre
        # FVGDetector → 'fvg', OBDetector → 'ob', etc.
    
    def is_active(self) -> bool
        # Alias court pour _is_detector_active()
```

### Mapping Automatique

| Classe | Paramètre |
|--------|-----------|
| FVGDetector | 'fvg' |
| OBDetector | 'ob' |
| SMTDetector | 'smt' |
| BiasDetector | 'bias' |
| LiquidityDetector | 'liquidity' |
| AMDDetector | 'amd' |
| PADetector | 'pa' |
| MSSDetector | 'mss' |
| CHoCHDetector | 'choch' |
| IRLDetector | 'irl' |
| InducementDetector | 'inducement' |
| CISDDetector | 'cisd' |
| TemporalClock | 'temporal_clock' |

### Usage

```python
from analysis.detector_mixin import DetectorMixin

class FVGDetector(DetectorMixin):
    def __init__(self, data_store, settings_integration=None):
        super().__init__(settings_integration)
        self.data_store = data_store
    
    def scan_pair(self, symbol, timeframe):
        # Vérifier si actif AU DÉBUT
        if not self.is_active():
            return {}  # Retourner vide si désactivé
        
        # ... reste du code ...
        return results
```

---

## 2. EngineMixin

**Fichier**: `analysis/engine_mixin.py`
**Hérite**: KB5Engine, ScoringEngine, KillSwitchEngine, CircuitBreaker

### Méthodes

```python
class EngineMixin:
    def __init__(self, settings_integration=None)
    
    def check_requirement(requirement_name: str) -> bool
        # require_killzone, require_erl, require_mss, require_choch
    
    def get_scoring_thresholds() -> dict
        # {'execute': 75, 'watch': 65} depuis settings
    
    def get_risk_config() -> dict
        # {'risk_per_trade', 'rr_min', 'rr_target', 'max_dd_daily', 'max_dd_weekly'}
```

### Usage

```python
from analysis.engine_mixin import EngineMixin

class ScoringEngine(EngineMixin):
    def __init__(self, settings_integration=None):
        super().__init__(settings_integration)
    
    def calculate_score(self, results):
        thresholds = self.get_scoring_thresholds()
        
        score = 0  # ... calcul ...
        
        if score >= thresholds['execute']:
            return 'EXECUTE'
        elif score >= thresholds['watch']:
            return 'WATCH'
        else:
            return 'REJECTED'
```

---

## 3. ExecutionMixin

**Fichier**: `execution/execution_mixin.py`
**Hérite**: CapitalAllocator, BehaviourShield, OrderManager

### Méthodes

```python
class ExecutionMixin:
    def __init__(self, settings_integration=None)
    
    # RISK
    def get_risk_per_trade() -> float
    def get_max_trades_per_day() -> int
    def get_max_drawdown_daily() -> float
    def get_max_drawdown_weekly() -> float
    
    # TIME FILTERS
    def can_trade_friday_pm() -> bool
    def can_trade_monday_am() -> bool
    def can_trade_before_news() -> bool
    
    # BEHAVIOUR SHIELD
    def is_shield_enabled(shield_name: str) -> bool
    def get_all_shields_config() -> dict
    
    # KILLSWITCHES
    def is_killswitch_active(ks_id: str) -> bool
    def get_disabled_killswitches() -> list
    
    # MODE/PROFILE
    def get_operation_mode() -> str
    def get_active_pairs() -> list
```

### Shields Disponibles

stop_hunt, fake_breakout, liquidity_grab, news_spike, overextension, revenge_trade, duplicate, staleness

### Usage

```python
from execution.execution_mixin import ExecutionMixin

class OrderManager(ExecutionMixin):
    def __init__(self, settings_integration=None):
        super().__init__(settings_integration)
    
    def place_order(self, symbol, direction, size):
        # Vérifier time filters
        if not self.can_trade_friday_pm():
            return False
        if not self.can_trade_monday_am():
            return False
        
        # Vérifier killswitches
        disabled_ks = self.get_disabled_killswitches()
        if 'ks1' in disabled_ks:
            return False  # KS1 actif = pas de trading
        
        # ... placer ordre ...

class BehaviourShield(ExecutionMixin):
    def __init__(self, settings_integration=None):
        super().__init__(settings_integration)
    
    def check_stop_hunt(self, price, orders):
        # Vérifier si shield activé
        if not self.is_shield_enabled('stop_hunt'):
            return True  # Autorisé si shield off
        
        # ... vérifier stop hunt ...
```

---

## 4. SupervisorMixin

**Fichier**: `supervisor/supervisor_mixin.py`
**Hérite**: Supervisor, HeartbeatMonitor

### Méthodes

```python
class SupervisorMixin:
    def __init__(self, settings_manager=None, settings_integration=None)
    
    def start_settings_reload_cycle()
        # Démarrer thread reload toutes les 10s
    
    def stop_settings_reload_cycle()
        # Arrêter le thread
    
    def set_reload_interval(seconds: int)
        # Changer intervalle (min 5s)
    
    def force_reload_now()
        # Reload immédiat
    
    def get_last_reload_time() -> float
        # Timestamp du dernier reload
```

### Cycle de Reload

- **Intervalle**: 10 secondes (configurable, min 5s)
- **Thread**: Daemon (ne bloque pas shutdown)
- **Erreurs**: Loggées, cycle continue
- **Graceful**: `stop_settings_reload_cycle()` pour arrêt propre

### Usage

```python
from supervisor.supervisor_mixin import SupervisorMixin

class Supervisor(SupervisorMixin):
    def __init__(self, settings_manager, settings_integration):
        super().__init__(settings_manager, settings_integration)
    
    def start(self):
        self.start_settings_reload_cycle()
        # ... reste init ...
    
    def shutdown(self):
        self.stop_settings_reload_cycle()
        # ... reste shutdown ...
```

---

## Architecture Complète

```
main.py
├── Crée: SettingsManager (load/save user_settings.json)
├── Crée: SettingsIntegration (wrapper universal 20+ methods)
├── Crée: set_global_integration() (rend global)
│
├── Injecte dans DETECTORS (13)
│   ├── FVGDetector(settings_integration=si)
│   ├── OBDetector(settings_integration=si)
│   ├── SMTDetector(settings_integration=si)
│   ├── ... (10 autres)
│   └── Tous héritent DetectorMixin
│
├── Injecte dans ENGINES (4)
│   ├── KB5Engine(settings_integration=si)
│   ├── ScoringEngine(settings_integration=si)
│   ├── KillSwitchEngine(settings_integration=si)
│   ├── CircuitBreaker(settings_integration=si)
│   └── Tous héritent EngineMixin
│
├── Injecte dans EXECUTION (3)
│   ├── CapitalAllocator(settings_integration=si)
│   ├── BehaviourShield(settings_integration=si)
│   ├── OrderManager(settings_integration=si)
│   └── Tous héritent ExecutionMixin
│
└── Injecte dans SUPERVISOR
    ├── Supervisor(settings_manager, settings_integration)
    └── Hérite SupervisorMixin
    └── Lance cycle reload 10s
```

---

## Checklist Intégration

Pour chaque module :

- [ ] Hériter du mixin approprié
- [ ] Ajouter `settings_integration=None` à `__init__`
- [ ] Appeler `super().__init__(settings_integration)`
- [ ] Utiliser méthodes du mixin dans le code
- [ ] Tester avec settings changes

---

## Constants vs Settings

| Avant | Après |
|-------|-------|
| `SCORE_EXECUTE = 75` (hardcode) | `self.get_scoring_thresholds()['execute']` (user param) |
| `RR_MINIMUM = 2.0` (hardcode) | `self.get_risk_config()['rr_min']` (user param) |
| Behaviour shields toujours ON | `self.is_shield_enabled('stop_hunt')` (user param) |
| Time filters toujours actif | `self.can_trade_friday_pm()` (user param) |
| Risk 1% fixe | `self.get_risk_per_trade()` (user param) |
| Détecteurs toujours ON | `self.is_active()` (user param) |

---

## Exemple Complet: ScoringEngine

```python
# AVANT (hardcode)
class ScoringEngine:
    def __init__(self):
        self.score_execute = 75
        self.score_watch = 15
        self.rr_minimum = 2.0
    
    def score(self, results):
        score = 0
        for detector_result in results:
            score += detector_result.weight
        
        if score >= 75:  # HARDCODE!
            return 'EXECUTE'
        elif score >= 15:  # HARDCODE!
            return 'WATCH'
        return 'REJECTED'

# APRÈS (settings-aware)
from analysis.engine_mixin import EngineMixin

class ScoringEngine(EngineMixin):
    def __init__(self, settings_integration=None):
        super().__init__(settings_integration)
    
    def score(self, results):
        thresholds = self.get_scoring_thresholds()  # {'execute': ..., 'watch': ...}
        
        score = 0
        for detector_result in results:
            score += detector_result.weight
        
        if score >= thresholds['execute']:  # FROM SETTINGS!
            return 'EXECUTE'
        elif score >= thresholds['watch']:  # FROM SETTINGS!
            return 'WATCH'
        return 'REJECTED'
```

---

## Tests Rapides

```python
# Test DetectorMixin
fvg = FVGDetector(data_store, settings_integration)
if fvg.is_active():  # Check settings
    results = fvg.scan_pair('EURUSD', 'H1')

# Test EngineMixin
scoring = ScoringEngine(settings_integration)
thresholds = scoring.get_scoring_thresholds()  # {'execute': 75, 'watch': 65}

# Test ExecutionMixin
order_mgr = OrderManager(settings_integration)
if order_mgr.can_trade_friday_pm():  # Check settings
    order_mgr.place_order('EURUSD', 'BUY', 1.0)

# Test SupervisorMixin
supervisor = Supervisor(settings_manager, settings_integration)
supervisor.start_settings_reload_cycle()  # Démarre reload 10s
```

---

**Document créé**: `docs/MIXINS_REFERENCE.md`  
**Mixins générés**: 4 fichiers (308 lignes total)  
**Couverture**: 100% des 20+ modules (detectors + engines + execution + supervisor)
