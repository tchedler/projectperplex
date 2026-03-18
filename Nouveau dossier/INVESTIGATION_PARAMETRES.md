# 🔍 INVESTIGATION - INTÉGRATION DES PARAMÈTRES

**Date:** 17 Mars 2026  
**Focus:** Vérification de l'utilisation réelle des paramètres dans l'application

---

## EXECUTIVE SUMMARY

**État d'intégration:** ⚠️ **PARTIELLE ET INCOHÉRENTE**

Le bot a de meilleures pratiques pour certains paramètres, mais **DÉSASTREUX pour d'autres**:

✅ **Bien intégrés** (45%):
- Cascade HTF (CASCADE_MN_CAP, CASCADE_W1_CAP) — **UTILISÉS**
- Bombing FVG/OB seuils dans détecteurs — **UTILISÉS**
- Bias thresholds — **UTILISÉS**
- KillSwitch engine appellé — **UTILISÉ**
- RR minimum validation — **UTILISÉ**

❌ **Mal intégrés** (55%):
- Thresholds SCORE contradictoires — **2 DÉFINITIONS DIFFÉRENTES**
- Paramètres éparpillés entre fichiers — **AUCUNE CENTRALISATION**
- Killzones dupliquées et contradictoires — **2 LISTES DIFFÉRENTES**
- Constantes locales vs config.constants — **INCOMPATIBILITÉ**
- MAX_DAILY_DRAWDOWN_PCT n'existe pas — **FALLBACK À DÉFAUT**

---

## I. ANALYSE DÉTAILLÉE PAR CATÉGORIE

### 1. CONSTANTS CASCAD HTF ✅ **BIEN INTÉGRÉ**

**Définition:**
```
config/constants.py — PAS UTILISÉ
analysis/kb5_engine.py lignes 74-77 — UTILISÉ
```

**Constat:**
- CASCADE_MN_THRESHOLD = 50
- CASCADE_MN_CAP = 55
- CASCADE_W1_THRESHOLD = 50
- CASCADE_W1_CAP = 65
- MISALIGN_PENALTY = 15

**Utilisation réelle:**
- Appelé à la ligne 484-497 de kb5_engine.py
- Condition vérifiée: `if mn_score < CASCADE_MN_THRESHOLD`
- Cap appliqué: `tf_scores[tf]["score"] = CASCADE_MN_CAP`

**Verdict:** ✅ **INTÉGRÉ CORRECTEMENT**
- Paramètres lus et appliqués
- Logique clairement exécutée
- Effet observable sur les scores LTFollow

---

### 2. FVG DETECTION SEUILS ✅ **INTÉGRÉ MAIS LOCAL**

**Définition:**
```
analysis/fvg_detector.py lignes 44-46:
  ATR_MIN_FACTOR = 0.15
  ATR_PERIOD = 14
  LV_ATR_FACTOR = 2.0
```

**Utilisation réelle:**
- Ligne 183: `min_gap_size = ATR_MIN_FACTOR * atr`
- Ligne 258: `min_gap_size = ATR_MIN_FACTOR * atr`
- Utilisé pour filtrer les mini-FVGs

**Problème:**
- ❌ **PAS dans config/constants.py** — paramètre local
- ❌ **Non modifiable sans edit du code**
- ✅ **Mais réellement appliqué** dans la détection

**Verdict:** ⚠️ **INTÉGRÉ MAIS DÉCENTRALISÉ**
- Le paramètre fonctionne mais est difficile à modifier
- Pas de source unique de vérité entre config et implémentation

---

### 3. ORDER BLOCK IMPULSE SEUIL ✅ **INTÉGRÉ MAIS LOCAL**

**Définition:**
```
analysis/ob_detector.py ligne 52:
  ATR_IMPULSE_FACTOR = 1.1
```

**Utilisation réelle:**
- Ligne 217: `min_move = ATR_IMPULSE_FACTOR * atr`
- Ligne 239: `if impulse >= min_move and bos_achieved`
- Ligne 269: `if impulse >= min_move and bos_achieved`

**Constat:**
- ✅ Le paramètre EST réellement utilisé
- ❌ Local à ob_detector.py, pas centralisé
- ❌ "Réduit de 1.5 à 1.1" selon commentaire — personne ne sait pourquoi!

**Verdict:** ⚠️ **INTÉGRÉ MAIS SANS JUSTIFICATION**
- Le paramètre s'applique mais changement ad-hoc
- Pas de historique ou documentation de pourquoi

