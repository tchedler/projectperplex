# 📐 PROPOSITION DE RÉORGANISATION — PARAMÈTRES INTERFACE

**Date:** 17 Mars 2026
**Objectif:** Restructurer les paramètres pour meilleure ergonomie et flux utilisateur
**Status:** Proposition design (PAS DE CODE)

---

## ANALYSE DE L'ÉTAT ACTUEL

### Structure Existante (Ordre Streamlit)
```
1️⃣  Profils préconçus                    (Cards 5 profils)
2️⃣  Sélection des paires                 (Multi-select large)
3️⃣  Écoles + Principes                   (Toggles école + expander)
4️⃣  Risque                               (3 colonnes: Position/Jour/RR)
5️⃣  Scoring                              (2 colonnes + visualisation)
6️⃣  Filtres Globaux                      (4 checkboxes + KillSwitches)
7️⃣  IA Configuration                     (Provider + API Key)
8️⃣  Réinitialisation                     (Bouton danger)
```

### Problèmes Identifiés

| Problème | Impact | Sévérité |
|----------|--------|----------|
| **Flux non logique** | User doit faire défiler 8 sections = fatigue | 🟡 MOYEN |
| **Profile appliqué PUIS on change détails** | User confus (où sont les champs appliqués?) | 🟡 MOYEN |
| **Écoles + Principes trop profonds** | Expanders imbriquées = UX confusing | 🟠 FAIBLE |
| **Filtres mélangés** | Filtres + KillSwitches = 2 responsabilités | 🔴 CRITIQUE |
| **Pas de hiérarchie claire** | Tout au même niveau visuel | 🟡 MOYEN |
| **Risque vs Scoring fragmentation** | 2 concepts liés, séparés visuellement | 🟡 MOYEN |
| **Paires isolées** | Doit scroller loin du profil/école | 🟡 MOYEN |
| **IA en fin** | Moins souvent configurée, mais trop bas | 🟠 FAIBLE |

---

## NOUVELLE PROPOSITION — "FLOW PYRAMIDAL"

### Concept : Entonnoir de Configuration

```
┌─────────────────────────────────────────────────┐
│   🎯 DÉMARRAGE — Choisir un profil              │  ← Quick Start
├─────────────────────────────────────────────────┤
│   📈 SETUP — Paires & Écoles de trading         │  ← Core Settings
├─────────────────────────────────────────────────┤
│   ⚙️  AVANCÉ — Risque, Scoring, Filtres         │  ← Fine-tuning
├─────────────────────────────────────────────────┤
│   🧠 OPTIONNEL — IA, Notifications              │  ← Extra Features
├─────────────────────────────────────────────────┤
│   🗑️  DANGER — Réinitialisation                 │  ← Destructive
└─────────────────────────────────────────────────┘
```

---

## DÉTAIL DE LA NOUVELLE DISPOSITION

### 📌 NIVEAU 0 — PRÉAMBULE (Aide rapide)

**Élément:** Banner informatif
```
┌──────────────────────────────────────────────────────────────┐
│  💡 Nouveau ? Commencez par un profil préconçu, puis affinez │
│  👉 Guide rapide: [ICT Pur] [SMC+ICT] [Conservateur]         │
└──────────────────────────────────────────────────────────────┘
```

**Disposition:** Une ligne banner en haut
**Avantage:** User sait par où commencer

---

### 🎯 SECTION 1 — DÉMARRAGE RAPIDE (PROFILS)

