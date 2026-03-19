# 📊 TABLEAU RÉCAPITULATIF D'AUDIT — KB5 PARAMÈTRES

**Généré:** 19 Mars 2026 | **Format:** Vue condensée pour scan rapide

---

## 🎯 STATUT GLOBAL

| Métrique | Valeur | Sévérité |
|----------|--------|----------|
| **Total parametres** | ~105 | - |
| **Définis en UI** | 105 | ✅ |
| **Synchronisés vers settings** | ~100 | ✅ |
| **Réellement UTILISÉS** | ~12-15 | ⚠️ |
| **Complètement IGNORÉS** | ~56 | 🔴 |
| **Partiellement utilisés (via constants)** | ~30 | ⚠️ |

---

## 🟢 PARAMÈTRES FONCTIONNELS (Confirmés utilisés)

```
✅ op_mode               → Détermine PAPER/SEMI_AUTO/FULL_AUTO
✅ active_pairs         → Paires à scanner  
✅ disabled_ks          → Killswitches à désactiver
✅ require_killzone     → Force KS4 (Killzone ICT)
✅ require_erl          → Force ERL sweep confirmation
✅ news_filter          → Bloque trades avant news (KS3)
✅ htf_bias             → Cascades biais HTF
✅ llm_provider         → Choix Gemini/Grok
✅ llm_api_key          → Clé API IA
✅ cot                  → Bonus COT saisonnalité
✅ profile              → Charge un preset (mais pas détails)
```

**Total: ~11 paramètres fonctionnels** (10.5% de 105)

---

## 🟡 PARAMÈTRES PARTIELLEMENT UTILISÉS (via Constants hardcodées, pas Settings)

```
⚠️ risk_per_trade       → Via Risk.DEFAULT_RISK_PCT = constant 1.0%
⚠️ max_dd_day_pct       → Via Risk.MAX_DAILY_DRAWDOWN_PCT = constant
⚠️ max_dd_week_pct      → Via constant hardcodée
⚠️ rr_min               → Via RR_MINIMUM constant = 2.0x hardcodée √
⚠️ rr_target            → JAMAIS utilisé
⚠️ score_execute        → Via SCORE_EXECUTE constant = 75 hardcodée
⚠️ score_watch          → Via SCORE_WATCH constant = 15 hardcodée
⚠️ use_partial_tp       → JAMAIS appliqué (TP = 50% toujours)
⚠️ require_mss          → Chargé mais application incertaine
⚠️ require_choch        → Chargé mais application incertaine
```

**Total: ~10 paramètres partiels** (9.5% de 105)

---

## 🔴 PARAMÈTRES COMPLÈTEMENT IGNORÉS (56+ paramètres = 53% du total)

### ICT Core Concepts (17 = 16%)
```
❌ principles_enabled[ICT:fvg]              → Toujours scanné
❌ principles_enabled[ICT:order_blocks]     → Toujours scanné  
❌ principles_enabled[ICT:liquidity]        → Toujours scanné
❌ principles_enabled[ICT:mss]              → Toujours scanné
❌ principles_enabled[ICT:choch]            → Toujours scanné
❌ principles_enabled[ICT:smt]              → Toujours scanné
❌ principles_enabled[ICT:bos]              → Toujours scanné
❌ principles_enabled[ICT:amd]              → Toujours scanné
❌ principles_enabled[ICT:silver_bullet]    → Toujours scanné
❌ principles_enabled[ICT:macros_ict]       → Toujours scanné
❌ principles_enabled[ICT:midnight_open]    → Toujours scanné
❌ principles_enabled[ICT:irl]              → Toujours scanné
❌ principles_enabled[ICT:pd_zone]          → Toujours scanné
❌ principles_enabled[ICT:ote]              → Toujours scanné
❌ principles_enabled[ICT:cbdr]             → Toujours scanné
❌ principles_enabled[ICT:cisd]             → Toujours scanné
❌ principles_enabled[ICT:killzone]         → Voir require_killzone séparé
```

### SMC Concepts (8 = 7.6%)
```
❌ principles_enabled[SMC:bos]              → Toujours scanné
❌ principles_enabled[SMC:choch_smc]        → Toujours scanné
❌ principles_enabled[SMC:inducement]       → Toujours scanné
❌ principles_enabled[SMC:ob_smc]           → Toujours scanné
❌ principles_enabled[SMC:fvg_smc]          → Toujours scanné
❌ principles_enabled[SMC:equal_hl]         → Toujours scanné
❌ principles_enabled[SMC:premium_discount] → Toujours scanné
❌ principles_enabled[SMC:bpr]              → Toujours scanné
```