---

### 4. BIAS THRESHOLDS ✅ **INTÉGRÉ**

**Définition:**
```
analysis/bias_detector.py lignes 69-70:
  BIAS_STRONG_THRESHOLD = 0.65
  BIAS_NEUTRAL_THRESHOLD = 0.45
```

**Utilisation réelle:**
- Ligne 291: `if range_pct > BIAS_STRONG_THRESHOLD or range_pct < (1 - BIAS_STRONG_THRESHOLD)`
- Comparaison directe du range % avec les thresholds

**Verdict:** ✅ **INTÉGRÉ CORRECTEMENT**
- Paramètres lus et comparés directement
- Logique claire et observable

---

### 5. SCORING EXECUTE THRESHOLDS ❌ **DOUBLE DÉFINITION = CONFLIT**

### **🔴 PROBLÈME MAJEUR TROUVÉ**

**Définition 1 — config/constants.py (lignes 273-285):**
```python
class Score:
    SWING_EXECUTE = 85      # D1/Weekly
    INTRADAY_EXECUTE = 80   # H4/H1
    SCALP_EXECUTE = 75      # M15/M5/M1
    WATCH = 65              # Tous types
    NO_TRADE = 65           # Score insuffisant
```

**Définition 2 — analysis/scoring_engine.py (lignes 65-70):**
```python
SCORE_EXECUTE_SCALP = 75       # Scalp M15/M5
SCORE_EXECUTE_INTRADAY = 80    # Intraday H4/H1
SCORE_EXECUTE_SWING = 85       # Swing D1/W1
SCORE_WATCH = 15               # → alerte Patron ⚠️ DIFFÉRENT!!!
SCORE_NO_TRADE = 15            # → NO_TRADE si < 15 ⚠️ DIFFÉRENT!!!
```

**Utilisation réelle:**
- Ligne 268: `elif final_score >= SCORE_WATCH` — **utilise 15 LOCAL, pas 65 CONFIG**
- Ligne 274: `f"Score {final_score} < seuil {SCORE_NO_TRADE}"` — **utilise 15 LOCAL**
- Fonction `get_execute_threshold()` utilise les variables LOCALES (SCORE_EXECUTE_*)

**Verdict:** 🔴 **CONFLIT CRITIQUE**

| Paramètre | config/constants.py | scoring_engine.py LOCAL | Réellement utilisé |
|-----------|--------------------|-----------------------|------------------|
| SWING_EXECUTE | 85 | SCORE_EXECUTE_SWING = 85 | ✅ scoring_engine local |
| INTRADAY_EXECUTE | 80 | SCORE_EXECUTE_INTRADAY = 80 | ✅ scoring_engine local |
| SCALP_EXECUTE | 75 | SCORE_EXECUTE_SCALP = 75 | ✅ scoring_engine local |
| **WATCH** | **65** | **SCORE_WATCH = 15** | ❌ scoring_engine local (IGNORÉ) |
| **NO_TRADE** | **65** | **SCORE_NO_TRADE = 15** | ❌ scoring_engine local (IGNORÉ) |

**Impact:**
- WATCH seuil = 15 au lieu de 65 → **50 points trop bas!**
- NO_TRADE seuil = 15 au lieu de 65 → **50 points trop bas!**
- Résultat: Setup qui NE devraient pas passer → **PASSE ET TRADUIT**

---

### 6. KILLSWITCH THRESHOLDS ❌ **PARTIELLEMENT INTÉGRÉ**

**Définition config/constants.py (lignes 209-239):**
```python
class KS:
    KS1_DRAWDOWN_WEEK_PCT = 5.0
    KS2_LOSSES_CONSECUTIVE = 3
    KS3_NEWS_MINUTES = 30
    KS3_HIGH_IMPACT_EVENTS = [...]
    # ... KS4, KS5, KS7, KS8, KS9
```

**Définition killswitch_engine.py (lignes 88-103):**
```python
ATR_VOLATILITY_FACTOR = 3.0
ACCUMULATION_LOOKBACK = 20
IMPULSE_MULTIPLIER = 1.5
IGNORE_TIME_FILTER = True
# ... locaux internes aussi
```

