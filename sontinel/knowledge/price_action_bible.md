# 📖 La Bible Ultime du Price Action (Synthèse Brooks & Classique)

Ce document constitue le référentiel unique pour l'analyse Price Action de l'écosystème **SENTINEL**. Il fusionne la clarté du Price Action classique avec la précision chirurgicale de la méthode d'Al Brooks pour créer un système de règles non-redondantes et prêtes à l'automatisation.

---

## Chapitre 1 : Les 3 États du Cycle de Marché

Tout mouvement de prix, sur n'importe quel timeframe, appartient obligatoirement à l'une de ces trois phases. Savoir identifier l'état actuel est la condition *sine qua non* pour choisir la stratégie d'exécution.

### 1.1 Le Breakout (L'Urgence / Spike)
C'est la phase la plus violente. Un déséquilibre total où un camp (Acheteurs ou Vendeurs) prend le contrôle absolu.

*   **Analyse Visuelle** : Succession de 2 à 5 bougies de tendance fortes (Trend Bars) avec de grands corps et de petites mèches. Les bougies se ferment près de leurs extrêmes.
*   **Signaux Al Brooks** : "Gap Bar". Le point bas d'une bougie haussière est au-dessus du point haut de la bougie précédente (ou inversement).
*   **Psychologie** : Sentiment d'urgence ("FOMO"). Les traders entrent au marché à n'importe quel prix.
*   **Règle Algorithmique** : 
    *   Si corps de bougie > 70% de la taille totale (OHLC).
    *   Si clôture > 80% du range de la bougie.
    *   **Action** : Ne jamais parier contre. Entrer sur de petits Stop Orders ou sur la clôture de la première barre.

### 1.2 Le Canal (La Tendance Lente)
Une fois l'urgence passée, le marché continue dans la même direction mais de façon plus hésitante. C'est ici que la plupart des traders perdent de l'argent en entrant trop tard ou sur des pullbacks trop profonds.

*   **Analyse Visuelle** : Progression en escalier (HH/HL ou LH/LL). Apparition de bougies contraires et de mèches plus longues.
*   **Règle des "Legs"** : La tendance progresse par "poussées" (Legs) séparées par des corrections (Pullbacks).
*   **La Moyenne Mobile (EMA 20)** : Le prix tend à revenir tester l'EMA 20 régulièrement sans la traverser violemment.
*   **Règle Algorithmique** : 
    *   Présence de chevauchements (Overlaps) entre les bougies.
    *   Pente moins raide que le Breakout.
    *   **Action** : Acheter uniquement sur Pullback (Setups H1/H2) ou rejeter les tests de l'EMA 20.

### 1.3 Le Trading Range (Équilibre / Congestion)
Les deux camps sont à égalité. Le prix rebondit entre un plafond (Résistance) et un plancher (Support).

*   **Analyse Visuelle** : Succession de bougies "Doji" ou de bougies de couleurs alternées (Achat, Vente, Achat...). Manque de direction claire.
*   **Signaux Al Brooks** : "Barb Wire" (Fils barbelés). 3 bougies ou plus qui se chevauchent presque entièrement.
*   **Psychologie** : Incertitude ou accumulation. Toute tentative de sortie (Breakout) a 80% de chances d'échouer.
*   **Règle Algorithmique** : 
    *   Le prix traverse l'EMA 20 de haut en bas sans résistance.
    *   Les bollinger bands sont horizontaux.
    *   **Action** : "Buy Low, Sell High, Scalp Only". Ne pas chercher de grands mouvements.

---

### Synthèse : Le Flux Logique du Cycle

Le marché suit généralement cet ordre :
`Breakout` ➡️ `Canal` ➡️ `Trading Range` ➡️ `Nouveau Breakout`

> **Note Cruciale pour le Code** : 
> L'Agent Expert ne doit JAMAIS utiliser une stratégie de "Trading Range" (vente en haut) si le marché est en phase de "Breakout". C'est l'erreur n°1 des traders débutants.
---

## Chapitre 2 : Anatomie Chirurgicale des Barres

Dans cette Bible, nous ne traitons pas les bougies comme de simples formes, mais comme des **barres de données** révélant la balance entre pression acheteuse et vendeuse.

### 2.1 La Barre de Tendance (Trend Bar)
Indique que le marché "Always In" est dans une direction.

*   **Critères** : Corps occupant plus de 50% de la taille totale (High-Low).
*   **Signification** : Une barre de tendance haussière forte avec une petite mèche en haut signifie que les acheteurs ont gardé le contrôle jusqu'à la dernière seconde.
*   **Usage Expert** : Plusieurs barres de tendance consécutives forment un **Breakout** (cf. Chapitre 1).

### 2.2 La Barre de Signal (Signal Bar)
C'est la bougie qui précède l'entrée. Elle "donne l'alerte".

