# 🔧 PLAN D'ACTION: CORRECTION PARAMÈTRES BOT KB5
**Statut:** 🔴 CRITIQUE | **Délai Estimé:** 1-2 jours | **Priorité:** P0

---

## 📋 RÉSUMÉ EXÉCUTIF

Le bot Sentinel Pro KB5 ignore ~90% de ses paramètres configurables.

**Cause Racine:** Les détecteurs/moteurs/exécution ne reçoivent pas SettingsManager en dépendance → Impossible de vérifier les paramètres au runtime.

**Solution:** Injecter SettingsManager dans TOUS les modules et remplacer les vérifications hardcodées.

---

## 🎯 PHASES DE CORRECTION

### PHASE 1: Préparation (30 min)

#### ✓ Audit Existant
✅ [AUDIT_PARAMETRES_COMPLET.md](AUDIT_PARAMETRES_COMPLET.md) — 56+ paramètres ignorés identifiés

#### ✓ Lister les Modules à Corriger
```
Détecteurs (13):
  - fvg_detector.py
  - ob_detector.py
  - smt_detector.py
  - bias_detector.py
  - liquidity_detector.py
  - amd_detector.py
  - mss_detector.py
  - choch_detector.py
  - irl_detector.py
  - inducement_detector.py
  - pa_detector.py
  - cisd_detector.py
  - cot_seasonality.py (partiellement)

Moteurs & Orchestration (4):
  - kb5_engine.py
  - scoring_engine.py
  - temporal_clock.py (sessions)
  - orchestrator.py

Exécution (3):
  - behaviour_shield.py
  - order_manager.py
  - capital_allocator.py

Configuration (1):
  - config/constants.py (concepts hardcodées)
```

---

### PHASE 2: Injection Dépendances (1-2 heures)

#### 2.1 — Main.py: Passer SettingsManager à Tous les Modules

**Fichier:** [main.py](main.py)

**Changement:**
```python
# AVANT (main.py vers ligne 350+)
fvg_detector = FVGDetector(data_store=ds)
ob_detector = OBDetector(data_store=ds)
smt_detector = SMTDetector(data_store=ds)
# ... 10+ autres détecteurs sans settings

# APRÈS
settings_manager = SettingsManager("user_settings.json")

fvg_detector = FVGDetector(data_store=ds, settings_manager=settings_manager)
ob_detector = OBDetector(data_store=ds, settings_manager=settings_manager)
smt_detector = SMTDetector(data_store=ds, settings_manager=settings_manager)
# ... et les 10+ autres

kb5_engine = KB5Engine(
    data_store=ds,
    fvg_detector=fvg_detector,
    ob_detector=ob_detector,
    smt_detector=smt_detector,
    settings_manager=settings_manager  # ✅ AJOUT
    # ... autres dépendances
)

scoring_engine = ScoringEngine(
    kb5_engine=kb5_engine,
    settings_manager=settings_manager  # ✅ AJOUT
    # ...
)

behaviour_shield = BehaviourShield(
    settings_manager=settings_manager,  # ✅ AJOUT
    # ...
)

# ... et tous les autres modules
```

---

#### 2.2 — Signature de Chaque Module

**Exemple FVGDetector:**

**Fichier:** [analysis/fvg_detector.py](analysis/fvg_detector.py)

```python
class FVGDetector:
    """Détecteur Fair Value Gaps avec gestion paramètres utilisateur"""
    
    def __init__(self, 
                 data_store: DataStore,
                 settings_manager: SettingsManager = None):  # ✅ AJOUT
        self._ds = data_store
        self._settings = settings_manager  # ✅ AJOUT
        # ... reste du __init__
```