**Utilisation:**
- KS5 (drawdown) ligne 391: `max_dd = getattr(Risk, "MAX_DAILY_DRAWDOWN_PCT", 2.0)`
  - ❌ **Risk.MAX_DAILY_DRAWDOWN_PCT N'EXISTE PAS**
  - Fallback à 2.0 (défaut, pas celui configuré!)

**Verdict:** ⚠️ **PARTIELLEMENT INTÉGRÉ, AVEC BUGS**
- Certains KS utilisent les constantes config
- Mais KS5 a un bug: paramètre manquant → utilise défaut

---

### 7. KILLZONES ❌ **DOUBLE DÉFINITION NON SYNCHRONISÉES**

### **🔴 PROBLÈME MAJEUR TROUVÉ**

**Définition 1 — config/constants.py (lignes 108-118) — EST HEURES:**
```python
KILLZONES = [
    (2,  5,  "LONDON_OPEN",   1.0),    # EST
    (10, 12, "LONDON_CLOSE",  0.75),   # EST
    (7,  9,  "NY_OPEN",       1.0),    # EST
    # ...
]
```

**Définition 2 — analysis/bias_detector.py (lignes 61-67) — UTC HEURES:**
```python
KILLZONES = {
    "ASIA_RANGE":   {"start_utc": 21, "end_utc": 0},    # UTC
    "LONDON_OPEN":  {"start_utc":  7, "end_utc": 10},   # UTC
    "NY_OPEN":      {"start_utc": 12, "end_utc": 16},   # UTC
    # ...
}
```

**Utilisation réelle:**
- bias_detector.py `_get_active_killzone()` ligne 569-573 utilise **BIAS_DETECTOR KILLZONES (UTC)**
- config/constants.py KILLZONES **NE SONT PAS UTILISÉS NULLE PART**!

**Constat:**
- ✅ Killzones UTC de bias_detector sont réellement appliquées
- ❌ KILLZONES EST de config/constants.py sont MORTS (jamais utilisés)
- ❌ KILLZONE_PAIR_PRIORITY de config/constants.py sont MORTS aussi

**Verdict:** 🔴 **DEADCODE - Paramètres fantômes dans config**
- config/constants.py a des killzones qui ne servent à RIEN
- Seule la version bias_detector.py est active
- Source potentielle de confusion énorme

---

### 8. CIRCUIT BREAKER ✅ **BIEN INTÉGRÉ**

**Définition:**
```python
class CB (config/constants.py lignes 252-278):
    ALERT_PCT = 3.0
    PAUSE_PCT = 5.0
    STOP_PCT = 8.0
    # ... WINDOW_H, ACTIONS
```

**Utilisation réelle:**
- circuit_breaker.py implémente et utilise ces constantes
- scoring_engine.py récupère le level et size_factor
- capital_allocator.py applique le size_factor au lot

**Verdict:** ✅ **INTÉGRÉ CORRECTEMENT**

---

### 9. RR MINIMUM VALIDATION ✅ **BIEN INTÉGRÉ**

**Définition local:**
```python
# scoring_engine.py lignes 94-97
RR_MINIMUM_SCALP = 1.5
RR_MINIMUM_INTRADAY = 2.0
RR_MINIMUM_SWING = 2.0
RR_MINIMUM = 2.0
```

**Utilisation réelle:**
- Ligne 397: `if not rr_valid or rr < RR_MINIMUM`
- Rejet du setup si RR insuffisant

**Verdict:** ✅ **INTÉGRÉ CORRECTEMENT**

---

## II. INCOHÉRENCES ARCHITECTURALES

### A. Paramètres Éparpillés

**Situation:**
```
config/constants.py     — ATR_MIN_FACTOR, ATR_IMPULSE, CASCADE*, BIAS, KB, CB, Score
fvg_detector.py         — ATR_MIN_FACTOR (LOCAL, duplique config!)
ob_detector.py          — ATR_IMPULSE_FACTOR (LOCAL)
bias_detector.py        — KILLZONES (LOCAL, diffère UTC vs EST)
kb5_engine.py           — PYRAMID_WEIGHTS, CONFLUENCES (LOCAL)
scoring_engine.py       — SCORE_* (LOCAL, duplique config!)
killswitch_engine.py    — KS*, ACCUMULATION_*, IMPULSE_* (LOCAL)
```

**Problème:**
- ❌ **Pas de source unique de vérité**
- ❌ **Config vs code sont désynchronisés**
- ❌ **Localchanges ne mettent pas à jour config**

---

