# 📊 PROFILS DE TRADING ET TIMEFRAMES ICT (Précision Michel) v2.1
# CHANGELOG v2.1 : Correction TF Day Trading et Scalp (alignement Mentorship 2022/2023),
#                  Ajout règle Risk unifiée, navigation inter-TF enrichie

Ce document définit les hiérarchies de timeframes et les plans de trading intelligents pour chaque catégorie, conformément aux enseignements d'ICT.

> ⚠️ **Règle de Risk Universelle (tous profils)** : Max **1% par trade**, max **5% d'exposition totale ouverte**.

---

## 1. LONG TERME (Position Trading)
*Cible : Mouvements macro-économiques et institutionnels à grande échelle.*

| Flux | Timeframe | Rôle Algorithmique |
|---|---|---|
| **HTF (Context)** | **MN (Monthly)** | Seasonal Tendencies, Quarterly Theory, Highs/Lows annuels. |
| **LTF (Execution)** | **W1 (Weekly)** | Structure W1, MSS sur W1, entrée sur PD Array Hebdomadaire. |

**Narration Intelligente :**
L'analyse mensuelle définit le "Where is price going?" (DOL). L'hebdomadaire cherche la "Confirmation de départ" (MSS). On entre sur le retracement Weekly pour viser des cibles trimestrielles.

**COT Integration :** Lire le COT chaque vendredi. Si Non-Commercial positions alignées avec la direction → Confiance maximale pour position trading.

---

## 2. MOYEN TERME (Swing Trading)
*Cible : Le Weekly Template (Distribution de la bougie hebdomadaire).*

| Flux | Timeframe | Rôle Algorithmique |
|---|---|---|
| **HTF (Context)** | **D1 (Daily)** | Daily Bias, Midnight Open, PDH/PDL, Liquidity Gaps. |
| **MTF (Filter)** | **H4 (4h)** | Structure intermédiaire, alignement avec le biais D1. |
| **LTF (Execution)** | **H2 (2h)** | Précision chirurgicale pour l'entrée (OB, FVG ou Breaker). |

**Narration Intelligente :**
On utilise le Daily pour la direction du jour. Le 4H sert à filtrer le bruit. Le 2H (préféré par Michel pour le Swing) permet d'identifier l'entrée exacte sans attendre le 1H qui peut être trop bruyant pour du Swing.

**AMD Weekly :** Sur le swing, identifier la phase AMD hebdomadaire :
- Lundi = Accumulation / Seek & Destroy → Ne pas entrer
- Mardi = Manipulation potentielle → Attendre le Judas Sweep
- Mercredi+ = Distribution → Entrée sur pullback dans FVG/OB H2

---

## 3. COURT TERME (Day Trading / Short-term)
*Cible : La session de la journée (London / NY).*

> ⚠️ **CORRECTION v2.1** : L'alignement tri-temporel a été corrigé selon le Mentorship 2022/2023.
> Entrer au M15 est trop imprécis selon ICT — cela génère un drawdown élevé.

| Flux | Timeframe | Rôle Algorithmique |
|---|---|---|
| **HTF (Direction)** | **H1 (1h)** | Market Structure H1, Sessions Highs/Lows, DOL identification. |
| **MTF (Setup/Filter)** | **M15 (15m)** | Identification des zones OTE et PD Arrays de session, validation du narratif. |
| **LTF (Entry)** | **M5 (5m)** | MSS avec Displacement confirmé, Silver Bullet, Entrée finale précise. |

**Narration Intelligente :**
H1 donne la structure de la session et le DOL. M15 identifie la zone d'intérêt (POI) et valide le narratif. M5 attend le MSS pour l'entrée précise. Ce tri-temporel réduit significativement le drawdown vs l'ancien H1/M30/M15.

---

## 4. SCALP (Ultra Court Terme)
*Cible : Réactions de liquidité rapides intra-session.*

> ⚠️ **CORRECTION v2.1** : ICT utilise M15 comme HTF pour le scalp (pas M5),
> et M1 comme LTF d'exécution. Pour des entrées ultra-précises, il descend même
> aux secondes (30s/15s) dès lors que M1 dessine un retournement intra-barres.

