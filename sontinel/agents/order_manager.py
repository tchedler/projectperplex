"""
OrderManager — Gestionnaire d'ordres MT5
Gère le cycle de vie complet des positions : placement, trailing SL,
partial TP, fermeture, et mode Paper (simulation sans ordres réels).
"""
import datetime
from typing import Optional, List, Dict, Any, Tuple, Set
import pytz # type: ignore
import time
import json
import os
import logging

# Logging local
log = logging.getLogger("OrderManager")

try:
    import MetaTrader5 as mt5 # type: ignore
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

from agents.trading_judge import TradeSignal # type: ignore

# I9 FIX : Magic number centralisé pour isoler les positions du bot
BOT_MAGIC_NUMBER = 20260001


# ============================================================
# ÉTAT DES POSITIONS (STATE MACHINE)
# ============================================================
class PositionState:
    SCAN    = "SCAN"
    PENDING = "PENDING"   # Ordre limite en attente
    ACTIVE  = "ACTIVE"    # Position ouverte
    EXIT    = "EXIT"      # Fermée
    ERROR   = "ERROR"     # Erreur MT5


class ManagedPosition:
    """Représentation interne d'une position gérée par le bot."""
    def __init__(self, signal: TradeSignal, ticket: int = -1, paper: bool = False):
        self.signal          = signal
        self.ticket          = ticket        # MT5 ticket (ou ID interne si paper)
        self.paper           = paper
        self.state           = PositionState.ACTIVE if ticket > 0 else PositionState.PENDING
        self.open_time       = datetime.datetime.now(pytz.timezone("America/New_York"))
        self.close_time: Optional[datetime.datetime] = None
        self.close_price: Optional[float]            = None
        self.close_reason: Optional[str]             = None           # "TP1" / "TP2" / "SL" / "MANUAL" / "TIMEOUT"
        self.current_sl: float                       = float(signal.sl)      # SL courant (mis à jour par trailing)
        self.tp1_hit: bool                           = False          # TP1 partiel déjà pris ?
        self.pnl_pips: float                         = 0.0
        self.pnl_money: float                        = 0.0
        self.partial_done: bool                      = False          # Partial TP 50% déjà exécuté ?

    def to_dict(self) -> dict:
        return {
            "ticket":       self.ticket,
            "symbol":       self.signal.symbol,
            "direction":    self.signal.direction,
            "entry":        self.signal.entry,
            "sl":           self.current_sl,
            "tp1":          self.signal.tp1,
            "tp2":          self.signal.tp2,
            "lot_size":     self.signal.lot_size,
            "score":        self.signal.score,
            "state":        self.state,
            "setup":        self.signal.setup_name,
            "partial_done": self.partial_done,
            "open_time":    self.open_time.strftime("%Y-%m-%d %H:%M:%S"),
            "pnl_pips":     self.pnl_pips,
            "pnl_money":    self.pnl_money,
            "paper":        self.paper,
        }