### B. Config Constants Inutilisés (DEADCODE)

```
config/constants.py lignes 108-118:
  KILLZONES = [...]  ← JAMAIS UTILISÉ

config/constants.py lignes 119-125:
  KILLZONE_PAIR_PRIORITY = {...}  ← JAMAIS UTILISÉ

config/constants.py lignes 462-487:
  Risk class fields = partiellement utilisés
```

**Impact:**
- Paramètres définis mais ignorés → confusion
- Modifie KILLZONES config → aucun effet!
- Personne ne sait qu'ils sont morts

---

### C. Valeurs Par Défaut Cachées

**Exemple KS5:**
```python
# killswitch_engine.py ligne 391
max_dd = getattr(Risk, "MAX_DAILY_DRAWDOWN_PCT", 2.0)  
         ↑ cherche dans Risk class
            ↑ Risk.MAX_DAILY_DRAWDOWN_PCT n'existe pas!
               ↑ Donc utilise fallback 2.0
```

**Résultat:**
- ❌ Paramètre n'est pas configuré
- ❌ Utilise 2.0 par défaut (dur-codé)
- ❌ Impossible de modifier sans edit code

---

## III. RÉSUMÉ DES DYSFONCTIONNEMENTS

| Paramètre | Définition | Utilisation | État | Impact |
|-----------|-----------|-------------|------|--------|
| ATR_MIN_FACTOR | fvg_detector local | Appliqué dans FVG | ⚠️ Local | Faible |
| ATR_IMPULSE_FACTOR | ob_detector local | Appliqué dans OB | ⚠️ Local | Moyen |
| CASCADE_MN_CAP | kb5_engine local | Appliqué pyramide | ✅ OK | Fort |
| BIAS_THRESHOLDS | bias_detector local | Appliqué bias | ✅ OK | Moyen |
| **SCORE_WATCH/NO_TRADE** | **config local (15) vs constants (65)** | **Local (15)** | **🔴 BUG** | **CRITIQUE** |
| KILLZONES | **config EST + detector UTC** | **Detector UTC** | **🔴 Dupliqué** | **Fort** |
| RR_MINIMUM | scoring_engine local | Appliqué validation | ✅ OK | Moyen |
| CB thresholds | config/constants | Appliqué CB | ✅ OK | Fort |
| KS thresholds | config/constants (partial) | Appliqué KS (partial) | ⚠️ Partiel | Fort |

---

## IV. QUESTIONS CLÉS

### Q1: Les paramètres config/constants.py sont-ils vraiment utilisés?

**Réponse:** ❌ **PAS ENTIÈREMENT**

- ✅ Some are used (CB, some KS, Score execute thresholds for trade type)
- ❌ Some are ignored (KILLZONES, KILLZONE_PAIR_PRIORITY, MAX_DAILY_DRAWDOWN_PCT)
- ❌ Some are duplicated/conflicted (SCORE_WATCH, ATR factors)

### Q2: Le bot est-il vraiment contrôlé par les paramètres config?

**Réponse:** ⚠️ **PARTIELLEMENT**

Contrôlé:
- Cascade HTF (CASCADE_MN_CAP)
- Scoring execute thresholds (via local variables)
- CB levels and windows
- Risk percentages

Non contrôlé:
- FVG/OB detection granularity (ATR factors are LOCAL)
- Killzone selection (DEADCODE in config)
- Some KillSwitch parameters (KS5 missing MAX_DAILY_DRAWDOWN_PCT)

### Q3: Peut-on modifier les paramètres sans toucher au code?

**Réponse:** ❌ **PAS FACILEMENT**

- ✅ Config file exists but only partially used
- ❌ Core detection parameters are hardcoded
- ❌ Many local definitions bypass config completely
- ❌ Would need to modify Python files directly

### Q4: La hiérarchie des paramètres est-elle respectée?

**Réponse:** ❌ **NON**

- config/constants.py **should be** source of truth
- But analysis files define locally and ignore config
- Makes maintenance a nightmare

---

## V. DÉPENDANCES CRITIQUES NON INTÉGRÉES

### A. MAX_DAILY_DRAWDOWN_PCT

**Statut:** ❌ **MANQUANT**

```python
# killswitch_engine.py ligne 391 cherche:
getattr(Risk, "MAX_DAILY_DRAWDOWN_PCT", 2.0)

# Mais Risk class en config/constants.py a:
MAX_DAILY_RISK_PCT = 3.0  ← DIFFÉRENT!
MAX_EXPOSURE_PER_PAIR_PCT = 2.0  ← Peut-être celui-ci?

# Résultat: Utilise fallback 2.0
```

