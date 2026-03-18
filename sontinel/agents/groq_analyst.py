"""
groq_analyst.py — Analyste IA avec GROQ (Llama 3.1 8B Instant)
Ultra-rapide : ~100-200ms par requête vs 1-2s pour Gemini.
Utilisé pour :
1. Analyse de contexte rapide (sentiment, risque événementiel)
2. Pré-filtrage des signaux en temps quasi-réel
3. Détection de conditions de marché dangereuses (NFP, FOMC, etc.)
4. Second avis express sur un setup ICT

Documentation API : https://console.groq.com/docs/
"""
import os
import re
import json
import time
import logging
from typing import Optional

try:
    import dotenv  # type: ignore
    dotenv.load_dotenv()
except ImportError:
    pass

try:
    import groq  # type: ignore
    from groq import Groq # type: ignore
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

log = logging.getLogger("ICT_BOT.GROQ")

# ============================================================
# CONFIGURATION
# ============================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

GROQ_SYSTEM = """You are a professional ICT (Inner Circle Trader) trading assistant.
You are fast, precise, and always respond in French.
You evaluate market conditions based on ICT methodology.
Your answers are concise, direct, and structured.
You never recommend a trade without proper ICT confirmation.
"""

# Événements macro à risque (détection simple sur calendrier)
HIGH_RISK_KEYWORDS = [
    "nfp", "non-farm", "fomc", "fed", "bce", "boj", "cpi", "inflation",
    "pce", "gdp", "pib", "rate decision", "taux", "powell", "lagarde",
    "jobs report", "payrolls", "unemployment"
]


