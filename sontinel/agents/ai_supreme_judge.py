"""
ai_supreme_judge.py — Juge Final IA du Centre d'Opérations
Prend en entrée un signal algorithmique pur (généré par le math de la stratégie)
et valide le trade via Groq (rapidité) et Gemini (analyse profonde).
"""
import logging
from typing import Optional
from agents.trading_judge import TradeSignal

# Dégradation Gracieuse
try:
    from agents.ai_analyst import AIAnalyst
    from agents.groq_analyst import GroqAnalyst
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

log = logging.getLogger("ICT_BOT.AISupreme")


class AISupremeJudge:
    def __init__(self, score_execute: int = 80):
        self.score_execute = score_execute
        self.groq = None
        self.gemini = None
        
        if AI_AVAILABLE:
            try:
                self.groq = GroqAnalyst()
                self.gemini = AIAnalyst()
                log.info("⚖️ AI Supreme Judge initialisé avec succès.")
            except Exception as e:
                log.warning(f"Erreur init AI Supreme Judge: {e}")

    def evaluate_signal(self, signal: TradeSignal, context: dict) -> TradeSignal:
        """
        Évalue le signal généré mathématiquement.
        Utilise Groq pour un pré-filtre rapide, et Gemini pour une validation finale.
        :param signal: Le signal TradeSignal généré par la stratégie via TradingJudge.
        :param context: Dictionnaire contenant toutes les informations de l'analyse ICT.
        :return: Le TradeSignal enrichi et potentiellement déclassé/bloqué par l'IA.
        """
        if not AI_AVAILABLE:
            return signal

        if signal.action == "NO_TRADE":
            return signal  # Inutile de gaspiller des tokens si le signal est déjà rejeté mathématiquement

        groq_flag = "OK"
        groq_note = ""
        gemini_validated = True
        gemini_note = ""
        gemini_risks = []

        # --- VALIDATION DES DONNÉES CRITIQUES (Anti-Dossier Vide) ---
        bias = context.get("bias")
        smc = context.get("smc")
        mmxm = context.get("mmxm")
        clock = context.get("clock")

        if not bias or not smc or not mmxm or not clock:
            signal.reason += " | ❌ IA: Contexte incomplet (Calculs en cours...)"
            if signal.action == "EXECUTE":
                signal.action = "LIMIT"
            return signal

        sweep = smc.get("boolean_sweep_erl", {}) if smc else {}
        fvg_ct = len(smc.get("fvgs_pd_arrays", {}).get("all_fvgs", [])) if smc else 0
        ob_ct = len(smc.get("institutional_blocks", [])) if smc else 0
        dol_d = bias.get("draw_on_liquidity", {}) if bias else {}

        # Reconstruire le sig_ctx attendu par Groq/Gemini
        sig_ctx = {
            "symbol": signal.symbol,
            "tf": signal.timeframe,
            "direction": signal.direction,
            "score": signal.score,
            "setup_name": signal.setup_name,
            "htf_bias": bias.get("htf_bias", "?") if bias else "?",
            "po3_phase": mmxm.get("po3_phase", "") if mmxm else "",
            "structure_mode": smc.get("structure", {}).get("mode", "") if smc else "",
            "displacement": smc.get("displacement", {}).get("is_displaced", False) if smc else False,
            "sweep_erl": sweep.get("value", False),
            "killzone": clock.get("killzone", "NONE"),
            "macro": clock.get("macro", "NONE"),
            "entry": signal.entry,
            "sl": signal.sl,
            "tp1": signal.tp1,
            "tp2": signal.tp2,
            "rr": 0.0,
            "dol_name": dol_d.get("name", "?"),
            "dol_price": dol_d.get("price", 0),
            "eq_zone": "DISCOUNT" if signal.direction == "BUY" else "PREMIUM",
            "eq_pct": 50.0,
            "fresh_fvg_count": fvg_ct,
            "ob_fresh_count": ob_ct,
        }

        # 1. GROQ — pré-filtre ultra-rapide
        if self.groq and self.groq.is_available:
            try:
                gq = self.groq.quick_signal_filter(sig_ctx)
                groq_flag = gq.get("flag", "OK")
                groq_note = gq.get("note", "")
                
                signal.groq_flag = groq_flag
                signal.groq_note = groq_note

                if groq_flag == "BLOCKED":
                    signal.action = "NO_TRADE"
                    signal.reason = f"GROQ: {gq.get('critical_issue', 'Signal bloqué')} — {groq_note}"
                    return signal

                if groq_flag == "DUBIOUS" and signal.action == "EXECUTE":
                    signal.action = "LIMIT"
                    signal.confidence = "MEDIUM"
                    signal.reason += " | ⚠️ Groq douteux -> LIMIT"
            except Exception as e:
                log.warning(f"AI Supreme Judge - Erreur Groq: {e}")
                if signal.action == "EXECUTE":
                    signal.action = "LIMIT"
                    signal.reason += " | ⚠️ IA Indisponible (Groq) -> Sécurité LIMIT"

        # 2. GEMINI — validation profonde (seulement pour les A+)
        if self.gemini and self.gemini.is_available and signal.action in ["EXECUTE", "LIMIT"] and signal.score >= self.score_execute:
            try:
                gv = self.gemini.validate_signal(sig_ctx)
                signal.gemini_validated = gv.get("validated", True)
                signal.gemini_note = gv.get("gemini_note", "")
                signal.gemini_risks = gv.get("risks", [])
                
                if not gv.get("trade_ok", True):
                    if signal.action == "EXECUTE":
                        signal.action = "LIMIT"
                        signal.confidence = "MEDIUM"
                    signal.reason += f" | ⚠️ Gemini: {gv.get('main_reason', 'Vigilance requise')}"
            except Exception as e:
                log.warning(f"AI Supreme Judge - Erreur Gemini: {e}")
                if signal.action == "EXECUTE":
                    signal.action = "LIMIT"
                    signal.reason += " | ⚠️ IA Indisponible (Gemini) -> Sécurité LIMIT"

        return signal
