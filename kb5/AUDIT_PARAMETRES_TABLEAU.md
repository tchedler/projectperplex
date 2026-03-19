# ⚡ AUDIT ULTRA-CONDENSÉ — STATUT CHAQUE PARAMÈTRE

| # | Paramètre | Catégorie | Stockage | Status | Fichiers |
|----|-----------|-----------|----------|--------|----------|
| **A. PROFILS & MODE** |
| 1 | `profile` | Profile | user_settings.json | ⚠️ Partiellement | main.py:287, settings_manager.py:595 |
| 2 | `op_mode` | Mode | user_settings.json | ✅ Utilisé | order_manager.py:85+ |
| 3 | `active_pairs` | Paires | user_settings.json | ✅ Utilisé | main.py:210-238 |
| **B. CONCEPTS ICT (17)** |
| 4 | `ICT:fvg` | Concept | principles_enabled | ❌ IGNORÉ | fvg_detector.py (PAS REÇOIT) |
| 5 | `ICT:order_blocks` | Concept | principles_enabled | ❌ IGNORÉ | ob_detector.py (PAS REÇOIT) |
| 6 | `ICT:liquidity` | Concept | principles_enabled | ❌ IGNORÉ | liquidity_detector.py |
| 7 | `ICT:mss` | Concept | principles_enabled | ❌ IGNORÉ | mss_detector.py |
| 8 | `ICT:choch` | Concept | principles_enabled | ❌ IGNORÉ | choch_detector.py |
| 9 | `ICT:smt` | Concept | principles_enabled | ❌ IGNORÉ | smt_detector.py |
| 10 | `ICT:bos` | Concept | principles_enabled | ❌ IGNORÉ | kb5_engine.py |
| 11 | `ICT:amd` | Concept | principles_enabled | ❌ IGNORÉ | amd_detector.py |
| 12 | `ICT:silver_bullet` | Concept | principles_enabled | ❌ IGNORÉ | temporal_clock.py |
| 13 | `ICT:macros_ict` | Concept | principles_enabled | ❌ IGNORÉ | kb5_engine.py |
| 14 | `ICT:midnight_open` | Concept | principles_enabled | ❌ IGNORÉ | kb5_engine.py |
| 15 | `ICT:irl` | Concept | principles_enabled | ❌ IGNORÉ | irl_detector.py |
| 16 | `ICT:pd_zone` | Concept | principles_enabled | ❌ IGNORÉ | bias_detector.py |
| 17 | `ICT:ote` | Concept | principles_enabled | ❌ IGNORÉ | ote_detector.py |
| 18 | `ICT:cbdr` | Concept | principles_enabled | ❌ IGNORÉ | kb5_engine.py |
| 19 | `ICT:cisd` | Concept | principles_enabled | ❌ IGNORÉ | cisd_detector.py |
| 20 | `ICT:killzone` | Concept | principles_enabled | ⚠️ Voir require_killzone | - |
| **B. CONCEPTS SMC (7)** |
| 21 | `SMC:bos` | Concept | principles_enabled | ❌ IGNORÉ | kb5_engine.py |
| 22 | `SMC:choch_smc` | Concept | principles_enabled | ❌ IGNORÉ | - |
| 23 | `SMC:inducement` | Concept | principles_enabled | ❌ IGNORÉ | inducement_detector.py |
| 24 | `SMC:ob_smc` | Concept | principles_enabled | ❌ IGNORÉ | ob_detector.py |
| 25 | `SMC:fvg_smc` | Concept | principles_enabled | ❌ IGNORÉ | fvg_detector.py |
| 26 | `SMC:equal_hl` | Concept | principles_enabled | ❌ IGNORÉ | bias_detector.py |
| 27 | `SMC:premium_discount` | Concept | principles_enabled | ❌ IGNORÉ | bias_detector.py |
| **C. CONCEPTS PA (6)** |
| 28 | `PA:engulfing` | Concept | principles_enabled | ❌ IGNORÉ | pa_detector.py |
| 29 | `PA:trendlines` | Concept | principles_enabled | ❌ IGNORÉ | pa_detector.py |
| 30 | `PA:round_numbers` | Concept | principles_enabled | ❌ IGNORÉ | pa_detector.py |
| 31 | `PA:pin_bar` | Concept | principles_enabled | ❌ IGNORÉ | pa_detector.py |
| 32 | `PA:inside_bar` | Concept | principles_enabled | ❌ IGNORÉ | pa_detector.py |
| 33 | `PA:sr_levels` | Concept | principles_enabled | ❌ IGNORÉ | pa_detector.py |
| **D. SESSIONS (8)** |
| 34 | `sessions_actives` | Sessions | user_settings.json | ❌ IGNORÉ | temporal_clock.py |
| 35 | `session_london` | Sessions | sessions_actives | ❌ IGNORÉ | temporal_clock.py |
| 36 | `session_ny` | Sessions | sessions_actives | ❌ IGNORÉ | temporal_clock.py |
| 37 | `session_asia` | Sessions | sessions_actives | ❌ IGNORÉ | temporal_clock.py |
| 38 | `overlap_lnny` | Sessions | sessions_actives | ❌ IGNORÉ | temporal_clock.py |
| 39 | `sb_london` | Sessions | sessions_actives | ❌ IGNORÉ | temporal_clock.py |
| 40 | `sb_am` | Sessions | sessions_actives | ❌ IGNORÉ | temporal_clock.py |
| 41 | `sb_pm` | Sessions | sessions_actives | ❌ IGNORÉ | temporal_clock.py |
| **E. RISQUE** |
| 42 | `risk_per_trade` | Risque | user_settings.json | ⚠️ Constant hardcodée | capital_allocator.py:295 (Risk.DEFAULT_RISK_PCT) |
| 43 | `max_trades_day` | Risque | user_settings.json | ❌ IGNORÉ | - |
| 44 | `max_dd_day_pct` | Risque | user_settings.json | ⚠️ Constant hardcodée | killswitch_engine.py:391 (Risk.MAX_DAILY_DRAWDOWN_PCT) |
| 45 | `max_dd_week_pct` | Risque | user_settings.json | ⚠️ Constant hardcodée | killswitch_engine.py:391 |
| 46 | `rr_min` | Risque | user_settings.json | ⚠️ Constant hardcodée | scoring_engine.py:398 (RR_MINIMUM = 2.0) |
| 47 | `rr_target` | Risque | user_settings.json | ❌ IGNORÉ | - |
| **F. FILTRES GLOBAUX** |
| 48 | `require_killzone` | Filtres | user_settings.json | ✅ Utilisé | killswitch_engine.py (KS4) |
| 49 | `require_erl` | Filtres | user_settings.json | ✅ Utilisé | boolean_erl.py |
| 50 | `require_mss` | Filtres | user_settings.json | ⚠️ Chargé/Incertain | kb5_engine.py |
| 51 | `require_choch` | Filtres | user_settings.json | ⚠️ Chargé/Incertain | kb5_engine.py |
| 52 | `disabled_ks` | KS | user_settings.json | ✅ Utilisé | killswitch_engine.py:199-210 |
| 53 | `behaviour_shield` | BS | user_settings.json | ❌ JAMAIS LU | behaviour_shield.py (N'existe pas dans __init__) |
| 54 | `behaviour_shield[stop_hunt]` | BS | behaviour_shield | ❌ IGNORÉ | behaviour_shield.py |
| 55 | `behaviour_shield[fake_breakout]` | BS | behaviour_shield | ❌ IGNORÉ | behaviour_shield.py |
| 56 | `behaviour_shield[liquidity_grab]` | BS | behaviour_shield | ❌ IGNORÉ | behaviour_shield.py |
| 57 | `behaviour_shield[news_spike]` | BS | behaviour_shield | ❌ IGNORÉ | behaviour_shield.py |
| 58 | `behaviour_shield[overextension]` | BS | behaviour_shield | ❌ IGNORÉ | behaviour_shield.py |
| 59 | `behaviour_shield[revenge_trade]` | BS | behaviour_shield | ❌ IGNORÉ | behaviour_shield.py |
| 60 | `behaviour_shield[duplicate]` | BS | behaviour_shield | ❌ IGNORÉ | behaviour_shield.py |
| 61 | `behaviour_shield[staleness]` | BS | behaviour_shield | ❌ IGNORÉ | behaviour_shield.py |
| **G. TEMPS** |
| 62 | `time_filters` | Temps | user_settings.json | ❌ JAMAIS LU | order_manager.py |
| 63 | `time_filters[friday_pm]` | Temps | time_filters | ❌ IGNORÉ | order_manager.py |
| 64 | `time_filters[monday_morning]` | Temps | time_filters | ❌ IGNORÉ | order_manager.py |
| 65 | `time_filters[before_news]` | Temps | time_filters | ❌ IGNORÉ | order_manager.py |
| **H. SCORING** |
| 66 | `score_execute` | Scoring | user_settings.json | ⚠️ Constant hardcodée | scoring_engine.py:82 (SCORE_EXECUTE = 75) |
| 67 | `score_watch` | Scoring | user_settings.json | ⚠️ Constant hardcodée | scoring_engine.py:83 (SCORE_WATCH = 15) |
| **I. IA** |
| 68 | `llm_provider` | IA | user_settings.json | ✅ Utilisé | llm_narrative.py |
| 69 | `llm_api_key` | IA | user_settings.json | ✅ Utilisé | llm_narrative.py |
| **J. UTILITAIRES** |
| 70 | `use_partial_tp` | Utile | user_settings.json | ❌ IGNORÉ | order_manager.py |

---

## 📊 RÉSUMÉ COMPTAGE

```
✅ UTILISÉS                    : 9-11 paramètres  (8.5%-10.5%)
⚠️  PARTIELS (constants)       : 9-10 paramètres  (8.5%-9.5%)
❌ COMPLÈTEMENT IGNORÉS        : 50-56 paramètres (47%-53%)
❓ INCERTAINS/DÉPENDANCES      : 20+ paramètres   (19%)
────────────────────────────────
TOTAL                          : 105+ paramètres
```

---

## 🎯 VERDICT PAR CRITICITÉ

### DÉFECTIEUX (Utilisateur ne peut RIEN configurer)
- Tous les 17 concepts ICT core
- Tous les 7 concepts SMC
- Tous les 6 concepts PA
- Toutes les 8 sessions
- Tous les 8 behaviour shields
- Tous les 3 time filters
- 2 score thresholds

### PARTIELLEMENT FONCTIONNELS (Constants, pas Settings)
- risk_per_trade
- max_dd_day/week_pct
- rr_min
- score_execute (hardcodée 75)

### RÉELLEMENT FONCTIONNELS
- op_mode
- active_pairs
- disabled_ks
- require_killzone
- require_erl
- news_filter (KS3)
- llm_provider
- htf_bias
- profile (partiellement)

---

_Voir AUDIT_PARAMETRES_COMPLET.md pour détails exhaustifs_