class GroqAnalyst:
    """
    Analyste IA ultra-rapide via GROQ/Llama 3.1.
    Conçu pour les analyses en temps quasi-réel sans latence.
    """

    def __init__(self):
        self.client = None
        self._init_groq()
        self._call_count = 0

    def _init_groq(self):
        if not GROQ_AVAILABLE:
            log.warning("groq non installé. Pip: pip install groq")
            return
        try:
            self.client = Groq(api_key=GROQ_API_KEY)
            log.info(f"✅ GROQ initialisé : {GROQ_MODEL}")
        except Exception as e:
            log.error(f"Erreur init GROQ: {e}")

    def _call(self, prompt: str, max_tokens: int = 512,
              temperature: float = 0.2) -> Optional[str]:
        """Appel GROQ/Llama avec gestion d'erreur."""
        # I7 FIX : Type narrowing pour satisfaire l'IDE (Pyre/Pylance)
        client = self.client
        if client is None:
            return None
            
        try:
            # On utilise le client déjà vérifié non-None
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": GROQ_SYSTEM},
                    {"role": "user",   "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            self._call_count += 1
            content = response.choices[0].message.content
            if content is None:
                return None
            return str(content)
        except Exception as e:
            log.warning(f"GROQ erreur: {e}")
            return None

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extrait un dictionnaire JSON d'une chaîne brute avec robustesse type-safe."""
        try:
            # I7 FIX : Utilisation de REGEX pour éviter le slicing (conflit IDE/Pyre)
            match = re.search(r"(\{.*\})", text, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
        except Exception:
            pass
        return None

    # ============================================================
    # MÉTHODE 1 : PRÉ-FILTRE RAPIDE DU SIGNAL
    # ============================================================
    def quick_signal_filter(self, signal_context: dict) -> dict:
        """
        Pré-filtre ultra-rapide (~150ms) d'un signal ICT.
        Retourne {pass_filter: bool, flag: str, note: str}
        """
        sf = signal_context
        score  = sf.get("score", 0)
        htf    = sf.get("htf_bias", "NEUTRAL")
        kz     = sf.get("killzone", "NONE")
        sweep  = sf.get("sweep_erl", False)
        disp   = sf.get("displacement", False)
        po3    = sf.get("po3_phase", "")
        direction = sf.get("direction", "NONE")

        prompt = f"""
Évalue ce signal ICT en 10 secondes. Réponds UNIQUEMENT en JSON.

Signal: {direction} sur {sf.get('symbol','?')} ({sf.get('tf','?')})
Score: {score}/100 | KZ: {kz} | HTF Bias: {htf}
Sweep ERL: {sweep} | Displacement: {disp} | Phase PO3: {po3}
R/R: {sf.get('rr', 0):.1f}

JSON requis:
{{
  "pass_filter": true/false,
  "flag": "OK" | "DUBIOUS" | "BLOCKED",
  "critical_issue": "problème principal ou null",
  "note": "1 phrase max"
}}
"""
        raw = self._call(prompt, max_tokens=150, temperature=0.1)
        if isinstance(raw, str):
            res = self._extract_json(raw)
            if res: return res

        # Fallback règle simple si GROQ indisponible
        flag = "OK"
        issue = None
        if not sweep:
            flag = "BLOCKED"
            issue = "Boolean_Sweep_ERL = False"
        elif score < 65:
            flag = "BLOCKED"
            issue = f"Score trop bas: {score}/100"
        elif kz == "NONE" and sf.get("macro", "NONE") == "NONE":
            flag = "DUBIOUS"
            issue = "Hors Killzone et Macro"
        elif "ACCUMULATION" in po3:
            flag = "DUBIOUS"
            issue = "Phase d'accumulation — pas d'entrée"

        return {
            "pass_filter": flag != "BLOCKED",
            "flag":        flag,
            "critical_issue": issue,
            "note":        issue or "Conditions ICT acceptables"
        }

    # ============================================================
    # MÉTHODE 2 : ANALYSE DU CONTEXTE DE MARCHÉ
    # ============================================================
    def analyze_market_context(self, symbol: str, clock: dict,
                               bias: dict, smc: dict) -> dict:
        """
        Analyse rapide du contexte général du marché.
        Retourne un résumé en 2-3 lignes + alerte si risque.
        """
        kz     = clock.get("killzone", "NONE")
        macro  = clock.get("macro", "NONE")
        day    = clock.get("day", "?")
        htf    = bias.get("htf_bias", "NEUTRAL") if bias else "NEUTRAL"
        mode   = smc.get("structure", {}).get("mode", "?") if smc else "?"
        disp   = smc.get("displacement", {}).get("is_displaced", False) if smc else False

        prompt = f"""
Context marché ICT rapide pour {symbol}.

Jour: {day} | KZ: {kz} | Macro: {macro}
Biais HTF: {htf} | Structure: {mode} | Displacement: {disp}

En 3 lignes maximum :
1. Résumé du contexte actuel
2. Ce que le marché cherche maintenant
3. Alerte si risque particulier (LUNDI = Seek&Destroy, etc.)
"""
        result = self._call(prompt, max_tokens=200)
        return {
            "context_summary": result or "Contexte non disponible",
            "symbol":  symbol,
            "killzone": kz,
            "timestamp": clock.get("ny_time", "?")
        }

    # ============================================================
    # MÉTHODE 3 : DÉTECTION D'ÉVÉNEMENTS MACRO RISQUÉS
    # ============================================================
    def check_macro_risk(self, news_text: str = "") -> dict:
        """
        Détecte si un événement macro à risque est présent.
        Si news_text vide, analyse uniquement le calendrier temporel.
        """
        # Détection locale sans appel API (rapide)
        risk_level = "LOW"
        detected   = []

        if news_text:
            text_lower = news_text.lower()
            for kw in HIGH_RISK_KEYWORDS:
                if kw in text_lower:
                    detected.append(kw.upper())
                    risk_level = "HIGH"

        if detected and self.client:
            prompt = f"""
Événements macro détectés : {', '.join(detected)}

Ces événements affectent-ils le trading ICT aujourd'hui ?
Réponds en JSON :
{{
  "should_avoid_trade": true/false,
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "events": ["{detected[0] if detected else 'NONE'}"],
  "recommendation": "1 phrase d'action"
}}
"""
            raw = self._call(prompt, max_tokens=150)
            if isinstance(raw, str):
                res = self._extract_json(raw)
                if res: return res

        return {
            "should_avoid_trade": risk_level == "HIGH",
            "risk_level":   risk_level,
            "events":       detected,
            "recommendation": "Éviter les trades les 30min avant/après l'événement" if detected else "Contexte macro normal"
        }

    # ============================================================
    # MÉTHODE 4 : DEBRIEFING RAPIDE D'UN TRADE FERMÉ
    # ============================================================
    def debrief_trade(self, trade: dict) -> str:
        """
        Analyse rapide d'un trade fermé (win ou loss).
        Retourne une leçon ICT concise.
        """
        status    = trade.get("status", "?")
        pnl       = trade.get("pnl_money", 0)
        direction = trade.get("direction", "?")
        symbol    = trade.get("symbol", "?")
        score     = trade.get("score", 0)
        kz        = trade.get("killzone", "?")
        error     = trade.get("error_category", "NONE")
        reason    = trade.get("close_reason", "?")
        setup     = trade.get("setup_name", "?")

        prompt = f"""
Débriefe ce trade ICT en 2-3 phrases max.

{direction} {symbol} | Résultat: {status} ({pnl:+.2f}$)
Score au départ: {score}/100 | Setup: {setup}
Killzone: {kz} | Fermeture: {reason}
Erreur identifiée: {error}

Donne une leçon ICT concrète et un point d'amélioration spécifique.
"""
        return self._call(prompt, max_tokens=150) or "Débrief indisponible."

    @property
    def is_available(self) -> bool:
        return self.client is not None and GROQ_AVAILABLE