**Titre:** `🎯 Démarrage — Choisir votre stratégie`

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  Description: "Choisissez une approche de trading"      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐          │
│  │ 🟢 ICT     │ │ SMC + ICT  │ │ 🟡 Neutre  │  ← Active│
│  │ Pur        │ │ (Hybride)  │ │ (Custom)   │          │
│  └────────────┘ └────────────┘ └────────────┘          │
│                                                           │
│  ┌────────────┐ ┌────────────┐                          │
│  │ 🟢 Conserv.│ │ 🔥 Agressif│                          │
│  │ (Prudent)  │ │ (Risqué)   │                          │
│  └────────────┘ └────────────┘                          │
│                                                           │
│  Détails du profil actif: [ICT Pur]                    │
│  ├─ RR min: 2.0x                                        │
│  ├─ Risque/trade: 1% → DD max jour: 5%                │
│  └─ Filtres: Killzone + ERL requis                    │
│                                                           │
│  [💾 Sauvegarder si modifié]                           │
└─────────────────────────────────────────────────────────┘
```

**Changements:**
- ✅ Cards profils d'abord (visual, choix clair)
- ✅ Résumé du profil sous le choix
- ✅ User comprend TÔT quel profil est actif

---

### 📈 SECTION 2 — SETUP PRINCIPAL (PAIRES + ÉCOLES)

**Titre:** `📈 Configuration — Paires & Écoles de Trading`

**Layout – Deux colonnes:**

```
LEFT COLUMN (50%)           │  RIGHT COLUMN (50%)
─────────────────────────   │  ──────────────────────────
                            │
Paires de trading       │  Écoles de trading
────────────────────    │  ─────────────────
                        │
Sélectionnez 6-8        │  Activez les écoles
paires (max).          │  de votre stratégie
                        │
[Multi-select]          │  🟢 ICT              [Toggle]
├─ EUR/USD              │     ├─ Impulse/Impulsion   ☑
├─ GBP/USD              │     ├─ Fair Value Gaps     ☑
├─ AUD/USD              │     ├─ OB (Order Block)    ☑
├─ SPX (US500)          │     └─ BiasStructure       ☑
├─ GOLD                 │
└─ ... (21 total)        │  🟠 SMC               [Toggle]
                        │     ├─ Supply Zones        ☑
Affichage: "6 paires"  │     ├─ Demand PullBacks    ☑
                        │     └─ Market Structure    ☑
[💾 Sauvegarder]        │
                        │  🔵 VOLUME            [Toggle]
                        │     ├─ Profile VPA        ☑
                        │     └─ Liquidité          ☑
                        │
                        │  ⚫ IA (Sentiment)    [Toggle]
                        │     └─ LLM Narrative      ☑
                        │
                        │  [💾 Sauvegarder]
