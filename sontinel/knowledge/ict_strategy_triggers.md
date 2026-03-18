# 🕒 DÉCLENCHEURS DE STRATÉGIES ICT (Sentinel Mode) v2.1
# CHANGELOG v2.1 : Grail Setup ajouté, CBDR Trigger intégré, Hints Anti-Inducement renforcés

Ce document répertorie les déclencheurs automatiques basés sur le temps et les setups pour chaque stratégie prédéfinie par Michael Huddleston (ICT).

---

## 📅 MATRICE DES FENÊTRES TEMPORELLES (Heure New York EST)

| Fenêtre | Heure UTC-5 | Stratégie(s) Cible(s) |
|---|---|---|
| **London Open Manipulation** | 01:30 – 02:30 | Judas Swing, London Trap |
| **London Silver Bullet** | 03:00 – 04:00 | Silver Bullet Standard |
| **NY AM Manipulation** | 08:30 – 09:30 | Judas Swing, News Trap |
| **NY AM Silver Bullet** | 10:00 – 11:00 | Silver Bullet Standard |
| **London Close / NY Lunch** | 10:00 – 12:00 | London Close Reversal *(double pression institutionnelle)* |
| **NY PM Transition** | 13:00 – 14:00 | PM Session Shift |
| **NY PM Silver Bullet** | 14:00 – 15:00 | Silver Bullet Standard |
| **NY Close Macro** | 15:15 – 15:45 | Closing Distribution |

---

## 🎯 LOGIQUE DÉTAILLÉE PAR STRATÉGIE

### 1. London Silver Bullet
- **Déclencheur Temporel** : 03:00:00 – 03:59:59 NY.
- **Conditions de Setup** :
  1. `Boolean_Sweep_ERL == True` : Le prix a sweepé une liquidité externe (PDH/PDL, Asia H/L).
  2. Création d'un **MSS** (clôture de corps) avec **Displacement**.
  3. Formation d'un **FVG** après le MSS.
- **Action de l'Agent** : Entrer sur le retracement dans le FVG (idéalement au CE 50%).
  Target : Liquidity Pool opposé (EQH/EQL smooth).

### 2. NY AM Silver Bullet
- **Déclencheur Temporel** : 10:00:00 – 10:59:59 NY.
- **Conditions de Setup** :
  1. Biais D1 déjà identifié (Midnight Open + NDOG analysés).
  2. `Boolean_Sweep_ERL == True` : Sweep ERL confirmé pendant London ou NY AM open.
  3. MSS + Displacement sur M15/M5.
  4. FVG frais non comblé.
- **Règle Spéciale** : Si le DOL HTF a **déjà été atteint** avant 10h, NE PAS prendre le trade.

### 3. Judas Swing (Manipulation d'ouverture)
- **Déclencheur Temporel** : London (01h30–02h30) ou NY (08h30–09h30).
- **Conditions de Setup** :
  1. Le prix sort de la zone d'accumulation (Asia) avec force.
  2. Sweep de liquidité visible (BSL ou SSL purgé).
  3. Réintégration rapide (SFP ou Turtle Soup en 1-3 bougies).
- **Action de l'Agent** : Prédire le retournement. Entrer dans la "vraie" direction de session.
- **Validation AMD** : Si phase A (Accumulation) et M (Manipulation) détectées → Se positionner pour phase D (Distribution).

### 4. Turtle Soup
- **Déclencheur Temporel** : Toutes sessions (plus fort en Killzones).
- **Conditions de Setup** :
  1. Prix casse un High/Low évident (Double Top/Bottom, EQH/EQL).
  2. Mèche profonde au-delà du niveau, mais **clôture de corps en deçà** (Sweep).
  3. La bougie suivante est un displacement inverse.
- **Action de l'Agent** : Entrée immédiate post-sweep.

### 5. Unicorn Setup
- **Déclencheur Temporel** : Toutes sessions.
- **Conditions de Setup** :
  1. Identification d'un **Breaker Block** (ancien OB cassé).
  2. Le Breaker est aligné avec un **FVG** (le FVG se trouve DANS ou à la frontière du Breaker).
- **Action de l'Agent** : Confiance de setup +20% (Priorité Maximale).

### 6. The Grail Setup (AJOUT v2.1)
- **Déclencheur Temporel** : Killzone Active + Macro algorithmique (toutes sessions).
- **Conditions de Setup (TOUTES obligatoires)** :
  1. `Boolean_Sweep_ERL == True` : Liquidité externe (EQH/EQL/PDH/PDL) sweepée.
  2. MSS avec Displacement confirmé sur le TF d'entrée.
  3. OB de qualité ≥ 4/5 + FVG à l'intérieur de l'OB (confluence).
  4. SMT Divergence inter-marchés confirme la direction.
  5. Timing = Killzone valide + Macro algorithmique active.
- **Optionnel (bonus score)** :
  - **Alignement** D1 biais dans la même direction
  - Prix dans bonne zone Premium/Discount HTF
  - COT Report aligné avec la direction (+5 pts)
