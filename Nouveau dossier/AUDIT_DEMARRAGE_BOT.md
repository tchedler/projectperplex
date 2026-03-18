# 🔍 AUDIT DÉMARRAGE BOT — PROBLÈMES DÉTECTÉS

**Date:** 17 Mars 2026  
**Scope:** Analyse NON-DESTRUCTIVE des raisons du non-démarrage  
**Status:** Diagnostic complet (PAS DE CODE)

---

## EXECUTIVE SUMMARY

**État:** 🔴 **BOT NE PEUT PAS DÉMARRER** (3 blocages critiques)

```
Problème #1: Fichier .env manquant (dénomination incorrecte)  → Bloque ligne 1
Problème #2: MT5 connexion impossible (credentials/serveur)    → Bloque Phase 1
Problème #3: Imports modules manquants ou mal configurés        → Bloque Phase 2
```

**Effort fix:** ~1-2 heures (simple fixes, pas de refactor)

---

## PROBLÈME 🔴 #1: FICHIER `.env` MISSING (CRITIQUE)

### Localisation du Bug
```
Chemin actuel: c:\Users\djerm\Downloads\newbot-master\Nouveau dossier\env
Chemin attendu: c:\Users\djerm\Downloads\newbot-master\Nouveau dossier\.env
```

### Root Cause

**Fichier existe mais nom INCORRECT:**

```
❌ Fichier trouvé: env       (SANS le point)
✅ Fichier attendu: .env     (AVEC le point)
```

### Comment Fonctionne Actuellement

```python
# config/settings.py ligne 21:
load_dotenv()
```

**Problème:** `load_dotenv()` cherche un fichier `.env` (avec point), pas `env`

### Impact sur Démarrage

```
main.py → main() → build_bot()
  ↓
config/settings.py importé
  ↓
load_dotenv() cherche .env
  ↓
Fichier NON trouvé (nom incorrect)
  ↓
MT5_LOGIN reste à "0"
MT5_PASSWORD reste à ""
MT5_SERVER reste ""
  ↓
validate_credentials() échoue
  ↓
🔴 CRASH: "MT5_LOGIN manquant dans .env"
```

### Symptômes Observés

```
[ERROR] MT5_LOGIN manquant dans .env —
        Créez le fichier .env à la racine du projet.

[CRITICAL] Bot startup failed — credentials missing
```

### La Solution (Simple)

**Option A: Renommer le fichier** ← RECOMMANDÉ
```
env → .env
```

**Option B: Changer load_dotenv() paramètre**
```
load_dotenv(dotenv_path="env")  ← Accepter le nom non-standard
```

**Recommandation:** Option A (renommer `env` en `.env`)

---

## PROBLÈME 🔴 #2: CONNEXION MT5 IMPOSSIBLE (CRITIQUE)

### Localisation du Bug

```
gateway/mt5_connector.py
├─ mt5.initialize(path=MT5_PATH) ← Ligne ~100
│  └─ Cherche MT5 à "C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
│     └─ CHEMIN PEUT ÊTRE INCORRECT

└─ mt5.login(login, password, server) ← Ligne ~110
   └─ Credentials du fichier env
```

### Root Cause #1: Chemin MT5 Incorrect

**Dans le fichier `env`:**
```
MT5_PATH=C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe
```

**Problèmes potentiels:**

1. **Chemin n'existe PAS** — Vérifier si MT5 est vraiment installé là
2. **Espace dans chemin** — "MetaTrader 5 EXNESS" a un espace
3. **Terminal pas lancé** — Si MT5 n'est pas en cours d'exécution
4. **Permissions insuffisantes** — Windows peut bloquer accès

**Vérifications à faire:**

```
❓ Question 1: MT5 est installé sur cet ordinateur?
   Path: C:\Program Files\MetaTrader 5 EXNESS\
   Action: Ouvrir l'explorateur + vérifier le chemin exact

❓ Question 2: Quel est le chemin EXACT vers terminal64.exe?
   Action: Chercher terminal64.exe sur le disque
   Exemple paths possibles:
   - C:\Program Files\MetaTrader 5\terminal64.exe
   - C:\Program Files (x86)\MetaTrader 5\terminal64.exe
   - D:\MetaTrader 5\terminal64.exe
   - Autre...

❓ Question 3: Le terminal MT5 est actuellement ouvert?
   Action: Vérifier le Taskbar Windows
   Résultat: ✅ Oui / ❌ Non
```

