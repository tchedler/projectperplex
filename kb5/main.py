#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════
SENTINEL PRO KB5 — Point d'Entrée Principal
══════════════════════════════════════════════════════════════
Responsabilités :
  - Vérifier et installer automatiquement les prérequis
  - Configurer le logging global
  - Charger la configuration depuis .env
  - Instancier les 18 modules dans l'ordre correct
  - Injecter les dépendances entre modules
  - Lancer le Command Center (nouvelle vitrine)
  - Démarrer le Supervisor (boucle bloquante)
  - Garantir l'arrêt propre en cas d'exception fatale

Ordre d'instanciation :
  0. Logging + Config
  1. DataStore
  2. MT5Connector  ← connexion MT5 vérifiée ici
  3. TickReceiver
  4. CandleFetcher
  5. OrderReader
  6. ReconnectManager
  7. FVGDetector
  8. OBDetector
  9. SMTDetector
  10. BiasDetector
  11. KB5Engine
  12. KillSwitchEngine
  13. CircuitBreaker
  14. ScoringEngine
  15. CapitalAllocator
  16. BehaviourShield
  17. OrderManager
  18. Supervisor
  19. Command Center (nouvelle UI)

Ce fichier NE CONTIENT AUCUNE logique métier.
Toute la logique est dans les modules.
══════════════════════════════════════════════════════════════
"""

import os
import sys
import subprocess
import importlib.util
import time
import webbrowser

# FIX: Python 3.14 incompatibility with protobuf C-extension metaclasses
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import logging
import threading
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from pathlib import Path

def check_and_install_prerequisites():
    """
    Vérifie et installe automatiquement les prérequis.
    - Vérifie si les packages de requirements.txt sont installés
    - Installe automatiquement si manquants
    """
    logger.info("Vérification des prérequis...")

    # Lire requirements.txt
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        logger.warning("requirements.txt non trouvé — passage à l'instanciation")
        return

    with open(requirements_file, "r") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    missing_packages = []
    
    # List of packages to skip import check (known compatibility issues)
    skip_import_check = {'streamlit', 'google-generativeai', 'nltk'}
    
    for req in requirements:
        # Extraire le nom du package (avant == ou autre)
        package_name = req.split()[0].split("==")[0].split(">=")[0].split("<=")[0]
        
        # Skip import check for problematic packages
        if package_name in skip_import_check or package_name.replace("-", "_") in skip_import_check:
            continue
            
        try:
            importlib.import_module(package_name.replace("-", "_"))
        except (ImportError, TypeError):
            # TypeError can occur with Python 3.14 + old protobuf versions
            missing_packages.append(req)

    if missing_packages:
        logger.info(f"Installation automatique de {len(missing_packages)} packages manquants...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            logger.info("Prérequis installés avec succès ✅")
        except subprocess.CalledProcessError as e:
            logger.error(f"Échec installation prérequis : {e}")
            sys.exit(1)
    else:
        logger.info("Tous les prérequis sont déjà installés ✅")


# ══════════════════════════════════════════════════════════════
# IMPORTS MODULES KB5
# ══════════════════════════════════════════════════════════════

# Config
from config.constants import Trading, Gateway, Risk, CB, KS, Score, Log
from config.settings_manager import SettingsManager
from config.settings_integration import SettingsIntegration, set_global_integration


# Phase 1 — Gateway + DataStore
from datastore.data_store          import DataStore
from gateway.mt5_connector         import MT5Connector
from gateway.tick_receiver         import TickReceiver
from gateway.candle_fetcher        import CandleFetcher
from gateway.order_reader          import OrderReader
from gateway.reconnect_manager     import ReconnectManager

# Phase 2 — Cerveau KB5
from analysis.fvg_detector         import FVGDetector
from analysis.ob_detector          import OBDetector
from analysis.smt_detector         import SMTDetector
from analysis.bias_detector        import BiasDetector
from analysis.liquidity_detector   import LiquidityDetector
from analysis.amd_detector         import AMDDetector
from analysis.pa_detector          import PADetector
from analysis.mss_detector         import MSSDetector
from analysis.choch_detector       import CHoCHDetector
from analysis.irl_detector         import IRLDetector
from analysis.kb5_engine           import KB5Engine
from analysis.killswitch_engine    import KillSwitchEngine
from analysis.circuit_breaker      import CircuitBreaker
from analysis.scoring_engine       import ScoringEngine

# Phase 3 — Exécution + Interface
from execution.capital_allocator   import CapitalAllocator
from execution.behaviour_shield    import BehaviourShield
from execution.market_state_cache  import MarketStateCache
from execution.order_manager       import OrderManager
from supervisor.supervisor         import Supervisor

# ══════════════════════════════════════════════════════════════
# CONFIGURATION LOGGING
# ══════════════════════════════════════════════════════════════

LOG_DIR      = Path("logs")
LOG_FILE     = LOG_DIR / "sentinel_kb5.log"
LOG_LEVEL    = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_MAX_MB   = int(os.getenv("LOG_MAX_MB",   "50"))
LOG_BACKUPS  = int(os.getenv("LOG_BACKUPS",   "5"))

def setup_logging() -> None:
    """
    Configure le logging global :
      - Console  : INFO + couleurs (si colorlog disponible)
      - Fichier  : DEBUG rotatif 50MB × 5 backups
    """
    LOG_DIR.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt_file    = (
        "%(asctime)s | %(levelname)-8s | "
        "%(name)-30s | %(message)s"
    )
    fmt_console = (
        "%(asctime)s | %(levelname)-8s | %(message)s"
    )
    datefmt = "%Y-%m-%d %H:%M:%S"

    # ── Handler fichier rotatif ──────────────────────────────
    fh = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_MB * 1024 * 1024,
        backupCount=LOG_BACKUPS,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(fmt_file, datefmt=datefmt)
    )
    root.addHandler(fh)

    # ── Handler console ──────────────────────────────────────
    try:
        from colorlog import ColoredFormatter
        console_fmt = ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s | "
            "%(message)s%(reset)s",
            datefmt=datefmt,
            log_colors={
                "DEBUG":    "cyan",
                "INFO":     "white",
                "WARNING":  "yellow",
                "ERROR":    "red",
                "CRITICAL": "bold_red",
            },
        )
    except ImportError:
        console_fmt = logging.Formatter(
            fmt_console, datefmt=datefmt
        )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    ch.setFormatter(console_fmt)
    root.addHandler(ch)

    # Réduire le bruit des libs tierces
    for noisy in ["urllib3", "asyncio", "MetaTrader5"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# CONFIGURATION PAIRES ACTIVES
# ══════════════════════════════════════════════════════════════

def get_active_pairs() -> list:
    """
    Charge les paires actives en priorité depuis le tableau de bord (SettingsManager),
    puis depuis l'environnement ou les défauts.

    Returns:
        list de symboles ex. ["EURUSD", "XAUUSD"]
    """
    
    settings = SettingsManager()
    user_pairs = settings.get_active_pairs()
    
    if user_pairs:
        logger.info(f"Paires chargées dynamiquement depuis l'interface utilisateur : {user_pairs}")
        return user_pairs

    env_pairs = os.getenv("ACTIVE_PAIRS", "")
    if env_pairs:
        pairs = [p.strip() for p in env_pairs.split(",")
                 if p.strip()]
        logger.info(f"Paires chargées depuis .env : {pairs}")
        return pairs

    default_pairs = getattr(
        Trading, "ACTIVE_PAIRS",
        ["EURUSD", "GBPUSD", "USDJPY",
         "XAUUSD", "US30",   "NAS100"]
    )
    logger.info(
        f"Paires par défaut utilisées : {default_pairs}"
    )
    return default_pairs

# ══════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE D'INSTANCIATION
# ══════════════════════════════════════════════════════════════

def build_bot(enable_dashboard: bool = False) -> tuple:
    # Vérification cohérence imports AVANT instanciation
    try:
        from tools.check_imports import check_all
        if not check_all():
            raise RuntimeError("Imports incohérents détectés.")
    except ImportError:
        # Fallback si tools n'est pas dans le path (peu probable ici)
        logger.warning("Avertissement : tools.check_imports non trouvé, passage à l'instanciation.")

    """
    Instancie et câble tous les modules KB5.

    Note:
        Le dashboard (interface terminal rich) est optionnel et peut être
        désactivé pour isoler le moteur principal.

    Returns:
        tuple (Supervisor, PatronDashboard|None)

    Raises:
        RuntimeError si la connexion MT5 échoue
        ImportError  si un module est manquant
    """
    logger.info("═" * 60)
    logger.info("SENTINEL PRO KB5 — Instanciation des modules")
    logger.info("═" * 60)
    # ══════════════════════════════════════════════════════════
    # SYNC UI → CERVEAU : lecture bot_config.json avant tout
    # ══════════════════════════════════════════════════════════
    # Synchronisation avec bot_config.json (UI) désormais gérée 
    # automatiquement par l'instanciation de SettingsManager()

    pairs = get_active_pairs()


    # ══════════════════════════════════════════════════════════
    # PHASE 0 — DATASTORE
    # ══════════════════════════════════════════════════════════

    logger.info("Phase 0 — DataStore")
    # MarketStateCache : pont vers le dashboard Streamlit
    # Chemin absolu pour garantir que cerveau et interface lisent le même fichier
    import os as _os
    _root = _os.path.dirname(_os.path.abspath(__file__))
    _pkl  = _os.path.join(_root, "market_state.pkl")
    msc = MarketStateCache(cache_file=_pkl)
    ds = DataStore(market_cache=msc)

    # ══════════════════════════════════════════════════════════
    # PHASE 1 — GATEWAY MT5
    # ══════════════════════════════════════════════════════════

    logger.info("Phase 1 — Gateway MT5")

    # MT5Connector — connexion obligatoire
    connector = MT5Connector()


    connected = connector.connect()
    if not connected:
        raise RuntimeError(
            "Impossible de se connecter à MT5. "
            "Vérifier login/password/server dans .env"
        )
    logger.info("MT5Connector — Connecté ✅")


    # TickReceiver
    tick_receiver = TickReceiver()

    # CandleFetcher
    candle_fetcher = CandleFetcher()

    logger.info("CandleFetcher — Chargement bougies initiales")
    for pair in pairs:
        tf_data = candle_fetcher.fetch_all_timeframes(pair)
        for tf_name, df in tf_data.items():
            if not df.empty:
                ds.set_candles(pair, tf_name, df)

    # OrderReader
    order_reader = OrderReader()

    # ReconnectManager
    reconnect_manager = ReconnectManager(
        connector      = connector,
        data_store     = ds,
        tick_receiver  = tick_receiver,
        candle_fetcher = candle_fetcher,
        active_pairs   = pairs,
    )

    # ══════════════════════════════════════════════════════════
    # PHASE 1.5 — COUCHE D'INTÉGRATION DES PARAMÈTRES
    # ══════════════════════════════════════════════════════════
    
    logger.info("Phase 1.5 — Configuration usager (SettingsIntegration)")
    
    # ✅ CRÉATION CENTRALISÉE DES PARAMÈTRES
    # Ceci permet à TOUS les modules d'accéder aux paramètres utilisateur
    settings_manager = SettingsManager("user_settings.json")
    settings_integration = SettingsIntegration(settings_manager)
    set_global_integration(settings_integration)
    
    logger.info(f"✅ SettingsIntegration activée — Profile: {settings_manager.get('profile', 'Custom')}")
    logger.info(f"✅ Paires actives: {settings_manager.get_active_pairs()}")
    
    # ══════════════════════════════════════════════════════════
    # PHASE 2 — CERVEAU KB5
    # ══════════════════════════════════════════════════════════

    logger.info("Phase 2 — Cerveau KB5")

    # Détecteurs de structures
    # ✅ CHAQUE détecteur reçoit maintenant settings_integration
    fvg_detector = FVGDetector(data_store=ds, settings_integration=settings_integration)
    ob_detector  = OBDetector(data_store=ds, settings_integration=settings_integration)
    smt_detector = SMTDetector(
        data_store=ds,
        settings_integration=settings_integration
    )

    # BiasDetector
    bias_detector = BiasDetector(
        data_store=ds,
        fvg_detector=fvg_detector,
        ob_detector=ob_detector,
        settings_integration=settings_integration
    )

    # LiquidityDetector — Radar de liquidité ICT (Sweeps, DOL, Aimants)
    # DOIT être instancié AVANT KB5Engine
    liquidity_detector = LiquidityDetector(data_store=ds, settings_integration=settings_integration)

    # AMDDetector — Power of 3 / Cycles ICT (AMD Fractal)
    # DOIT être instancié APRES LiquidityDetector (partage Asia Range)
    amd_detector = AMDDetector(
        data_store=ds,
        bias_detector=bias_detector,
        liquidity_detector=liquidity_detector,
        settings_integration=settings_integration
    )

    # PADetector -- Price Action pur (Rounds, Trendlines, Engulfing)
    pa_detector = PADetector(data_store=ds, settings_integration=settings_integration)

    # MSSDetector — Market Structure Shift (cassures avec momentum institutionnel)
    mss_detector = MSSDetector(data_store=ds, settings_integration=settings_integration)

    # CHoCHDetector — Change of Character (premiers signes de retournement LTF)
    choch_detector = CHoCHDetector(data_store=ds, settings_integration=settings_integration)

    # IRLDetector — Internal Range Liquidity (cibles TP intermédiaires précises)
    irl_detector = IRLDetector(data_store=ds, fvg_detector=fvg_detector, settings_integration=settings_integration)

    # KB5Engine -- pyramide 6 niveaux
    kb5_engine = KB5Engine(
        data_store=ds,
        fvg_detector=fvg_detector,
        ob_detector=ob_detector,
        smt_detector=smt_detector,
        bias_detector=bias_detector,
        liquidity_detector=liquidity_detector,
        amd_detector=amd_detector,
        pa_detector=pa_detector,
        mss_detector=mss_detector,
        choch_detector=choch_detector,
        irl_detector=irl_detector,
        settings_integration=settings_integration
    )

    # CircuitBreaker (avant KS + Scoring)
    circuit_breaker = CircuitBreaker(
        data_store=ds,
        order_reader=order_reader,
        mt5_connector=connector,
        settings_integration=settings_integration
    )

    # KillSwitchEngine
    killswitch_engine = KillSwitchEngine(
        data_store=ds,
        tick_receiver=tick_receiver,
        order_reader=order_reader,
        bias_detector=bias_detector,
        settings_integration=settings_integration
    )

    # ScoringEngine
    scoring_engine = ScoringEngine(
        data_store=ds,
        kb5_engine=kb5_engine,
        killswitch_engine=killswitch_engine,
        circuit_breaker=circuit_breaker,
        bias_detector=bias_detector,
        settings_integration=settings_integration
    )

    # ══════════════════════════════════════════════════════════
    # PHASE 3 — EXÉCUTION
    # ══════════════════════════════════════════════════════════

    logger.info("Phase 3 — Exécution")

    # CapitalAllocator
    capital_allocator = CapitalAllocator(
        data_store=ds,
        mt5_connector=connector,
        circuit_breaker=circuit_breaker,
        settings_integration=settings_integration
    )

    # BehaviourShield
    behaviour_shield = BehaviourShield(
        data_store=ds,
        fvg_detector=fvg_detector,
        ob_detector=ob_detector,
        bias_detector=bias_detector,
        order_reader=order_reader,
        settings_integration=settings_integration
    )

    # OrderManager
    order_manager = OrderManager(
        data_store=ds,
        mt5_connector=connector,
        order_reader=order_reader,
        capital_allocator=capital_allocator,
        circuit_breaker=circuit_breaker,
        settings_integration=settings_integration
    )

    # ══════════════════════════════════════════════════════════
    # SUPERVISOR — ORCHESTRATEUR
    # ══════════════════════════════════════════════════════════

    logger.info("Supervisor — Câblage final")

    supervisor = Supervisor(
        # Phase 1
        data_store=ds,
        mt5_connector=connector,
        tick_receiver=tick_receiver,
        candle_fetcher=candle_fetcher,
        order_reader=order_reader,
        reconnect_manager=reconnect_manager,
        # Phase 2
        fvg_detector=fvg_detector,
        ob_detector=ob_detector,
        smt_detector=smt_detector,
        bias_detector=bias_detector,
        kb5_engine=kb5_engine,
        killswitch_engine=killswitch_engine,
        circuit_breaker=circuit_breaker,
        scoring_engine=scoring_engine,
        # Phase 3
        capital_allocator=capital_allocator,
        behaviour_shield=behaviour_shield,
        order_manager     = order_manager,
        # Config
        active_pairs      = pairs,
        settings_integration=settings_integration,
        settings_manager=settings_manager,
    )

    # ══════════════════════════════════════════════════════════
    # DASHBOARD PATRON (optionnel)
    # ══════════════════════════════════════════════════════════

    dashboard = None
    if enable_dashboard:
        # Importer l'interface uniquement si elle est explicitement activée
        from interface.patron_dashboard import PatronDashboard

        logger.info("Dashboard — Instanciation")
        dashboard = PatronDashboard(
            supervisor        = supervisor,
            scoring_engine    = scoring_engine,
            killswitch_engine = killswitch_engine,
            circuit_breaker   = circuit_breaker,
            order_manager     = order_manager,
            order_reader      = order_reader,
        )
    else:
        logger.info("Dashboard désactivé (DASHBOARD_ENABLED=false).")

    logger.info("═" * 60)
    logger.info("Tous les modules instanciés — Bot prêt")
    logger.info("═" * 60)

    return supervisor, dashboard

# ══════════════════════════════════════════════════════════════
# DÉMARRAGE DASHBOARD (thread séparé)
# ══════════════════════════════════════════════════════════════

def start_dashboard(dashboard,
                     live: bool = True) -> threading.Thread:
    """
    Lance le Dashboard Patron dans un thread daemon séparé.
    Ne bloque pas le thread principal (supervisor).

    Args:
        dashboard: instance du dashboard (optionnel)
        live:      True = refresh auto, False = static

    Returns:
        threading.Thread du dashboard
    """
    t = threading.Thread(
        target=dashboard.start,
        args=(live,),
        name="KB5_DASHBOARD",
        daemon=True,
    )
    t.start()
    logger.info(
        f"Dashboard lancé en thread séparé "
        f"(live={live})"
    )
    return t

# ══════════════════════════════════════════════════════════════
# BANNIÈRE DE DÉMARRAGE
# ══════════════════════════════════════════════════════════════

def print_banner() -> None:
    """Affiche la bannière de démarrage dans les logs."""
    now = datetime.now(timezone.utc)
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║          SENTINEL PRO KB5 — TRADING BOT ICT                 ║
║                                                              ║
║  Version    : 1.0.0                                          ║
║  Démarrage  : {now.strftime('%Y-%m-%d %H:%M:%S')} UTC               ║
║  Modules    : 19 (Phase 1 + Phase 2 + Phase 3)               ║
║  Méthode    : ICT KB5 — Pyramide 6 niveaux                   ║
║                                                              ║
║  MN → W1 → D1 → H4 → H1 → M15                               ║
║  FVG + OB + SMT + Biais + KS + CB                            ║
╚══════════════════════════════════════════════════════════════╝
"""
    for line in banner.strip().split("\n"):
        logger.info(line)

# ══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════

def main() -> int:
    """
    Point d'entrée principal.
    Vérifie prérequis → Configure → Instancie → Lance Command Center.

    Returns:
        int code de sortie (0 = succès, 1 = erreur)
    """
    # ── Vérification prérequis ──────────────────────────────
    check_and_install_prerequisites()

    # ── Logging ─────────────────────────────────────────────
    setup_logging()
    print_banner()

    # ── Instanciation ───────────────────────────────────
    supervisor, dashboard = build_bot(enable_dashboard=False)  # Pas de dashboard legacy

    # ── Vérification Supervisor prêt ─────────────────────
    if not supervisor.is_ready():
        logger.critical("Supervisor non prêt — Command Center non lancé")
        return 1

    # Interface Streamlit lancée séparément via LANCER_SENTINEL_KB5.bat (port 8502)
    logger.info("Supervisor actif — Interface sur http://localhost:8502")
    logger.info("Appuyez sur Ctrl+C pour arrêter.")
    try:
        supervisor.start()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé.")
    except Exception as e:
        logger.critical(f"Erreur Supervisor : {e}")
        return 1

    return 0
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.exit(main())
