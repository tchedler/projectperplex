# 📊 TABLEAU SYNTHÈSE: STATUT DE CHAQUE PARAMÈTRE

## 🟢 PARAMÈTRES QUI FONCTIONNENT (9 paramètres)

| # | Paramètre | Stocké | Chargé | Utilisé | Fichier(s) | État |
|---|-----------|--------|--------|---------|-----------|------|
| 1 | `op_mode` (PAPER/SEMI/FULL) | ✅ JSON | ✅ SM | ✅ OUI | order_manager.py | ✅ **FONCTIONNE** |
| 2 | `active_pairs` | ✅ JSON | ✅ SM | ✅ OUI | main.py, reconnect_manager.py | ✅ **FONCTIONNE** |
| 3 | `disabled_ks` (KS à désactiver) | ✅ JSON | ✅ SM | ✅ OUI | killswitch_engine.py L209 | ✅ **FONCTIONNE** |
| 4 | `require_killzone` | ✅ JSON | ✅ SM | ✅ OUI | killswitch_engine.py KS4 | ✅ **FONCTIONNE** |
| 5 | `require_erl` | ✅ JSON | ✅ SM | ✅ OUI | boolean_erl.py | ✅ **FONCTIONNE** |
| 6 | `news_filter` | ✅ JSON | ✅ SM | ✅ OUI | killswitch_engine.py KS3 | ✅ **FONCTIONNE** |
| 7 | `htf_bias` | ✅ JSON | ✅ SM | ✅ OUI | bias_detector.py | ✅ **FONCTIONNE** |
| 8 | `cot` (COT Saisonnalité) | ✅ JSON | ✅ SM | ✅ OUI | kb5_engine.py | ✅ **FONCTIONNE** |
| 9 | `llm_provider` | ✅ JSON | ✅ SM | ✅ OUI | llm_narrative.py | ✅ **FONCTIONNE** |

**Total: 9/105 = 8.6%**

---

## 🟠 PARAMÈTRES PARTIELS (12 paramètres via CONSTANTS)

Ces paramètres **sont sauvegardés** mais **lus depuis des constantes hardcodées**, pas depuis les settings.
Pour les changer, il faut **modifier le code source** et redéployer.

| # | Paramètre | Stocké | Chargé | Utilisé (via Constant) | Constante | Fichier | État |
|---|-----------|--------|--------|--------|-----------|---------|------|
| 1 | `risk_per_trade` | ✅ | ✅ | ⚠️ CONSTANT | `Risk.DEFAULT_RISK_PCT = 1.0` | capital_allocator.py L295 | ⚠️ **PARTIELLEMENT** |
| 2 | `max_dd_day_pct` | ✅ | ✅ | ⚠️ CONSTANT | `Risk.MAX_DAILY_DRAWDOWN_PCT = 2.0` | killswitch_engine.py KS5 | ⚠️ **PARTIELLEMENT** |
| 3 | `max_dd_week_pct` | ✅ | ✅ | ⚠️ CONSTANT | `Risk.MAX_WEEKLY_DRAWDOWN_PCT = 5.0` | killswitch_engine.py | ⚠️ **PARTIELLEMENT** |
| 4 | `rr_min` | ✅ | ✅ | ⚠️ CONSTANT | `RR_MINIMUM = 2.0` | scoring_engine.py L398 | ⚠️ **PARTIELLEMENT** |
| 5 | `rr_target` | ✅ | ✅ | ⚠️ CONSTANT | `RR_TARGET = 3.0` | capital_allocator.py | ⚠️ **PARTIELLEMENT** |
| 6 | `score_execute` | ✅ | ✅ | ⚠️ CONSTANT | `SCORE_EXECUTE = 75` | scoring_engine.py L82 | ⚠️ **PARTIELLEMENT** |
| 7 | `score_watch` | ✅ | ✅ | ⚠️ CONSTANT | `SCORE_WATCH = 15` | scoring_engine.py L83 | ⚠️ **PARTIELLEMENT** |
| 8 | `max_trades_day` | ✅ | ✅ | ⚠️ CONSTANT | `Max.DAILY_TRADES = 5` | No implementation | ⚠️ **PARTIELLEMENT** |
| 9 | `require_mss` | ✅ | ✅ | ⚠️ Chargé seulement | N/A | kb5_engine.py | ⚠️ **PARTIELLEMENT** |
| 10 | `require_choch` | ✅ | ✅ | ⚠️ Chargé seulement | N/A | kb5_engine.py | ⚠️ **PARTIELLEMENT** |
| 11 | `use_partial_tp` | ✅ | ✅ | ⚠️ CONSTANT | `PARTIAL_TP_PCTS = [0.5, 1.0]` | capital_allocator.py | ⚠️ **PARTIELLEMENT** |
| 12 | `llm_api_key` | ✅ | ✅ | ⚠️ Utilisé si llm_provider actif | N/A | llm_narrative.py | ⚠️ **PARTIELLEMENT** |