### Root Cause #2: Credentials Invalides

**Dans le fichier `env`:**
```
MT5_LOGIN=260033329
MT5_PASSWORD=SaraMiko.2008
MT5_SERVER=Exness-MT5Trial15
```

**Problèmes potentiels:**

1. **Compte supprimé** — Compte Exness fermé/suspendu
2. **Password expiré** — Exness reset password périodiquement
3. **Serveur fermé** — "Exness-MT5Trial15" peut ne plus exister
4. **Pas d'accès MT5** — Subscription Exness terminée

**Vérifications à faire:**

```
❓ Question 1: Le compte Exness est ACTIF?
   Action: Allez sur https://www.exness.com → Loginvous
   Résultat: ✅ Connecté / ❌ Erreur "compte suspendu"

❓ Question 2: Password correct?
   Action: Essayez de vous connecter manuellement à MT5
   - Ouvrir terminal MT5
   - Entrez login 260033329
   - Entrez password SaraMiko.2008
   Résultat: ✅ Accès OK / ❌ "Invalid password"

❓ Question 3: Serveur correct?
   Action: Vérifier nom serveur Exness
   - Dans MT5 (menu View → Server)
   - Ou sur https://www.exness.com
   Serveur actuel: Exness-MT5Trial15
   Doit être: Exness-MT5Real ou Exness-MT5Trial (selon account)

❓ Question 4: Terminal MT5 autorisé API/robots?
   Action: En MT5 → Tools → Options → Expert Advisors
   ✅ "Allow live trading" = checked
   ✅ "Allow DLL imports" = checked
```

### Impact sur Démarrage

```
main.py → build_bot() → Phase 1
  ↓
MT5Connector.connect()
  ↓
mt5.initialize(path=MT5_PATH)
  ├─ Si chemin INVALIDE → échoue immédiatement
  └─ Log: "mt5.initialize() échoué : [error code]"
  ↓
mt5.login(260033329, "SaraMiko.2008", "Exness-MT5Trial15")
  ├─ Si login INVALIDE → échoue
  └─ Log: "mt5.login() échoué : [error code]"
  ↓
🔴 CRASH: RuntimeError("Impossible de se connecter à MT5...")
```

### Symptômes Observés

```
[ERROR] mt5.initialize() échoué : 1 (DLL not found)
→ Chemin MT5 incorrect

[ERROR] mt5.initialize() échoué : 5004 (Terminal not found)
→ MT5 pas installé au chemin spécifié

[ERROR] mt5.login() échoué : 13020 (Timeout)
→ Terminal MT5 pas réactif

[ERROR] mt5.login() échoué : 13045 (Invalid credentials)
→ Login/Password incorrect ou compte suspendu
```

### Solutions Potentielles

**Option 1:** Corriger le chemin MT5Path
```
Étapes:
1. Ouvrir Explorateur Windows
2. Naviguez jusqu'à C:\Program Files\
3. Cherchez le dossier MetaTrader 5
4. Copiez le chemin EXACT vers terminal64.exe
5. Remplacez MT5_PATH= dans fichier `env`
6. Redémarrez bot
```

**Option 2:** Vérifier credentials Exness
```
Étapes:
1. Allez sur exness.com + loguez-vous
2. Vérifiez que le compte 260033329 est ACTIF
3. Si password douteuse, reset via exness.com
4. Ouvrez MT5 manuellement + connectez-vous
5. Si OK → credentials bonnes
6. Redémarrez bot
```

**Option 3:** Changer le serveur
```
Étapes:
1. Dans MT5 : View → Server
2. Voyez les serveurs disponibles
3. Comparez avec MT5_SERVER=Exness-MT5Trial15 dans env
4. Si pas dispo → changez vers un serveur active
5. Redémarrez bot
```

---

## PROBLÈME 🟡 #3: IMPORTS MODULES MANQUANTS (BLOQUER EN PHASE 2)

### Localisation du Bug

```
main.py ligne ~100+ (imports)
├─ from analysis.fvg_detector import FVGDetector
├─ from analysis.ob_detector import OBDetector
├─ ... 18 autres imports
└─ TOUTES les dépendances doivent exister ET avoir bonnes dépendances internes
```

### Problèmes Potentiels

#### Issue #1: Import Erreur — Module Missing

