# 🛠️ GUIDE D'IMPLÉMENTATION CONCRÈTE - Correction Paramètres KB5

**Cible:** Faire fonctionner 100+ paramètres au lieu de 9 seulement  
**Durée:** 1-2 jours de développement  
**Difficulté:** Moyenne – Plomberie + pas de logique complexe

---

## TAPE 1: Modifier main.py (30-45 min)

### Objectif
Injecter SettingsManager dans TOUS les modules au démarrage.

### Fichier: [main.py](main.py)

#### 1.1 — Importer SettingsManager (si absent)

```python
# Vers la ligne 30-50, dans les imports
from config.settings_manager import SettingsManager

# ... autres imports ...
```

#### 1.2 — Créer instance SettingsManager AVANT les détecteurs

Trouvez la ligne où on instancie DataStore (~ligne 350):

```python
# AVANT
ds = DataStore()
fvg_detector = FVGDetector(ds)

# APRÈS (insérer après DataStore)
ds = DataStore()
settings_manager = SettingsManager("user_settings.json")  # ✅ AJOUT

fvg_detector = FVGDetector(ds, settings_manager)  # ✅ MODIFIÉ
# ... et tous les détecteurs après
```

#### 1.3 — Modifier CHAQUE instantiation de détecteur

**Modèle à appliquer:**

```python
# AVANT
quelque_detector = QuelqueDetector(data_store=ds)

# APRÈS
quelque_detector = QuelqueDetector(
    data_store=ds,
    settings_manager=settings_manager  # ✅ AJOUT
)
```

**Détecteurs à modifier (13):**

```python
# Détecteurs
fvg_detector = FVGDetector(ds, settings_manager)
ob_detector = OBDetector(ds, settings_manager)
liquidity_detector = LiquidityDetector(ds, settings_manager)
smt_detector = SMTDetector(ds, settings_manager)
mss_detector = MSSDetector(ds, settings_manager)
choch_detector = CHoCHDetector(ds, settings_manager)
amd_detector = AMDDetector(ds, settings_manager)
bias_detector = BiasDetector(ds, settings_manager)
irl_detector = IRLDetector(ds, settings_manager)
inducement_detector = InducementDetector(ds, settings_manager)
cisd_detector = CISDDetector(ds, settings_manager)
pa_detector = PADetector(ds, settings_manager)
cot_seasonality = COTSeasonality(settings_manager)
```

#### 1.4 — Modifier moteurs

```python
# Avant
kb5_engine = KB5Engine(ds, fvg_detector, ob_detector, ...)

# Après
kb5_engine = KB5Engine(
    data_store=ds,
    fvg_detector=fvg_detector,
    ob_detector=ob_detector,
    # ... autres dépendances ...
    settings_manager=settings_manager  # ✅ AJOUT
)

# Idem pour
scoring_engine = ScoringEngine(kb5_engine, settings_manager)
behaviour_shield = BehaviourShield(ds, settings_manager)
order_manager = OrderManager(ds, settings_manager)
capital_allocator = CapitalAllocator(settings_manager)
```

#### 1.5 — Ajouter reload() loop (optionnel mais recommandé)

Dans la boucle de supervision (environ ligne 450+):

```python
# ... dans supervisor.run() ou similaire ...
import time
last_settings_reload = time.time()

while True:
    # Recharger settings toutes les 10 secondes
    if time.time() - last_settings_reload > 10:
        settings_manager.reload()  # ✅ AJOUT
        logger.debug("Settings reloaded")
        last_settings_reload = time.time()
    
    # ... analyser paires ...
    # ... placer ordres ...
    time.sleep(0.1)
```

---

## ÉTAPE 2: Modifier Chaque Détecteur (4-5 heures)

### Modèle à Appliquer

Prenons **FVGDetector** comme exemple, le pattern s'applique à TOUS les détecteurs.

### Fichier: [analysis/fvg_detector.py](analysis/fvg_detector.py)

#### 2.1 — Importer SettingsManager

```python
# Vers ligne 1-30
from config.settings_manager import SettingsManager

class FVGDetector:
    """Détecteur Fair Value Gaps — KB5 Edition"""
    
    def __init__(self, 
                 data_store: DataStore,
                 settings_manager: SettingsManager = None):  # ✅ AJOUT param
        self._ds = data_store
        self._settings = settings_manager  # ✅ AJOUT attribut
        # ... reste du __init__ ...
```

#### 2.2 — Ajouter Vérification dans scan_pair()