**Total: 12/105 = 11.4%**

---

## 🔴 PARAMÈTRES IGNORÉS COMPLÈTEMENT (56+ paramètres)

Définis en UI, sauvegardés en JSON, **mais CHAQUE MOD`ule fait l'inverse de ce qui est requis**.

### A) CONCEPTS ICT CORE (17 paramètres ignorés)

| # | Paramètre | UI | JSON | Chargé | Utilisé? | Estado |
|---|-----------|-----|------|--------|----------|---------|
| 1 | `ICT:fvg` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | FVGDetector scan TOUJOURS |
| 2 | `ICT:order_blocks` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | OBDetector scan TOUJOURS |
| 3 | `ICT:liquidity` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | Sweeps TOUJOURS scannés |
| 4 | `ICT:mss` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | MSS TOUJOURS détecté |
| 5 | `ICT:choch` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | CHoCH TOUJOURS détecté |
| 6 | `ICT:smt` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | SMT TOUJOURS analysé |
| 7 | `ICT:bos` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | BOS TOUJOURS inclus |
| 8 | `ICT:amd` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | AMD TOUJOURS calculé |
| 9 | `ICT:silver_bullet` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS scannés |
| 10 | `ICT:macros_ict` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS appliquées |
| 11 | `ICT:midnight_open` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS utilisé |
| 12 | `ICT:irl` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS calculé |
| 13 | `ICT:pd_zone` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS appliqué |
| 14 | `ICT:ote` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS calculé |
| 15 | `ICT:cbdr` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS considéré |
| 16 | `ICT:cisd` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS scanné |
| 17 | `ICT:killzone` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | (voir require_killzone) |

**Sous-total: 17/105 = 16.2%**

### B) CONCEPTS SMC (8 paramètres ignorés)

| # | Paramètre | UI | JSON | Chargé | Utilisé? | Estado |
|---|-----------|-----|------|--------|----------|---------|
| 1 | `SMC:bos` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | BOS TOUJOURS inclus |
| 2 | `SMC:choch_smc` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS détecté |
| 3 | `SMC:inducement` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS scanné |
| 4 | `SMC:ob_smc` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS analysés |
| 5 | `SMC:fvg_smc` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS inclus |
| 6 | `SMC:equal_hl` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS utilisés |
| 7 | `SMC:premium_discount` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS appliqué |
| 8 | `SMC:bpr` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS calculé |

**Sous-total: 8/105 = 7.6%**

### C) CONCEPTS PRICE ACTION (6 paramètres ignorés)

| # | Paramètre | UI | JSON | Chargé | Utilisé? | Estado |
|---|-----------|-----|------|--------|----------|---------|
| 1 | `PA:engulfing` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS scanné |
| 2 | `PA:trendlines` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS utilisées |
| 3 | `PA:round_numbers` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS appliquées |
| 4 | `PA:pin_bar` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS détectés |
| 5 | `PA:inside_bar` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS détectés |
| 6 | `PA:sr_levels` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS utilisés |

**Sous-total: 6/105 = 5.7%**

### D) SESSIONS & TEMPORALITÉ (8 paramètres ignorés)

| # | Paramètre | UI | JSON | Chargé | Utilisé? | Estado |
|---|-----------|-----|------|--------|----------|---------|
| 1 | `sessions_actives` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUTES scannées |
| 2 | `session_london` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS active |
| 3 | `session_ny` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS active |
| 4 | `session_asia` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS active |
| 5 | `overlap_lnny` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS considéré |
| 6 | `sb_london` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |
| 7 | `sb_am` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |
| 8 | `sb_pm` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |

**Sous-total: 8/105 = 7.6%**

### E) BEHAVIOUR SHIELD (8 paramètres ignorés)

| # | Paramètre | UI | JSON | Chargé | Utilisé? | Estado |
|---|-----------|-----|------|--------|----------|---------|
| 1 | `behaviour_shield[stop_hunt]` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |
| 2 | `behaviour_shield[fake_breakout]` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |
| 3 | `behaviour_shield[liquidity_grab]` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |
| 4 | `behaviour_shield[news_spike]` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |
| 5 | `behaviour_shield[overextension]` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |
| 6 | `behaviour_shield[revenge_trade]` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |
| 7 | `behaviour_shield[duplicate]` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |
| 8 | `behaviour_shield[staleness]` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |

**Sous-total: 8/105 = 7.6%**

### F) TIME FILTERS (3 paramètres ignorés)

| # | Paramètre | UI | JSON | Chargé | Utilisé? | Estado |
|---|-----------|-----|------|--------|----------|---------|
| 1 | `time_filters[friday_pm]` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |
| 2 | `time_filters[monday_morning]` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |
| 3 | `time_filters[before_news]` | ✅ | ✅ | ✅ | ❌ **JAMAIS** | TOUJOURS actif |

**Sous-total: 3/105 = 2.9%**

### G) AUTRES NON-UTILISÉS (2 paramètres)

| # | Paramètre | UI | JSON | Chargé | Utilisé? | Estado |
|---|-----------|-----|------|--------|----------|---------|
| 1 | `profile` | ✅ | ✅ | ⚠️ Partiellement | ❌ À peine | Détection du profil seulement |
| 2 | `schools_enabled` | ✅ | ✅ | ✅ | ❌ JAMAIS | Concepts TOUJOURS tous scannés |

**Sous-total: 2/105 = 1.9%**

**GRAND TOTAL IGNORÉS: 56/105 = 53.3%**

---

## 📊 GRAPHIQUE DE DISTRIBUTION

```
Paramètres du Bot KB5:

