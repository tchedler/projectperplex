# 🔧 PLAN D'ACTION CORRECTION

## Situation Actuelle (Issues Trouvées)

### 🚨 BUG CRITIQUE ARCHITECTURE:
**Les ~105 paramètres UI sont IGNORÉS au runtime**

#### Chaîne Fonctionnelle (Correcte):
```
UI → JSON → SettingsManager ✅
```

#### Chaîne Brisée (Modules):
```
SettingsManager → ??? → Détecteurs/Moteurs/Exécution ❌
```

**Cause racine:** Les modules n'ont PAS SettingsManager en dépendance, et ne recharges JAMAIS les settings.

---

## Étapes de Correction (Priorisé)

### ÉTAPE 1: AUDIT CODE (✅ TERMINÉ)
- [x] Identifier tous les paramètres définis
- [x] Vérifier où ils sont utilisés/ignorés
- [x] Documenter l'architecture brisée
- [x] Créer matrice d'audit complète

**Documents créés:**
- `AUDIT_PARAMETRES_COMPLET.md` — 600+ lignes d'analyse
- `AUDIT_TABLEAU_RESUME.md` — Vue condensée
- `AUDIT_PARAMETRES_TABLEAU.md` — Matrice des 70+ paramètres

---

### ÉTAPE 2: INJECTION DÉPENDANCES (1-2h = Priorité 1)

**Objectif:** Passer SettingsManager à TOUS les modules

#### Modules à modifier (dans main.py):

```python
# AVANT (actuel):
fvg_detector = FVGDetector(data_store=ds)
ob_detector  = OBDetector(data_store=ds)
smt_detector = SMTDetector(data_store=ds)
bias_detector = BiasDetector(data_store=ds, fvg_detector=fvg_detector, ob_detector=ob_detector)
liquidity_detector = LiquidityDetector(data_store=ds)
amd_detector = AMDDetector(data_store=ds, bias_detector=bias_detector, liquidity_detector=liquidity_detector)
pa_detector = PADetector(data_store=ds)
mss_detector = MSSDetector(data_store=ds)
choch_detector = CHoCHDetector(data_store=ds)
irl_detector = IRLDetector(data_store=ds, fvg_detector=fvg_detector)

kb5_engine = KB5Engine(data_store=ds, fvg_detector=fvg_detector, ...)
circuit_breaker = CircuitBreaker(data_store=ds, ...)
killswitch_engine = KillSwitchEngine(data_store=ds, tick_receiver=tick_receiver, ...)
scoring_engine = ScoringEngine(data_store=ds, kb5_engine=kb5_engine, ...)

capital_allocator = CapitalAllocator(data_store=ds, mt5_connector=connector, circuit_breaker=circuit_breaker)
behaviour_shield = BehaviourShield(data_store=ds, fvg_detector=fvg_detector, ...)
order_manager = OrderManager(data_store=ds, mt5_connector=connector, ...)
```

#### APRÈS (correction):
```python
# Créer une instance SettingsManager au démarrage
settings_manager = SettingsManager()

# Passer à TOUS les modules analyse
fvg_detector = FVGDetector(data_store=ds, settings=settings_manager)
ob_detector  = OBDetector(data_store=ds, settings=settings_manager)
smt_detector = SMTDetector(data_store=ds, settings=settings_manager)
bias_detector = BiasDetector(data_store=ds, fvg_detector=fvg_detector, ob_detector=ob_detector, settings=settings_manager)
liquidity_detector = LiquidityDetector(data_store=ds, settings=settings_manager)
amd_detector = AMDDetector(data_store=ds, bias_detector=bias_detector, liquidity_detector=liquidity_detector, settings=settings_manager)
pa_detector = PADetector(data_store=ds, settings=settings_manager)
mss_detector = MSSDetector(data_store=ds, settings=settings_manager)
choch_detector = CHoCHDetector(data_store=ds, settings=settings_manager)
irl_detector = IRLDetector(data_store=ds, fvg_detector=fvg_detector, settings=settings_manager)

# Moteurs
kb5_engine = KB5Engine(data_store=ds, fvg_detector=fvg_detector, ..., settings=settings_manager)
circuit_breaker = CircuitBreaker(data_store=ds, ..., settings=settings_manager)
killswitch_engine = KillSwitchEngine(data_store=ds, tick_receiver=tick_receiver, ..., settings=settings_manager)
scoring_engine = ScoringEngine(data_store=ds, kb5_engine=kb5_engine, ..., settings=settings_manager)

# Exécution
capital_allocator = CapitalAllocator(data_store=ds, mt5_connector=connector, circuit_breaker=circuit_breaker, settings=settings_manager)
behaviour_shield = BehaviourShield(data_store=ds, fvg_detector=fvg_detector, ..., settings=settings_manager)
order_manager = OrderManager(data_store=ds, mt5_connector=connector, ..., settings=settings_manager)
```

**Effort:** 15-30 minutes (juste passer le paramètre)

---

### ÉTAPE 3: LECTURES SETTINGS (2-4h = Priorité 1)