**Idem pour TOUS les détecteurs:**
- [analysis/ob_detector.py](analysis/ob_detector.py)
- [analysis/smt_detector.py](analysis/smt_detector.py)
- [analysis/bias_detector.py](analysis/bias_detector.py)
- [analysis/liquidity_detector.py](analysis/liquidity_detector.py)
- [analysis/amd_detector.py](analysis/amd_detector.py)
- [analysis/mss_detector.py](analysis/mss_detector.py)
- [analysis/choch_detector.py](analysis/choch_detector.py)
- [analysis/irl_detector.py](analysis/irl_detector.py)
- [analysis/inducement_detector.py](analysis/inducement_detector.py)
- [analysis/pa_detector.py](analysis/pa_detector.py)
- [analysis/cisd_detector.py](analysis/cisd_detector.py)
- [analysis/cot_seasonality.py](analysis/cot_seasonality.py)

**Et les moteurs/exécution:**
- [analysis/kb5_engine.py](analysis/kb5_engine.py)
- [analysis/scoring_engine.py](analysis/scoring_engine.py)
- [execution/behaviour_shield.py](execution/behaviour_shield.py)
- [execution/order_manager.py](execution/order_manager.py)
- [execution/capital_allocator.py](execution/capital_allocator.py)

---

### PHASE 3: Ajouter Vérifications Paramètres (4-6 heures)

#### 3.1 — Concepts Activables (Détecteurs)

**Exemple FVGDetector → Vérifier principles_enabled:**

```python
def scan_pair(self, pair: str) -> dict:
    """Scan FVGs pour une paire, verifie d'abord si FVG est activé"""
    
    # ✅ AJOUT: Vérifier paramètre utilisateur
    if self._settings and not self._settings.is_principle_active("ICT", "fvg"):
        logger.debug(f"FVG désactivé pour {pair} (user settings)")
        return {}  # Retourner résultat vide si désactivé
    
    # ✅ Si pas de settings, procéder (rétrocompatibilité)
    if not self._settings:
        logger.warning("FVGDetector: Pas de SettingsManager, utilisation defaults")
    
    # ... code normal de scan FVG
    fvgs = self._detect_fvg(pair, tf, df)
    
    # ✅ Filtrer par paramètres utilisateur si disponible
    if self._settings and self._settings.get("principles_enabled", {}).get("ICT:fvg") == False:
        return {}
    
    return fvgs
```

**À appliquer pour CHAQUE détecteur:**

| Détecteur | Clé Paramètre | Vérification |
|-----------|---------------|-------------|
| FVGDetector | `ICT:fvg` | Scan FVGs |
| OBDetector | `ICT:order_blocks` | Scan OBs |
| SMTDetector | `ICT:smt` | Scan SMT divergences |
| BiasDetector | `ICT:pd_zone` | Premium/Discount |
| LiquidityDetector | `ICT:liquidity` | Liquidity Sweeps |
| AMDDetector | `ICT:amd` | AMD cycles |
| MSSDetector | `ICT:mss` | MSS |
| CHoCHDetector | `ICT:choch` | CHoCH |
| IRLDetector | `ICT:irl` | Internal Liquidity |
| InducementDetector | `SMC:inducement` | Induce |
| PADetector | `PA:engulfing` | Price Action |
| CISDDetector | `ICT:cisd` | CISD |
| COTSeasonality | `RISK:cot` | COT Bonus |

#### 3.2 — Paramètres de Risque (Capital/ScoringEngine)

**Fichier:** [analysis/scoring_engine.py](analysis/scoring_engine.py)