# ============================================================
# ORDER MANAGER PRINCIPAL
# ============================================================
class OrderManager:
    """
    Gestion complète des ordres MT5 avec trailing SL ICT,
    partial TP automatique, et mode Paper Trading.
    """

    def __init__(self, config: Optional[dict] = None, journal=None):
        """
        config : dict de configuration bot
        journal : instance de TradeJournal (optionnel)
        """
        self.config      = config or {}
        self.journal     = journal
        self.paper_mode  = self.config.get("mode", "PAPER") in ["PAPER", "paper"]
        self.tz          = pytz.timezone("America/New_York")

        # Positions gérées en mémoire
        self.positions: list[ManagedPosition] = []

        # Compteurs de session
        self.session_trades  = 0
        self.session_losses  = 0
        self.session_trades_week = 0  # MIN-5 FIX: Limite hebdo
        self.session_date    = datetime.datetime.now(self.tz).date()

        # ID interne pour le mode paper
        self._paper_id_counter = 1000

    def update_config(self, config: dict):
        self.config.update(config)
        self.paper_mode = self.config.get("mode", "PAPER") in ["PAPER", "paper"]

    @property
    def session_loss_money(self) -> float:
        """
        AUDIT #5 FIX — Calcule la perte monétaire totale de la session courante.
        Utilisé par bot_runner.py pour vérifier le drawdown max configuré.
        """
        today = datetime.datetime.now(self.tz).date()
        total_loss: float = 0.0
        for p in self.positions:
            if p.state == PositionState.EXIT:
                c_time = p.close_time
                if c_time is not None:
                    p_date = c_time.date()
                    if p_date == today:
                        pnl_val = p.pnl_money
                        if isinstance(pnl_val, (int, float)):
                            if float(pnl_val) < 0:
                                pnl_f: float = float(pnl_val)  # type: ignore[arg-type]
                                total_loss = total_loss + pnl_f
        return abs(min(0.0, float(total_loss)))

    # ============================================================
    # RÉINITIALISATION DE SESSION
    # ============================================================
    def _check_new_session(self):
        """Réinitialise les compteurs si nouveau jour de trading (Heure NY)."""
        today = datetime.datetime.now(self.tz).date()
        if today != self.session_date:
            self.session_trades = 0
            self.session_losses = 0
            # On réinitialise la semaine si on change de semaine calendrier (Lundi = 0)
            if today.weekday() < self.session_date.weekday() or (today - self.session_date).days >= 7:
                self.session_trades_week = 0
            self.session_date   = today

    # ============================================================
    # RÈGLES DE SESSION
    # ============================================================
    def check_session_rules(self) -> tuple[bool, str]:
        """
        Retourne (peut_trader, raison).
        Bible ICT : max 3 trades/session, stop après 2 pertes consécutives.
        """
        self._check_new_session()

        if self.session_trades >= 3:
            return False, "Max 3 trades/session atteint (règle ICT discipline)"
        if self.session_trades_week >= 15:
            return False, "Max 15 trades/semaine atteint (règle ICT de préservation du capital)"
        if self.session_losses >= 2:
            return False, "2 pertes consécutives — arrêt de session (règle discipline ICT)"
            
        # IMP-10 FIX: Vérification du Drawdown Max journalier
        account_balance = self.config.get("account_balance", 10000)
        max_dd_pct = self.config.get("drawdown_max_pct", 5.0)
        max_loss_money = (account_balance * max_dd_pct) / 100.0
        
        session_pnl = 0.0
        for p in self.positions:
            if p.state == PositionState.EXIT:
                c_time = p.close_time
                if c_time is not None and c_time.date() == self.session_date:
                    pnl_val = p.pnl_money
                    if isinstance(pnl_val, (int, float)):
                        session_pnl = float(session_pnl) + float(pnl_val)
        limit_loss: float = float(max_loss_money) * -1.0
        current_pnl: float = float(session_pnl)
        if current_pnl <= limit_loss:
            return False, f"Drawdown max de session atteint ({current_pnl:.2f}$ <= {limit_loss:.2f}$)"

        return True, ""

    def _get_simulated_spread(self, symbol: str) -> float:
        """MOY-11 FIX: Retourne un spread simulé en fonction de l'instrument."""
        sym = symbol.upper()
        if "XAU" in sym or "XAG" in sym: return 0.20       # 20 cents
        if "JPY" in sym: return 0.015                      # 1.5 pips
        if sym in ["US30", "NAS100", "US500", "BTCUSD", "ETHUSD"]: return 1.5  # 1.5 points
        return 0.00015                                     # 1.5 pips defaut (Forex majeur)

    # ============================================================
    # PLACEMENT D'ORDRE
    # ============================================================
    def place_order(self, signal: TradeSignal) -> ManagedPosition | None:
        """
        Place un ordre selon le signal reçu.
        Retourne la ManagedPosition créée ou None si échec.
        BUG FIX : méthode complétée — appelle _place_paper_order ou _place_live_order
        """
        # Vérification SL obligatoire — aucun ordre sans Stop Loss valide
        if not signal.sl or signal.sl == 0:
            log.error(f"[OrderManager] BLOQUÉ — SL invalide (sl={signal.sl}) pour {signal.symbol}. Ordre annulé.")
            return None

        # Vérification cohérence SL / direction
        if signal.direction == "BUY" and signal.sl >= signal.entry:
            log.error(f"[OrderManager] BLOQUÉ — SL ({signal.sl}) >= entry ({signal.entry}) pour BUY {signal.symbol}. Ordre annulé.")
            return None
        if signal.direction == "SELL" and signal.sl <= signal.entry:
            log.error(f"[OrderManager] BLOQUÉ — SL ({signal.sl}) <= entry ({signal.entry}) pour SELL {signal.symbol}. Ordre annulé.")
            return None

        # Mode SEMI_AUTO — log seulement, pas d'exécution
        if self.config.get("mode", "PAPER") == "SEMI_AUTO":
            log.info(f"[SEMI_AUTO] Signal {signal.action} généré mais exécution bloquée (Attente validation manuelle).")
            return None

        # Vérification règles de session
        can_trade, reason = self.check_session_rules()
        if not can_trade:
            log.warning(f"[OrderManager] Blocage session: {reason}")
            return None

        # Vérification doublon — un seul ordre actif par symbole
        if self.is_symbol_under_management(signal.symbol):
            log.info(f"[OrderManager] {signal.symbol} déjà sous gestion — ordre ignoré.")
            return None

        # Routage selon le mode
        op_mode = self.config.get("mode", "PAPER").upper()
        if op_mode in ["PAPER", "SIMULATION"]:
            return self._place_paper_order(signal)
        elif op_mode in ["FULL_AUTO", "LIVE"]:
            return self._place_live_order(signal)
        else:
            # Fallback sécurisé — toujours paper si mode inconnu
            log.warning(f"[OrderManager] Mode '{op_mode}' inconnu — fallback Paper Trading.")
            return self._place_paper_order(signal)

    def is_symbol_under_management(self, symbol: str) -> bool:
        """Vérifie si le symbole a déjà une position active ou un ordre en attente."""
        for pos in self.positions:
            if pos.signal.symbol == symbol and pos.state in [PositionState.ACTIVE, PositionState.PENDING]:
                return True
        return False

    def _place_paper_order(self, signal: TradeSignal) -> ManagedPosition:
        """Simule un ordre sans l'envoyer à MT5."""
        ticket = self._paper_id_counter
        self._paper_id_counter += 1

        pos = ManagedPosition(signal, ticket=ticket, paper=True)
        pos.state = PositionState.ACTIVE if signal.action == "EXECUTE" else PositionState.PENDING
        self.positions.append(pos)
        self.session_trades += 1
        self.session_trades_week += 1

        log.info(f"[PAPER] {signal.action} {signal.direction} {signal.symbol} "
                  f"@ {signal.entry:.5f} | SL: {signal.sl:.5f} | TP2: {signal.tp2:.5f} "
                  f"| Lots: {signal.lot_size} | Setup: {signal.setup_name}")

        if self.journal:
            self.journal.log_trade_open(pos)

        return pos

    def _place_live_order(self, signal: TradeSignal) -> ManagedPosition | None:
        """Place un ordre réel via MT5."""
        if not MT5_AVAILABLE:
            log.error("[OrderManager] MT5 non disponible")
            return None

        if not mt5.initialize():
            log.error("[OrderManager] MT5 non initialisé")
            return None

        symbol_info = mt5.symbol_info(signal.symbol)
        if symbol_info is None:
            log.error(f"[OrderManager] Symbole inconnu: {signal.symbol}")
            return None

        # Type d'ordre
        if signal.action == "EXECUTE":
            order_type = mt5.ORDER_TYPE_BUY if signal.direction == "BUY" else mt5.ORDER_TYPE_SELL
        else:
            # Ordre limite
            order_type = mt5.ORDER_TYPE_BUY_LIMIT if signal.direction == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT

        action_type = mt5.TRADE_ACTION_DEAL if signal.action == "EXECUTE" else mt5.TRADE_ACTION_PENDING

        setup_str: str = str(signal.setup_name)[:15]
        score_val: int = int(signal.score)
        comment_raw: str = "ICT|" + setup_str + "|" + str(score_val)
        comment_val: str = comment_raw[:31]
        request = {
            "action":    action_type,
            "symbol":    signal.symbol,
            "volume":    signal.lot_size,
            "type":      order_type,
            "price":     signal.entry,
            "sl":        signal.sl,
            "tp":        signal.tp2,
            "deviation": 20,
            "magic":     BOT_MAGIC_NUMBER,
            "comment":   comment_val,
            "type_time": mt5.ORDER_TIME_GTC,
        }

        # Pour MT5, le type_filling est uniquement pour les ordres MARKET/DEAL (EXECUTE)
        # Il provoque une "Invalid FillType" pour les ordres PENDING (LIMIT) chez la plupart des brokers
        if action_type == mt5.TRADE_ACTION_DEAL:
            request["type_filling"] = mt5.ORDER_FILLING_IOC

        result = mt5.order_send(request)
        if result is None:
            err = mt5.last_error()
            log.error(f"[OrderManager] mt5.order_send a retourné None. Erreur MT5: {err} | Request: {request}")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            log.error(f"[OrderManager] Erreur MT5 code={result.retcode} — {result.comment} | Request: {request}")
            return None

        pos = ManagedPosition(signal, ticket=result.order, paper=False)
        pos.state = PositionState.ACTIVE if signal.action == "EXECUTE" else PositionState.PENDING
        self.positions.append(pos)
        self.session_trades += 1
        self.session_trades_week += 1

        log.info(f"[LIVE] Ordre placé: ticket={result.order} | {signal.direction} "
                  f"{signal.symbol} @ {signal.entry:.5f}")

        if self.journal:
            self.journal.log_trade_open(pos)

        return pos

    # ============================================================
    # MISE À JOUR DES POSITIONS ACTIVES
    # ============================================================
    def update_all_positions(self, current_price: float, smc_m15: Optional[dict] = None):
        """
        Appelée à chaque cycle de la boucle principale.
        - Check partial TP (Paper) ou réconciliation MT5 (Live)
        - Update trailing SL ICT
        - Check clôture forcée (Paper seulement — le broker gère le SL/TP pour le Live)
        """
        
        # I9 FIX : Filtrer par magic number pour isoler les positions de ce bot
        live_tickets_open = set()
        live_orders_pending = set()
        if MT5_AVAILABLE:
            # 1. Positions ACTIVES
            open_mt5_positions = mt5.positions_get()
            if open_mt5_positions is not None:
                live_tickets_open = {
                    p.ticket for p in open_mt5_positions
                    if p.magic == BOT_MAGIC_NUMBER
                }
            
            # 2. Ordres PENDANTS (LIMIT/STOP)
            open_mt5_orders = mt5.orders_get()
            if open_mt5_orders is not None:
                live_orders_pending = {
                    o.ticket for o in open_mt5_orders
                    if o.magic == BOT_MAGIC_NUMBER
                }
            
            # --- DEBUG LOG ---
            if len(live_tickets_open) > 0 or len(live_orders_pending) > 0:
                log.info(f"[OrderManager] MT5 Check: {len(live_tickets_open)} pos, {len(live_orders_pending)} orders (magic={BOT_MAGIC_NUMBER})")
            
            # --- RÉCONCILIATION AUTOMATIQUE (Audit duplication fix) ---
            # Si un ticket est sur MT5 mais pas dans notre liste locale, on l'ajoute.
            # Cela arrive au redémarrage du bot.
            all_live_tickets = list(live_tickets_open) + list(live_orders_pending)
            for ticket in all_live_tickets:
                already_managed = False
                for p in self.positions:
                    if p.ticket == ticket:
                        already_managed = True
                        break
                
                if not already_managed:
                    # Tenter de reconstruire un signal minimal pour le suivi
                    source = None
                    if ticket in live_tickets_open:
                        if open_mt5_positions is not None:
                            mtch = [p for p in open_mt5_positions if p.ticket == ticket]
                            if mtch:
                                source = mtch[0]
                    else:
                        if open_mt5_orders is not None:
                            mtch2 = [o for o in open_mt5_orders if o.ticket == ticket]
                            if mtch2:
                                source = mtch2[0]
                    
                    if source:
                        # Création d'un signal "fantôme" pour la réconciliation
                        dir_str = "BUY" if source.type in [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT] else "SELL"
                        recon_sig = TradeSignal(
                            action="EXECUTE" if ticket in live_tickets_open else "LIMIT",
                            direction=dir_str,
                            symbol=source.symbol,
                            entry=source.price_open if hasattr(source, 'price_open') else source.price_current,
                            sl=source.sl,
                            tp2=source.tp,
                            setup_name="RECONCILED"
                        )
                        pos = ManagedPosition(recon_sig, ticket=ticket, paper=False)
                        pos.state = PositionState.ACTIVE if ticket in live_tickets_open else PositionState.PENDING
                        self.positions.append(pos)
                        log.info(f"[OrderManager] Réconciliation auto du ticket {ticket} ({recon_sig.symbol})")

        for pos in list(self.positions):
            if pos.state != PositionState.ACTIVE:
                continue

            # ================================================================
            # POSITIONS LIVE : Le broker MT5 a déjà le SL et le TP intégrés.
            # ================================================================
            if not pos.paper and MT5_AVAILABLE:
                # Si c'était un PENDING et qu'il est passé en ACTIVE sur MT5
                if pos.state == PositionState.PENDING and pos.ticket in live_tickets_open:
                    pos.state = PositionState.ACTIVE
                    log.info(f"🚀 Ordre PENDING {pos.ticket} est maintenant ACTIF sur MT5.")

                # Si le ticket local n'est pas dans la liste globale de MT5 (ni active, ni pending) -> Fermé ou annulé
                if pos.ticket not in live_tickets_open and pos.ticket not in live_orders_pending:
                    tick = mt5.symbol_info_tick(pos.signal.symbol)
                    close_px = tick.bid if pos.signal.direction == "BUY" else tick.ask if tick else 0
                    
                    # Récupérer l'historique pour le PnL réel
                    hist = mt5.history_deals_get(position=pos.ticket)
                    if hist:
                        profit_sum = sum(d.profit for d in hist)
                        pos.pnl_money = profit_sum
                        pos.pnl_pips = profit_sum
                        
                    self._close_position(pos, close_px, "EXTERNAL_CLOSE")
                    continue
                
                # Le ticket est toujours ouvert sur MT5, récupérer le prix courant depuis la vue globale ou tick
                tick = mt5.symbol_info_tick(pos.signal.symbol)
                if tick:
                    price = tick.bid if pos.signal.direction == "BUY" else tick.ask
                    
                    # --- TRAILING SL ICT (Live) ---
                    if smc_m15 is not None:
                        self._update_trailing_sl(pos, float(price), smc_m15) # type: ignore
                        
                    # --- CHECK PARTIAL TP (Live) ---
                    if not pos.partial_done:
                        self._check_partial_tp(pos, float(price))
                continue

            # ================================================================
            # POSITIONS PAPER : Simulation manuelle des SL/TP
            # ================================================================
            # MOY-11 FIX: Simulation du spread (Ask/Bid)
            spread = self._get_simulated_spread(pos.signal.symbol)
            # Pour un BUY, on ferme sur le BID (prix actuel - moitié du spread)
            # Pour un SELL, on ferme sur le ASK (prix actuel + moitié du spread)
            if pos.signal.direction == "BUY":
                price = float(current_price) - (float(spread) / 2.0)
            else:
                price = float(current_price) + (float(spread) / 2.0)

            # --- CHECK PARTIAL TP (50% du range) ---
            if not pos.partial_done:
                self._check_partial_tp(pos, price)

            # --- TRAILING SL ICT ---
            if smc_m15 is not None:
                self._update_trailing_sl(pos, float(price), smc_m15)

            # --- CHECK SL/TP HIT (Paper uniquement) ---
            self._check_close(pos, price)

    def _check_partial_tp(self, pos: ManagedPosition, price: float):
        """
        Ferme 50% de la position si TP1 atteint.
        Puis déplace le SL au breakeven.
        Bible ICT : sécuriser la position à 50% du range.
        """
        tp1 = pos.signal.tp1
        direction = pos.signal.direction
        hit = (direction == "BUY" and price >= tp1) or (direction == "SELL" and price <= tp1)

        if hit:
            print(f"[OrderManager] TP1 atteint @ {price:.5f} — Tentative de Partial 50% + Breakeven SL")
            
            # 1. Action Réelle sur MT5 (si pas en mode Paper)
            if not pos.paper and MT5_AVAILABLE:
                mt5_pos = mt5.positions_get(ticket=pos.ticket)
                if mt5_pos and len(mt5_pos) > 0:
                    current_vol = mt5_pos[0].volume
                    close_vol = round(current_vol * 0.5, 2)
                    
                    if close_vol >= 0.01:
                        order_type = mt5.ORDER_TYPE_SELL if direction == "BUY" else mt5.ORDER_TYPE_BUY
                        tick = mt5.symbol_info_tick(pos.signal.symbol)
                        if tick:
                            close_price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
                            request = {
                                "action":    mt5.TRADE_ACTION_DEAL,
                                "position":  pos.ticket,
                                "symbol":    pos.signal.symbol,
                                "volume":    close_vol,
                                "type":      order_type,
                                "price":     close_price,
                                "deviation": 20,
                                "magic":     20260001,
                                "comment":   "ICT_PARTIAL_TP1",
                                "type_filling": mt5.ORDER_FILLING_IOC,
                            }
                            result = mt5.order_send(request)
                            if result.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"[OrderManager] ✅ Partial TP clôturé sur MT5: {close_vol} lots")
                            else:
                                print(f"[OrderManager] ❌ Échec Partial TP MT5: {result.comment}")

            # 2. Update interne
            pos.partial_done = True
            pos.tp1_hit = True
            
            # Déplacer SL au breakeven (= entry)
            new_sl = pos.signal.entry
            self._modify_sl(pos, new_sl)

            if self.journal:
                self.journal.log_partial_tp(pos, price)

    def _update_trailing_sl(self, pos: ManagedPosition, price: float, smc: Optional[dict]):
        """
        Trailing SL basé sur les swings ICT (SWH/SWL du M15).
        Bible ICT : on déplace le SL au dernier swing bas/haut confirmé.
        AUDIT #4 EXT — Buffer adaptatif selon le symbole (pas de 0.9999 fixe).
        """
        try:
            if smc is None:
                return
            smc_dict: dict = smc
            swh = smc_dict.get("structure", {}).get("swh", 0)
            swl = smc_dict.get("structure", {}).get("swl", 0)
            direction = pos.signal.direction
            sym = pos.signal.symbol

            # Buffer adaptatif pour le trailing SL (même logique que _get_sl_margin)
            sym_u = sym.upper()
            if 'XAU' in sym_u or 'GOLD' in sym_u:  buf = 0.30
            elif 'XAG' in sym_u:                    buf = 0.03
            elif 'NAS100' in sym_u:                 buf = 10.0
            elif 'US30' in sym_u or 'DJ' in sym_u:  buf = 20.0
            elif 'US500' in sym_u:                  buf = 3.0
            elif 'BTC' in sym_u:                    buf = 30.0
            elif 'ETH' in sym_u:                    buf = 2.0
            elif 'JPY' in sym_u:                    buf = swl * 0.0003 if swl > 0 else 0.03
            elif 'OIL' in sym_u or 'WTI' in sym_u:  buf = 0.10
            else:                                   buf = 0.0002  # Forex standard

            if direction == "BUY" and swl > pos.current_sl and swl < price:
                new_sl = swl - buf
                if new_sl > pos.current_sl:
                    self._modify_sl(pos, new_sl)
                    log.info(f"[Trailing SL] BUY: SL déplacé à {new_sl:.5f} (swl={swl:.5f})")

            elif direction == "SELL" and swh < pos.current_sl and swh > price:
                new_sl = swh + buf
                if new_sl < pos.current_sl:
                    self._modify_sl(pos, new_sl)
                    log.info(f"[Trailing SL] SELL: SL déplacé à {new_sl:.5f} (swh={swh:.5f})")

        except Exception as e:
            log.warning(f"[Trailing SL] Erreur: {e}")

    def _modify_sl(self, pos: ManagedPosition, new_sl: float):
        """Modifie le SL d'une position (Paper ou Live)."""
        pos.current_sl = new_sl
        if not pos.paper and MT5_AVAILABLE:
            mt5_pos = mt5.positions_get(ticket=pos.ticket)
            if mt5_pos and len(mt5_pos) > 0:
                request = {
                    "action":   mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "symbol":   pos.signal.symbol,
                    "sl":       float(new_sl),
                    "tp":       float(pos.signal.tp2),
                    "magic":    BOT_MAGIC_NUMBER,
                }
                mt5.order_send(request)

    def _check_close(self, pos: ManagedPosition, price: float):
        """Vérifie si SL ou TP2 est atteint et ferme la position."""
        direction = pos.signal.direction
        sl  = pos.current_sl
        tp2 = pos.signal.tp2

        hit_sl  = (direction == "BUY"  and price <= sl)  or (direction == "SELL" and price >= sl)
        hit_tp2 = (direction == "BUY"  and price >= tp2) or (direction == "SELL" and price <= tp2)

        if hit_tp2:
            self._close_position(pos, price, "TP2")
        elif hit_sl:
            self._close_position(pos, price, "SL")

    def _close_position(self, pos: ManagedPosition, price: float, reason: str):
        """Ferme une position et met à jour les compteurs."""
        pos.state       = PositionState.EXIT
        pos.close_time  = datetime.datetime.now(self.tz)
        pos.close_price = price
        pos.close_reason = reason

        # Calcul PnL — CRIT-4 FIX : formule correcte par instrument
        entry = pos.signal.entry
        diff  = (price - entry) if pos.signal.direction == "BUY" else (entry - price)
        sym   = pos.signal.symbol.upper()
        # Taille de pip réelle selon l'instrument
        _pip_size = {
            "XAUUSD": 0.01, "XAGUSD": 0.01,
            "USDJPY": 0.01, "EURJPY": 0.01, "GBPJPY": 0.01,
            "NAS100": 1.0,  "US30": 1.0,    "US500": 1.0,
            "BTCUSD": 1.0,  "ETHUSD": 0.1,
        }
        pip_sz = _pip_size.get(sym, 0.0001)
        _pip_val = {
            "XAUUSD": 1.0,  "XAGUSD": 50.0,
            "EURUSD": 10.0, "GBPUSD": 10.0, "AUDUSD": 10.0,
            "USDJPY": 9.0,  "EURJPY": 9.0,  "GBPJPY": 9.0,
            "NAS100": 1.0,  "US30": 1.0,    "US500": 1.0,
            "BTCUSD": 1.0,  "ETHUSD": 1.0,
        }
        pip_vl = _pip_val.get(sym, 10.0)
        val_pips_f: float = float(diff) / float(pip_sz)
        pos.pnl_pips  = round(val_pips_f, 1) # type: ignore
        val_money_f: float = float(pos.pnl_pips) * float(pip_vl) * float(pos.signal.lot_size)
        pos.pnl_money = round(val_money_f, 2) # type: ignore


        if reason == "SL":
            self.session_losses += 1
            print(f"[OrderManager] ❌ SL touché @ {price:.5f} | PnL: {pos.pnl_money:.2f}$")
        elif reason in ("TP2", "TP1_FULL"):
            # I2 FIX : session_losses reset UNIQUEMENT sur un vrai TP (win confirmé)
            # EXTERNAL_CLOSE et CANCEL ne comptent ni comme win ni comme loss
            self.session_losses = 0
            print(f"[OrderManager] ✅ {reason} @ {price:.5f} | PnL: {pos.pnl_money:.2f}$")
        else:
            # EXTERNAL_CLOSE, MANUAL, CANCEL : neutre — ne pas modifier session_losses
            print(f"[OrderManager] ℹ️ {reason} @ {price:.5f} | PnL: {pos.pnl_money:.2f}$")

        # Si live, envoyer l'ordre de fermeture manuelle (PARTIAL TP, TIMEOUT, etc.)
        # IMPORTANT : NE PAS fermer si EXTERNAL_CLOSE — la position a déjà été
        # fermée par le broker via SL/TP. Envoyer un ordre en double provoquerait
        # une erreur MT5 "Position not found" et pourrait violer les règles Prop Firm.
        if not pos.paper and MT5_AVAILABLE and reason not in ("EXTERNAL_CLOSE", "EXTERNAL_SL"):
            # Vérification prudente : la position existe-t-elle encore ?
            mt5_pos = mt5.positions_get(ticket=pos.ticket)
            if mt5_pos and len(mt5_pos) > 0:
                order_type = mt5.ORDER_TYPE_SELL if pos.signal.direction == "BUY" else mt5.ORDER_TYPE_BUY
                tick = mt5.symbol_info_tick(pos.signal.symbol)
                if tick:
                    close_price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
                    sym_info = mt5.symbol_info(pos.signal.symbol)
                    # Tenter FOK d'abord, puis IOC en fallback (compatibilité broker)
                    for filling in [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC]:
                        request = {
                            "action":    mt5.TRADE_ACTION_DEAL,
                            "position":  pos.ticket,
                            "symbol":    pos.signal.symbol,
                            "volume":    mt5_pos[0].volume,
                            "type":      order_type,
                            "price":     close_price,
                            "deviation": 20,
                            "magic":     20260001,
                            "comment":   f"ICT_CLOSE | {reason}",
                            "type_filling": filling,
                        }
                        result = mt5.order_send(request)
                        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                            break
                        print(f"[OrderManager] Filling {filling} échoué ({result.retcode if result else 'None'}), retry...")

            # Annulation d'un ordre LIMIT PENDING si reason=CANCEL
            elif reason == "CANCEL":
                pending = mt5.orders_get(ticket=pos.ticket)
                if pending and len(pending) > 0:
                    mt5.order_send({
                        "action": mt5.TRADE_ACTION_REMOVE,
                        "order":  pos.ticket,
                    })

        if self.journal:
            self.journal.log_trade_close(pos)

        # Retirer de la liste gérée
        self.positions = [p for p in self.positions if p.ticket != pos.ticket]

    # ============================================================
    # ACCESSEURS
    # ============================================================
    def get_active_positions(self) -> list:
        return [p for p in self.positions if p.state == PositionState.ACTIVE]

    def get_pending_positions(self) -> list:
        return [p for p in self.positions if p.state == PositionState.PENDING]

    def open_position_count(self) -> int:
        return len(self.get_active_positions()) + len(self.get_pending_positions())

    def close_all_positions(self, reason: str = "MANUAL"):
        """Ferme toutes les positions ouvertes (urgence ou fin de session)."""
        for pos in list(self.positions):
            if pos.state == PositionState.ACTIVE:
                # Prix approximatif — en production, lire le bid/ask MT5
                approx_price = pos.signal.entry  # fallback
                self._close_position(pos, approx_price, reason)