```

**Avantages:**
- ✅ Paires côte-à-côte écoles = setup logique
- ✅ Pas d'expanders imbriquées (flat, clair)
- ✅ User voit immédiatement ses choix
- ✅ Pas besoin de scroller beaucoup

---

### ⚙️ SECTION 3 — AVANCÉ (RISQUE + SCORING + FILTRES)

**Titre:** `⚙️ Avancé — Risque, Scoring & Filtres`

**Sous-titre:** "Pour traders expérimentés. Modifiez si vous comprenez l'impact."

**Layout – 3 onglets / Tabs:**

#### TAB 1: "💰 Risque"
```
┌────────────────────────────────────────────┐
│  Position                                  │
├────────────────────────────────────────────┤
│  Risque par trade:  [==== 1.0% ====]      │
│  Use partial TP:    [☑ Fermer 50% à TP1] │
│                                            │
│  Limites journalières                     │
├────────────────────────────────────────────┤
│  Max trades/jour:   [==== 10 ====]        │
│  Drawdown max/jour: [==== 5% ====]        │
│  Drawdown max/sem:  [==== 10% ====]       │
│                                            │
│  Risk/Reward                              │
├────────────────────────────────────────────┤
│  RR minimum:   [==== 2.0x ====]  ✅ Good  │
│  RR cible:     [==== 3.5x ====]           │
│                                            │
│  [💾 Sauvegarder Risque]                  │
└────────────────────────────────────────────┘
```

#### TAB 2: "🏆 Scoring"
```
┌────────────────────────────────────────────┐
│  Seuils de Verdict                        │
├────────────────────────────────────────────┤
│                                            │
│  Score EXECUTE:  [════60════]  Red zone  │
│  Score WATCH:    [════40════]  Orange    │
│                                            │
│  ┌────────────────────────────────────┐  │
│  │ 0    NO_TRADE    WATCH   EXECUTE 100│  │
│  │      ▼           ▼       ▼         │  │
│  │ ├─────────────┬────────┬───────────┤  │
│  │ │ ROUGE       │ORANGE  │ VERT      │  │
│  │ └─────────────┴────────┴───────────┘  │
│  └────────────────────────────────────┘  │
│                                            │
│  Explication: Score = moyenne pyramide    │
│  (MN/W1/D1/H4/H1/M15). Augmenté par       │
│  confluences (FVG+OB, Killzone, etc)     │
│                                            │
│  [💾 Sauvegarder Scoring]                 │
└────────────────────────────────────────────┘
```

#### TAB 3: "🔒 Filtres & Conditions"
```
┌────────────────────────────────────────────┐
│  Filtres Obligatoires (refus si non OK)   │
├────────────────────────────────────────────┤
│  ☑ Killzone ICT (Londres/NY/Asie active)  │
│  ☑ ERL Sweep (prise de liquidité requis)  │
│  ☑ MSS Confirmé (structure fraîche)       │
│  ☑ CHoCH LTF (changement micro requis)    │
│                                            │
│  Résumé: 4 filtres actifs               │
│  → Haute probabilité, trades moins fréq. │
│                                            │
├────────────────────────────────────────────┤
│  KillSwitches (Avertissement/Arrêt)       │
├────────────────────────────────────────────┤
│  [Grille 3×3 Switches]                    │
│                                            │
│  🟢 KS1: Spread OK     🟢 KS4: Killzone OK │
│  🟢 KS2: Vol normal    🟢 KS5: DD OK      │
│  🟢 KS3: Pas de news   🟢 KS6: Bias OK    │
│  🟢 KS7: Positions OK  🟢 KS8: Corr OK    │
│  🟢 KS9: Phase OK      [?] = Hover info    │
│                                            │
│  [💾 Sauvegarder KillSwitches]            │
└────────────────────────────────────────────┘
```

**Avantages des Tabs:**
- ✅ 3 concepts distincts = 3 onglets
- ✅ User ne voit QUE ce qui le concerne
- ✅ Pas d'overflow vertical
- ✅ Logique visuelle claire

---

### 🧠 SECTION 4 — OPTIONNEL (IA + NOTIFICATIONS)

**Titre:** `🧠 Extras — IA & Notifications`

**Layout – 2 sous-sections côte-à-côte:**

```
LEFT: IA Configuration          │  RIGHT: Notifications
──────────────────────────────  │  ───────────────────────
                                │
🗣️ LLM Narrative                │  📲 Telegram Bot
Fournisseur: [Gemini ▼]         │  Token: [****]
API Key:     [****]             │  Chat ID: [****]
Status: ✅ Connected             │  Status: ✅ Active
                                │
Generate narrative on:          │  Alertes:
[☑] EXECUTE verdicts            │  [☑] EXECUTE entry
[☑] HTF confluence hits         │  [☑] KillSwitch actif
[☑] Session analysis            │  [☑] Drawdown alert
                                │  [☑] Bot error
[💾 Save IA Config]             │  [💾 Save Telegram]
```

**Avantage:** Optionnel = en bas, mais clairement visible

---

### 🗑️ SECTION 5 — DANGER ZONE (Réinitialisation)

**Titre:** `🗑️ Danger Zone — Action Irréversible`

```
┌─────────────────────────────────────────────┐
│  ⚠️ ATTENTION — Réinitialiser tout         │
├─────────────────────────────────────────────┤
│  Restaurer tous les paramètres aux valeurs │
│  par défaut. Cette action est IRRÉVERSIBLE. │
│                                             │
│  Dernière backup auto: 2026-03-17 14:32   │
│  [📥 Restaurer depuis backup]              │
│                                             │
│  Confirmez: Je veux réinitialiser          │
│  [☐] Je confirme cette action               │
│                                             │
│  [RED BUTTON: 🗑️ Réinitialiser Tout]      │
│  (désactivé si checkbox non coché)         │
│                                             │
│  Dernière mise à jour: 2026-03-17 15:30   │
└─────────────────────────────────────────────┘
```

**Améliorations:**
- ✅ Checkbox de confirmation obligatoire
- ✅ Affichage du backup automatique
- ✅ Bouton désactivé par défaut
- ✅ Clarté du danger

---

## COMPARAISON AVANT / APRÈS

### Structure Actuelle (Linear)
```
Profils (cards)
    ↓ scroll