### Price Action Concepts (6 = 5.7%)
```
❌ principles_enabled[PA:engulfing]         → Toujours scanné
❌ principles_enabled[PA:trendlines]        → Toujours scanné
❌ principles_enabled[PA:round_numbers]     → Toujours scanné
❌ principles_enabled[PA:pin_bar]           → Toujours scanné
❌ principles_enabled[PA:inside_bar]        → Toujours scanné
❌ principles_enabled[PA:sr_levels]         → Toujours scanné
```

### Sessions & Timing (8 = 7.6%)
```
❌ sessions_actives[session_london]         → TOUJOURS active
❌ sessions_actives[session_ny]             → TOUJOURS active
❌ sessions_actives[session_asia]           → TOUJOURS active
❌ sessions_actives[overlap_lnny]           → TOUJOURS active
❌ sessions_actives[sb_london]              → TOUJOURS active
❌ sessions_actives[sb_am]                  → TOUJOURS active
❌ sessions_actives[sb_pm]                  → TOUJOURS active
❌ sessions_actives (dict principal)        → JAMAIS contrôlé
```

### Behaviour Shield (8 = 7.6%)
```
❌ behaviour_shield[stop_hunt]              → TOUJOURS actif (BS1)
❌ behaviour_shield[fake_breakout]          → TOUJOURS actif (BS2)
❌ behaviour_shield[liquidity_grab]         → TOUJOURS actif (BS3)
❌ behaviour_shield[news_spike]             → TOUJOURS actif (BS4)
❌ behaviour_shield[overextension]          → TOUJOURS actif (BS5)
❌ behaviour_shield[revenge_trade]          → TOUJOURS actif (BS6)
❌ behaviour_shield[duplicate]              → TOUJOURS actif (BS7)
❌ behaviour_shield[staleness]              → TOUJOURS actif (BS8)
```

### Time Filters (3 = 2.8%)
```
❌ time_filters[friday_pm]                  → TOUJOURS appliqué
❌ time_filters[monday_morning]             → TOUJOURS appliqué
❌ time_filters[before_news]                → TOUJOURS appliqué
```

### Limites & Contraintes (6 = 5.7%)
```
❌ max_trades_day                           → PAS DE LIMITE
❌ rr_target                                → JAMAIS UTILISÉ
❌ (redondants/dupliqués)
```

---

## 📈 DISTRIBUTION PAR ÉTAT

```
Graphique de statut:

✅ UTILISÉS (11)          : ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 10.5%
⚠️  PARTIELS (10)         : ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 9.5%
❌ IGNORÉS (56)           : ██████████████████████░░░░░░░░░░░░░░░░░░░░░░░░ 53%
❓ INCERTAINS/REDONDANTS : ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 26.6%
                           ├─────────────────────────────────────────────
                           Total = 105 paramètres
```

---

## 🚨 IMPACT UTILISATEUR

### Ce que l'utilisateur ATTEND:
```
"Je configure le bot avec mes paramètres..."
         ↓
"Je clique SAUVEGARDER"
         ↓
"Le bot re-démarre (ou recharge)"
         ↓
"Les paramètres que j'ai choisis s'appliquent"
```

### Ce qui RÉELLEMENT se passe:
```
"Je configure le bot avec mes paramètres..."
         ↓
"Je clique SAUVEGARDER"
         ↓
"Le bot re-démarre (ou recharge)"
         ↓
"Les paramètres sont synchronisés vers user_settings.json ✅"
         ↓
"MAIS... Les modules du bot ne les lisent jamais ❌"
         ↓
"Le bot fonctionne selon sa config hardcodée par défaut"
         ↓
"Utilisateur frustré: 'Pourquoi mes paramètres ne fonctionnent pas?!'"
```

---

## 🔧 ARCHITECTURE DU PROBLÈME

