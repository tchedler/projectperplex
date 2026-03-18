"""
ai_analyst.py — Analyste IA avec Google Gemini 2.0 Flash
Enrichit les analyses ICT avec une intelligence artificielle profonde.
Utilisé pour :
1. Validation A+ d'un signal ICT (confluence vérifiée par LLM)
2. Narratif qualitatif enrichi (analyse comme un trader ICT expert)
3. Rapport post-session intelligent

Documentation API : https://ai.google.dev/
"""
import os
import json
import time
import logging
from typing import Optional

# Charger .env si python-dotenv installé
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

log = logging.getLogger("ICT_BOT.Gemini")

# ============================================================
# CONFIGURATION
# ============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCzI-7c5LGpLX-VMHvLERJbJRcSiFkSA1Y")
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

# Profil système : Gemini joue le rôle d'un trader ICT Senior
SYSTEM_PROMPT = """Tu es un trader ICT (Inner Circle Trader) expert de niveau mentorship avancé.
Tu maîtrises parfaitement :
- La Bible ICT complète : IPDA, AMD, MSS, BOS, FVG, OB, Breaker, SMT, ERL/IRL
- Le scoring de probabilité basé sur la confluence multi-timeframe
- La gestion du risque ICT : 1% par trade, SL sous le dernier swing structurel
- Les profils de trading : Scalp (M1/M5), Day Trade (H1/M15/M5), Swing (D1/H4/H2)

Tu réponds TOUJOURS en français.
Tu es PRÉCIS, DIRECT et HONNÊTE. Si les conditions ne sont pas réunies, tu le dis clairement.
Tu ne trades JAMAIS sans : Killzone active + Boolean_Sweep_ERL confirmé + MSS avec Displacement.
"""