Paires (multi-select)
    ↓ scroll
Écoles + Principes (toggles + expanders)
    ↓ scroll
Risque (3 colonnes)
    ↓ scroll
Scoring (2 colonnes)
    ↓ scroll
Filtres + KillSwitches (mixed)
    ↓ scroll
IA (2 champs)
    ↓ scroll
Reset (button)

PROBLÈME: User doit scroller ~10 "écrans" pour tout voir
```

### Structure Proposée (Pyramidal)
```
PRÉAMBULE: Aide rapide (1 ligne)

SECTION 1: Profils (MUST DO FIRST)
  └─ Sous-sections claires

SECTION 2: Setup Principal (Paires + Écoles)
  └─ 2 colonnes, logique symétrique

SECTION 3: Avancé (3 ONGLETS)
  ├─ Risque
  ├─ Scoring
  └─ Filtres & KS

SECTION 4: Optionnel (IA + Notif)

SECTION 5: Danger Zone

AVANTAGES:
✅ Flow logique: simple → complexe
✅ User commence par profil (quick win)
✅ Paires+Écoles ensemble (setup concis)
✅ Risque/Scoring/Filtres dans tab (modular)
✅ Moins d'expanders (flat = clair)
✅ Très peu de scroll (toute section fit écran)
```

---

## MOCKUP TEXTE — VUE COMPLÈTE (Déroulement User)

### Étape 1: User ouvre Settings
```
══════════════════════════════════════════════════════════════
                    ⚙️ PARAMÈTRES AVANCÉS
         Configuration — Sentinel Pro KB5
══════════════════════════════════════════════════════════════

💡 NOUVEAU? Commencez par profil, puis affinez.
   [Aide]

🎯 DÉMARRAGE — Choisir votre stratégie
───────────────────────────────────────

    [ICT Pur]    [SMC+ICT]    [Neutre]
    
    [Conserv.]   [Agressif]

    Profil actif: ICT Pur
    ├─ RR min: 2.0x | Risque: 1%
    └─ Killzone + ERL requis
    
      [Confirmer]

                        ↓↓↓ SCROLL ↓↓↓
```

### Étape 2: Setup paires & écoles
```
📈 CONFIGURATION — Paires & Écoles
────────────────────────────────────

[LEFT: Multi-select paires]        [RIGHT: Toggles écoles]

Paires (6 sélectionnées)           Écoles

EUR/USD  ✓                         🟢 ICT              ✓
GBP/USD  ✓
SPX500   ✓                         🟠 SMC              ✓
GOLD     ✓
BTC/USD  ✓                         🔵 VOLUME           ✓
AUD/USD  ✓
                                   ⚫ IA (Sentiment)    ✗

[Sauvegarder]                      [Sauvegarder]

                        ↓↓↓ SCROLL ↓↓↓
```

### Étape 3: Onglets Avancé
```
⚙️ AVANCÉ — Risque, Scoring & Filtres
──────────────────────────────────────

   [💰 Risque]  [🏆 Scoring]  [🔒 Filtres]

   ╔═══════════════════════════════════╗
   ║   💰 RISQUE                       ║
   ║                                   ║
   ║   Risque/trade: [===1.0%===]    ║
   ║   RR min: [===2.0x===] ✅ Good   ║
   ║   DD max jour: [===5%===]        ║
   ║                                   ║
   ║   [Sauvegarder Risque]           ║
   ╚═══════════════════════════════════╝

                        ↓↓↓ SCROLL ↓↓↓