**Objectif:** Vérifier les settings avant chaque utilisation

#### Exemple 1: Détecteur FVG
```python
# Dans FVGDetector.__init__():
def __init__(self, data_store: DataStore, settings: SettingsManager = None):
    self._ds = data_store
    self._settings = settings
    
# Dans FVGDetector.scan_pair():
def scan_pair(self, pair: str) -> dict:
    # ✅ NEW: Vérifier si FVG est activé
    if self._settings and not self._settings.is_principle_active("ICT", "fvg"):
        logger.info(f"FVG désactivé pour {pair} — skipped")
        return {}
    
    # ... scan normal
    results: dict[str, list] = {}
    for tf in Trading.TIMEFRAMES:
        df = self._ds.get_candles(pair, tf)
        if df is None or len(df) < ATR_PERIOD + 3:
            continue
        
        fvg_list = self._detect_fvg(pair, tf, df)  # ✅ Scan si activé
        ...
```

#### Exemple 2: ScoringEngine (Score Threshold)
```python
# Dans ScoringEngine.__init__():
def __init__(self, data_store: DataStore, kb5_engine, killswitch_engine, 
             circuit_breaker, bias_detector, settings: SettingsManager = None):
    self._ds = data_store
    self._kb5 = kb5_engine
    self._ks = killswitch_engine
    self._cb = circuit_breaker
    self._bias = bias_detector
    self._settings = settings

# Dans ScoringEngine._evaluate_scalp():
def _evaluate_scalp(self, scalp_output: dict) -> str:
    score = scalp_output.get("score", 0)
    
    # ✅ NEW: Lire threshold depuis settings (fallback à constant)
    score_execute = self._settings.get("score_execute", 80) if self._settings else 80
    score_watch = self._settings.get("score_watch", 65) if self._settings else 65
    
    if score >= score_execute:
        return "EXECUTE"
    elif score >= score_watch:
        return "WATCH"
    else:
        return "NO_TRADE"
```

#### Exemple 3: Behaviour Shield
```python
# Dans BehaviourShield.__init__():
def __init__(self, data_store: DataStore, fvg_detector, ob_detector,
             bias_detector, order_reader, settings: SettingsManager = None):
    self._ds = data_store
    self._fvg = fvg_detector
    self._ob = ob_detector
    self._bias = bias_detector
    self._orders = order_reader
    self._settings = settings
    
# Dans BehaviourShield.validate():
def validate(self, pair: str, scalp_output: dict, allocation: dict) -> dict:
    # ✅ NEW: Lire behaviour_shield settings
    shields_config = self._settings.get("behaviour_shield", {}) if self._settings else {}
    
    bs1_enabled = shields_config.get("stop_hunt", True)
    bs2_enabled = shields_config.get("fake_breakout", True)
    # ... etc
    
    # Sauter BS1 si désactivé
    if bs1_enabled:
        bs1 = self._check_bs1_stop_hunt(pair, direction, entry)
        if bs1["triggered"]:
            return self._reject("BS1_STOP_HUNT", bs1["reason"], 1)
```

#### Exemple 4: OrderManager (Time Filters)
```python
# Dans OrderManager.__init__():  
def __init__(self, data_store: DataStore, mt5_connector, order_reader,
             capital_allocator, circuit_breaker, settings: SettingsManager = None):
    self._ds = data_store
    self._connector = mt5_connector
    self._reader = order_reader
    self._allocator = capital_allocator
    self._cb = circuit_breaker
    self._settings = settings

# Dans OrderManager.send_order():
def send_order(self, pair: str, scalp_output: dict, allocation: dict) -> dict:
    # ✅ NEW: Vérifier time_filters avant envoi
    time_filters = self._settings.get("time_filters", {}) if self._settings else {}
    
    now = datetime.now(timezone.utc)
    ny_time = now.astimezone(timezone("US/Eastern"))
    
    # Faire: Vendredi après 14h NY
    if time_filters.get("friday_pm"):
        if ny_time.weekday() == 4 and ny_time.hour >= 14:
            logger.warning(f"Time Filter: Vendredi PM bloqué")
            return {"approved": False, "reason": "Vendredi PM"}
    
    # ... check monday_morning, before_news, etc
    
    # ✅ Envoyer ordre si tous filters OK
    # ... normal flow
```

**Effort:** 2-4 heures (pour tous les modules)

---

### ÉTAPE 4: TESTS VALIDATION (2-4h = Priorité 2)

**Objectif:** Vérifier que les settings appliquent réellement

#### Test 1: Concepts Activés/Désactivés
```python
# Test Case: FVG Desactivé
def test_fvg_disabled():
    settings = SettingsManager()
    settings.set_principle("ICT", "fvg", False)
    
    detector = FVGDetector(data_store=ds, settings=settings)
    result = detector.scan_pair("EURUSD")
    
    assert result == {}  # Aucun FVG si désactivé
    
# Test Case: FVG Activé
def test_fvg_enabled():
    settings = SettingsManager()
    settings.set_principle("ICT", "fvg", True)
    
    detector = FVGDetector(data_store=ds, settings=settings)
    result = detector.scan_pair("EURUSD")
    
    assert len(result) > 0  # Détecte FVGs si activé
```