UTILISÉS:                    Concepts:
  ━━━━━━━━━━━━━━━━━━━━━━    ⛏️ ICT Core ★★★★★★★★★★★★★★★★★ (17 ignorés)
  9/105 (8.6%)              ⛏️ SMC        ★★★★★★★★ (8 ignorés)
                             ⛏️ PA         ★★★★★★ (6 ignorés)
VIA CONSTANTS:              Sessions:
  ━━━━━━━━━━━━━━━━━━━━━━    ⛏️ Temporalité ★★★★★★★★ (8 ignorés)
  12/105 (11.4%)            Filters:
                             ⛏️ Behaviour  ★★★★★★★★ (8 ignorés)
IGNORÉS:                     ⛏️ Time       ★★★ (3 ignorés)
  ━━━━━━━━━━━━━━━━━━━━━━    Autres:
  56/105 (53.3%)            ⛏️ Misc       ★★ (2 ignorés)
```

---

## 🎯 Pour l'Utilisateur

### Avant Correction ❌
```
Configuration UI          JSON Storage        Runtime Bot
────────────────────────────────────────────────────────────
Set FVG = OFF ─────────→ ✅ Sauvegardé ─────→ ❌ Bot scan TOUJOURS
Set Risk = 0.5% ───────→ ✅ Sauvegardé ─────→ ❌ Bot use 1%
Set Sessions = London ──→ ✅ Sauvegardé ─────→ ❌ Bot tune TOUTES
```

### Après Correction ✅
```
Configuration UI          JSON Storage        Runtime Bot
────────────────────────────────────────────────────────────
Set FVG = OFF ─────────→ ✅ Sauvegardé ─────→ ✅ Bot skip FVG
Set Risk = 0.5% ───────→ ✅ Sauvegardé ─────→ ✅ Bot use 0.5%
Set Sessions = London ──→ ✅ Sauvegardé ─────→ ✅ Bot tune LONDON seul
```

---

_Tableau généré le 19 Mars 2026_