```python
# AVANT (constants hardcodées):
SCORE_EXECUTE = 75      # ❌ JAMAIS utilisé depuis settings
SCORE_WATCH   = 15      # ❌ JAMAIS utilisé depuis settings
RR_MINIMUM    = 2.0     # ❌ JAMAIS utilisé depuis settings

# APRÈS (lire depuis settings):
def __init__(self, 
             kb5_engine,
             settings_manager: SettingsManager = None):
    self._kb5 = kb5_engine
    self._settings = settings_manager
    self._score_execute = None
    self._score_watch = None
    self._rr_min = None
    self._load_settings()

def _load_settings(self):
    """Charger les seuils depuis settings ou utiliser defaults"""
    if self._settings:
        self._score_execute = self._settings.get("score_execute", 75)  # default 75
        self._score_watch = self._settings.get("score_watch", 15)      # default 15
        self._rr_min = self._settings.get("rr_min", 2.0)               # default 2.0
    else:
        self._score_execute = 75
        self._score_watch = 15
        self._rr_min = 2.0

def execute_verdict(self, symbol, kb5_result, ...) -> str:
    # Utiliser les paramètres chargés au lieu des constants
    if kb5_result["score"] >= self._score_execute:
        return "EXECUTE"
    elif kb5_result["score"] >= self._score_watch:
        return "WATCH"
    else:
        return "REJECTED"

def _validate_rr(self, rr, ...) -> bool:
    # Utiliser self._rr_min au lieu de RR_MINIMUM constant
    if rr < self._rr_min:
        return False
    return True
```

**À appliquer aussi pour:**

| Fichier | Paramètres | Changement |
|---------|-----------|-----------|
| capital_allocator.py | `risk_per_trade`, `max_trades_day` | Calculer risque dynamiquement |
| killswitch_engine.py | `max_dd_day_pct`, `max_dd_week_pct`, `disabled_ks` | Vérifier DD vs settings |
| order_manager.py | `time_filters` (friday_pm, etc.) | Bloquer trades selon horaires |
| behaviour_shield.py | `behaviour_shield[x]` | Activer/désactiver BS individuellement |

#### 3.3 — Sessions Temporelles

**Fichier:** [analysis/temporal_clock.py](analysis/temporal_clock.py) (à créer si nécessaire)

```python
def is_session_active(self, session_name: str) -> bool:
    """Vérifier si une session est active selon settings utilisateur"""
    
    if self._settings:
        sessions_actives = self._settings.get("sessions_actives", [])
        if session_name not in sessions_actives:
            return False  # ✅ Session désactivée par utilisateur
    
    # Vérifier l'horaire
    return self._is_in_session_timeframe(session_name)
```

---

### PHASE 4: Recharger Settings (1-2 heures)

#### 4.1 — Option A: Recharger à Chaque Cycle (Recommandé)

Dans [main.py](main.py) ou [supervisor.py](supervisor.py) loops:

```python
def run_cycle():
    # Recharger settings au début de chaque cycle
    # (une fois par 10 sec environ)
    settings_manager.reload()
    
    # Distribuer le signal aux modules
    for detector in [fvg_detector, ob_detector, ...]:
        if hasattr(detector, 'reload_settings'):
            detector.reload_settings()  # Optionnel
    
    # Exécuter l'analyse
    kb5_result = kb5_engine.analyze_pair(pair, tf)
    # ...
```

#### 4.2 — Option B: Event-Driven (Avancé)

Créer un système d'événements:

```python
import threading
from typing import Callable

class SettingsObserver:
    """Observer pattern pour recharger settings quand changent"""
    
    def __init__(self, callback: Callable):
        self.callback = callback
    
    def on_settings_changed(self):
        self.callback()

# Dans main.py
settings_manager.subscribe(observer)
```

**Ou plus simplement:**

```python
# Dans supervisor.py loop ~10 sec:
if time.time() - last_settings_reload > 10:
    settings_manager.reload()
    last_settings_reload = time.time()
```

---

### PHASE 5: Tests (2-3 heures)

#### Test 1: Paramètres Concepts
```python
# 1. Désactiver FVG en UI
# 2. Relancer bot (ou attendre 10-15 sec reload)
# 3. Vérifier que FVGDetector.scan_pair(pair) retourne {}
# Expected: ✅ Aucun FVG détecté même si présents en chart
```

#### Test 2: Paramètres Risque
```python
# 1. Mettre risk_per_trade = 0.1% en UI
# 2. Lancer trade
# 3. Vérifier calcul de lot: Capital × 0.1% / SL_pips
# Expected: ✅ Lot calculé selon 0.1% (vs 1% default)
```