```python
def scan_pair(self, pair: str, timeframe: str = "D1") -> dict:
    """
    Scanner FVGs pour une paire + timeframe.
    
    Param utilisateur:
      - principles_enabled['ICT:fvg'] = True/False
    """
    
    # ✅ AJOUT: Vérifier si FVG activé
    if self._settings:
        if not self._settings.is_principle_active("ICT", "fvg"):
            logger.debug(f"FVG désactivé pour {pair} (user settings)")
            return {}  # Retourner vide si désactivé
    
    # ... code normal de scan FVG ...
    # Chercher FVGs dans les bougies
    # ...
    
    return fvgs_found
```

#### 2.3 — Logging Defensive

```python
def scan_pair(self, pair: str) -> dict:
    # Log si pas de settings (fallback gracieux)
    if not self._settings:
        logger.warning("FVGDetector: Pas de SettingsManager, utilisant defaults")
    else:
        logger.debug(f"FVGDetector: FVG active={self._settings.is_principle_active('ICT', 'fvg')}")
    
    # ... continue normally ...
```

### À Appliquer dans Ces Fichiers:

| Fichier | Clé à Vérifier | Vérification |
|---------|----------------|-------------|
| [analysis/fvg_detector.py](analysis/fvg_detector.py) | `ICT:fvg` | `if not settings.is_principle_active("ICT", "fvg"): return {}` |
| [analysis/ob_detector.py](analysis/ob_detector.py) | `ICT:order_blocks` | `if not settings.is_principle_active("ICT", "order_blocks"): return {}` |
| [analysis/liquidity_detector.py](analysis/liquidity_detector.py) | `ICT:liquidity` | `if not settings.is_principle_active("ICT", "liquidity"): return {}` |
| [analysis/smt_detector.py](analysis/smt_detector.py) | `ICT:smt` | Skip SMT analysis |
| [analysis/bias_detector.py](analysis/bias_detector.py) | `ICT:pd_zone` | Skip Premium/Discount |
| [analysis/amd_detector.py](analysis/amd_detector.py) | `ICT:amd` | Skip AMD analysis |
| [analysis/mss_detector.py](analysis/mss_detector.py) | `ICT:mss` | Skip MSS detection |
| [analysis/choch_detector.py](analysis/choch_detector.py) | `ICT:choch` | Skip CHoCH detection |
| [analysis/irl_detector.py](analysis/irl_detector.py) | `ICT:irl` | Skip IRL calculation |
| [analysis/inducement_detector.py](analysis/inducement_detector.py) | `SMC:inducement` | Skip Inducement |
| [analysis/pa_detector.py](analysis/pa_detector.py) | `PA:engulfing` | Skip PA patterns |
| [analysis/cisd_detector.py](analysis/cisd_detector.py) | `ICT:cisd` | Skip CISD |
| [analysis/cot_seasonality.py](analysis/cot_seasonality.py) | `RISK:cot` | Skip COT bonus |

---

## ÉTAPE 3: Modifier ScoringEngine (1-2 heures)

### Objectif
Lire `score_execute`, `score_watch`, `rr_min` depuis **settings** au lieu de constants hardcodées.

### Fichier: [analysis/scoring_engine.py](analysis/scoring_engine.py)

#### 3.1 — Modifier __init__()

```python
class ScoringEngine:
    def __init__(self,
                 kb5_engine,
                 settings_manager: SettingsManager = None):  # ✅ AJOUT
        self._kb5 = kb5_engine
        self._settings = settings_manager  # ✅ AJOUT
        
        # ✅ AJOUT: Charger seuils depuis settings
        self._load_settings()
    
    def _load_settings(self):
        """Charger les seuils de scoring depuis settings utilisateur"""
        if self._settings:
            self._score_execute = self._settings.get("score_execute", 75)
            self._score_watch = self._settings.get("score_watch", 65)
            self._rr_min = self._settings.get("rr_min", 2.0)
            logger.info(f"ScoringEngine: Loaded thresholds "
                       f"execute={self._score_execute}, "
                       f"watch={self._score_watch}, "
                       f"rr_min={self._rr_min}")
        else:
            # Defaults si pas de SettingsManager
            self._score_execute = 75
            self._score_watch = 65
            self._rr_min = 2.0
            logger.warning("ScoringEngine: No SettingsManager, using defaults")
```

#### 3.2 — Modifier execute_verdict()

**AVANT (constants hardcodées):**

```python
def execute_verdict(self, symbol, kb5_result) -> str:
    SCORE_EXECUTE = 75  # ❌ Hardcodé
    SCORE_WATCH = 65    # ❌ Hardcodé
    
    if kb5_result["score"] >= SCORE_EXECUTE:
        return "EXECUTE"
    elif kb5_result["score"] >= SCORE_WATCH:
        return "WATCH"
    return "REJECTED"
```

**APRÈS (depuis settings):**