class AIAnalyst:
    """
    Analyste IA propulsé par Google Gemini 2.0 Flash.
    Fournit une validation qualitative des signaux ICT
    et génère des narratifs de niveau expert.
    """

    def __init__(self):
        self.model = None
        self._init_gemini()
        self._call_count    = 0
        self._last_reset    = time.time()
        self._daily_limit   = 1400  # sécurité sous les 1500 req/jour gratuit

    def _init_gemini(self):
        if not GEMINI_AVAILABLE:
            log.warning("google-generativeai non installé. Pip: pip install google-generativeai")
            return
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=SYSTEM_PROMPT,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,      # Précision > créativité pour le trading
                    max_output_tokens=1024,
                )
            )
            log.info(f"✅ Gemini initialisé : {GEMINI_MODEL}")
        except Exception as e:
            log.error(f"Erreur init Gemini: {e}")

    def _check_quota(self) -> bool:
        """Vérifie qu'on ne dépasse pas la limite quotidienne."""
        # Reset compteur toutes les 24h
        if time.time() - self._last_reset > 86400:
            self._call_count = 0
            self._last_reset = time.time()
        return self._call_count < self._daily_limit

    def _call(self, prompt: str, max_retries: int = 2) -> Optional[str]:
        """Appel Gemini avec retry automatique."""
        if self.model is None:
            return None
        if not self._check_quota():
            log.warning("Quota Gemini journalier atteint")
            return None

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                self._call_count += 1
                return response.text
            except Exception as e:
                log.warning(f"Gemini erreur (tentative {attempt+1}): {e}")
                time.sleep(2 ** attempt)   # Backoff exponentiel
        return None

    # ============================================================
    # MÉTHODE 1 : VALIDATION A+ DU SIGNAL
    # ============================================================
    def validate_signal(self, signal_context: dict) -> dict:
        """
        Valide un signal ICT avec Gemini.
        signal_context doit contenir les données clés de l'analyse.
        Retourne {validated: bool, confidence: str, reason: str, gemini_note: str}
        """
        sf = signal_context

        prompt = f"""
Voici les conditions de marché actuelles pour un signal ICT. Valide ou invalide ce trade.

=== CONTEXTE ===
Symbole    : {sf.get('symbol', '?')}
Timeframe  : {sf.get('tf', '?')}
Direction  : {sf.get('direction', '?')}
Score ICT  : {sf.get('score', 0)}/100
Setup      : {sf.get('setup_name', '?')}

=== ANALYSE ICT ===
Biais HTF  : {sf.get('htf_bias', '?')}
Phase PO3  : {sf.get('po3_phase', '?')}
Structure  : {sf.get('structure_mode', '?')}
Displacement: {sf.get('displacement', False)}
Boolean_Sweep_ERL: {sf.get('sweep_erl', False)}
Killzone   : {sf.get('killzone', 'NONE')}
Macro      : {sf.get('macro', 'NONE')}

=== NIVEAUX ===
Entry      : {sf.get('entry', 0):.5f}
Stop Loss  : {sf.get('sl', 0):.5f}
TP1 (50%)  : {sf.get('tp1', 0):.5f}
TP2 (DOL)  : {sf.get('tp2', 0):.5f}
DOL cible  : {sf.get('dol_name', '?')} @ {sf.get('dol_price', 0):.5f}
Zone       : {sf.get('eq_zone', '?')} ({sf.get('eq_pct', 0):.1f}%)
R/R estimé : {sf.get('rr', 0):.1f}

=== FVG / OB FRAIS ===
FVG Fresh  : {sf.get('fresh_fvg_count', 0)}
OB Frais   : {sf.get('ob_fresh_count', 0)}
EQH SMOOTH : {sf.get('eqh_smooth', False)}
EQL SMOOTH : {sf.get('eql_smooth', False)}

RÉPONSE REQUISE (JSON strict) :
{{
  "validated": true/false,
  "confidence": "A_PLUS" | "HIGH" | "MEDIUM" | "LOW",
  "trade_ok": true/false,
  "main_reason": "explication courte (1 phrase)",
  "risks": ["risque 1", "risque 2"],
  "setup_quality": "excellent/bon/acceptable/insuffisant",
  "gemini_note": "commentaire expert court (2-3 phrases max)"
}}
"""
        raw = self._call(prompt)
        if raw:
            try:
                # Extraire le JSON de la réponse
                start = raw.find("{")
                end   = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass

        return {
            "validated": True,   # Fallback neutre si Gemini indisponible
            "confidence": "MEDIUM",
            "trade_ok": True,
            "main_reason": "Validation Gemini indisponible — score ICT utilisé",
            "risks": [],
            "setup_quality": "acceptable",
            "gemini_note": "Analyse Gemini non disponible."
        }

    # ============================================================
    # MÉTHODE 2 : NARRATIF ICT ENRICHI PAR IA
    # ============================================================
    def generate_narrative(self, analysis_context: dict) -> str:
        """
        Génère un narratif de marché qualitatif enrichi par Gemini.
        Complète le narratif généré par ChecklistExpert.
        """
        sf = analysis_context

        prompt = f"""
En tant que trader ICT senior, analyse le marché suivant et rédige un brief de trading concis.

Symbole: {sf.get('symbol','?')} | TF: {sf.get('tf','?')} | Heure NY: {sf.get('ny_time','?')}

Biais HTF: {sf.get('htf_bias','?')} | Score: {sf.get('score',0)}/100 | Phase PO3: {sf.get('po3_phase','?')}
Structure: {sf.get('structure_mode','?')} | KZ: {sf.get('killzone','NONE')} | Macro: {sf.get('macro','NONE')}
DOL: {sf.get('dol_name','?')} @ {sf.get('dol_price',0):.5f} | Zone: {sf.get('eq_zone','?')} {sf.get('eq_pct',0):.0f}%
Boolean_Sweep_ERL: {sf.get('sweep_erl',False)} | Displacement: {sf.get('displacement',False)}
MMXM Cycle: {sf.get('mmxm_cycle','?')} | Silver Bullet: {sf.get('silver_bullet','?')}

Rédige un brief structuré en 3 parties (150 mots max total) :
1. **FLUX INSTITUTIONNEL** (ce que font les banques/algos en ce moment)
2. **SETUP ACTIF** (ce qu'on cherche + conditions manquantes)
3. **VERDICT** (trader ou attendre + pourquoi)

Style : professionnel, direct, comme un briefing de salle de marché.
"""
        result = self._call(prompt)
        return result if result else ""

    # ============================================================
    # MÉTHODE 3 : RAPPORT POST-SESSION IA
    # ============================================================
    def generate_session_report(self, session_stats: dict, failure_cases: list) -> str:
        """
        Génère un rapport de session intelligent avec analyse des erreurs.
        """
        fc_text = "\n".join([
            f"- {fc.get('error_type','?')}: {fc.get('lesson_learned','?')}"
            for fc in failure_cases[:5]
        ])

        prompt = f"""
Analyse cette session de trading ICT et génère un rapport d'amélioration.

STATISTIQUES :
- Win Rate : {session_stats.get('win_rate', 0)}% ({session_stats.get('win_count',0)}W / {session_stats.get('loss_count',0)}L)
- PnL : {session_stats.get('total_pnl', 0):+.2f}$
- Total trades : {session_stats.get('total_trades', 0)}

ERREURS IDENTIFIÉES :
{fc_text if fc_text else 'Aucune erreur catégorisée'}

Fournis :
1. **Analyse des patterns d'erreurs** (ce qui se répète)
2. **Actions correctives concrètes** (2-3 max, spécifiques ICT)
3. **Focus pour demain** (1 seule priorité d'apprentissage)

Sois direct et actionnable. Max 200 mots.
"""
        result = self._call(prompt)
        return result if result else "Rapport Gemini indisponible."

    @property
    def is_available(self) -> bool:
        return self.model is not None and GEMINI_AVAILABLE

    @property
    def quota_remaining(self) -> int:
        return max(0, self._daily_limit - self._call_count)
