"""
bot_runner.py — Boucle Principale du Bot de Trading ICT
Coordonne le SmartScheduler, ProOrchestrator, TradingJudge,
OrderManager et TradeJournal pour un trading autonome.

Usage :
    python bot_runner.py                    # Charge config depuis data/bot_config.json
    python bot_runner.py --dry-run          # Dry run (n'exécute pas d'ordres)
    python bot_runner.py --config custom.json
"""
import sys
import os
import time
import json
import datetime
import argparse
import logging
import logging.handlers  # I6 FIX : Rotating logs
import pytz # type: ignore
import threading

# Assure que le répertoire racine est dans le PATH
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Force l'encodage de la console en UTF-8 pour Windows
reconfig = getattr(sys.stdout, 'reconfigure', None)
if reconfig is not None:
    try:
        reconfig(encoding='utf-8')
    except Exception:
        pass

# I6 FIX : RotatingFileHandler — max 5 Mo par fichier, 3 fichiers de rotation
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            "data/bot.log",
            encoding="utf-8",
            maxBytes=5 * 1024 * 1024,   # 5 Mo max par fichier
            backupCount=3,              # 3 fichiers de rotation (bot.log, bot.log.1, bot.log.2)
        ),
    ]
)
log = logging.getLogger("ICT_BOT")

# --- Imports agents ---
from agents.ai_supreme_judge import AISupremeJudge # type: ignore
from agents.order_manager    import OrderManager # type: ignore
from agents.trade_journal    import TradeJournal # type: ignore
from core.market_state_cache import MarketStateCache # type: ignore
from agents.smart_scheduler  import SmartScheduler # type: ignore
from agents.trading_judge    import TradingJudge # type: ignore
from core.orchestrator       import ProOrchestrator # type: ignore

try:
    import MetaTrader5 as mt5 # type: ignore
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

# ============================================================
# CONFIGURATION
# ============================================================
CONFIG_PATH  = os.path.join(ROOT_DIR, "data", "bot_config.json")
DEFAULT_LOOP = 60   # secondes entre chaque cycle

def load_config(path: str = CONFIG_PATH) -> dict:
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {
        "profile":          "DAY_TRADE",
        "mode":             "PAPER",
        "symbols_watched":  ["XAUUSD"],
        "score_execute":    80,
        "score_limit":      65,
        "risk_pct":         1.0,
        "account_balance":  10000,
        "max_positions":    3,
        "trailing_sl":      True,
        "partial_tp":       True,
        "max_session_trades": 3,
        "max_session_losses": 2,
    }