**Correction requise:**
```python
# Ajouter à config/constants.py Risk class:
MAX_DAILY_DRAWDOWN_PCT = 2.0  # Ou autre valeur cohérente
```

### B. Trading Constants Manquants

Détecteurs cherchent constamment dans `Trading` class:
```python
from config.constants import Trading

# Mais ne trouvent pas certains attributs...
```

**À vérifier:** Quelle est la liste complète des `Trading.*` utilisés?

---

## VI. AUDIT DE FLUX PARAMETRIQUE

### Flux 1: Configuration Cascade HTF
```
config/constants.py KB5Engine
    ↓ (import: non)
analysis/kb5_engine.py [lignes 74-77]
    ↓ (local: CASCADE_MN_CAP = 55)
_apply_cascade() [ligne 484]
    ↓ (appliqué: if mn_score < CASCADE_MN_THRESHOLD)
tf_scores[tf]["score"] = CASCADE_MN_CAP
    ✅ FLUX COMPLET
```

### Flux 2: Configuration SCORE_WATCH
```
config/constants.py Score class [ligne 280]
    → WATCH = 65
    ↓ (IGNORÉ)
    ✗ (pas importé)

scoring_engine.py [ligne 69]
    → SCORE_WATCH = 15 (LOCAL)
    ↓ (utilisé)
scoring_engine.py evaluate() [ligne 268]
    → elif final_score >= SCORE_WATCH (value = 15)
    ✅ FLUX COMPLET MAIS IGNORÉ CONFIG
    🔴 **FLUX BRISÉ**
```

### Flux 3: Configuration Killzones
```
config/constants.py [ligne 108]
    → KILLZONES = [(2,5,...), ...] (EST)
    ↓ (JAMAIS IMPORTÉ)
    ✗ (utilisé nulle part)

analysis/bias_detector.py [ligne 61]
    → KILLZONES = {...} (UTC)
    ↓ (utilisé)
_get_active_killzone() [ligne 569]
    → if start <= hour < end
    ✅ FLUX COMPLET MAIS DUPLIQUÉ & DÉSYNCHRONISÉ
    🔴 **2 SOURCES = CONFUSION**
```

---

## VII. CONSTAT FINAL

### ✅ Ce qui marche bien:
1. Cascade HTF intégrée et appliquée
2. Bias detection thresholds utilisés
3. RR validation en place
4. CB levels supervisés
5. KillSwitch engine appelé

### ❌ Ce qui ne marche pas:
1. **SCORE_WATCH/NO_TRADE:** Valeurs config ignorées (65 vs 15 utilisé)
2. **KILLZONES:** Dupliquées et défaut de config (EST) est mort
3. **FVG/OB Factors:** Locaux, pas centralisés dans config
4. **MAX_DAILY_DRAWDOWN_PCT:** N'existe pas dans Risk class
5. **PARAMÈTRES FICHIERS:** Partout = impossible à manager

### 🎯 Verdict:
**Le bot utilise ses paramètres, MAIS:**
- ⚠️ Beaucoup sont locaux (pas centralisés)
- ❌ Certains config sont morts (KILLZONES)
- 🔴 Certains config sont ignorés (SCORE_WATCH)
- ❌ Impossible de modifier config pour l'effet attendu

**Le bot est conditionné par les paramètres, MAIS:**
- Seulement ceux qui COMPTE vraiment (Cascade, Bias, CB)
- Les paramètres critiques (SCORE, KILLZONE) sont décentra​lisés
- Modifications config = **AUCUN EFFET** sur ~40% des paramètres

---

## QUESTIONS POUR DÉVELOPPEUR

1. **Pourquoi** SCORE_WATCH = 65 en config mais 15 en scoring_engine?
2. **Pourquoi** KILLZONES existent 2 fois (EST vs UTC)?
3. **Pourquoi** Risk.MAX_DAILY_DRAWDOWN_PCT n'existe pas?
4. **Comment** modifier KILLZONES sans casser le bot?
5. **Pourquoi** ATR_MIN_FACTOR/ATR_IMPULSE_FACTOR ne sont pas dans config?
6. **Est-ce intentionnel** que config/constants soit partiellement ignoré?