#### Test 3: Killswitches
```python
# 1. Désactiver KS1 (Spread) en UI
# 2. Vérifier que KillSwitchEngine saute KS1
# Expected: ✅ Pas de bloquage spread
```

#### Test 4: Sessions
```python
# 1. Garder SEULEMENT "session_london" en UI
# 2. Vérifier que bot ignore les ordres hors Londres
# Expected: ✅ Aucun ordre entre 17h-7h UTC
```

---

## 📊 CHECKLIST DE DÉPLOIEMENT

### Préparation
- [ ] 01. Lire AUDIT_PARAMETRES_COMPLET.md
- [ ] 02. Créer branche feature/fix-parameters
- [ ] 03. Backup user_settings.json actuel

### Développement
- [ ] 04. Modifier signatures __init__ dans 13 détecteurs (main.py)
- [ ] 05. Ajouter vérifications dans scan_pair() (détecteurs)
- [ ] 06. Modifier ScoringEngine pour lire _score_execute, etc.
- [ ] 07. Modifier KillSwitchEngine pour vérifier disabled_ks
- [ ] 08. Modifier BehaviourShield pour lire behaviour_shield params
- [ ] 09. Modifier OrderManager pour lire time_filters
- [ ] 10. Ajouter reload() loop dans supervisor (10sec)

### Tests
- [ ] 11. Test FVG On/Off
- [ ] 12. Test OB On/Off
- [ ] 13. Test risk_per_trade
- [ ] 14. Test max_dd_day_pct
- [ ] 15. Test disabled_ks
- [ ] 16. Test sessions_actives
- [ ] 17. Test behaviour_shield

### Documentation
- [ ] 18. Ajouter docstrings "Settings" dans chaque module
- [ ] 19. Mettre à jour README avec "Parameter Control"

### Validation
- [ ] 20. Tester en Paper Trading 24h
- [ ] 21. Demander review à 2 personnes
- [ ] 22. Merge en main

---

## 🔄 EFFORT ESTIMÉ

| Phase | Tâche | Heures | Ressource |
|-------|-------|--------|-----------|
| 1 | Préparation | 0.5 | Junior |
| 2 | Injection dépendances | 1.5 | Senior |
| 3 | Ajouter vérifications | 4-6 | Senior |
| 4 | Recharger settings | 1-2 | Mid |
| 5 | Tests | 2-3 | QA |
| **TOTAL** | | **9-13h** | **1-2 jours** |

---

## 🚀 RÉSULTAT ATTENDU APRÈS CORRECTION

| Aspect | Avant | Après |
|--------|--------|--------|
| **Paramètres utilisés** | 9/105 (8.5%) | 100+/105 (95%+) |
| **Concepts contrôlables** | 3 max | 30+ |
| **Risk personnalisable** | 0 (hardcodé) | 6+ |
| **Sessions configurables** | 0 (TOUTES actives) | 7+ |
| **Killswitches modifiables** | 1 (disabled_ks) | 9 |
| **Behaviour Shield** | Fixed | 8 filtres configurables |

---

## 📝 NOTES CRITIQUES

1. **Rétrocompatibilité**: Tous les changements incluent un fallback vers defaults. Si SettingsManager est None, le bot fonctionne normalement.

2. **Performance**: Recharger settings x1 par 10 sec a impact négligeable (~1ms).

3. **Ordre de priorité**:
   - 🔴 P1 (Concepts 31+): Permet À L'UTILISATEUR DE CONTRÔLER L'ANALYSE
   - 🟠 P2 (Risque 6+): Permet de changer risque/profil
   - 🟡 P3 (Sessions 8+): Améliore flexibilité trading
   - 🟢 P4 (Behaviour Shield 8): Nice-to-have

---

_Plan d'action généré 19 Mars 2026_