# ============================================================
# CLASSE PRINCIPALE DU BOT
# ============================================================
class ICTTradingBot:
    """
    Agent de trading ICT autonome.
    Coordonne tous les agents et la boucle d'exécution.
    """

    def __init__(self, config: dict, dry_run: bool = False):
        self.config   = config
        self.dry_run  = dry_run
        self.running  = False
        self.tz       = pytz.timezone("America/New_York")

        # Forcer PAPER en dry_run
        if dry_run:
            self.config["mode"] = "PAPER"
            log.info("🧪 Mode DRY RUN actif — aucun ordre réel.")

        # Instanciation des modules
        self.journal   = TradeJournal(db_path=os.path.join(ROOT_DIR, "data", "trades.db"))
        self.judge     = TradingJudge(config=config)
        self.ai_judge  = AISupremeJudge(score_execute=config.get("score_execute", 80))
        self.orders    = OrderManager(config=config, journal=self.journal)
        # M8 FIX : Notifications Telegram pour les signaux A+
        try:
            from agents.telegram_notifier import TelegramNotifier # type: ignore
            self.telegram = TelegramNotifier()
        except Exception:
            self.telegram = None

        # Un SmartScheduler INDÉPENDANT par symbole (multi-paires sans blocage)
        self.schedulers: dict = {
            sym: SmartScheduler(symbol=sym, profile=config.get("profile", "DAY_TRADE"))
            for sym in config.get("symbols_watched", ["XAUUSD"])
        }

        # Cache d'orchestrateurs : UN PAR SYMBOLE, créé une seule fois (correction CRIT-2)
        # Évite de recréer 8 agents à chaque cycle d'analyse
        self.orchestrators: dict = {
            sym: ProOrchestrator(sym)
            for sym in config.get("symbols_watched", ["XAUUSD"])
        }

        # Initialiser le cache global HTF
        self.market_cache = MarketStateCache()

        # Cache local des derniers résultats d'analyse par symbole
        self.latest_results: dict = {}   # {symbol: {tf: analyse_result}}
        self.latest_signals: dict = {}   # {symbol: {tf: TradeSignal}}
        self.symbol_threads: dict = {}   # {symbol: Thread}

        log.info(
            f"🤖 ICT Trading Bot initialisé | Profil: {config.get('profile')} | "
            f"Mode: {config.get('mode')} | "
            f"Symboles: {', '.join(config.get('symbols_watched', []))}"
        )

    # ============================================================
    # CONNEXION MT5
    # ============================================================
    def _connect_mt5(self) -> bool:
        if not MT5_AVAILABLE:
            log.warning("MetaTrader5 non installé — mode Paper only.")
            return False
        if not mt5.initialize():
            log.error(f"MT5 initialize() échoué: {mt5.last_error()}")
            return False
        info = mt5.account_info()
        if info:
            log.info(f"✅ MT5 connecté | Compte: {info.login} | Balance: {info.balance}$")
            self.config["account_balance"] = info.balance
            self.judge.update_config(self.config)
        return True

    # ============================================================
    # ACCÈS À L'ORCHESTRATEUR (depuis le cache — correction CRIT-2)
    # ============================================================
    def _get_orchestrator(self, symbol: str):
        """Retourne l'orchestrateur mis en cache pour ce symbole.
        Si le symbole n'existe pas encore (ajout dynamique), le crée et le met en cache.
        Plus d'import depuis main.py.
        """
        if symbol not in self.orchestrators:
            log.info(f"Création d'un nouvel orchestrateur pour {symbol}")
            self.orchestrators[symbol] = ProOrchestrator(symbol, self.config)
        return self.orchestrators[symbol]

    # ============================================================
    # ANALYSE D'UN TF POUR UN SYMBOLE
    # ============================================================
    def _analyze_tf(self, symbol: str, tf: str) -> dict | None:
        """
        Lance l'analyse ICT complète pour un TF donné.
        Réutilise les agents existants via ProOrchestrator.
        """
        try:
            orch = self._get_orchestrator(symbol)
            if orch is None:
                return None

            df = orch._fetch_pro(tf)
            if df is None or len(df) < 50:
                log.warning(f"[{symbol}/{tf}] Données insuffisantes")
                return None

            # Lancer tous les agents
            clock  = orch.time_ac.get_audit()
            smc    = orch.smc_ac.analyze(df, clock=clock)
            liq    = orch.liq_ac.analyze(df, tf=tf)  # AUDIT #10 FIX : passer tf pour fenêtre adaptative
            exe    = orch.exe_ac.analyze(df, smc, liq) if smc and liq else None
            mmxm   = orch.mmxm_ac.get_model(df, clock, smc, liq) if smc and liq else None

            # Biais HTF (Stratégie de Cache Event-Driven)
            # Vérifier si c'est l'heure de le rafraîchir ou si le cache est vide
            bias = self.market_cache.get_global_bias(symbol)
            
            # On recalcule le biais seulement au 1er lancement ou si la bougie D1 vient de clore (via scheduler condition).
            # On le lie à la ré-analyse du timeframe "D1" si "D1" est dans les timeframes à refresh (ou au tout premier cycle).
            if bias is None or tf == "D1": 
                try:
                    d1_df  = orch._fetch_pro("D1")
                    w1_df  = orch._fetch_pro("W1")
                    mn_df  = orch._fetch_pro("MN")
                    bias   = orch.bias_ac.analyze(d1_df, w1_df, mn_df)
                    
                    # Sauvegarder dans le cache global persistant
                    self.market_cache.update_global_bias(symbol, bias)
                    log.info(f"[{symbol}/HTF] 🌐 Biais HTF actualisé et mis en cache : {bias.get('htf_bias', 'UNKNOWN')}")
                except Exception as e:
                    log.warning(f"Erreur actualisation biais HTF pour {symbol}: {e}")
                    if bias is None:
                        bias = {"htf_bias": "UNKNOWN", "draw_on_liquidity": {"name": "UNKNOWN", "price": 0, "dist": 0}}

            # Checklist et score (MOY-9 FIX : réutiliser l'instance de l'orchestrateur)
            checklist_result = {"score": 0, "verdict": "NO_DATA"}
            if all([smc, liq, bias, exe, mmxm]):
                _, score, verdict = orch.chk_ac.generate(tf, smc, liq, bias, exe, mmxm, clock)
                checklist_result = {"score": score, "verdict": verdict}

            smt_res = None
            if smc:  # MOY-4 FIX : SMT Divergence analysée sur TOUS les TFs, pas juste M15 et H1
                try: 
                    smt_res = orch.smt_ac.analyze_smt(df)
                except Exception as e:  # MOY-1 FIX : logger l'erreur silencieuse
                    log.warning(f"[{symbol}/SMT] Erreur SMT Divergence pour TF {tf} : {e}")

            return {
                "clock":            clock,
                "smc":              smc,
                "liq":              liq,
                "exe":              exe,
                "mmxm":             mmxm,
                "smt_result":       smt_res,
                "bias":             bias,
                "checklist":        checklist_result,
                "df":               df,
            }

        except Exception as e:
            log.error(f"[{symbol}/{tf}] Erreur analyse: {e}", exc_info=True)
            return None

    # ============================================================
    # CYCLE D'ANALYSE LENTE (HTF)
    # ============================================================
    def _slow_loop_symbol(self, symbol: str, loop_interval: int):
        """
        Thread dédié à l'analyse lourde pour UN SEUL symbole.
        Chaque paire a son propre scheduler et tourne en totale indépendance.
        """
        scheduler = self.schedulers[symbol]
        log.info(f"🐢 [SLOW LOOP/{symbol}] Démarrée.")

        if symbol not in self.latest_results:
            self.latest_results[symbol] = {}

        while self.running:
            cycle_start = time.time()
            try:
                # 1. Mettre à jour le statut global (seul le 1er thread le fait)
                if list(self.schedulers.keys())[0] == symbol:
                    all_symbols = self.config.get("symbols_watched", [])
                    now_str = datetime.datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S")
                    self.market_cache.update_bot_status(self.running, now_str, all_symbols)

                # 2. Identifier les TF à rafraîchir pour CE symbole
                tfs_to_refresh = scheduler.get_tfs_to_refresh()
                if tfs_to_refresh:
                    log.info(f"🔄 [{symbol}] TF a analyser : {', '.join(tfs_to_refresh)}")

                for tf in scheduler.active_timeframes:
                    needs_refresh = (tf in tfs_to_refresh) or (not scheduler.has_cache(tf))
                    if needs_refresh:
                        result = self._analyze_tf(symbol, tf)
                        if result:
                            scheduler.update_analysis(tf, result)
                            # Ne loguer que si le score a changé
                            old = self.latest_results.get(symbol, {}).get(tf, {})
                            old_score = old.get("checklist", {}).get("score", -1) if old else -1
                            new_score = result["checklist"]["score"]
                            self.latest_results[symbol][tf] = result
                            self.market_cache.update_symbol_tf(symbol, tf, result)
                            if new_score != old_score:
                                log.info(
                                    f"[{symbol}/{tf}] Score: {new_score}/100 "
                                    f"| {result['checklist']['verdict']}"
                                )
                        else:
                            cached = scheduler.get_cached(tf)
                            if cached:
                                self.latest_results[symbol][tf] = cached
                    else:
                        cached = scheduler.get_cached(tf)
                        if cached:
                            self.latest_results[symbol][tf] = cached

            except Exception as e:
                log.error(f"[{symbol}] Erreur slow loop: {e}", exc_info=True)

            elapsed = time.time() - cycle_start
            time.sleep(max(0.0, float(loop_interval) - float(elapsed)))

    # ============================================================
    # CYCLE D'EXÉCUTION RAPIDE (TICK / M1)
    # ============================================================
    def _fast_loop_worker(self):
        """
        Thread dédié à l'évaluation rapide des signaux, au placement
        d'ordres et au suivi dynamique des positions.
        """
        log.info("⚡ [FAST LOOP] Démarrée.")
        FAST_INTERVAL = 3  # secondes entre chaque check rapide
        last_config_mtime = 0.0

        # I5 FIX : Attendre que la slow loop ait fait sa première analyse
        # pour éviter de tourner sur des données vides au démarrage
        log.info("⚡ [FAST LOOP] Attente initiale 20s pour laisser la slow loop charger les données...")
        time.sleep(20)

        while self.running:
            try:
                # Rechargement dynamique de la configuration locale (IMP-8 FIX)
                if os.path.exists(CONFIG_PATH):
                    current_mtime = os.path.getmtime(CONFIG_PATH)
                    if current_mtime > last_config_mtime:
                        new_config = load_config(CONFIG_PATH)
                        self.config.update(new_config)
                        self.judge.update_config(self.config)
                        self.orders.update_config(self.config)
                        last_config_mtime = current_mtime

                symbols = self.config.get("symbols_watched", [])
                
                for symbol in symbols:
                    if symbol not in self.latest_signals:
                        self.latest_signals[symbol] = {}

                    from agents.smart_scheduler import PROFILE_TFS # type: ignore
                    profile_tfs = PROFILE_TFS.get(self.config.get("profile", "DAY_TRADE"), ["M15"])
                    # On évalue tous les TF d'entrée actifs du profil
                    entry_tfs = profile_tfs

                    # AUDIT #5 FIX — Vérification du drawdown maximum de session
                    # Si le bot a perdu plus que drawdown_max_pct% du capital, on arrête les ordres.
                    dd_max_pct = self.config.get("drawdown_max_pct", 5.0) / 100.0
                    session_loss_money = getattr(self.orders, 'session_loss_money', 0.0)
                    account_bal = self.config.get("account_balance", 10000)
                    if account_bal > 0 and session_loss_money >= account_bal * dd_max_pct:
                        log.warning(
                            f"[{symbol}] ⚠️ DRAWDOWN MAX ATTEINT ({session_loss_money:.2f}$ / "
                            f"{account_bal * dd_max_pct:.2f}$ autorisé) — Trading suspendu pour cette session."
                        )
                        continue  # Passer au prochain symbole sans évaluer les signaux
                    
                    best_signal = None
                    best_sig_ctx = None
                    
                    # 1. Évaluer chaque TF d'entrée pour trouver le meilleur Setup
                    for tf in entry_tfs:
                        result = self.latest_results.get(symbol, {}).get(tf)
                        if result and result.get("clock") and result.get("bias") and result.get("checklist"):
                            
                            # --- Évaluer le signal brut ---
                            signal = self.judge.evaluate(
                                symbol        = symbol,
                                tf            = tf,
                                clock         = result["clock"],
                                bias          = result["bias"],
                                smc           = result["smc"],
                                liq           = result["liq"],
                                exe           = result["exe"],
                                mmxm          = result["mmxm"],
                                checklist_result = result["checklist"],
                                open_positions = self.orders.open_position_count(),
                                session_losses = self.orders.session_losses,
                                session_trades = self.orders.session_trades,
                            )
                            # I7 FIX : Vigilance NoneType
                            if signal is not None:
                                # Stockage itératif
                                if signal.timeframe:
                                    self.latest_signals[symbol][signal.timeframe] = signal.to_dict()
                                
                                # On retient le meilleur signal qui propose une entrée
                                if signal.action in ["EXECUTE", "LIMIT"]:
                                    current_score = getattr(signal, "score", 0)
                                    best_score = getattr(best_signal, "score", 0) if best_signal else -1
                                    if best_signal is None or current_score > best_score:
                                        best_signal = signal
                                        best_sig_ctx = {
                                            "clock": result["clock"],
                                        "bias": result["bias"],
                                        "smc": result["smc"],
                                        "mmxm": result["mmxm"]
                                    }
                            elif signal is not None and signal.action == "NO_TRADE" and getattr(signal, "score", 0) >= self.config.get("score_limit", 65):
                                # Log why a potentially good setup was rejected
                                log.info(f"[{symbol}/{tf}] Setup rejected (Score: {getattr(signal, 'score', 0)}). Reason: {getattr(signal, 'reason', 'Unknown')}")

                    # 2. IA Supreme Judge & Exécution MT5 (uniquement sur le meilleur signal)
                    if best_signal:
                        # --- CRIT-3 FIX : Blindage de l'AI Judge ---
                        # Si l'IA plante (NameError, réseau, quota), on garde le signal ICT brut
                        # Le bot NE DOIT PAS s'arrêter de trader à cause d'une IA défaillante.
                        try:
                            final_signal = self.ai_judge.evaluate_signal(best_signal, best_sig_ctx)
                        except Exception as ai_err:
                            log.warning(
                                f"[{symbol}] ⚠️ AI Judge indisponible ({type(ai_err).__name__}: {ai_err}) "
                                f"— Signal ICT conservé sans validation IA."
                            )
                            final_signal = best_signal  # Conserver le signal brut ICT

                        # I7 FIX : Vérification final_signal non-None et narrowing
                        if final_signal is not None and best_signal is not None:
                            # Mettre à jour l'UI avec le verdict final de l'IA (si elle refuse)
                            tf_sig = best_signal.timeframe
                            if tf_sig:
                                self.latest_signals[symbol][tf_sig] = final_signal.to_dict()

                            # --- Placer l'ordre si l'IA valide (ou si IA indisponible) ---
                            if final_signal.action in ["EXECUTE", "LIMIT"]:
                                # M12 FIX : Anti-duplication (Bible ICT : ne pas sur-trader le même actif)
                                if self.orders.is_symbol_under_management(symbol):
                                    log.info(f"🚫 SIGNAL [{final_signal.action}] ignoré pour {symbol} : déjà une position ou un ordre en cours.")
                                else:
                                    fs = final_signal # Narrowing pour Pyre
                                    log.info(
                                        f"🎯 SIGNAL [{fs.action}] {fs.direction} {symbol} "
                                        f"| TF: {fs.timeframe} | Score: {fs.score} "
                                        f"| Setup: {fs.setup_name} "
                                        f"| E:{fs.entry:.5f} SL:{fs.sl:.5f} TP:{fs.tp2:.5f}"
                                    )
                                    self.orders.place_order(fs)
                                    # M8 FIX : Notification Telegram sur signal A+
                                    if self.telegram:
                                        try:
                                            self.telegram.notify_signal_a_plus(fs)
                                        except Exception:
                                            pass  # Ne pas bloquer le bot si Telegram échoue


                    # --- Mise à jour en temps réel des positions ouvertes ---
                    update_tf = entry_tfs[0] if entry_tfs else "M15"
                    if MT5_AVAILABLE:
                        tick = mt5.symbol_info_tick(symbol)
                        if tick:
                            price = tick.bid # ou ask
                            smc_entry = self.latest_results.get(symbol, {}).get(update_tf, {}).get("smc")
                            self.orders.update_all_positions(price, smc_m15=smc_entry)
                    else:
                        current_bf = self.latest_results.get(symbol, {}).get(update_tf, {}).get("df")
                        if current_bf is not None and len(current_bf) > 0:
                            price = float(current_bf["Close"].iloc[-1])
                            smc_entry = self.latest_results.get(symbol, {}).get(update_tf, {}).get("smc")
                            self.orders.update_all_positions(price, smc_m15=smc_entry)

            except Exception as e:
                log.error(f"Erreur dans la fast loop: {e}", exc_info=True)

            time.sleep(FAST_INTERVAL)

    def _get_entry_tf(self) -> str:
        """Retourne le TF d'entrée selon le profil."""
        from agents.smart_scheduler import PROFILE_TFS  # type: ignore
        profile_tfs = PROFILE_TFS.get(self.config.get("profile", "DAY_TRADE"), ["M15"])
        # Le TF d'entrée est le plus petit TF du profil
        tf_order = ["M1", "M5", "M15", "H1", "H2", "H4", "D1", "W1", "MN"]
        for tf in tf_order:
            if tf in profile_tfs:
                return tf
        return "M15"

    # ============================================================
    # BOUCLE PRINCIPALE
    # ============================================================
    def start(self, loop_interval: int = DEFAULT_LOOP):
        """Lance la boucle principale du bot."""
        log.info("=" * 55)
        log.info("🚀 ICT SENTINEL PRO — BOT DE TRADING DÉMARRÉ")
        log.info("=" * 55)

        # Connexion MT5
        mt5_ok = self._connect_mt5()
        if not mt5_ok and self.config.get("mode") == "FULL_AUTO":
            log.warning("MT5 non connecté — passage en mode PAPER.")
            self.config["mode"] = "PAPER"

        self.running = True

        # Un thread de Slow Loop par symbole (analyse en parallèle)
        symbols = self.config.get("symbols_watched", ["XAUUSD"])
        for sym in symbols:
            t = threading.Thread(
                target=self._slow_loop_symbol,
                args=(sym, loop_interval),
                daemon=True,
                name=f"SlowLoop_{sym}"
            )
            t.start()
            self.symbol_threads[sym] = t
            log.info(f"🚀 Thread analyse lance pour : {sym}")

        # Thread d'exécution rapide unique (lecture du cache + ordres MT5)
        fast_thread = threading.Thread(target=self._fast_loop_worker, daemon=True, name="FastLoop_Executor")
        fast_thread.start()

        try:
            while self.running:
                # Thread principal sert juste de watch-dog et rapports journa
                time.sleep(60)

                # Rapport session à 17h NY
                tz  = pytz.timezone("America/New_York")
                now = datetime.datetime.now(tz)
                if now.hour == 17 and now.minute < 1:
                    self._generate_end_of_session_report()
                    time.sleep(60) # Éviter de générer plusieurs fois par minute

        except KeyboardInterrupt:
            log.info("Interruption utilisateur - arret propre...")
        finally:
            self.stop()
            for sym, t in self.symbol_threads.items():
                t.join(timeout=2)
            fast_thread.join(timeout=2)

    def stop(self):
        """Arrêt propre du bot."""
        self.running = False
        log.info("🏁 Bot arrêté.")
        # Status offline to dashboard
        symbols = self.config.get("symbols_watched", [])
        current_time_str = datetime.datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S")
        self.market_cache.update_bot_status(False, current_time_str, symbols)
        
        if MT5_AVAILABLE:
            mt5.shutdown()

    def _generate_end_of_session_report(self):
        """Génère le rapport de fin de session."""
        try:
            report = self.journal.generate_session_report()
            log.info(f"\n{report}")
        except Exception as e:
            log.warning(f"Erreur rapport session: {e}")


# ============================================================
# POINT D'ENTRÉE CLI
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ICT SENTINEL PRO — Trading Bot")
    parser.add_argument("--dry-run",   action="store_true", help="Mode simulation sans ordres réels")
    parser.add_argument("--config",    type=str, default=CONFIG_PATH, help="Chemin vers la config JSON")
    parser.add_argument("--interval",  type=int, default=DEFAULT_LOOP, help="Intervalle boucle lente en secondes")
    args = parser.parse_args()

    config = load_config(args.config)
    bot    = ICTTradingBot(config=config, dry_run=args.dry_run)
    bot.start(loop_interval=args.interval)