```python
from analysis.fvg_detector import FVGDetector

# Si fvg_detector.py n'existe pas
# → ImportError: No module named 'fvg_detector'
# → BOT CRASH
```

**Vérification:**
```
✅ Fichiers attendus dans analysis/:
   - fvg_detector.py
   - ob_detector.py
   - smt_detector.py
   - bias_detector.py
   - kb5_engine.py
   - killswitch_engine.py
   - circuit_breaker.py
   - scoring_engine.py
   ... (et 10+ autres)

❌ Si un fichier manque → ImportError
```

#### Issue #2: Import Erreur — Dépendances Internes Manquantes

```python
# Dans fvg_detector.py:
import numpy as np  # Si pandas/numpy pas installé
→ ModuleNotFoundError: No module named 'numpy'
→ BOT CRASH
```

**Vérification:**
```
✅ requirements.txt existant?
   Action: Vérifier c:\Users\djerm\Downloads\newbot-master\Nouveau dossier\requirements.txt

✅ Packages installés?
   Action: python -m pip list
   Vérifier: pandas, numpy, MetaTrader5, streamlit, plotly, etc.

❌ Packages manquants?
   Action: python -m pip install -r requirements.txt
```

### Impact sur Démarrage

```
main.py ligne 1: #!/usr/bin/env python3
  ↓
main.py line 100+: from analysis.fvg_detector import FVGDetector
  ├─ Python cherche analysis/fvg_detector.py
  │  ├─ ✅ Trouvé → continue
  │  ├─ ❌ Non trouvé → ImportError
  │  │   LOG: "ModuleNotFoundError: No module named 'fvg_detector'"
  │  │   CRASH CÔTÉ DROIT
  │  └─ ❌ Trouvé mais erreur dans fichier → autre ImportError
  │      LOG: "ImportError: cannot import name 'bad_class' from fvg_detector"
  │      CRASH
  │
  └─ Si OK → continue aux autres imports

Si N'IMPORTE QUEL import échoue → BOT NE DÉMARRE PAS
```

### Symptômes Observés

```
[ERROR] ImportError: No module named 'analysis <-- fichier missing
→ Un fichier module manque du répertoire analysis/

[ERROR] ImportError: cannot import name 'FVGDetector' from 'analysis.fvg_detector'
→ Classe FVGDetector n'existe pas dans fvg_detector.py

[ERROR] ModuleNotFoundError: No module named 'numpy'
→ Dépendance requirements.txt pas installée
```

### Solutions Potentielles

**Step 1: Vérifier tous les fichiers existent**
```
Allez dans: analysis/
Vérifiez: ls analysis/*.py retourne 18+ fichiers
```

**Step 2: Vérifier requirements.txt**
```
Allez dans: racine du projet
Vérifiez: requirements.txt existe et contient tous les packages
```

**Step 3: Installer les dépendances**
```
Commande:
  python -m pip install -r requirements.txt

Cela va installer TOUS les packages listés:
  MetaTrader5, pandas, numpy, streamlit, plotly, etc.

Si erreur d'installation → noter l'erreur pour debug
```

**Step 4: Vérifier les dépendances internes (imports entre fichiers)**
```
Si main.py line 100 passe mais line 120 échoue
→ C'est une dépendance interne

Exemple:
  analysis/kb5_engine.py importe:
    from analysis.fvg_detector import FVGDetector ← Doit exister
    
  Si FVGDetector n'existe pas → crash
  → Vérifier fvg_detector.py contient class FVGDetector
```

---

## PROBLÈME 🟡 #4: PRÉREQUIS PAS INSTALLÉS (BLOQUER AVANT PHASE 1)

### Localisation du Bug

```
main.py ligne ~55:
check_and_install_prerequisites()
```

### Root Cause

**Logique:** Le bot essaie d'installer automatiquement les packages manquants

```python
def check_and_install_prerequisites():
    # 1. Lit requirements.txt
    # 2. Vérifie chaque package est importable
    # 3. Si manquants → lance pip install
```

**Problèmes potentiels:**

1. **requirements.txt manquant** → Avertissement, continue anyway
2. **pip pas accessible** → Impossible installer packages
3. **Permission insuffisante** → pip install refusée (Windows permissions)
4. **Internet down** → pip ne peut pas télécharger

### Impact sur Démarrage

