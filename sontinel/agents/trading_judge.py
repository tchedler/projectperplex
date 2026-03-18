"""
TradingJudge — Moteur de Décision ICT enrichi par IA
lit les résultats des agents, applique les règles ICT,
enrichit par GROQ (rapide) + Gemini (profond), retourne un signal structuré.
"""
import datetime
import pytz # type: ignore
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union

# Les Analystes IA ont été déplacés vers AISupremeJudge pour ne pas mélanger
# la génération de signaux mathématiques algorithmiques (ICT) avec l'intelligence artificielle.


# ============================================================
# STRUCTURES DE DONNÉES DE SORTIE
# ============================================================
@dataclass
class TradeSignal:
    action: str                  # "EXECUTE" | "LIMIT" | "WAIT" | "NO_TRADE"
    direction: str               # "BUY" | "SELL" | "NONE"
    symbol: str = ""
    timeframe: str = ""
    entry: float = 0.0
    sl: float = 0.0
    tp1: float = 0.0
    tp2: float = 0.0
    lot_size: float = 0.01
    score: float = 0.0
    confidence: str = "LOW"
    reason: str = ""
    setup_name: str = ""
    killzone: str = "NONE"
    macro: str = "NONE"
    htf_bias: str = "NEUTRAL"
    po3_phase: str = ""
    timestamp: str = ""
    # -- Enrichissements IA --
    groq_flag: str = "OK"        # OK | DUBIOUS | BLOCKED
    groq_note: str = ""          # Note rapide GROQ/Llama
    gemini_validated: bool = True # Validation Gemini
    gemini_note: str = ""         # Commentaire expert Gemini
    gemini_risks: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["gemini_risks"] = list(d.get("gemini_risks", []))
        return d