- **Action de l'Agent** : Score ≥ 90/100 → Exécution A+ avec taille maximale autorisée.
- **Remarque** : Grail Parfait = Unicorn (Breaker+FVG) + HTF alignment + SMT + Killzone.

### 7. Power of 3 (AMD)
- **Déclencheur Temporel** : Cycle complet 00:00 – 16:00 NY.
- **Conditions de Setup** :
  1. **A**ccumulation : Range étroit avant l'ouverture de session.
  2. **M**anipulation : Judas Swing hors de la range (Souvent à Londres).
  3. **D**istribution : Mouvement soutenu vers le DOL.
- **Action de l'Agent** : Si phase A et M sont détectées, se positionner exclusivement pour phase D.
- **Version Weekly** : Accumulation=Lundi / Manipulation=Mardi / Distribution=Mercredi+.

### 8. CBDR Explosive Setup (AJOUT v2.1)
- **Déclencheur Temporel** : Calcul CBDR à 20h00 EST la veille. Trigger actif à partir du lendemain 00:00.
- **Conditions de Setup** :
  1. `CBDR_Range_Pips < 40` → `CBDR_Explosive = True`
  2. Biais D1 identifié (Midnight Open).
  3. Premier MSS dans la direction du biais pendant une Killzone.
- **Action de l'Agent** : Appliquer les Projections SD avec pleine confiance.
  Targets : SD **-1.0**, **-2.0** (principal), **-2.5** (terminal), **-3.5** (extension max).
  Target primaire = SD -2.0 depuis le point B (fin du Judas Swing).
  > Note : Certaines sources ICT mentionnent -4.0 pour les setups Weekly. Utiliser -3.5 par défaut.

---

## ⚖️ SECTION 9 — GESTION DES CONFLITS DE TRIGGERS (Priorisation)

Dans le cas où plusieurs signaux apparaissent simultanément, l'Agent applique la hiérarchie de priorité ICT suivante :

1. **Priorité 1 : The Grail Setup** (Score ≥ 90). Si un Grail est détecté, il annule tout autre signal opposé.
2. **Priorité 2 : Unicorn / Breaker Block**. Un Breaker Block avec FVG a plus de poids qu'un simple FVG (Order Flow plus fort).
3. **Priorité 3 : Biais HTF (H1/D1)**. Si un Silver Bullet M5 est Bullish mais que le Biais H1 est Bearish et que le prix est en Zone Premium HTF → Ignorer le signal Bullish.
4. **Priorité 4 : Liquidité Externe (ERL)**. Un sweep de PDH/PDL est plus puissant qu'un sweep de liquidité interne.

**Règle du Conflit Direct** : Si deux signaux de même priorité pointent dans des directions opposées → **NE PAS TRADER** (Consolidation ou manipulation de type Seek & Destroy).

---

## 📢 SECTION 10 — PROTOCOLE "HIGH IMPACT NEWS"

Le calendrier économique (ForexFactory / Investing) doit être scanné quotidiennement.

### News "Dossier Rouge" (CPI, NFP, FOMC)
- **Arrêt Automatique** : Suspendre toute exécution 10 minutes AVANT l'annonce.
- **Délai de Reprise** : Attendre minimum 15 à 30 minutes APRÈS l'annonce pour laisser l'algorithme "nettoyer" la liquidité (Judas Swing de news).
- **Condition de Reprise** : Un MSS clair avec Displacement doit se former APRÈS le pic de volatilité initial.

### News Imprévues (Black Swan / Flash News)
- Si une bougie anormale (> 3x ATR) apparaît hors macro/news → **Fermeture immédiate des positions** au prix du marché et passage en mode observation 1h.

---

## 🤖 COMPORTEMENT DE L'AGENT "SENTINEL" v2.1

1. **Vérification Heure** : Comparer l'heure actuelle (NY EST avec passage été/hiver) avec la matrice.
2. **Vérification Anti-Inducement** : `Boolean_Sweep_ERL == True` avant toute analyse de signal.
3. **CBDR Check** : Au démarrage (00:00 EST), calculer `CBDR_Range_Pips` → Lever flag `CBDR_Explosive`.
4. **Scan Focalisé** : Si une fenêtre est active, basculer en "Score Prioritaire" pour la stratégie ciblée.
5. **Alerte Setup** : Dès que MSS + FVG + Sweep réunis pendant la fenêtre → Calculer score /100.
6. **Verdict d'Exécution** :
   - `≥ 80 pts` → **EXÉCUTION A+** (Ordre LMT immédiat + Bracket Orders)
   - `65–79 pts` → **WATCH/SNIPER** (Ordre Limit STRICTEMENT au 70.5% OTE uniquement)
   - `≤ 64 pts` → **INTERDIT** (Pas d'ordre, attendre Asia le lendemain)
7. **Calcul Target SD** : Toujours utiliser la Standard Deviation du Judas Swing pour les partiels.
8. **Trading Lock** : Suspendre l'agent après atteinte de SD -2.5 ou +3R. Ne pas chercher de nouveaux setups.