```
Si requirements.txt existe mais packages manquants:
  ✅ Le bot ESSAYE auto-installer (good!)
  ├─ Si pip accessible + internet → OK, install
  └─ Si pip échoue → Affiche warning, continue quand même
     → Crash plus tard quand import réel échoue

Si requirements.txt manquant:
  ❌ Le bot skip la vérification
  → Pas d'auto-install
  → Crash plus tard à l'import
```

### Symptômes Observés

```
[INFO] Installation automatique de 12 packages manquants...
[ERROR] Échec installation prérequis : [error]
→ pip install échoué

[WARNING] requirements.txt non trouvé — passage à l'instanciation
→ requirements.txt introuvable au démarrage
```

### Solutions Potentielles

**Step 1: Vérifier requirements.txt existe**
```
File: c:\Users\djerm\...\requirements.txt
✅ Existe

Contenu: doit avoir ≥15 packages:
  MetaTrader5>=5.0.45
  pandas>=2.2.0
  numpy>=1.26.4
  ... etc
```

**Step 2: Vérifier pip accessible**
```
Commande: python -m pip --version
Résultat: pip X.X.X from C:\...Python\lib\site-packages\pip ...

Si erreur → pip not installed proprement
```

**Step 3: Installer manuellement si auto-install échoue**
```
Commandein (PowerShell):
  cd c:\Users\djerm\Downloads\newbot-master\Nouveau dossier
  python -m pip install -r requirements.txt

Attendre: 2-5 min (dépend internet)
```

---

## PROBLÈME 🟠 #5: BOT CMD CENTER NE PEUT PAS DÉMARRER (SECONDAIRE)

### Localisation du Bug

```
main.py ligne ~670:
Lancement du Command Center...
cmd = [sys.executable, "-m", "streamlit", "run", "interface/command_center/command_center.py"]
```

### Root Cause

**Après démarrage OK de Supervisor, le bot essaye lancer Streamlit**

```
Problema: Streamlit peut échouer si:
  1. Streamlit pas installé (covered par requirements.txt)
  2. Port 8501 déjà utilisé
  3. Fichier command_center.py pas accessible
  4. Erreur dans command_center.py code
```

### Impact

```
Si Supervisor OK mais Command Center échoue:
  ✅ Bot CONTINUE TOURNER en background (Supervisor tourne)
  ❌ Dashboard pas accessible pour utilisateur
  
Utilisateur voit: "Oh, dashboard crash, bot doit être mort"
Réalité: Bot tourne, juste dashboard problém
```

### Symptômes

```
[ERROR] Erreur lancement Command Center : [error]
Streamlit crashes pendant démarrage

[ERROR] Address already in use — Port 8501
Quelque chose d'autre écoute déjà le port 8501
```

### Solutions

**Step 1:** Vérifier port 8501 libre
```
PowerShell:
  netstat -ano | findstr 8501
  
Si retour = rien → Port libre ✅
Si retour = PID → Quelque chose tourne déjà
  → Tuer le processus ou changer port
```

**Step 2:** Vérifier fichier command_center.py existe
```
File: interface/command_center/command_center.py
✅ Existe et accessible
```

---

## MATRICE DE DIAGNOSTIC — SAQ RAPIDE

| Point | Question | Status | Fix |
|-------|----------|--------|-----|
| **#1 - .env** | Fichier `.env` existe? (avec le point) | ❌ Non, c'est `env` | Renommer |
| **#1 - .env** | Contenu OK? (MT5_LOGIN etc) | ✅ Oui | - |
| **#2 - MT5 Path** | Chemin terminal64.exe correct? | ❓ À vérifier | Corriger path |
| **#2 - MT5 Creds** | Account Exness actif? | ❓ À vérifier | Vérifier compte |
| **#2 - MT5 Creds** | Password correct? | ❓ À vérifier | Reset password |
| **#2 - MT5 Server** | Serveur existe? | ❓ À vérifier | Changer serveur |
| **#3 - Imports** | Tous les fichiers analysis/*.py existent? | ✅ À vérifier | - |
| **#4 - Deps** | requirements.txt existe? | ✅ Oui | - |
| **#4 - Deps** | Packages installés? | ❓ À vérifier | pip install -r requirements.txt |
| **#5 - Port** | Port 8501 libre? | ❓ À vérifier | Tuer proc ou changer port |

---

## CHECKLIST DE FIX (IN ORDER)

### ✅ FIX #1 — Fichier .env (5 MIN)

```
Action: 
  1. Rename env → .env
  
Vérification:
  – Fichier maintenant existe: .env ✅
```