*   **Reversal Bar (Brooks)** : Une barre avec une longue mèche (au moins 1/3 de la barre) qui rejette un niveau clé.
    *   *Exemple haussier* : Le prix descend, touche un support, et remonte pour fermer dans sa moitié supérieure (Pin Bar / Hammer).
*   **Conditions de validation** :
    1.  Doit toucher un niveau magnétique (EMA 20, Support, Trendline).
    2.  Doit avoir une couleur cohérente avec le signal (ex: une barre de renversement haussier est plus forte si elle clôture haussière).

### 2.3 La Barre de Doji (Hésitation)
Le corps est petit ou inexistant.

*   **Signification** : Équilibre parfait. Pas de direction.
*   **Danger** : Ne jamais entrer sur un Doji seul. Dans un "Always In", un Doji représente souvent une pause ou un futur "Trading Range".

### 2.4 Le Concept de "Overlap" (Chevauchement)
Critère fondamental pour différencier une impulsion d'une correction.

*   **Calcul** : Si le corps de la bougie actuelle partage une zone de prix commune avec le corps de la bougie précédente.
*   **Logique Expert** :
    *   **Faute d'Overlap** = Force (Breakout).
    *   **Fort Overlap** = Faiblesse (Trading Range ou Canal lent).

### 2.5 Les Gaps de Corps (Body Gaps)
Plus précis que les gaps classiques (vides de prix).

*   **Définition** : L'espace entre la clôture de la barre N et l'ouverture de la barre N+1.
*   **Signification** : Un "Body Gap" même minime dans le sens de la tendance confirme l'urgence institutionnelle.
---

## Chapitre 3 : Dynamique des "Legs" et Pullbacks

La tendance ne monte pas en ligne droite. Elle respire. Comprendre cette respiration permet d'entrer au moment où la probabilité est la plus forte.

### 3.1 Le Concept de "Leg" (Poussée)
Une tendance est une succession de "Legs" séparés par des "Pullbacks".
*   **Leg 1** : La première poussée après un renversement ou une sortie de range.
*   **Leg 2** : La reprise de la tendance après le premier pullback. C'est statistiquement le mouvement le plus fiable à trader.

### 3.2 Le "Bar Counting" (Setups H1, H2, L1, L2)
L'une des contributions majeures d'Al Brooks. Au lieu d'utiliser des indicateurs, on compte les bougies qui tentent d'aller contre la tendance.

#### Pour une Tendance Haussière (High 1, High 2) :
1.  **H1 (High 1)** : La première bougie dont le sommet dépasse le sommet de la bougie précédente *pendant un pullback*. C'est souvent un piège (trop tôt).
2.  **H2 (High 2)** : La deuxième fois que le sommet d'une bougie dépasse celui de la précédente. **C'est le setup de base** du Price Action. Il indique que les vendeurs ont essayé deux fois de faire baisser le prix et ont échoué.

#### Pour une Tendance Baissière (Low 1, Low 2) :
1.  **L1 (Low 1)** : Première tentative de reprise de la baisse.
2.  **L2 (Low 2)** : Deuxième tentative. Signal de vente haute probabilité.

### 3.3 La Règle de la "Deuxième Tentative"
Le marché essaie toujours de faire deux fois la même chose. S'il échoue deux fois à inverser la tendance, il repart violemment dans le sens initial.
*   **Application Code** : L'expert PA cherchera prioritairement les setups **H2** et **L2**.

### 3.4 Interaction avec l'EMA 20 (La Ligne de Vie)
En Price Action Brooks, l'EMA 20 exponentielle est le seul "indicateur" toléré.
*   **Tendance Forte** : Le prix reste d'un côté de l'EMA sans jamais la toucher ("Gap Bar").
*   **Tendance Saine** : Le prix revient "embrasser" l'EMA 20 (Pullback) et repart sur un signal H2/L2.
*   **Alerte** : Si le prix traverse l'EMA 20 et clôture de l'autre côté, le canal s'affaiblit.
---

## Chapitre 4 : Niveaux Magnétiques et Objectifs

Le Price Action n'est pas seulement une question d'entrée, c'est surtout une question de **cible**. Le marché est attiré par certains niveaux comme par des aimants.

### 4.1 Les Measured Moves (MM) — La règle de symétrie
Le marché a une mémoire mathématique. Il tend à répéter la taille de ses impulsions précédentes.
*   **MM sur Leg** : Si le Leg 1 (Breakout) a fait 50 points, le Leg 2 fera très probablement 50 points après le pullback.
*   **MM sur Range** : Si le prix casse un Trading Range de 30 points de large, l'objectif minimal est de 30 points au-delà de la cassure.
*   **Usage Algorithmique** : Le bot fixera ses **Take Profit (TP)** sur ces niveaux de projection 100%.

