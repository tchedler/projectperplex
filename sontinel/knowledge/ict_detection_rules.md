# 🔧 RÈGLES DE DÉTECTION ICT v4.0 (ALGORITHME D'AGENT EXPERT)
# VERSION : 4.0 (Institutionnelle & Orientée Programmation — Enrichie Grok + Audit Expert)
# COMPILATION : Michael J. Huddleston Concepts (Mentorships 2016-2024)
# CHANGELOG v4.0 : Correction OB multi-bougie, BPR timing, Anti-Inducement renforcé,
#                  CBDR/Flout ajoutés, Scalp TF corrigé, Fusion Macros unifiées

---

## 0. PRÉ-REQUIS SYSTÈME ET VARIABLES GLOBALES

- [Timezone]: Le script entier (bot/algo) doit impérativement utiliser la Timezone
  **"EST/EDT - Time In New York"** (UTC-5 hiver / UTC-4 été).
  ⚠️ CRITIQUE : Implémenter le **passage automatique heure Hiver/Été** dans la classe
  DateTime. Sans ce mapping, toutes les Macros 1 à 12 seront décalées d'1h en période
  d'heure d'été — toutes les fenêtres seront fausses.

- [Variables d'état IA]:
  `Boolean_Sweep_ERL = False`          (External Range Liquidity Sweep)
  `Boolean_Sweep_IRL = False`          (Internal Range Liquidity Sweep)
  `State_of_Delivery = "UNKNOWN"`      (ACCUMULATION | MANIPULATION | DISTRIBUTION | RE-ACCUMULATION)
  `CBDR_Range_Pips = 0`               (Calculé entre 14h00 et 20h00 EST la veille)
  `CBDR_Explosive = False`            (True si CBDR_Range_Pips < 40)

- [Condition Anti-Inducement — RENFORCÉE v4.0]:
  L'algo IGNORE tous CHoCH, MSS et FVG tant que `Boolean_Sweep_ERL == False`.
  **RÈGLE ABSOLUE** : Un CHoCH interne sans purge ERL préalable = INDUCEMENT.
  Les bots Smart Money ciblent exactement ces entrées prématurées.
  La variable bascule à `True` UNIQUEMENT si :
  - `c.Low < PDL` (Previous Day Low) avec réintégration du PDL (Sweep confirmé), OU
  - `c.High > PDH` (Previous Day High) avec réintégration du PDH (Sweep confirmé).
  Après un vrai Sweep ERL → attendre le premier MSS → c'est l'unique signal valide.

---

## 1. FAIR VALUE GAP (Déséquilibre Algorithmique)

- [Déplacement — Vision Institutionnelle]:
  ICT privilégie l'évaluation **visuelle** (corps large, momentum fort, pas de chevauchement).
  
  **Critères Objectifs v4.1 (Algorithmiques) :**
  1. **Momentum Candle** : Le corps de la bougie doit être > 2x la taille moyenne des 5 corps précédents.
  2. **Gap de Livraison** : Création immédiate d'un FVG ou d'un Volume Imbalance.
  3. **Vitesse** : Traversée d'un PD Array opposé sans hésitation (mèche courte).
  4. **Quantification ATR** : `|Close - Open| > ATR(14) * 1.5` (Seuil de force institutionnelle).

  Hiérarchie de confirmation (2/3 conditions suffisent) :
  1. Visuel pur : Corps larges, séquence directionnelle, FVG créé
  2. `|Close - Open| > 0.70 * (High - Low)` (bougie volumineuse)
  3. `Body > ATR(14) * 1.5` (quantification optionnelle)

- [Bullish FVG]:
  Condition : `c[i-1].High < c[i+1].Low` && `c[i].Close > c[i].Open` && Displacement = True.
  Zone : `Top = c[i+1].Low`, `Bot = c[i-1].High`, `CE = (Top + Bot) / 2`

- [Bearish FVG]:
  Condition : `c[i-1].Low > c[i+1].High` && `c[i].Close < c[i].Open` && Displacement = True.
  Zone : `Top = c[i-1].Low`, `Bot = c[i+1].High`, `CE = (Top + Bot) / 2`

- [High Probability FVG — AJOUT v4.0]:
  Sur une jambe complète, n'accepter que le **PREMIER FVG** créé depuis l'origine
  (le plus proche du discount extrême en bull / premium extrême en bear).
  Les FVG qui apparaissent au-delà de 60-70% d'un rally naissant sont en zone d'"épuisement"
  (Running Out of Fuel) — ratio institutionnel non valide.
  → `IF FVG_position > 65% of swing range THEN FVG_quality = LOW`

- [Inversion FVG (IFVG)]:
  Si un FVG est cassé (Clôture de corps `Body Close` ferme au-delà de sa zone),
  le script renverse son rôle de PD Array (Support ↔ Résistance).

- [Statut de Qualité du FVG]:
  - **Frais** : Corps du prix hors de la zone → Force maximale
  - **Mitigé** : Mèche touche mais corps ne clôture pas dedans → Force réduite -30%
  - **Utilisé** : Corps clôture dans la zone → Zone invalidée

---

## 2. ORDER BLOCKS (Boucle d'Itération Multi-Bougies — CORRECTION INSTITUTIONNELLE v4.0)

> ⚠️ CORRECTION CRITIQUE Grok : L'OB institutionnel n'est PAS une seule bougie.
> C'est l'**ensemble des bougies consécutives de même couleur** avant le rallye/chute.

- [Concept institutionnel]: L'algorithme cherche un **"bloc de livraison" complet**,
  pas une bougie isolée.

- [Algorithme OB Haussier (Bullish) — CORRIGÉ]:
  1. Identifier l'origine du mouvement fort haussier (Displacement validé).
  2. Lancer une boucle arrière depuis ce point : `For i = index_origin step -1`
  3. Grouper **TOUTES les bougies BAISSIÈRES contiguës** (`Close < Open`).
  4. Stopper l'itération à la première bougie HAUSSIÈRE rencontrée.
  5. `OB_Low_Zone = Minimum(c.Low)` du groupe entier de bougies baissières.
  6. `OB_High_Zone = Maximum(c.Open OR c.High)` du groupe entier.
  7. ⚠️ Le FVG de confirmation peut survenir aux bougies +2 ou +3 après l'OB (pas forcément +1).

- [Algorithme OB Baissier (Bearish) — CORRIGÉ]:
  Identiquement : boucle arrière depuis l'origin du mouvement baissier,
  grouper toutes les bougies HAUSSIÈRES contiguës.
  `OB_High_Zone = Maximum(c.High)`, `OB_Low_Zone = Minimum(c.Open OR c.Low)`.

- [Scoring OB — Checklist Qualité]:
  +1 pt : La bougie/bloc a créé un new high ou new low sur le TF supérieur
  +1 pt : Il y a un FVG juste après (dans les +1 à +3 bougies)
  +1 pt : L'OB est dans la bonne zone Premium/Discount
  +1 pt : Il s'est formé pendant une Killzone ou Macro
  +1 pt : Il n'a pas encore été revisité
  Score 5/5 = OB institutionnel de premier ordre

- [Breaker Block]:
  Ancien OB touché/purgé, puis cassé fermement par le marché (Displacement).
  Inverse sa polarité → devient un POI massif (⭐⭐⭐⭐⭐).

- [Rejection Block — AJOUT v4.1]:
  **Définition** : Zone de mèches longues et répétées qui ont échoué à clôturer au-delà d'un niveau. 
  - **Bullish** : Formation de mèches sous un Swing Low sans clôture de corps. 
  - **Bearish** : Formation de mèches au-dessus d'un Swing High sans clôture de corps.
  **Logique** : L'algorithme rejette le prix. Le "corps" de la bougie est le vrai prix, la "mèche" est la manipulation.
  **Entrée** : Au sommet de la mèche (bearish) ou au bas de la mèche (bullish) du bloc de rejet.

- [Vacuum Block — AJOUT v4.1]:
  **Définition** : Un vide de liquidité créé par une annonce news (Slippage/Gap).
  **Condition** : Le prix "saute" des niveaux sans aucune transaction entre Close(i) et Open(i+1).
  **Comportement** : L'algorithme a une "mémoire" de ces vides et cherchera à les combler à 100% très rapidement (souvent dans la même session).

---

## 3. STRUCTURE DE LIVRAISON DE PRIX (Anti-Fakeout)

- [Swing Definition]:
  `c[i].High` est supérieur à `n` bougies à sa gauche et `n` bougies à sa droite
  (Fractal 5 bars recommandé : n=2 pour scalp, n=5 pour day trade, n=10 pour swing).

- [SFP (Swing Failure Pattern)]:
  `Sweep = True` si mèche casse le Swing High MAIS `Close` revient en dessous.
  Signal d'absorption → retournement immédiat attendu.

- [CHoCH]:
  Requis formel : `Boolean_Sweep_ERL == True` avant tout CHoCH valide.
  Premier bris de structure contre-tendance = **ALERTE UNIQUEMENT** (pas d'exécution).

- [MSS — Market Structure Shift]:
  Validé si : BOS de structure locale + Déplacement Mathématique + FVG créé.
  Requis : `Boolean_Sweep_ERL == True`.
  **UNIQUE signal autorisant l'exécution.**

- [State of Delivery — AJOUT v4.0]:
  Variable de suivi de la phase macro du marché à mettre à jour après chaque événement :
  - `ACCUMULATION`  : Range étroit, CBDR_Explosive possible
  - `MANIPULATION`  : Judas Swing / Sweep ERL détecté
  - `DISTRIBUTION`  : MSS confirmé, mouvement en cours vers DOL
  - `RE-ACCUMULATION` : Pullback dans FVG/OB après première Distribution
  → L'agent ne prend un trade que si `State_of_Delivery == "DISTRIBUTION"` ou
    `State_of_Delivery == "RE-ACCUMULATION"` en concordance avec HTF.

---

## 4. IPDA MATRICE DES MACROS ET TIME (NY EST) — UNIFIÉES v4.0

> ⚠️ CORRECTION CRITIQUE : Unification des macros (incohérence entre v3.0 et l'encyclopédie).
> Liste unifiée et canonique ci-dessous — À utiliser comme référence unique.

- [Daily Bias Data]: Enregistrement indispensable de `Midnight_Open_Price` (00:00 EST)
  et `NY_0830_Open_Price`.

- [12 Macros Algorithmiques Complètes — LISTE CANONIQUE]:

  | # | Macro | Heure NYC EST | Marché |
  |---|---|---|---|
  | 1 | Midnight Open Macro | 23:50 – 00:10 | Forex, Cryptos |
  | 2 | London Open Macro | 01:50 – 02:10 | Forex |
  | 3 | London AM Macro 1 | 04:03 – 04:23 | Forex |
  | 4 | London AM Macro 2 | 05:13 – 05:33 | Forex |
  | 5 | NY Open Macro | 07:50 – 08:10 | Forex, Indices |
  | 6 | NY AM Macro 1 | 08:50 – 09:10 | Indices, Forex |
  | 7 | NY AM Macro 2 | 09:50 – 10:10 | Forex, Indices |
  | 8 | NY AM Macro 3 | 10:50 – 11:10 | Forex, Indices |
  | 9 | NY Lunch Macro | 11:50 – 12:10 | Forex |
  | 10 | NY PM Macro 1 | 13:10 – 13:30 | Indices, Forex |
  | 11 | NY PM Macro 2 | 14:50 – 15:10 | Indices, Forex |
  | 12 | NY Close Macro | 15:15 – 15:45 | Indices |

- [Silver Bullet Windows]:
  [03:00–04:00] London | [10:00–11:00] NY AM | [14:00–15:00] NY PM

- [Règle Scoring Algorithmique UNIQUE — SEUIL UNIFIÉ v4.0]:
  Signal MSS DANS une Macro / KZ → +10 pts (validation algorithmique)
  Signal MSS HORS Macro / KZ → -20 pts (confiance réduite)
  **SEUIL D'EXÉCUTION : ≥ 80 pts = A+ (Exécution immédiate)**
  **[65–79 pts] = Watch/Sniper Limit Order uniquement**
  **[≤ 64 pts] = Interdit — Attendre nouvelles conditions**

---

## 5. CBDR & FLOUT — CIBLES ALGORITHMIQUES BANCAIRES (AJOUT v4.0)

> 💡 Outil institutionnel clé du HFT algorithmique — Manquant dans v3.0

- [CBDR (Central Bank Dealers Range)]:
  Gamme de prix mesurée **strictement de 14:00 à 20:00 (EST) la veille**.
  `CBDR_High = Max(High) entre 14h et 20h`
  `CBDR_Low = Min(Low) entre 14h et 20h`
  `CBDR_Range_Pips = (CBDR_High - CBDR_Low) / pip_value`

- [Flout]:
  Extension du CBDR de **15:00 à Minuit (00:00 EST)**.
  `Flout_High = Max(High) entre 15h et 00h`
  `Flout_Low = Min(Low) entre 15h et 00h`

- [Condition d'Explosivité]:
  `IF CBDR_Range_Pips < 40 THEN CBDR_Explosive = True`
  → Algorithme prépare un déploiement tendanciel massif le lendemain.
  → Appliquer Projections SD avec pleine confiance.

- [Projections Cibles depuis CBDR]:
  1. Mesurer la hauteur du CBDR en pips.
  2. Projeter depuis le High ou Low du CBDR dans la direction du biais.
  3. Targets : SD -1.0, -2.0 (principal), -2.5 (terminal), -3.5 (extension max).
  → La convergence d'une SD CBDR avec un EQH/EQL ou PDH/PDL = cible A+.

---

## 6. CIBLAGE ALGORITHMIQUE DE LA LIQUIDITÉ (DOL)

- [Draw On Liquidity]: Identifier l'aimant à prix actif.

- [Smooth High/Low — Cible A+]:
  Zone avec ≥ 2 sommets dont l'écart sur l'axe Y est minimal.
  Tolérance : `Variance_Y ≤ ATR(14) * 0.15`
  → Bassin de liquidité prioritaire — cibler obligatoirement.

- [Jagged High/Low]:
  Sommets/creux irréguliers, décalés > ATR(14)*0.15.
  → Liquidité épuisée ou non ciblée → L'agent IGNORE ces zones comme cible principale.

- [Règle de déplacement IRL/ERL]:
  - Si sweep ERL (PDH/PDL, PWH/PWL) → Target suivante : IRL (FVG, OB).
  - Si touche IRL (FVG, OB) → Target suivante : ERL opposé.
  Le prix se déplace TOUJOURS alternativement de ERL→IRL→ERL.

- [Gaps d'Ouverture]:
  NDOG (gap veille/aujourd'hui 17:00 EST) et NWOG (Open dimanche) = Aimants algorithmiques.
  `IF price between NDOG_Low and NDOG_High THEN Gap_Fill_Magnet = True`

---

## 7. SMT DIVERGENCES (Réseaux Croisés et Secteurs)

- [Forex SMT]:
  EUR/USD franchit un Lower Low MAIS GBP/USD fait un Higher Low → Manipulation identifiée.
  → Acheter GBP/USD (paire la plus forte, non manipulée).

- [DXY SMT]:
  DXY et EURUSD dans la MÊME direction → Anomalie → Inversion attendue.

- [Crypto SMT — AJOUT v4.0 (Mentorship 2024)]:
  Si BTC crée un nouveau High (Higher High) MAIS ETH/Alts bloquent sous leur résistance →
  **SMT Baissière sur BTC** : Les institutions pompent BTC pour liquider et distribuer.
  Biais Bearish programmé sur BTC.
  Inversement : ETH nouveau Low sans BTC → manipulation ETH → Rebond probable.

- [Yields US SMT]:
  Corrélation Inverse avec USD.
  Si Yields montent + USD descend → Manipulation USD → Retournement USD attendu.

- [Indices SMT]:
  ES (S&P500) nouveau haut mais NQ (Nasdaq) non → Divergence → Prudence.

- [Tolérance Temporelle SMT]:
  Comparer les swings sur la MÊME bougie ou dans un écart de ≤ 3 bougies sur le même TF.
  Au-delà de 5 bougies d'écart → Divergence non valide.

---

## 8. MATRICE P/D & ENTRÉE OPTIMISÉE (Premium / Discount)

- [Dealing Range]:
  Traçage continu 0–100% entre le dernier swing high et swing low valide.
  `Equilibrium = 50%`

- [Conditionnement du Biais]:
  Achat autorisé **UNIQUEMENT** si `Price_Current < 50%` (Discount).
  Vente autorisée **UNIQUEMENT** si `Price_Current > 50%` (Premium).
  Zones Extrêmes (< 25% ou > 75%) : Force de signal +10%.

- [OTE (Optimal Trade Entry)]:
  Zone dorée : `62.0% à 79.0%` du retracement du swing.
  Point idéal : `70.5%`
  Invalide si retracement > 79% (setup abandonné).
  Confluence FVG/CE à l'intérieur OTE = +20% score.

---

## 9. BPR & VOLUME IMBALANCE (Micro-PD Arrays) — AVEC CONDITION TIMING v4.0

- [BPR (Balanced Price Range)]:
  **Définition** : Superposition exacte d'un Bearish FVG et d'un Bullish FVG.
  **CONDITION TIMING CRITIQUE — AJOUT v4.0** :
  Pour qu'un BPR soit "institutionnel" et de force maximale, les deux FVG opposés
  doivent être formés en **moins de 20 bougies d'intervalle**.
  `IF candle_gap_between_FVGs > 20 THEN BPR_strength = "DILUTED" (force -50%)`
  `IF candle_gap_between_FVGs <= 20 THEN BPR_strength = "INSTITUTIONAL"`
  → Support/Résistance le plus puissant. Réaction quasi-immédiate attendue.

- [Volume Imbalance (VI)]:
  Gap entre corps de bougies consécutives (`Open c[i+1] vs Close c[i]`).
  Traité comme un FVG ultra-rapide — muraille/soutien sur M1.
  Particulièrement puissant sur les indices (ES/NQ).

---

## 10. RISQUE PARAMÉTRIQUE (Sauvegarde et Killswitch Algo)

- [Volume de Base]:
  `Risk_per_Trade ≤ Balance_Equity * 0.01` (1% du nominal max par ordre)
  `Total_Open_Exposure ≤ Balance_Equity * 0.05` (5% max total ouvert — règle prop firm)
  ⚠️ CORRECTION v4.0 : Le "Stop 5% hebdo" concerne l'exposition TOTALE, pas par trade.

- [Stop Loss ICT]:
  SL placé STRICTEMENT sous/sur le pool d'origine de manipulation (hors FVG/OB) ± spread.
  Jamais basé sur ATR constant.
  Max 20-30 pips pour le scalp. Peut être plus large sur le swing.
  SL dans l'OB lui-même = ERREUR → le prix "respire" toujours dans la zone avant de partir.

- [Régulation des Pertes]:
  `IF consecutive_losses >= 3 THEN lot_size = lot_size * 0.50` (réduction 50%)
  `IF intraday_drawdown >= 0.03 THEN lot_size = lot_size * 0.50` (Killswitch DD 3%)
  `IF weekly_drawdown >= 0.05 THEN trading_locked = True` (Lock hebdomadaire)

- [Trading Lock]:
  Suspendre l'Agent pour le reste de la journée EST une fois la cible journalière
  atteinte (SD -2.5 ou +3R percuté avec succès). Ne pas chercher de nouveaux trades.

---

## 11. SCORING INTÉGRAL D'EXÉCUTION v4.0 (Score / 100 pts)

**[25 pts — Narratif HTF & ERL]**
- `Boolean_Sweep_ERL == True` et sweep confirmé (+10)
- MSS avec déplacement ultra-volumique confirmant changement state of delivery (+10)
- Contexte en alignement avec Midnight Open Daily (+5)

**[25 pts — Emplacement (PD Arrays & Macro Time)]**
- Setup = FVG dans un Refined OB (Breaker > OB > FVG) (+10)
- Signal dans une Macro de 20 min OU Silver Bullet OU Killzone (+10)
- En zone OTE 62-79% (+5)

**[25 pts — Liquidity Draw]**
- Bassin Smooth (EQH/EQL) opposé localisé en LRLR (chemin libre) (+15)
- SD projetée (-2.0) ou NWOG/NDOG converge avec la cible (+10)

**[25 pts — Risk / Rendement]**
- `RR ≥ 2:1` (+10)
- `RR > 3:1` (+15)
- `RR > 5:1` (+25)
- `IF RR < 1:2 THEN score -= 25` (Le SL > Target → Ordre abandonné automatiquement)

**BONUS : COT Report aligné avec biais (+5 pts supplémentaires)**
> Ces 5 pts bonus peuvent faire passer un setup de 75→80 (Watch→Exécution).
> ⚠️ **Cap algorithmique** : `Final_Score = MIN(score + COT_bonus, 100)` — Le score ne dépasse pas 100.

> **[ VERDICTS EXÉCUTIFS BOT ]**
> `[≥ 80 pts]` : **Exécution A+** → EA émet Ordre LMT, pose Bracket Orders partiels.
> `[65–79 pts]` : **Watch/Sniper Limit** → Entrée STRICTEMENT au 70.5% OTE. Rejet si raté d'1 pip.
> `[≤ 64 pts]` : **Interdit Technique** → Détruire le calcul, attendre Asia le lendemain.

---

## 12. AMD (Power of 3) — APPLICABILITÉ ÉTENDUE v4.0

**Sur le DAILY (cycle standard):**
- Accumulation (00:00–09:30 NYC) : Range étroit pré-session
- Manipulation (09:30–10:00 NYC) : Judas Swing
- Distribution (10:00–16:00 NYC) : Vrai mouvement

**Sur le WEEKLY (AJOUT v4.0):**
- Accumulation : Lundi (consolidation après Seek & Destroy)
- Manipulation : Mardi (Judas Swing hebdomadaire, prend les stops de lundi)
- Distribution : Mercredi–Vendredi (vrai mouvement de la semaine)
→ Le High ou Low de la semaine = formé dans 80% des cas lundi ou mardi.

---

## 13. MMXM (Market Maker Models)

**Cycle complet :**
Consolidation → Manipulation (Judas Sweep ERL) → CHoCH → MSS → Expansion →
Retracement (OB/FVG — Point d'entrée) → Continuation vers DOL.

**Variables d'état associées:**
- Phase 1-2 : `State_of_Delivery = "ACCUMULATION"` puis `"MANIPULATION"`
- Phase 3-4 : `Boolean_Sweep_ERL = True`, `State_of_Delivery = "DISTRIBUTION"`
- Phase 5-6 : `State_of_Delivery = "RE-ACCUMULATION"` → Entrée confirmation

---

## 14. CONFLUENCES CROISÉES (Logique OU Inclusif — AJOUT v4.0)

Pour valider une entrée, croiser en logique OU inclusif :

```
IF (Price IN OTE_Zone[62-79%])
  AND (FVG_CE[50%] PRESENT in zone)
  THEN score += 15  // Confluence OTE + CE

IF (OB_quality_score >= 4)
  AND (FVG_present_after_OB)
  AND (Killzone_active)
  THEN setup_grade = "A+"

IF (Time_Based_PD_Array_match)     // Même heure que création FVG
  THEN score += 10  // Bonus temporel algorithmique

IF (COT_aligned_with_bias)
  THEN score += 5   // Validation institutionnelle externe
```