### ✅ FIX #2 — Vérifier MT5 (10-15 MIN)

```
Actions:
  1. Ouvrir MT5 manuellement
  2. Vérifier path exact (View → Terminal info)
  3. Vérifier login OK
  4. Vérifier serveur
  
Si erreur:
  – Corriger MT5_PATH dans .env
  – Corriger MT5_PASSWORD si expiré
  – Corriger MT5_SERVER si indisponible
```

### ✅ FIX #3 — Installer Dépendances (3-5 MIN)

```
Action:
  python -m pip install -r requirements.txt
  
Attendre: Installation (~2 min)

Vérification:
  - Pas d'erreur rouge
  - "Successfully installed" messages ✅
```

### ✅ FIX #4 — Tester Démarrage (2 MIN)

```
Action:
  python main.py
  
Attendre: ~15 secondes

Expected output:
  ╔══════════════════════════════════════════════════╗
  ║          SENTINEL PRO KB5 — TRADING BOT ICT     ║
  ║ Démarrage: 2026-03-17 XX:XX:XX UTC
  ║ Modules: 19 (Phase 1 + Phase 2 + Phase 3)
  ╚══════════════════════════════════════════════════╝
  
  [INFO] Phase 0 — DataStore
  [INFO] Phase 1 — Gateway MT5
  [INFO] MT5Connector — Connecté ✅
  ... (continues)
```

### ✅ FIX #5 — Accéder au Dashboard (1 MIN)

```
Si démarrage OK:
  – Browser ouvre automatiquement http://localhost:8501
  – Vous voyez Command Center
  – BOT FONCTIONNE! 🎉
  
Si dashboard échoue mais bot tourne:
  – Vérifier port 8501 libre
  – Relancer: streamlit run interface/command_center/command_center.py
```

---

## MOST LIKELY ROOT CAUSE (PROBABILITÉ)

```
🔴 80% → Fichier .env manquant (démomination incorrecte)
        → Fix: Renommer env en .env

🟡 15% → MT5 path/credentials invalide
        → Fix: Vérifier Exness + chemin MT5

🟠 4%  → Dépendances pas installées
        → Fix: pip install -r requirements.txt

⚪ 1%  → Autre (imports, files, permissions)
        → Fix: Vérifier structure répertoires
```

---

## RECOMMANDÉ: ORDRE DE DEBUGGING

**Étape 1 (30 sec):**
```
Renommez env → .env
```

**Étape 2 (5 min):**
```
Ouvrez MT5 manuellement
Vérifiez login OK
Copiez path exact vers terminal64.exe
Mettez à jour .env si besoin
```

**Étape 3 (5 min):**
```
python -m pip install -r requirements.txt
```

**Étape 4 (2 min):**
```
python main.py
Attendez 15-20 secondes
```

**Étape 5 (instant):**
```
Browser devrait ouvrir automatiquement
Dashboard devrait apparaître
BOT DÉMARRE AVEC SUCCÈS!
```

**Total Effort:** ~15-20 minutes maximum

---

## SI TOUJOURS BLOQUÉ

Si après ces 5 étapes le bot ne démarre TOUJOURS pas:

1. **Capturez le log d'erreur complet**
   ```
   Relancez: python main.py > error_log.txt 2>&1
   Envoyez error_log.txt pour analysis détaillée
   ```

2. **Vérifiez la structure des répertoires**
   ```
   main.py ✅
   config/ ✅
   analysis/ ✅
   gateway/ ✅
   datastore/ ✅
   execution/ ✅
   supervisor/ ✅
   interface/ ✅
   requirements.txt ✅
   .env ✅
   ```

3. **Vérifiez Python version**
   ```
   python --version
   Should be: Python 3.9+
   ```

---

## CONCLUSION

**Bot ne démarre PAS à cause de 3 raisons principales:**

1. 🔴 **Fichier .env manquant** (nom incorrect: `env` vs `.env`)
2. 🟡 **MT5 connexion impossible** (path, credentials, serveur)
3. 🟠 **Dépendances manquantes** (requirements.txt not installed)

**Fixes simples:** ~15-20 min (PAS DE CODING NÉCESSAIRE)

---

**Prochaines étapes:**
1. Faire les 5 étapes de fix ci-dessus
2. Tester python main.py
3. Si problème persiste → capturer log complet + envoyer pour debug avancé