| Flux | Timeframe | Rôle Algorithmique |
|---|---|---|
| **HTF (Context)** | **M15 (15m)** | Structure locale, DOL immédiat, identification EQH/EQL proches. |
| **MTF (Setup)** | **M5 (5m)** | Validation de la zone (OB, FVG), confirmation Sweep local. |
| **LTF (Execution)** | **M1 (1m)** | Entrée Sniper sur MSS M1, SMT Divergence locale, IFVG, Volume Imbalance. |
| **Ultra-Précision** | **30s / 15s** | Entrée intra-barre sur retournement M1 à proximité d'une zone M15 POI. |

**Narration Intelligente :**
M15 montre où sont les BSL/SSL les plus proches. M5 valide la zone de réaction attendue.
M1 est l'outil d'exécution pur : le MSS sur M1 dans une zone M15 = signal d'entrée scalp.
SL maximum : 10–15 pips. Target : CE du FVG supérieur ou EQH/EQL le plus proche.

---

## 🎯 LOGIQUE DE NAVIGATION INTER-TIMEFRAMES v2.1

L'IA doit suivre ce protocole de pensée :

1. **Direction** : Toujours déterminée par le timeframe HTF du profil.
2. **Zone** : Toujours cherchée en zone de Discount/Premium du range HTF.
3. **Trigger** : Toujours un MSS avec Displacement sur le timeframe d'exécution.
4. **Invalidation** : Si le timeframe HTF casse sa structure inverse → Trade abandonné.
5. **Scoring** : Chaque profil utilise le même scoring 100 pts de `ict_detection_rules.md`

**Règles communes à tous les profils :**
- Jamais d'entrée HORS d'une Killzone ou Macro algorithmique
- Jamais de trade si `Boolean_Sweep_ERL == False`
- Jamais de trade si `State_of_Delivery` est `ACCUMULATION` ou `UNKNOWN`
- Le DOL doit toujours être identifié AVANT l'entrée (pas après)

---

## 🔀 5. CRITÈRES DE SWITCH (Changement de Profil Dynamique)

L'Agent ou le trader peut passer d'un profil à l'autre selon les conditions de marché :

- **Scalp → Day Trade** : Si la volatilité est faible (ATR réduit) mais que l'IOF HTF est extrêmement clair. On cherche alors à tenir la position sur une session entière plutôt qu'à sortir sur une réaction M1.
- **Day Trade → Scalp** : Si le marché est en "Seek and Destroy" (Lundis, pré-FOMC). Les targets long terme sont peu probables, on privilégie les prises de liquidité rapides (sweeps) sur M1.
- **Switch Interdit** : Ne jamais basculer sur un timeframe inférieur (ex: M5 → M1) pour "sauver" un trade perdant. C'est du **Revenge Trading** algorithmique.

---

## 🧠 6. RÈGLES PSYCHOLOGIQUES ET DISCIPLINE

Conformément à l'enseignement de Michel sur la longévité du trader :

- **Max Trades par Session** : 3 trades maximum. Au-delà, l'acuité cognitive (ou celle des filtres de l'IA) diminue.
- **Règle des 2 Pertes** : Après 2 pertes consécutives dans une session → **ARRET IMMÉDIAT** (Trade-Lock). Le marché n'est pas synchronisé avec votre modèle actuel.
- **Retrait de Profit** : Après un gain de +3R, fermer l'ordinateur. Le marché tend à reprendre ce qu'il a donné si on reste exposé par gourmandise.
- **Anti-Overtrading** : Si aucun setup n'atteint le score de 80/100 après 2h d'observation → Session considérée comme "No-Trade".

## 📋 MATRICE DE SÉLECTION DU PROFIL

| Critère | Long Terme | Swing | Day Trade | Scalp |
|---|---|---|---|---|
| Temps disponible | Hebdomadaire | Quotidien | 2-4h/jour | 30min-2h/jour |
| TF d'entrée | W1 | H2 | M5 | M1/30s |
| SL typique | **Structure Swing** \* | 50-100 pips | 20-30 pips | 5-15 pips |
| RR minimum | 1:4 | 1:3 | 1:2 | 1:2 |
| Macros ciblées | Non utilisées (HTF) | Toutes | London + NY AM | Silver Bullet |
| Fréquence trades | 1-4/mois | 2-8/semaine | 1-3/jour | 3-8/session |

> \* **SL Long Terme** : ICT n'utilise JAMAIS de SL en pips fixes pour les positions long terme.
> Le SL est toujours placé sous/sur le swing structurel majeur (Monthly ou Weekly Low/High).
> La taille de position est calculée en conséquence pour respecter la limite de 1% du capital.