```

### Étape 4: Optionnel
```
🧠 EXTRAS — IA & Notifications
──────────────────────────────

   [LEFT: IA]              [RIGHT: Telegram]
   
   Fournisseur: Gemini     Token: [****]
   Status: ✅ Connected    Status: ✅ Active
   
   [Sauvegarder]          [Sauvegarder]

                        ↓↓↓ SCROLL ↓↓↓
```

### Étape 5: Danger
```
🗑️ DANGER ZONE
──────────────

⚠️ Réinitialiser tout (IRRÉVERSIBLE)

[☐] Je confirme cette action

[RED: 🗑️ Réinitialiser]
```

---

## BÉNÉFICES DE CETTE RÉORGANISATION

### Pour l'Utilisateur
- ✅ **Flow logique:** Simple → Avancé
- ✅ **Quick wins:** Profil d'abord = 1 clic = configuration ok
- ✅ **Moins de scroll:** Chaque section = 1 écran (sauf onglets)
- ✅ **Hiérarchie claire:** Quoi faire d'abord (profil) vs options (IA)
- ✅ **Sécurité:** Danger zone clairement séparée
- ✅ **Apprentissage:** Groupes logiques = facile à comprendre

### Pour le Code
- ✅ **Même logique Streamlit:** Juste réordonner les sections
- ✅ **Onglets faciles:** `st.tabs()` natifs
- ✅ **2 colonnes:** `st.columns()` existants
- ✅ **Aucune nouvelle fonction:** Juste refactor layout

### Pour l'Expérience
- ✅ **Moins de fatigue:** Pas 10 sections d'affilée
- ✅ **Cohérence visuelle:** Theme "entonnoir" = pro
- ✅ **Guidance implicite:** User sait quoi faire en premier
- ✅ **Réduction erreurs:** Filtres groupés ensemble

---

## ALTERNATIVES CONSIDÉRÉES (et rejetées)

### Option A: "Dashboard Principal + Modal Paramètres"
❌ **Rejeté:** Trop modal, user doit switch page

### Option B: "Sidebar étroite + Main content"
❌ **Rejeté:** Sidebar cramée, pas assez d'espace paires

### Option C: "Wizard étapes (Step 1/2/3)"
❌ **Rejeté:** Trop linéaire, user peut pas revenir facilement

### Option D: "Arborescence (Tree view hierarchique)"
❌ **Rejeté:** Trop complexe pour Streamlit, peu responsive

### **Option E: "Pyramidal (CHOISIE)"**
✅ **Retenue:** Linéaire mais structurée, clair, facile Streamlit

---

## TIMING DE MIGRATION

**Phase d'implémentation:**

```
Semaine 1:
  [ ] Restructurer sections 1-2 (profils, paires, écoles)
  [ ] Test sur demi-dozen utilisateurs
  
Semaine 2:
  [ ] Implémenter onglets section 3 (risque/scoring/filtres)
  [ ] Polir sections 4-5 (IA, danger)
  
Semaine 3:
  [ ] Testing complet + refinements
  [ ] Déployer en prod
```

**Effort estimé:** ~3-4 jours (refactor layout, ~200 lignes code)

---

## PROCHAINES ÉTAPES

Si vous approuvez cette proposition:

1. **Validation client:** Montrer wireframe à 2-3 utilisateurs
2. **Feedback:** Ajustements couleurs/espacement/wording
3. **Codage:** 1 dev pour ~4 jours
4. **Testing:** Cross-browser + Streamlit
5. **Déploiement:** Feature flag → tous utilisateurs

---

## FICHIER DE RÉFÉRENCE

Ce fichier peut servir de:
- 📋 **Specification UI/UX** pour le dev
- 📸 **Reference visuelle** pour validation
- ✅ **Checklist** d'implémentation
- 📊 **Documentation** pour nouvelles features

**Version:** 1.0 | **Date:** 17 Mars 2026
