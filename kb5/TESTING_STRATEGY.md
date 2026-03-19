# Plan de Test Pratique — Vérifier que les Paramètres s'Appliquent

## 🎯 Objectif
Vérifier que les paramètres dans `user_settings.json` sont **réellement utilisés** par le bot en runtime (sans redémarrage)

---

## ✅ Test 1: Reload Cycle du Supervisor (10 secondes)

**Vérifier que les paramètres se rechargent automatiquement**

```bash
# Terminal 1: Lancer le bot
python main.py

# Terminal 2: Modifier user_settings.json
# Changer une valeur:
# "risk_per_trade": 0.5 → "risk_per_trade": 1.0
# "score_execute": 80 → "score_execute": 85

# Attendre 10 secondes

# Vérifier dans les logs du bot:
# "Settings reloaded" ou "Paramètres rechargés"
```

**Résultat attendu**: Les logs montrent "Settings reloaded" tous les 10 secondes ✅

---

## ✅ Test 2: Détecteurs Toggle (Désactiver/Activer)

**Vérifier que les détecteurs respectent is_active()**

### Test FVG Detector:
```python
# Dans user_settings.json, désactiver FVG:
"ICT:fvg": false

# Attendre 10 secondes

# Analyser une paire
# Chercher dans les logs: 
# ❌ Pas de output FVG
# ❌ Pas de ["FVG"] detection

# Réactiver:
"ICT:fvg": true

# Attendre 10 secondes

# ✅ Maintenant FVG detections apparaissent
```

### Script de Test Automatique:
```python
# test_detector_toggle.py
from analysis.fvg_detector import FVGDetector
from config.settings_integration import SettingsIntegration
from datastore.data_store import DataStore

settings = SettingsIntegration()
ds = DataStore()

# Test 1: FVG Enabled
print("Test 1: FVG actif")
fvg = FVGDetector(ds, settings)
result = fvg.analyze("EURUSD")
print(f"FVG résult: {len(result)} FVGs trouvés")

# Test 2: FVG Disabled
settings.settings['principles_enabled']['ICT:fvg'] = False
print("\nTest 2: FVG désactivé (is_active=False)")
result = fvg.analyze("EURUSD")
print(f"FVG résult: {result}")  # Doit être {}

# Test 3: Re-enable
settings.settings['principles_enabled']['ICT:fvg'] = True
print("\nTest 3: FVG réactivé")
result = fvg.analyze("EURUSD")
print(f"FVG résult: {len(result)} FVGs trouvés")  # Doit retrouver FVGs
```

---

## ✅ Test 3: Risk Parameters — Changement en Temps Réel

**Vérifier que risk_per_trade affecte la taille des ordres**

### Test Manual:
```bash
# Étape 1: Définir risk_per_trade = 0.5
# user_settings.json: "risk_per_trade": 0.5

# Étape 2: Créer un signal de trade
# Score = 85 (EXECUTE)
# Account = $10,000
# Risk par trade = 0.5% = $50

# Vérifier dans los logs:
# "Order size: 50 (0.5% of $10,000)"

# Étape 3: Changer risk_per_trade = 1.0
# user_settings.json: "risk_per_trade": 1.0
# Attendre 10 secondes

# Étape 4: Créer un autre signal
# Vérifier dans logs:
# "Order size: 100 (1.0% of $10,000)"
```

### Script Python:
```python
# test_risk_parameters.py
from execution.capital_allocator import CapitalAllocator
from config.settings_integration import SettingsIntegration
from datastore.data_store import DataStore

settings = SettingsIntegration()
ds = DataStore()
allocator = CapitalAllocator(ds, settings)

# Test 1: risk_per_trade = 0.5
account_equity = 10000
risk_amount = allocator.get_risk_per_trade()  # 0.5%
position_size = (account_equity * risk_amount / 100) / 100
print(f"Test 1 - Risk 0.5%: Position size = ${position_size:.2f}")

# Test 2: Changer à 1.0
settings.settings['risk_per_trade'] = 1.0
risk_amount = allocator.get_risk_per_trade()  # 1.0%
position_size = (account_equity * risk_amount / 100) / 100
print(f"Test 2 - Risk 1.0%: Position size = ${position_size:.2f}")

# Résultat attendu:
# Test 1 - Risk 0.5%: Position size = $50.00
# Test 2 - Risk 1.0%: Position size = $100.00
```

---

## ✅ Test 4: Scoring Thresholds (⭐ CRITIQUE)

**Vérifier que score_execute et score_watch sont DYNAMIQUES**

### Test:
```bash
# Étape 1: Score = 85, score_execute = 80
# Résultat = EXECUTE ✅

# Étape 2: Changer score_execute = 90
# Attendre 10 secondes

# Étape 3: Score = 85 avec même signal
# Résultat = WATCH (pas EXECUTE)
# Car 85 < 90 ✅
```

### Script:
```python
# test_scoring_thresholds.py
from analysis.scoring_engine import ScoringEngine
from config.settings_integration import SettingsIntegration

settings = SettingsIntegration()
engine = ScoringEngine(..., settings)

# Test 1: execute_threshold = 80, score = 85
thresholds = settings.get_scoring_thresholds()
print(f"Test 1 - Thresholds: {thresholds}")  # {'execute': 80, 'watch': 65}
print(f"Score 85 >= 80? → EXECUTE ✅")

# Test 2: Changer execute_threshold = 90
settings.settings['score_execute'] = 90
thresholds = settings.get_scoring_thresholds()
print(f"\nTest 2 - Thresholds: {thresholds}")  # {'execute': 90, 'watch': 65}
print(f"Score 85 >= 90? → WATCH ✅")
```