### 4.2 Les Niveaux Magnétiques Classiques
Outre les MM, le bot doit surveiller :
1.  **Le Haut/Bas de la veille (Previous Day High/Low)** : Zones de liquidité massive.
2.  **L'Open de la session** : Un prix qui revient tester son point de départ est un signal fort.
3.  **Les Gaps de corps non comblés** : Le marché déteste laisser des vides de corps derrière lui.

### 4.3 Support et Résistance (S/R) — La Polarité
Un niveau est "Vivant". 
*   **Règle de Polarité** : Quand une résistance majeure est cassée, elle devient un support pour le prochain pullback.
*   **Validation Al Brooks** : Un test de niveau n'est valide que s'il s'accompagne d'une **Signal Bar** (Chapitre 2).

### 4.4 Gestion du Stop Loss (SL) — Trailing adaptatif
Le Price Action utilise un SL "vivant".
*   **Initial SL** : Placé 1 tick derrière la Signal Bar.
*   **Break-even** : Le SL est déplacé au point d'entrée dès que le prix a parcouru la taille de la bougie de signal.
*   **Trailing** : On déplace le SL derrière chaque nouveau point bas de pullback (HL) dans une tendance haussière.
---

## Chapitre 5 : Trading de Range et Inversions (MTR)

La phase de Trading Range est l'endroit où meurent les comptes de trading. L'expert PA doit savoir quand arrêter de chercher une tendance et quand parier sur un retournement majeur.

### 5.1 La Stratégie du Trading Range
Dans un range, le marché n'a pas d'inertie.
*   **La règle des 80%** : 80% des tentatives de cassure (Breakout) d'un range échouent.
*   **Action Algorithmique** : Vendre les Hauts, Acheter les Bas. Utiliser des Take Profits courts (Scalp) car le prix finit toujours par revenir au milieu du range (Moyenne).