```python
def execute_verdict(self, symbol, kb5_result) -> str:
    # Utiliser les seuils chargés au lieu des constants
    if kb5_result["score"] >= self._score_execute:
        return "EXECUTE"
    elif kb5_result["score"] >= self._score_watch:
        return "WATCH"
    return "REJECTED"
```

#### 3.3 — Modifier validation RR

**AVANT:**

```python
def _validate_rr(self, rr) -> bool:
    RR_MINIMUM = 2.0  # ❌ Hardcodé
    if rr < RR_MINIMUM:
        return False
    return True
```

**APRÈS:**

```python
def _validate_rr(self, rr) -> bool:
    # Utiliser self._rr_min au lieu de constant
    if rr < self._rr_min:
        logger.warning(f"RR {rr:.2f}x trop faible (min={self._rr_min:.2f}x)")
        return False
    return True
```

---

## ÉTAPE 4: Modifier Autres Moteurs/Exécution (2-3 heures)

### 4.1 — [execution/behaviour_shield.py](execution/behaviour_shield.py)

```python
class BehaviourShield:
    def __init__(self, data_store, settings_manager: SettingsManager = None):
        self._ds = data_store
        self._settings = settings_manager  # ✅ AJOUT
    
    def evaluate_trade(self, trade_info) -> dict:
        """Évalue si le trade doit être bloqué par BS"""
        
        # Charger les flags BS depuis settings
        behaviour_shield_cfg = {}
        if self._settings:
            behaviour_shield_cfg = self._settings.get("behaviour_shield", {})
        
        # stop_hunt
        if behaviour_shield_cfg.get("stop_hunt", True):  # default=True
            if self._detect_stop_hunt(trade_info):
                return {"blocked": True, "reason": "Stop Hunt Detected"}
        
        # fake_breakout  
        if behaviour_shield_cfg.get("fake_breakout", True):
            if self._detect_fake_breakout(trade_info):
                return {"blocked": True, "reason": "Fake Breakout"}
        
        # ... etc pour les 6 autres BS
        
        return {"blocked": False, "reason": None}
```

### 4.2 — [execution/order_manager.py](execution/order_manager.py)

```python
class OrderManager:
    def __init__(self, data_store, settings_manager: SettingsManager = None):
        self._ds = data_store
        self._settings = settings_manager  # ✅ AJOUT
    
    def can_place_order(self, symbol, order_type) -> bool:
        """Vérifier si on peut placer ordre selon time_filters"""
        
        # Charger time_filters
        time_filters = {}
        if self._settings:
            time_filters = self._settings.get("time_filters", {})
        
        # Friday PM bloqué?
        if time_filters.get("friday_pm", True):
            if self._is_friday_pm():
                logger.warning("Friday PM trades blocked (user settings)")
                return False
        
        # Monday morning bloqué?
        if time_filters.get("monday_morning", True):
            if self._is_monday_am():
                logger.warning("Monday AM trades blocked (user settings)")
                return False
        
        # Before news bloqué?
        if time_filters.get("before_news", True):
            if self._is_before_news():
                logger.warning("Before-news trades blocked (user settings)")
                return False
        
        return True
```

### 4.3 — [execution/capital_allocator.py](execution/capital_allocator.py)

```python
class CapitalAllocator:
    def __init__(self, settings_manager: SettingsManager = None):
        self._settings = settings_manager  # ✅ AJOUT
        self._total_capital = 10000  # Example
        self._load_settings()
    
    def _load_settings(self):
        if self._settings:
            # Charger paramètres de risque
            self._risk_per_trade = self._settings.get("risk_per_trade", 1.0)
            self._max_trades_day = self._settings.get("max_trades_day", 5)
            self._rr_target = self._settings.get("rr_target", 3.0)
    
    def calculate_lot_size(self, symbol, sl_pips) -> float:
        """Calculer lot size selon risque utilisateur"""
        
        risk_amount = (self._total_capital * self._risk_per_trade) / 100
        lot_size = risk_amount / (sl_pips * self._get_pip_value(symbol))
        
        logger.debug(f"Lot size: {lot_size:.2f} (risk={self._risk_per_trade}% per trade)")
        return lot_size
```

### 4.4 — [analysis/killswitch_engine.py](analysis/killswitch_engine.py) (partiellement)

```python
class KillSwitchEngine:
    def __init__(self, data_store, settings_manager: SettingsManager = None):
        self._ds = data_store
        self._settings = settings_manager  # ✅ AJOUT
    
    def check_all(self) -> dict:
        """Vérifier tous les KS, mais respecter disabled_ks"""
        
        # Charger liste de KS à désactiver
        disabled = []
        if self._settings:
            disabled = self._settings.get("disabled_ks", [])
        
        states = {}
        
        # KS1: Spread
        if "KS1" not in disabled:
            states["KS1"] = self.check_spread()
        else:
            states["KS1"] = {"triggered": False, "reason": "Disabled by user"}
        
        # KS2: Volatilité
        if "KS2" not in disabled:
            states["KS2"] = self.check_volatility()
        else:
            states["KS2"] = {"triggered": False, "reason": "Disabled by user"}
        
        # ...et les 7 autres KS
        
        return states
```

