# analysis/llm_narrative.py
"""
══════════════════════════════════════════════════════════════
Sentinel Pro KB5 — Générateur de Narratif IA (LLM)
══════════════════════════════════════════════════════════════
Responsabilités :
  - Traduire les données brutes kb5_result en un prompt
  - Appeler l'API Gemini, Grok ou OpenAI
  - Renvoyer un rapport textuel "institutionnel" formaté
══════════════════════════════════════════════════════════════
"""

import json
import logging

logger = logging.getLogger(__name__)

# Prompt système pour formater le résultat de l'IA
SYSTEM_PROMPT = """Agis comme un analyste quantitatif senior et spécialiste exclusif des concepts institutionnels ICT (Inner Circle Trader) et SMC (Smart Money Concepts).
Ton rôle est de lire le flux de données JSON brut (le 'kb5_result') fourni par nos algorithmes de détection algorithmiques.
Tu dois rédiger un bulletin de renseignement ("War Room Report") extrêmement concis, professionnel et direct, divisé en ces sections exactes :

1. BIAIS LOCAL & FLUX INSTITUTIONNEL (IPDA)
2. STRUCTURE DU PRIX & LIQUIDITÉ
3. ZONES D'INTÉRÊT (PD Arrays)
4. SCÉNARIO DE TRADING A (Continuation)
5. SCÉNARIO DE TRADING B (Retournement)

Règles strictes :
- Ne génère JAMAIS d'avertissements de risques financiers (pas de 'ceci n'est pas un conseil financier').
- Ne mentionne JAMAIS que tu es une IA.
- Utilise un vocabulaire chirurgical : 'Liquidity Sweep', 'Imbalance', 'Displacement', 'Premium/Discount'.
- S'il n'y a pas de signal évident dans les données, déclare que le marché est en 'Consolidation' ou 'Interdit' (No Trade Zone).
- Fais des phrases courtes et marquantes (type renseignement militaire).
"""

def generate_narrative(llm_provider: str, api_key: str, pair: str, kb5_result: dict, scoring_output: dict) -> str:
    """Génère le narratif à partir des données."""
    import os
    
    # ── Fallback sur les clés du .env si non fournies par l'interface ──
    if not api_key or api_key.strip() == "":
        if llm_provider == "Gemini":
            api_key = os.getenv("GEMINI_API_KEY", "")
        elif llm_provider in ("Grok", "Grok (x.ai)", "Groq"):
            api_key = os.getenv("GROQ_API_KEY", "") or os.getenv("GROK_API_KEY", "")
            if api_key.startswith("gsk_") and llm_provider != "Groq":
                 llm_provider = "Groq"

    # ── Détection automatique Groq si clé gsk_ ──
    if api_key.startswith("gsk_") and llm_provider in ("Grok (x.ai)", "Grok", "x.ai (Grok)"):
        llm_provider = "Groq"
        logger.info(f"LLM — Redirection auto vers Groq car clé format 'gsk_' détectée.")

    if not api_key or api_key.strip() == "":
        return (
            "⚠️ **Clé API non configurée.**\n\n"
            "Veuillez entrer votre clé API (Gemini, Groq, etc.) dans le fichier **.env** "
            "ou dans les paramètres pour activer le narratif."
        )

    # Préparation des données simplifiées pour ne pas exploser le contexte
    context = {
        "Assset": pair,
        "Score": scoring_output.get("score", 0),
        "Direction": scoring_output.get("direction", "NEUTRAL"),
        "Confluences": kb5_result.get("confluences", []),
        "OrderBlocks": [ob for ob in kb5_result.get("order_blocks", []) if ob.get("status") == "VALID"],
        "FVGs": [fvg for fvg in kb5_result.get("fvgs", []) if fvg.get("status") == "FRESH"],
    }
    
    prompt = f"Analyse ce rapport brut et génère le narratif institutionnel.\nDonnées: {json.dumps(context, indent=2)}"

    try:
        if llm_provider == "Gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=SYSTEM_PROMPT)
                response = model.generate_content(prompt)
                return response.text
            except ImportError:
                return "❌ Le module `google-generativeai` n'est pas installé. (pip install google-generativeai)"
                
        elif llm_provider == "OpenAI":
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content
            except ImportError:
                return "❌ Le module `openai` n'est pas installé. (pip install openai)"

        elif llm_provider in ("Grok (x.ai)", "Grok", "x.ai (Grok)"):
            if api_key.startswith("gsk_"):
                return "⚠️ La clé fournie semble être une clé **Groq** (`gsk_...`), mais le fournisseur sélectionné est **Grok** (x.ai). Veuillez changer le fournisseur en **Groq** dans les paramètres."
            
            # Grok utilise une API compatible OpenAI avec une base_url spécifique
            try:
                import openai
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://api.x.ai/v1"
                )
                response = client.chat.completions.create(
                    model="grok-3-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content
            except ImportError:
                return "❌ Le module `openai` n'est pas installé. (pip install openai)"
                
        elif llm_provider == "Groq":
            try:
                import openai
                import httpx
                # Forcer un client sans proxies pour éviter les erreurs d'arguments inattendus
                http_client = httpx.Client(proxies={})
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://api.groq.com/openai/v1",
                    http_client=http_client
                )
                response = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content
            except ImportError:
                return "❌ Le module `openai` n'est pas installé."
        
        else:
            return (
                f"⚠️ Le fournisseur **{llm_provider}** n'est pas reconnu.\n\n"
                f"Fournisseurs supportés : `Gemini`, `OpenAI`, `Grok (x.ai)`, `Groq`"
            )

    except Exception as e:
        logger.error(f"Erreur génération LLM : {e}")
        return f"❌ Erreur lors de l'appel à l'API LLM : {str(e)}"