### 5.2 Le Revers de Tendance Majeur (MTR — Major Trend Reversal)
C'est le signal le plus puissant pour attraper un nouveau mouvement à son début.
*   **Le processus en 3 étapes** :
    1.  **Casse de Trendline** : La tendance haussière est cassée par un mouvement baissier fort (souvent le Leg 1 d'un futur mouvement).
    2.  **Test du Haut** : Le prix remonte tester le dernier sommet haussier mais échoue à le dépasser (ou fait un "Faux Breakout").
    3.  **Signal Bar** : Une barre de signal de vente (Reversal Bar) apparaît sur le test.
*   **Cible** : Un mouvement opposé d'au moins 2 Legs.

### 5.3 Le "Failed Breakout" (Fausse Cassure)
En Price Action, une fausse cassure n'est pas une erreur, c'est un setup.
*   **Logique** : Si le prix casse un support et réintègre immédiatement le range avec une barre de tendance haussière, c'est un signal d'achat agressif pour viser le haut du range.

### 5.4 Le "Tight Trading Range" (Zone Interdite)
*   **Signe** : De nombreuses bougies Doji s'enchaînent avec beaucoup de chevauchements.
*   **Règle Algorithmique** : **Interdiction de trader**. Le risque de se faire "hacher" (Whipsaw) est trop élevé. Attendre une sortie claire par un Breakout validé.
---

## Chapitre 6 : Protocole d'Exécution et Filtres de Qualité

Pour transformer cette Bible en un Agent rentable, nous devons appliquer un protocole de filtrage strict. Un bon trader Price Action est défini par les trades qu'il **ne prend pas**.

### 6.1 La Checklist de l'Expert PA
Avant tout ordre, l'Agent doit valider ces 5 points :
1.  **Le Contexte (Tendance/Range)** : Sommes-nous dans un cycle favorable ?
2.  **La Signal Bar** : Est-elle forte ? Rejette-t-elle un niveau ?
3.  **L'Espace (Traffic)** : Y a-t-il un obstacle immédiat (EMA 20, Support) avant le premier profit ?
4.  **Le Bar Count** : Sommes-nous sur une deuxième tentative (H2/L2) ?
5.  **L'Équilibre (Risk/Reward)** : Le Stop Loss est-il raisonnable par rapport à l'objectif Measured Move ?

### 6.2 La Règle des "10 Barres" (Contre-tendance)
*   **Règle** : Ne jamais parier sur un retournement (MTR) contre une tendance forte tant que le prix n'a pas cassé sa trendline ET passé au moins 10 barres en correction.
*   **Pourquoi ?** : Les tendances fortes durent toujours plus longtemps que ce que les traders pensent.

### 6.3 Le Filtre de "Force Relative"
*   **Concept** : Si le prix casse un niveau avec une seule bougie géante, c'est un Breakout (Acheter). Si le prix casse le niveau avec 5 petites bougies hésitantes, c'est un "piège de range" (Vendre).

### 6.4 Tableau des Probabilités (Score PA)
| Setup | Contexte | Probabilité |
| :--- | :--- | :--- |
| **H2 / L2** | En tendance canal | **Élevée (70%+)** |
| **Breakout Test** | Sortie de range | **Moyenne (60%)** |
| **MTR** | Après break trendline | **Élevée (65%)** |
| **Doji Break** | En trading range | **Faible (40%)** |

---

## Chapitre 7 : Les Micro-Structures et Contractions

Les micro-structures sont la "loupe" du Price Action. Elles dictent le comportement immédiat et servent souvent de déclencheurs d'entrée ultra-précis (Scalping) ou de filtres de danger.

### 7.1 Les Micro-Canaux (Microchannels)
Un micro-canal est une tendance extrêmement serrée, visible sur le court terme, sans aucun vrai pullback.
*   **Structuration** : Une série ininterrompue de barres (généralement 3 à 5 barres ou plus) dont les plus bas (en hausse) ou les plus hauts (en baisse) ne sont jamais cassés par la barre suivante.
*   **La Règle d'Or d'Al Brooks** : **Ne jamais acheter le premier pullback** d'un micro-canal baissier, même s'il touche un support majeur. La force d'inertie est trop grande. Il faut attendre un "Double Bottom" ou une MTR (cf. Chapitre 5).

### 7.2 Les Lignes de Tendance Micro (Micro Trendlines)
*   **Définition** : Ligne reliant les extrêmes de 2 à 4 bougies consécutives.
*   **Usage** : La cassure d'une micro trendline dans le cadre d'un gros pullback est souvent le signal exact d'entrée en setup H2 ou L2 (Chapitre 3).

### 7.3 Les Contractions d'Inside Bars (iOi, ii)
Une "Inside Bar" est une bougie dont le range (High/Low) est totalement englobé par la bougie précédente. C'est l'équivalent d'un triangle sur une unité de temps inférieure.
*   **ii (Inside-Inside)** : Deux Inside Bars consécutives. C'est une compression extrême (ressort compressé). Le breakout de ces bougies donne souvent lieu à un mouvement mesuré (Measured Move).
*   **iOi (Inside-Outside-Inside)** : Figure de compression complexe indiquant un fort combat entre acheteurs et vendeurs. À trader comme un breakout de range très serré.

### 7.4 La Règle des 3 Barres Consécutives
*   **L'Urgence** : Si le marché affiche 3 grosses barres de tendance consécutives clôturant sur leurs extrêmes, les probabilités que la prochaine tentative d'inversion échoue (et crée un setup de continuation) montent à près de 80%.

---

## Chapitre 8 : Les Modèles Géométriques Classiques (Patterns)

Bien qu'Al Brooks explique tous les mouvements par des Legs et des Ranges, les algorithmes doivent être capables d'identifier les figures chartistes millénaires en raison de l'effet de "prophétie autoréalisatrice" (tout le marché les regarde).

### 8.1 Les Figures de Renversement (Reversals)
1.  **Le Double Bottom (W) / Double Top (M)**
    *   **Mathématique PA** : Un Double Bottom est simplement un "Fail Breakout" du bas d'un Trading Range ou l'échec d'un Leg 2 baissier. L'entrée se fait toujours sur la cassure de la **ligne de cou** (le plus haut du rebond central).
2.  **L'Épaule-Tête-Épaule (MTR Classique)**
    *   **Traduction PA** : C'est exactement un *Major Trend Reversal*. La première épaule est le dernier haut de tendance. La tête est le climax ou faux breakout. La seconde épaule est un Test de sommet qui échoue (Lower High).

### 8.2 Les Figures de Continuation
Ces figures traduisent de simples pullbacks (corrections) complexes avant la reprise du Breakout.
1.  **Le Drapeau (Bull/Bear Flag)**
    *   **Traduction PA** : Un canal serré allant contre la tendance principale, contenu entre deux lignes parallèles. Sa cassure est un setup de type "H1/H2" de haute qualité.
2.  **Le Triangle Symétrique**
    *   **Traduction PA** : Une série de hauts de plus en plus bas (Lower Highs) couplée à une série de bas de plus en plus hauts (Higher Lows).
    *   **Action Algorithmique** : Signe d'attente "Barb Wire". Le bot doit placer un ordre Bracket (Buy Stop au-dessus, Sell Stop en-dessous) car l'explosion est imminente mais la direction incertaine.

---

**Conclusion de la Bible** :
Le Price Action ne cherche pas à deviner le futur, il cherche à lire la balance du pouvoir actuelle. Cet Agent Expert travaillera en symbiose avec l'Expert ICT pour valider les zones de liquidité par des confirmations de chandeliers réelles, alliant ainsi structure macroéconomique et psychologie microscopique.

---
*Fin du document officiel de référence (V1 Complète).*