```
┌───────────────────────────────────┐
│  Interface Streamlit (UI)         │  ✅ Fonctionne parfaitement
│  ├─ bot_settings.py               │
│  └─ render_bot_settings()          │
└──────────────┬────────────────────┘
               │ Sauvegarde
               ↓
┌───────────────────────────────────┐
│  Persistence (Fichiers JSON)      │  ✅ Fonctionne parfaitement
│  ├─ bot_config.json               │
│  └─ user_settings.json            │
└──────────────┬────────────────────┘
               │ Lecture au démarrage
               ↓
┌───────────────────────────────────┐
│  SettingsManager                  │  ✅ Fonctionne parfaitement
│  ├─ sync_from_bot_config()        │
│  ├─ is_principle_active()         │
│  └─ get("behaviour_shield")       │
└───────────────────┬───────────────┘
                    │ ❌ JAMAIS UTILISÉ
                    │
        ┌───────────┴─────────────────────────┐
        │                                     │
        ↓                                     ↓
    OUBLIÉ                              PARTIELLEMENT
   (56 param)                            (10 param)
    
    ├─ FVGDetector.scan()           ├─ ScoringEngine (constants)
    ├─ OBDetector.scan()            ├─ CapitalAllocator (constants)
    ├─ SMTDetector.scan()           └─ Autres (via Risk.*)
    ├─ KB5Engine.analyze()
    ├─ BehaviourShield.validate()
    └─ OrderManager.send()
```

---

## 📋 TABLE DE VÉRITÉ (Exemple d'un seul concept)

**Exemple: `principles_enabled['ICT:fvg']` (FVG Detector)**

| Étape | État | Evidence |
|-------|------|----------|
| **1. Défini en UI** | ✅ Existe | bot_settings.py ligne 85 |
| **2. Checkbox cochée → Décochée** | ✅ Possible | Utilisateur peut modifier |
| **3. Sauvegardé JSON** | ✅ Sauvegardé | user_settings.json: `"ICT:fvg": false` |
| **4. Chargé SettingsManager** | ✅ Chargé | SettingsManager.principles_enabled['ICT:fvg'] = false |
| **5. Passé aux modules** | ❌ **NON** | FVGDetector reçoit UNIQUEMENT data_store, PAS settings |
| **6. Vérifié avant utilisation** | ❌ **NON** | FVGDetector.scan_pair() scan TOUJOURS indépendamment |
| **7. Impact observé** | ❌ **NON** | FVG TOUJOURS détecté, peu importe le paramètre |

**Résultat:** L'utilisateur désactive FVG, mais le bot détecte et scoring les FVG quand même.

---

## 💡 SOLUTIONS RAPIDES (Par urgence)

### 1️⃣ URGENT — Injection Dépendances (2-4h)
Passer `SettingsManager` à TOUS les modules au démarrage dans main.py:

```python
# AVANT:
fvg_detector = FVGDetector(data_store=ds)

# APRÈS:
fvg_detector = FVGDetector(data_store=ds, settings=settings_manager)
```

### 2️⃣ HIGH — Lectures de Settings (4-8h)
Ajouter vérifications dans chaque module:

```python
# Dans FVGDetector.scan_pair():
if not self._settings.is_principle_active("ICT", "fvg"):
    return {}  # Aucun FVG si principe désactivé

# Dans ScoringEngine():
score_threshold = self._settings.get("score_execute", 75)

# Dans BehaviourShield.validate():
shields = self._settings.get("behaviour_shield")
if not shields["stop_hunt"]:
    skip BS1 check
```

### 3️⃣ MEDIUM — Reload Runtime (8-16h)
Permettre reload sans redémarrage:

```python
# Watchdog: re-read settings chaque 5-10 sec
# OU: Événement de notification quando settings changent
```

### 4️⃣ LOW — Tests Utilisateur (2-4h)
Créer test suite pour valider that settings appliquent:

```
Teste 1: Désactive FVG → Scan ne trouvez PAS de FVG
Teste 2: Change rr_min → OrderManager rejette RR < threshold
Teste 3: Active/désactive KS → Killswitch respecte state
```

---

## ⏱️ ESTIMATION CORRECTION TOTALE

- **Injection dépendances:** 2-4 heures
- **Lectures settings:** 4-8 heures  
- **Tests:** 4-6 heures
- **Intégration & déploiement:** 2-4 heures

**Total:** 12-22 heures (1-3 jours de dev senior)

---

## 🎓 CONCLUSION

**Le bot a une "façade de paramètres" mais une "architecture sans paramètres".**

Les 105 paramètres UI sont cosmétiques. Le vrai contrôle du bot réside entièrement dans les constantes hardcodées du code source.

**Sévérité:** 🔴 **CRITIQUE**  
**Impactabilité:** Utilisateurs ne peuvent pas configurer le bot  
**Complexité de fix:** Moyen (architecture bien structurée, "juste" code manquant)

---

_Document généré automatiquement — 19 Mars 2026_