---

## ✅ Test 5: Behaviour Shields (Contrôle Individuel)

**Vérifier que chaque shield peut être désactivé indépendamment**

### Test stop_hunt Shield:
```python
# test_behaviour_shields.py
from execution.behaviour_shield import BehaviourShield
from config.settings_integration import SettingsIntegration

settings = SettingsIntegration()
shield = BehaviourShield(..., settings)

# Test 1: stop_hunt activé
is_enabled = settings.is_shield_enabled('stop_hunt')
print(f"Test 1 - stop_hunt enabled: {is_enabled}")

signal = "STOP_HUNT_PATTERN"
# Trade doit être REJETÉ

# Test 2: Désactiver stop_hunt
settings.settings['behaviour_shield']['stop_hunt'] = False

is_enabled = settings.is_shield_enabled('stop_hunt')
print(f"Test 2 - stop_hunt enabled: {is_enabled}")

# Même signal = ACCEPTÉ maintenant
```

---

## ✅ Test 6: Time Filters (Dépendance Temporelle)

**Vérifier que friday_pm et monday_am changent le comportement**

### Test:
```python
# test_time_filters.py
from execution.order_manager import OrderManager
from config.settings_integration import SettingsIntegration
from datetime import datetime, timezone

settings = SettingsIntegration()
manager = OrderManager(..., settings)

# Test 1: Vendredi 15h00 UTC, friday_pm = true
# Simul: can_trade_friday_pm() = False
# Trade REJETÉ

# Test 2: Désactiver friday_pm
settings.settings['time_filters']['friday_pm'] = False
# can_trade_friday_pm() = True
# Trade ACCEPTÉ
```

---

## ✅ Test 7: Killswitches (9 Toggles)

**Vérifier que KS1-KS9 peuvent être activés/désactivés**

### Test:
```python
# Vérifier que les killswitches agissent
# disabled_ks = ["KS1", "KS2"]  → KS1 et KS2 INACTIFS

# Lancer le bot
# Vérifier dans logs:
# "Killswitch KS1: DISABLED"
# "Killswitch KS2: DISABLED"
# "Killswitch KS3: ACTIVE"

# Changer:
# disabled_ks = ["KS1"]  → KS2 maintenant ACTIF

# Attendre 10 secondes
# Logs doivent montrer: "Killswitch KS2: ACTIVE"
```

---

## 🧪 Plan de Test Complet (Étapes)

### Phase 1: Vérification Basique (15min)
1. Démarrer bot
2. Vérifier "Settings reloaded" dans logs toutes les 10s
3. Modifier 1 paramètre (risk_per_trade: 0.5 → 1.0)
4. ✅ Vérifier changement appliqué au prochain cycle

### Phase 2: Détecteurs (30min)
1. Désactiver FVG: `"ICT:fvg": false`
2. ✅ Attendre 10s, vérifier pas de FVG output
3. Réactiver FVG: `"ICT:fvg": true`
4. ✅ Attendre 10s, vérifier FVG output revient

### Phase 3: Scoring (20min)
1. Set score_execute = 80
2. Signal score = 85 → doit être EXECUTE
3. Set score_execute = 90
4. ✅ Même signal = WATCH (85 < 90)

### Phase 4: Risk (20min)
1. Set risk_per_trade = 0.5
2. Créer trade, vérifier taille = 0.5% du compte
3. Set risk_per_trade = 1.0
4. ✅ Suivant trade = 1.0% du compte

### Phase 5: Intégration (15min)
1. Changer 5 paramètres aléatoires
2. Chaque 10s, vérifier changements appliqués
3. ✅ Teste le reload cycle complet

---

## 📊 Résumé Test

| Test | Quoi | Attendu | Status |
|------|------|---------|--------|
| 1 | Reload 10s | Logs "Settings reloaded" | ⏳ |
| 2 | FVG Toggle | FVG off = {}, FVG on = results | ⏳ |
| 3 | Risk Change | 0.5→1.0 double order size | ⏳ |
| 4 | Score Threshold | 85 < 90 = WATCH | ⏳ |
| 5 | Shields | Chaque shield toggle fonctionne | ⏳ |
| 6 | Time Filters | friday_pm bloque trade | ⏳ |
| 7 | Killswitches | KS toggle visible | ⏳ |
| **Total** | **105 params** | **Tous appliqués** | ⏳ |

**Durée Totale**: ~2 heures

---

## 🔍 Comment Vérifier dans les Logs

Ajouter au `main.py` ou `bot_settings.py`:

```python
# Afficher les paramètres actuels toutes les 30s
def log_current_settings():
    settings = SettingsIntegration()
    print(f"\n{'='*60}")
    print(f"⚙️  PARAMÈTRES ACTUELS")
    print(f"{'='*60}")
    print(f"Risk per trade: {settings.get_risk_per_trade()}%")
    print(f"Score execute: {settings.get_scoring_thresholds()['execute']}")
    print(f"FVG active: {settings.is_detector_active('fvg')}")
    print(f"stop_hunt shield: {settings.is_shield_enabled('stop_hunt')}")
    print(f"{'='*60}\n")
```

---

## ✅ Succès = Tous les paramètres appliqués SANS redémarrage

Une fois ces tests passent, les 105 paramètres fonctionnent correctement!