#### Test 2: Thresholds de Score
```python
def test_score_threshold_applied():
    settings = SettingsManager()
    settings.set("score_execute", 85)  # Plus strict
    
    engine = ScoringEngine(data_store=ds, ..., settings=settings)
    
    # Score 82 devrait être WATCH (< 85), pas EXECUTE
    result = engine._evaluate_scalp({"score": 82})
    assert result == "WATCH"
    
    # Score 85+ devrait être EXECUTE
    result = engine._evaluate_scalp({"score": 85})
    assert result == "EXECUTE"
```

#### Test 3: Behaviour Shield Contrôlable
```python
def test_behaviour_shield_toggle():
    settings = SettingsManager()
    
    # BS1 Desactivé
    settings.set("behaviour_shield", {"stop_hunt": False, ...})
    shield = BehaviourShield(data_store=ds, ..., settings=settings)
    result = shield.validate(pair, scalp_output, allocation)
    # BS1 check should be skipped
    assert "BS1" not in result.get("filters_failed", [])
```

**Effort:** 2-4 heures (créer suite de tests)

---

### ÉTAPE 5: RECONFIGURATION RUNTIME (optionnel, Priorité 3)

**Objectif:** Permettre reload sans redémarrag (bonus)

```python
# Dans Supervisor cycle principal:
def cycle_main(self):
    while self._running:
        # ✅ Reload settings chaque cycle (toutes les ~5 sec)
        self._kb5._settings.reload()  # Re-read JSON
        self._scoring._settings.reload()
        self._shield._settings.reload()
        
        # ... analyse normale
        self._analyze_pair("EURUSD")
        ...
        
        time.sleep(5)
```

**Effort:** 30 minutes - 1h (optionnel, nice-to-have)

---

## Priorités de Correction

### 🔴 URGENT (Jour 1)
1. **Injection dépendances** SettingsManager
2. **Lectures settings** dans tous les modules
3. **Tests** validation

Temps: 5-8 heures (1 dev senior)

### 🟡 HIGH (Jour 2)
4. **Reconfiguration runtime** (optionnel)
5. **Documentation** et déploiement

Temps: 2-4 heures

### 🟢 MEDIUM (Post-déploiement)
6. **Monitoring** que paramètres appliquent
7. **User feedback** et ajustements

---

## Impact Estimation Post-Correction

| Aspect | Avant | Après |
|--------|-------|-------|
| Paramètres fonctionnels | 11/105 (10%) | 100+/105 (95%+) |
| Utilisateur peut configurer | ❌ Non | ✅ Oui |
| Respect configuration UI | ❌ 0% | ✅ 100% |
| Effort déploiement | - | 1-2 jours |

---

## Fichiers à Modifier

### Priority 1 (Injection + Lectures)

1. **main.py** — Créer SettingsManager + passer à modules
2. **analysis/fvg_detector.py** — Ajouter settings + check principle_active
3. **analysis/ob_detector.py** — Ajouter settings + check
4. **analysis/smt_detector.py** — Ajouter settings + check
5. **analysis/kb5_engine.py** — Ajouter settings + vérifications cascade
6. **analysis/scoring_engine.py** — Lire score_execute/score_watch depuis settings
7. **analysis/bias_detector.py** — Check HTF bias, PD zone depuis settings
8. **execution/behaviour_shield.py** — Lire behaviour_shield dict depuis settings
9. **execution/order_manager.py** — Lire time_filters depuis settings
10. **execution/capital_allocator.py** — Lire risk_per_trade depuis settings
11. **analysis/killswitch_engine.py** — Lire risk thresholds depuis settings (déjà partiellement fait)

### Priority 2 (Tests)

12. **tests/test_settings_integration.py** (NEW) — Suite tests validation
13. **tests/test_detectors_respects_settings.py** (NEW) — Tests par détecteur

---

## Checklist de Déploiement

- [ ] Branche feature créée: `fix/settings-injection-dpendencies`
- [ ] SettingsManager injecté dans main.py
- [ ] Tous les modules reçoivent SettingsManager
- [ ] Lectures settings implémentées dans chaque module
- [ ] Tests passent (couverture > 90%)
- [ ] Code review approuvé
- [ ] Testé en bot paper trading 24h+
- [ ] Documentation updated
- [ ] Merged vers main
- [ ] Tag version créé
- [ ] Déploiement production

---

## FAQ Post-Correction

**Q: Et les constants dans config/constants.py?**  
A: Garder comme fallback si settings non disponible:
```python
score_threshold = self._settings.get("score_execute") or Score.EXECUTE_DEFAULT
```

**Q: Comment reload settings sans redémarrer?**  
A: Watchdog dans Supervisor qui re-read JSON chaque 5-10 sec (Étape 5)

**Q: Et les paramètres partiels (via constants)?**  
A: Prioritaire après URGENT—ils gagnent à être lus depuis settings aussi.

---

_Document généré 19 Mars 2026 — Copilot Analysis_