# ============================================================
# JUDGE PRINCIPAL
# ============================================================
class TradingJudge:
    """
    Cerveau de décision du bot de trading ICT.
    Transforme les résultats analytiques en signal de trading actionnable.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.tz = pytz.timezone("America/New_York")

        self.score_execute = self.config.get("score_execute", 80)
        self.score_limit   = self.config.get("score_limit", 65)
        self.risk_pct      = self.config.get("risk_pct", 1.0) / 100.0
        self.account_bal   = self.config.get("account_balance", 10000)
        self.max_positions = self.config.get("max_positions", 3)

        # Analystes IA supprimés du Juge ICT Mathématique.

    def update_config(self, config: dict):
        """Met à jour la configuration dynamiquement (depuis l'UI)."""
        self.config.update(config)
        self.score_execute = self.config.get("score_execute", 80)
        self.score_limit   = self.config.get("score_limit", 65)
        self.risk_pct      = self.config.get("risk_pct", 1.0) / 100.0
        self.account_bal   = self.config.get("account_balance", 10000)
        self.max_positions = self.config.get("max_positions", 3)

    # ============================================================
    # MÉTHODE PRINCIPALE : Évaluer un TF et retourner un signal
    # ============================================================
    def evaluate(self,
                 symbol: str,
                 tf: str,
                 clock: dict,
                 bias: dict,
                 smc: dict,
                 liq: dict,
                 exe: dict,
                 mmxm: dict,
                 checklist_result: dict,  # {score, verdict}
                 open_positions: int = 0,
                 session_losses: int = 0,
                 session_trades: int = 0) -> TradeSignal:
        """
        Évalue toutes les conditions ICT et retourne un TradeSignal.
        """
        now = datetime.datetime.now(self.tz)
        ts = now.strftime("%Y-%m-%d %H:%M:%S")

        score   = checklist_result.get("score", 0)
        verdict = checklist_result.get("verdict", "")

        # --- RÈGLES ABSOLUES DE BLOCAGE (Bible ICT) ---
        # C5 FIX : mmxm est maintenant passé en paramètre (NameError corrigé)
        block_reason = self._check_absolute_blocks(
            clock, smc, bias, mmxm, session_losses, session_trades, open_positions
        )
        if block_reason:
            return TradeSignal(
                action="NO_TRADE", direction="NONE",
                symbol=symbol, timeframe=tf,
                score=score, reason=block_reason,
                killzone=clock.get("killzone", "NONE"),
                macro=clock.get("macro", "NONE"),
                htf_bias=bias.get("htf_bias", "NEUTRAL"),
                timestamp=ts
            )

        # --- SCORE INSUFFISANT ---
        if score < self.score_limit:
            return TradeSignal(
                action="NO_TRADE", direction="NONE",
                symbol=symbol, timeframe=tf,
                score=score,
                reason=f"Score {score}/100 insuffisant (min requis: {self.score_limit})",
                killzone=clock.get("killzone", "NONE"),
                macro=clock.get("macro", "NONE"),
                htf_bias=bias.get("htf_bias", "NEUTRAL"),
                timestamp=ts
            )

        # --- DÉTERMINER LA DIRECTION ---
        direction = self._get_direction(bias, smc, mmxm)
        if direction == "NONE":
            return TradeSignal(
                action="WAIT", direction="NONE",
                symbol=symbol, timeframe=tf,
                score=score,
                reason="Direction indéterminée — pas de biais clair",
                killzone=clock.get("killzone", "NONE"),
                macro=clock.get("macro", "NONE"),
                htf_bias=bias.get("htf_bias", "NEUTRAL"),
                timestamp=ts
            )

        # --- CALCULER LES NIVEAUX ENTRY / SL / TP ---
        # C1 FIX : symbol est maintenant passé en paramètre pour MT5
        entry, sl, tp1, tp2 = self._calculate_levels(
            direction, smc, liq, exe, bias, symbol
        )

        if entry == 0 or sl == 0:
            return TradeSignal(
                action="WAIT", direction=direction,
                symbol=symbol, timeframe=tf,
                score=score,
                reason="Impossible de calculer les niveaux Entry/SL valides",
                killzone=clock.get("killzone", "NONE"),
                macro=clock.get("macro", "NONE"),
                htf_bias=bias.get("htf_bias", "NEUTRAL"),
                timestamp=ts
            )

        # --- VALIDER RATIO RISQUE/RENDEMENT ---
        rr = self._calc_rr(entry, sl, tp2)
        if rr < 2.0:
            return TradeSignal(
                action="NO_TRADE", direction=direction,
                symbol=symbol, timeframe=tf,
                score=score,
                reason=f"Ratio R/R insuffisant: {rr:.1f} (minimum 2.0)",
                killzone=clock.get("killzone", "NONE"),
                macro=clock.get("macro", "NONE"),
                htf_bias=bias.get("htf_bias", "NEUTRAL"),
                timestamp=ts
            )

        # --- CALCULER LA TAILLE DE POSITION ---
        lot_size = self._calculate_lot_size(entry, sl, symbol)

        # --- IDENTIFIER LE SETUP ---
        setup_name = self._identify_setup(mmxm, smc, clock)

        # --- DÉTERMINER L'ACTION ET LA CONFIANCE ---
        if score >= self.score_execute:
            action = "EXECUTE"
            confidence = "A_PLUS" if score >= 90 else "HIGH"
        else:
            # LIMIT : Le bot va placer un ordre en attente au niveau OTE
            # (70.5% du dealing range) — entrée différée si le prix retrace.
            action = "LIMIT"
            confidence = "MEDIUM"
            # I1 FIX : Recalculer entry OTE AVANT de valider le R/R
            # afin que le R/R mesuré corresponde à l'entrée réelle de l'ordre limite.
            ote_entry = exe.get("ote", {}).get("lvl_705", entry) if exe else entry
            if ote_entry > 0:
                entry = ote_entry
            # Recalculer le R/R avec la vraie entry OTE
            rr = self._calc_rr(entry, sl, tp2)
            if rr < 2.0:
                return TradeSignal(
                    action="NO_TRADE", direction=direction,
                    symbol=symbol, timeframe=tf,
                    score=score,
                    reason=f"Ratio R/R LIMIT insuffisant: {rr:.1f} (min 2.0 requis)",
                    killzone=clock.get("killzone", "NONE"),
                    macro=clock.get("macro", "NONE"),
                    htf_bias=bias.get("htf_bias", "NEUTRAL"),
                    timestamp=ts
                )

        reason = self._build_reason(
            score, direction, clock, bias, smc, liq, mmxm, setup_name
        )

        # ============================================================
        # NOTE : La COUCHE IA a été extraite et transférée à l'agent
        # AISupremeJudge afin de séparer la génération stricte du signal (math/algo)
        # de l'évaluation heuristique par Llama/Gemini.
        # ============================================================


        return TradeSignal(
            action=action,
            direction=direction,
            symbol=symbol,
            timeframe=tf,
            entry=round(float(entry), 5) if entry else 0.0, # type: ignore
            sl=round(float(sl), 5) if sl else 0.0, # type: ignore
            tp1=round(float(tp1), 5) if tp1 else 0.0, # type: ignore
            tp2=round(float(tp2), 5) if tp2 else 0.0, # type: ignore
            lot_size=lot_size,
            score=score,
            confidence=confidence,
            reason=reason,
            setup_name=setup_name,
            killzone=clock.get("killzone", "NONE"),
            macro=clock.get("macro", "NONE"),
            htf_bias=bias.get("htf_bias", "NEUTRAL") if bias else "NEUTRAL",
            po3_phase=mmxm.get("po3_phase", "") if mmxm else "",
            timestamp=ts,
            groq_flag="OK",
            groq_note="",
            gemini_validated=True,
            gemini_note="",
            gemini_risks=[],
        )

    # ============================================================
    # RÈGLES ABSOLUES DE BLOCAGE (Bible ICT)
    # ============================================================
    def _check_absolute_blocks(self, clock, smc, bias, mmxm,
                                session_losses, session_trades, open_positions) -> str:
        """C5 FIX : mmxm ajouté comme paramètre (corrige le NameError)."""
        # Garde ancienne signature pour compatibilité
        if mmxm is None:
            mmxm = {}
        """
        Retourne le motif de blocage si une règle absolue est violée,
        sinon retourne une chaîne vide.
        """
        # Règle 0 : Pas tradable (hors session)
        if not clock.get("is_tradable", False):
            return "Hors session de trading (pas de Killzone ni Macro)"

        # Règle 1 : Vendredi après 14h NY — NO TRADE (Bible §12 Step 0)
        if clock.get("friday_no_trade", False):
            return "Vendredi après 14h NY — NO TRADE (règle absolue ICT)"

        # Règle 2 : Boolean_Sweep_ERL = False (DÉSACTIVÉ en faveur du système de Score Pondéré)
        # La pénalité a été déplacée dans le ChecklistExpert (Score -15)
        # sweep_erl = smc.get("boolean_sweep_erl", {}) if smc else {}
        # if not sweep_erl.get("value", True):
        #     return "Boolean_Sweep_ERL = False — Règle absolue ICT : INTERDIT"

        # Règle 3 : Phase ACCUMULATION → Attendre (Bible §5.1)
        po3 = mmxm.get("po3_phase", "") if isinstance(mmxm, dict) else ""
        if "ACCUMULATION" in po3:
            return "Phase ACCUMULATION en cours — En attente du Manipulation (Sweep) (Bible §5.1)"

        # Règle 4 : Max 3 trades par session
        if session_trades >= 3:
            return "Maximum 3 trades/session atteint (règle ICT discipline)"

        # Règle 5 : Stop après 2 pertes consécutives
        if session_losses >= 2:
            return "2 pertes consécutives — arrêt de session (règle discipline ICT)"

        # Règle 6 : Max positions simultanées
        if open_positions >= self.max_positions:
            return f"Maximum {self.max_positions} positions simultanées atteint"

        # AUDIT #17 FIX — Vérification du spread MT5 avant exécution
        spread_reason = self._check_spread(clock.get("symbol_", "") or "")
        if spread_reason:
            return spread_reason

        return ""  # Pas de blocage

    def _check_spread(self, symbol: str) -> str:
        """
        AUDIT #17 FIX — Vérifie que le spread est acceptable avant de trader.
        Un spread trop large grignotage le R/R et signale un marché illiquide.
        Ceci peut être désactivé via config["disable_spread_check"].
        """
        if self.config.get("disable_spread_check", False):
            return ""

        max_spread_pips = {
            "XAUUSD": 5.0,  "XAGUSD": 8.0,
            "EURUSD": 2.0,  "GBPUSD": 3.0,  "AUDUSD": 2.5,
            "USDCAD": 3.0,  "USDCHF": 3.0,  "NZDUSD": 3.0,
            "USDJPY": 2.0,  "EURJPY": 3.0,  "GBPJPY": 4.0,
            "NAS100": 3.0,  "US30":   5.0,   "US500":  2.0,
            "BTCUSD": 50.0, "BTCUSDM": 50.0, "ETHUSD": 5.0,
            "XTIUSD": 4.0,  "USDX":   3.0,
        }
        pip_sizes = {
            "XAUUSD": 0.01, "XAGUSD": 0.01,
            "USDJPY": 0.01, "EURJPY": 0.01, "GBPJPY": 0.01,
            "NAS100": 1.0,  "US30":   1.0,   "US500":  1.0,
            "BTCUSD": 1.0,  "BTCUSDM": 1.0, "ETHUSD": 0.1,  "XTIUSD": 0.01,
        }
        if not symbol:
            return ""
        try:
            import MetaTrader5 as mt5  # type: ignore
            if mt5.initialize():
                tick = mt5.symbol_info_tick(symbol)
                if tick and tick.ask > 0 and tick.bid > 0:
                    spread_price = tick.ask - tick.bid
                    pip_size = pip_sizes.get(symbol.upper(), 0.0001)
                    spread_pips = spread_price / pip_size
                    max_pips = max_spread_pips.get(symbol.upper(), 5.0)
                    if spread_pips > max_pips:
                        return (
                            f"Spread trop large : {spread_pips:.1f} pips "
                            f"(max {max_pips:.1f} pour {symbol})"
                        )
        except Exception:
            pass  # Si MT5 indisponible, on ne bloque pas
        return ""

    # ============================================================
    # DÉTERMINER LA DIRECTION DU TRADE
    # ============================================================
    def _get_direction(self, bias, smc, mmxm) -> str:
        """
        Détermine la direction BUY/SELL en combinant :
        1. Biais HTF (prioritaire)
        2. Structure locale (MSS/BOS)
        3. Phase PO3 (distribution active = entrée dans le sens)
        """
        htf_bias = bias.get("htf_bias", "NEUTRAL") if bias else "NEUTRAL"
        mode     = smc.get("structure", {}).get("mode", "") if smc else ""
        po3      = mmxm.get("po3_phase", "") if mmxm else ""

        # Biais HTF clair → direction principale
        if "BULL" in htf_bias:
            base_dir = "BUY"
        elif "BEAR" in htf_bias:
            base_dir = "SELL"
        else:
            base_dir = "NONE"

        # Validation locale : MSS doit confirmer la direction
        if base_dir == "BUY" and ("MSS_BULL" in mode or "BOS_BULL" in mode):
            return "BUY"
        if base_dir == "SELL" and ("MSS_BEAR" in mode or "BOS_BEAR" in mode):
            return "SELL"

        # Phase de distribution active dans la direction HTF
        if "DISTRIBUTION" in po3 or "EXPANSION" in po3:
            if base_dir != "NONE":
                return base_dir

        # Biais fort sans confirmation locale → WAIT
        if base_dir != "NONE" and "NEUTRAL" not in htf_bias:
            # Accepter avec un biais expansion fort même sans MSS
            if "EXPANSION" in htf_bias:
                return base_dir

        return "NONE"

    # ============================================================
    # CALCULER ENTRY / SL / TP1 / TP2
    # ============================================================
    def _get_sl_margin(self, symbol: str, swing_low: float, swing_high: float) -> float:
        """
        AUDIT #4 FIX — Calcule un buffer SL adaptatif selon le type d'instrument.
        Bible ICT : SL placé sous/sur la mèche basse/haute du swing avec un
        buffer adapté à la volatilité de l'instrument (pas un ratio fixe).
        Returns: valeur absolue du buffer (en prix, pas en %)
        """
        sym = symbol.upper().replace('M', '', 1) if symbol.upper().endswith('M') else symbol.upper()
        # Nota: on strip le suffixe 'm' Exness pour la détection
        # (XAUUSDm → XAUUSD, BTCUSDm → BTCUSD, NAS100m → NAS100)
        sym_clean = sym.rstrip('M')  # Retire uniquement le dernier 'M' si présent
        # Métaux précieux
        if 'XAU' in sym_clean or 'GOLD' in sym_clean:
            return 1.00     # 1$ = ~10 pips sur XAUUSDm (or réel ~2900$)
        if 'XAG' in sym_clean:
            return 0.05
        # Indices (NAS100m, US30m, US500m, NAS100, US30...)
        if 'NAS' in sym_clean or 'NDX' in sym_clean or '100' in sym_clean:
            return 15.0     # 15 points index
        if 'US500' in sym_clean or 'SP500' in sym_clean or 'SPX' in sym_clean:
            return 5.0
        if 'US30' in sym_clean or 'DOW' in sym_clean or 'DJ' in sym_clean:
            return 30.0
        # Crypto
        if 'BTC' in sym_clean:
            return 100.0    # 100$ buffer (BTC à ~67 000$)
        if 'ETH' in sym_clean:
            return 5.0
        # JPY pairs : valeur nominale grande
        if 'JPY' in sym_clean:
            price_ref = swing_low if swing_low > 0 else swing_high
            return price_ref * 0.0005  # 5 pips JPY
        # Pétrole
        if 'OIL' in sym_clean or 'WTI' in sym_clean or 'XTI' in sym_clean:
            return 0.20
        # Forex majeurs / mineurs par défaut
        return 0.0003  # 3 pips standard

    def _calculate_levels(self, direction, smc, liq, exe, bias, symbol: str = ""):
        """
        C1 FIX : symbol ajouté comme paramètre pour récupérer le vrai prix MT5.
        Calcule les niveaux de trading selon la Bible ICT :
        - Entry EXECUTE : prix marché réel (tick MT5 ou fallback EQ)
        - Entry LIMIT   : niveau OTE (70.5% Fibonacci) — recalculé dans evaluate()
        - SL    : sous/sur le dernier swing structurel (buffer adaptatif #4)
        - TP1   : 50% du Dealing Range (Partial TP / Breakeven)
        - TP2   : DOL (Draw on Liquidity) — cible ultime
        """
        try:
            swh = smc["structure"]["swh"]
            swl = smc["structure"]["swl"]
            mid = (swh + swl) / 2

            erl_h = liq["erl"]["high"]
            erl_l = liq["erl"]["low"]
            dol   = bias.get("draw_on_liquidity", {})
            dol_price = dol.get("price", 0)

            # AUDIT #4 FIX : buffer adaptatif selon l'instrument
            sl_buffer = self._get_sl_margin(symbol, swl, swh)

            # --- C1 FIX : Vrai prix du marché pour EXECUTE (symbol maintenant défini) ---
            market_price = 0.0
            try:
                import MetaTrader5 as mt5 # type: ignore
                if mt5.initialize():
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        market_price = tick.ask if direction == "BUY" else tick.bid
            except Exception:
                pass

            # Fallback mode Paper : milieu du range (EQ)
            if market_price == 0.0:
                market_price = swl + (swh - swl) * 0.5

            if direction == "BUY":
                entry = market_price
                sl    = swl - sl_buffer           # Sous la mèche swing low
                tp1   = mid
                # DOL price for BUY must be HIGHER than the entry.
                tp2   = dol_price if (dol_price > entry) else erl_h

            else:  # SELL
                entry = market_price
                sl    = swh + sl_buffer           # Sur la mèche swing high
                tp1   = mid
                # DOL price for SELL must be LOWER than the entry.
                # If valid DOL is provided and it's lower than entry, use it. Otherwise use the External Range Liquidity low.
                tp2   = dol_price if (dol_price > 0 and dol_price < entry) else erl_l

            return entry, sl, tp1, tp2

        except (KeyError, TypeError, ZeroDivisionError):
            return 0, 0, 0, 0

    # ============================================================
    # CALCUL RATIO R/R
    # ============================================================
    def _calc_rr(self, entry, sl, tp) -> float:
        risk   = abs(entry - sl)
        reward = abs(tp - entry)
        if risk == 0:
            return 0.0
        return round(reward / risk, 2)

    # ============================================================
    # CALCUL TAILLE DE POSITION
    # ============================================================
    def _calculate_lot_size(self, entry, sl, symbol) -> float:
        """
        Calcule la taille de lot exacte pour risquer risk_pct% du capital.
        Utilise trade_tick_value de MT5 pour être parfaitement précis.
        """
        risk_amount = self.account_bal * self.risk_pct
        dist = abs(entry - sl)
        if dist == 0:
            return 0.01

        try:
            import MetaTrader5 as mt5  # type: ignore
            if mt5.initialize():
                sym_info = mt5.symbol_info(symbol)
                if sym_info and sym_info.trade_tick_size > 0 and sym_info.trade_tick_value > 0:
                    dist_ticks = dist / sym_info.trade_tick_size
                    lot = risk_amount / (dist_ticks * sym_info.trade_tick_value)
                    vol_step = sym_info.volume_step
                    # Arrondir au palier de volume correct (ex: 0.01)
                    lot = round(lot / vol_step) * vol_step
                    lot = max(sym_info.volume_min, min(lot, sym_info.volume_max))
                    # Limite raisonnable
                    return round(min(lot, 5.0), 2)
        except Exception:
            pass

        # Fallback si MT5 non disponible — CRIT-4 FIX
        # Valeur monétaire d'1 pip par lot standard (approximation réaliste)
        # XAUUSD: 1 pip = 0.01, taille contrat = 100oz → 1 lot = 1.0 $/pip
        # EURUSD/GBPUSD: 1 pip = 0.0001, contrat 100 000→ 10 $/pip/lot
        # NAS100/US30: 1 pip = 1.0 index point → 1 $/pip/lot
        pip_value_per_lot = {
            "XAUUSD":  1.0,   # 0.01 pip × 100 oz
            "XAGUSD":  50.0,  # métal argent
            "EURUSD":  10.0,  "GBPUSD":  10.0,  "AUDUSD":  10.0,
            "USDCAD":  10.0,  "USDCHF":  10.0,  "NZDUSD":  10.0,
            "USDJPY":  9.0,   "EURJPY":  9.0,   "GBPJPY":  9.0,
            "NAS100":  1.0,   "US30":    1.0,   "US500":   1.0,
            "BTCUSD":  1.0,   "ETHUSD":  1.0,
        }
        pip_size = {
            "XAUUSD": 0.01,  "XAGUSD": 0.01,
            "USDJPY": 0.01,  "EURJPY": 0.01, "GBPJPY": 0.01,
            "NAS100": 1.0,   "US30":   1.0,  "US500":  1.0,
            "BTCUSD": 1.0,   "ETHUSD": 0.1,
        }
        sym_upper = symbol.upper()
        p_size    = pip_size.get(sym_upper, 0.0001)  # Forex majeur par défaut
        p_val     = pip_value_per_lot.get(sym_upper, 10.0)
        dist_pips = dist / p_size
        if dist_pips == 0:
            return 0.01
        lot = risk_amount / (dist_pips * p_val)
        lot = max(0.01, round(lot, 2))
        return min(lot, 5.0)

    # ============================================================
    # IDENTIFIER LE SETUP ICT ACTIF
    # ============================================================
    def _identify_setup(self, mmxm, smc, clock) -> str:
        """Identifie le setup ICT le plus pertinent."""
        if mmxm is None or smc is None:
            return "STANDARD"

        sb_status = mmxm.get("silver_bullet", "INACTIVE")
        ts        = mmxm.get("turtle_soup", "NONE")
        po3       = mmxm.get("po3_phase", "")
        mode      = smc.get("structure", {}).get("mode", "")
        disp      = smc.get("displacement", {}).get("is_displaced", False)
        fvgs      = smc.get("fvgs", [])
        blocks    = smc.get("institutional_blocks", [])
        breakers  = [b for b in blocks if "BREAKER" in b.get("type", "")]
        kz        = clock.get("killzone", "NONE")

        # Grail : MSS + Displacement + FVG + Breaker + Killzone
        if "MSS" in mode and disp and fvgs and breakers and kz != "NONE":
            return "GRAIL_SETUP"

        # Silver Bullet : dans la fenêtre SB + MSS + FVG
        if "CONFIRMED" in sb_status:
            return "SILVER_BULLET"

        # Unicorn : Breaker + FVG alignés
        if breakers and fvgs:
            for bk in breakers:
                for f in fvgs:
                    z = bk.get("refined_zone", [0, 0])
                    if z[0] <= f.get("ce", 0) <= z[1]:
                        return "UNICORN"

        # Turtle Soup / SFP
        if ts != "NONE":
            return f"TURTLE_SOUP_{ts}"

        # Judas Swing
        if "MANIPULATION" in po3 and "MSS" in mode:
            return "JUDAS_SWING"

        return "STANDARD_ICT"

    # ============================================================
    # CONSTRUIRE LE NARRATIVE DE LA DÉCISION
    # ============================================================
    def _build_reason(self, score, direction, clock, bias, smc, liq, mmxm, setup) -> str:
        htf    = bias.get("htf_bias", "N/A") if bias else "N/A"
        kz     = clock.get("killzone", "NONE")
        macro  = clock.get("macro", "NONE")
        mode   = smc.get("structure", {}).get("mode", "N/A") if smc else "N/A"
        po3    = mmxm.get("po3_phase", "N/A") if mmxm else "N/A"
        dol    = bias.get("draw_on_liquidity", {}).get("name", "N/A") if bias else "N/A"

        parts = [
            f"Score {score}/100",
            f"Direction: {direction}",
            f"Setup: {setup}",
            f"HTF Bias: {htf}",
            f"Structure: {mode}",
            f"Phase PO3: {po3}",
            f"KZ: {kz}",
        ]
        if macro != "NONE":
            parts.append(f"Macro: {macro}")
        parts.append(f"Target: {dol}")

        return " | ".join(parts)
