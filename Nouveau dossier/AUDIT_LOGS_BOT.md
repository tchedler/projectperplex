# 🔴 AUDIT LOGS — POURQUOI LE BOT DÉMARRE PUIS S'ARRÊTE

**Date:** 17 Mars 2026  
**Log analysé:** logs/sentinel_kb5.log  
**Status:** 🔴 **BOT NE FONCTIONNE PAS CORRECTEMENT**

---

## WHAT HAPPENS (Flux d'exécution réel)

### ✅ Étape 1: Démarrage (ligne 1-20)
```
2026-03-17 07:35:46 | SENTINEL PRO KB5 démarrage
                      Version 1.0.0
                      Modules: 19 (Phase 1 + 2 + 3)
```
**Status:** ✅ OK

---

### ✅ Étape 2: Instanciation Phase 0-3 (ligne 21-100)
```
07:35:46 | Phase 0 — DataStore
         | DataStore initialisé
         | État restauré depuis datastore_state.json ✅

07:35:47 | Phase 1 — Gateway MT5
         | Connexion à Exness MT5...
         | Connecté — Compte: 260033329 ✅
         | Balance: 463.1 USD
         | Heartbeat démarré ✅
         
         | CandleFetcher — Chargement bougies
         | 4 paires × 8 timeframes = 32 candles datasets ✅
         
07:35:49 | Phase 2 — Cerveau KB5
         | FVGDetector ✅
         | OBDetector ✅
         | SMTDetector ✅
         | BiasDetector ✅
         | KB5Engine ✅
         | CircuitBreaker ✅
         | KillSwitchEngine ✅
         | ScoringEngine ✅
         
07:35:49 | Phase 3 — Exécution
         | CapitalAllocator ✅
         | BehaviourShield ✅
         | OrderManager ✅
         
07:35:49 | Supervisor — Câblage final
         | Supervisor initialisé ✅
         | Paires: ['EURUSDm', 'GBPUSDm', 'XAUUSDm', 'USTECm']
         | Tous les modules instanciés — Bot prêt
```
**Status:** ✅ OK (tous les modules créés)

---

### ❌ Étape 3: Lancement Interface + STOP (ligne 100-102)
```
07:35:49 | Lancement du Command Center...

07:35:51 | Ouverture du navigateur : http://localhost:8501

[PUIS... LE LOG S'ARRÊTE] ← 🔴 PROBLÈME!
```

**Status:** ❌ **ARRÊT COMPLET**

---

## 🔴 LES PROBLÈMES IDENTIFIÉS

### PROBLÈME #1: Supervisor Jamais Lancé

**Code dans main.py (ligne ~600+):**
```python
def main() -> int:
    # ...
    supervisor, dashboard = build_bot(enable_dashboard=False)
    
    # PROBLÈME: No supervisor.start() called!
    # La boucle principale du bot N'EST JAMAIS LANCÉE
    
    # On lance juste Streamlit et on attend
    cmd = [sys.executable, "-m", "streamlit", "run", "..."]
    proc = subprocess.Popen(cmd)
    proc.wait()  ← Attend que Streamlit se termine
    
    return 0  ← Bot s'arrête
```

**Impact:**
```
1. Supervisor créé ✅
2. Mais JAMAIS démarré (supervisor.start() manquant)
3. Boucle analyse/exécution JAMAIS lancée
4. Bot ne peut faire aucun trade
5. Streamlit lancé et attendre indéfiniment
```

**Résultat:** Bot affiche juste le dashboard, aucun trading réel!

---

### PROBLÈME #2: Streamlit Lance ET Bloque

**Code:**
```python
proc = subprocess.Popen(cmd)
proc.wait()  ← BLOQUE ICI
```

**Timeline:**
```
Ligne 600: Lancer Streamlit
Ligne 601: time.sleep(2)
Ligne 604: webbrowser.open(url)
Ligne 607: proc.wait()  ← ATTEND QUE STREAMLIT FERME

Streamlit tourne et attend...
Bot attend Streamlit...
DEADLOCK! 🔄
```

**Quand ça s'arrête:**
- ✅ Si vous fermez Streamlit → main() retourne 0 → bot s'arrête
- ✅ Si vous fermez la console PowerShell → bot s'arrête
- ❌ Autrement, Streamlit tourne indéfiniment (bien mais pas supervisé)

---

### PROBLÈME #3: Architecture Conceptuelle Mauvaise

**L'intention (supposed):**
```
┌─ Command Center (Streamlit UI)
│  └─ Affiche l'état du bot
│
└─ Supervisor (Boucle principale)
   ├─ Analyse des paires
   ├─ Génération verdicts
   ├─ Exécution trades
   └─ Gestion risque
```

**Ce qui se passe vraiment:**
```
┌─ main() lancé
│
├─ build_bot()
│  ├─ Crée Supervisor ✅
│  ├─ Mais le laisse INACTIF ❌
│  └─ Retourne supervisor, dashboard
│
├─ Lance Streamlit
│  └─ proc.wait() BLOQUE ❌
│
└─ Retourne 0 (bot "succès")
   ❌ Aucun trading, juste UI
```

**Problème fondamental:** 
- Supervisor créé mais JAMAIS TU LANCÉ
- Main block sur Streamlit
- Aucune analyse de trading

---

## LOG EVIDENCE (Preuve dans le log)