---

## ÉTAPE 5: Tests (2-3 heures)

### Test 1: Conceptional (30 min)

```python
# test_concepts.py
import pytest
from config.settings_manager import SettingsManager
from analysis.fvg_detector import FVGDetector
from datastore.data_store import DataStore

def test_fvg_disabled():
    """Test que FVG retourne vide si désactivé"""
    
    # Setup
    ds = DataStore()
    sm = SettingsManager()
    
    # Désactiver FVG
    sm.set("principles_enabled.ICT:fvg", False)
    
    detector = FVGDetector(ds, sm)
    
    # Test
    result = detector.scan_pair("EURUSD")
    assert result == {}, "FVG should return empty when disabled"
    
def test_fvg_enabled():
    """Test que FVG fonctionne si activé"""
    
    # Setup
    ds = DataStore()
    sm = SettingsManager()
    sm.set("principles_enabled.ICT:fvg", True)
    
    detector = FVGDetector(ds, sm)
    
    # Test (suppose des FVGs détectés)
    result = detector.scan_pair("EURUSD")
    assert isinstance(result, dict), "FVG should return dict"
```

### Test 2: Intégration (1 heure)

```bash
# 1. Démarrer le bot en Paper Mode
python main.py

# 2. Dans l'interface, essayer :
   - Désactiver FVG → Vérifier logs "FVG désactivé"
   - Changer risk_per_trade = 0.25% → Placer trade → Vérifier lot_size
   - Désactiver KS1 (Spread) → Vérifier "KS1 Disabled by user"

# 3. Vérifier les logs pour les messages DEBUG
tail -f logs/sentinel_pro.log | grep "Settings"
```

### Test 3: Rechargement Settings (30 min)

```python
# test_reload.py
import time

def test_settings_reload():
    """Test que settings se rechargent toutes les 10 sec"""
    
    # 1. Charger settings
    sm = SettingsManager()
    original_risk = sm.get("risk_per_trade", 1.0)
    print(f"Initial risk: {original_risk}%")
    
    # 2. Modifier JSON directement
    sm.set("risk_per_trade", 0.5)
    
    # 3. Recharger
    time.sleep(1)
    sm.reload()
    
    # 4. Vérifier
    new_risk = sm.get("risk_per_trade")
    assert new_risk == 0.5, f"Expected 0.5, got {new_risk}"
    print(f"✅ Settings reloaded correctly: {new_risk}%")
```

---

## CHECKLIST FINALE

### Code
- [ ] main.py: instances créées avec settings_manager
- [ ] 13 détecteurs: __init__ reçoit settings_manager
- [ ] 13 détecteurs: scan_pair() vérifie principles_enabled
- [ ] ScoringEngine: utilise self._score_execute au lieu de constant
- [ ] ScoringEngine: utilise self._rr_min au lieu de constant
- [ ] BehaviourShield: utilise behaviour_shield params
- [ ] OrderManager: utilise time_filters
- [ ] CapitalAllocator: utilise risk_per_trade
- [ ] KillSwitchEngine: utilise disabled_ks
- [ ] supervisor: reload() settings x1 par 10 sec

### Tests
- [ ] Test FVG On/Off
- [ ] Test OB On/Off
- [ ] Test risk_per_trade
- [ ] Test score_execute/score_watch
- [ ] Test disabled_ks
- [ ] Test behaviour_shield
- [ ] Test time_filters
- [ ] Test settings reload

### Documentation
- [ ] Docstrings ajoutées "Respects user settings"
- [ ] README mis à jour
- [ ] Logs DEBUG pour chaque paramètre appliqué

### Déploiement
- [ ] Backup user_settings.json
- [ ] Test Paper Trading 24h sans erreurs
- [ ] Merge en main

---

## EFFORT RÉSUMÉ

| Tâche | Durée | Difficulté |
|-------|-------|-----------|
| Étape 1: main.py | 0.5h | Facile |
| Étape 2: Détecteurs (13) | 4-5h | Moyen |
| Étape 3: ScoringEngine | 1-2h | Moyen |
| Étape 4: Autres (4) | 2-3h | Moyen |
| Étape 5: Tests | 2-3h | Moyen |
| **TOTAL** | **9-13h** | **9-13h travail développeur** |

---

_Guide d'implémentation généré le 19 Mars 2026_