### Ligne 101: Supervisor est créé
```
Supervisor — Câblage final
Supervisor initialisé | Paires : [...] | Cycle : 30s
```

### Ligne 102: Bot annonce qu'il est prêt
```
Tous les modules instanciés — Bot prêt
```

### MAIS: Aucun log de:
```
❌ "Démarrage de la boucle principale"
❌ "Analyse pair EURUSD ... verdict: ..."
❌ "Cycle #1 complété"
❌ "KillSwitch #1 vérifié"
❌ "Chercheur trades..."
```

**Réalité:** Le bot **NE FAIT RIEN** après le logging!

---

## GRAPH TEMPOREL

```
07:35:46 ✅ Bot démarre
         │
07:35:47 ✅ Phase 1 MT5 OK
         │
07:35:49 ✅ Tous modules chargés
         │
07:35:49 ✅ Supervisor créé
         │
07:35:49 🌍 Streamlit lancé
         │
07:35:51 🌐 Browser ouvre
         │
[SILENCE] ⏸️ proc.wait() BLOQUE
         │
         ❌ AUCUNE ANALYSE
         ❌ AUCUN TRADE
         ❌ AUCUN LOG
```

---

## SOLUTIONS POSSIBLES

### Option A: Lancer Supervisor dans Thread Séparé

**Code fix:**
```python
def main() -> int:
    supervisor, dashboard = build_bot(enable_dashboard=False)
    
    # NOUVEAU: Lancer Supervisor dans thread daemon
    sup_thread = threading.Thread(
        target=supervisor.start,
        name="KB5_SUPERVISOR",
        daemon=True
    )
    sup_thread.start()
    logger.info("Supervisor lancé en background")
    
    # PUIS: Lancer Streamlit (ne pas bloquer)
    cmd = [sys.executable, "-m", "streamlit", "run", "..."]
    proc = subprocess.Popen(cmd)
    
    # Attendre les deux: Supervisor + Streamlit
    sup_thread.join()  # Supervisor tourne indéfiniment
```

**Avantage:** 
- ✅ Supervisor tourne en background
- ✅ Streamlit tourne en foreground
- ✅ Bot trade PENDANT que UI affiche

---

### Option B: Lancer main.py en Arrière-plan ET Streamlit

**Architecture séparée:**
```
Process 1 (main.py)
  ├─ supervisor.start()  ← Boucle infinie, trading réel
  └─ Tourne indéfiniment

Process 2 (shell)
  └─ streamlit run interface/command_center/...
     └─ UI affiche l'état du Process 1
```

**Avantage:**
- ✅ Supervisor tourne VRAIMENT indéfiniment
- ✅ Streamlit peut être fermée sans arrêter le bot
- ❌ Plus complexe à déployer

---

### Option C: Fusionner Supervisor dans Streamlit

**Code:**
```python
# Dans interface/command_center/command_center.py

@st.cache_resource
def get_supervisor():
    if "supervisor" not in st.session_state:
        supervisor, _ = build_bot(enable_dashboard=False)
        supervisor.start()  ← Lanc dans Streamlit
        st.session_state.supervisor = supervisor
    return st.session_state.supervisor
```

**Avantage:**
- ✅ Single process
- ✅ UI et Bot intégrés
- ❌ Streamlit peut lag si bot trop lent

---

## CONCLUSION

**Pourquoi le bot démarre puis s'arrête:**

1. ✅ Bot démarre, charge tous les modules = OK
2. ✅ Crée le Supervisor = OK
3. ❌ **NE LANCE JAMAIS supervisor.start()** = PROBLÈME
4. ❌ Lance Streamlit et bloque sur proc.wait() = BLOQUE
5. ❌ Aucun trading, juste UI affichée

**Root cause:** `supervisor.start()` manquant dans main()

**Impact:** 
- Bot NE TRADE PAS
- Juste une UI statique
- Pas d'analyse en temps réel

**Effort fix:** ~10 lignes (ajouter threading)

---

## COMMANDS À AJOUTER

**Dans main.py, fonction main(), après `build_bot()`:**

```python
def main() -> int:
    # ... existant code ...
    supervisor, dashboard = build_bot(enable_dashboard=False)
    
    # ← AJOUTER CECI:
    import threading
    
    sup_thread = threading.Thread(
        target=supervisor.start,
        name="KB5_SUPERVISOR_MAIN",
        daemon=False
    )
    sup_thread.start()
    logger.info("Supervisor — Boucle principale lancée en thread")
    
    # ← FIN AJOUT
    
    # Reste du code Streamlit...
    logger.info("Lancement du Command Center...")
    try:
        cmd = [sys.executable, "-m", "streamlit", "run", "interface/command_center/command_center.py"]
        proc = subprocess.Popen(cmd)
        
        time.sleep(2)
        url = "http://localhost:8501"
        logger.info(f"Ouverture du navigateur : {url}")
        webbrowser.open(url)
        
        proc.wait()  ← Attend Streamlit (pas le bot)
    except Exception as e:
        logger.critical(f"Erreur Streamlit : {e}")
        return 1
    
    return 0
```

---

## STATUS FINAL

**Diagnostic:** 🔴 **SUPERVISOR NE TOURNE PAS**

**Evidence:**
- ✅ Tous les modules créés
- ❌ Boucle principale jamais lancée
- ❌ Aucun log d'analyse/trading


**Fix:** Ajouter `supervisor.start()` dans thread (10 lignes, no coding complexity)

