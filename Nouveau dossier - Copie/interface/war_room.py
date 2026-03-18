# interface/war_room.py
import os, json, logging
import streamlit as st
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SYSTEM_GROQ = (
    "Tu es un validateur de signaux ICT ultra-rapide. "
    "Reponds UNIQUEMENT en JSON strict, sans texte hors JSON. "
    'Format: {"verdict":"EXECUTE"|"WATCH"|"NO_TRADE",'
    '"confidence":"HIGH"|"MEDIUM"|"LOW",'
    '"reason":"1 phrase courte",'
    '"risk_alert":"risque principal ou null"}'
)

SYSTEM_GEMINI = (
    "Tu es un analyste ICT senior. "
    "Tu maitrises IPDA, AMD, Power of 3, MSS, BOS, FVG, OB, Breaker, SMT, ERL/IRL. "
    "Tu reponds TOUJOURS en francais. Tu es PRECIS, DIRECT, CHIRURGICAL. "
    "Style : bulletin de renseignement militaire. Phrases courtes et marquantes. "
    "Interdit : avertissements de risque financier."
)

WAR_ROOM_TEMPLATE = (
    "Analyse ce rapport KB5 et redige le WAR ROOM REPORT en 5 sections.\n\n"
    "=== DONNEES KB5 ===\n"
    "Symbole : {symbol} | Score : {score}/100 | Grade : {grade} | Verdict : {verdict}\n"
    "Direction : {direction} | Biais HTF : {htf_bias} | Zone : {pd_zone}\n"
    "Session : {session} | Killzone : {in_killzone} | RR : {rr}x\n\n"
    "Pyramide KB5 :\n{pyramid}\n\n"
    "Entry : {entry} | SL : {sl} | TP : {tp}\n"
    "Confluences : {confluences}\n"
    "KillSwitches : {killswitches}\n\n"
    "=== RAPPORT REQUIS ===\n"
    "1. BIAIS LOCAL ET FLUX INSTITUTIONNEL (IPDA)\n"
    "2. STRUCTURE DU PRIX ET LIQUIDITE\n"
    "3. ZONES D INTERET (PD Arrays actifs)\n"
    "4. SCENARIO A - Continuation {direction}\n"
    "5. SCENARIO B - Retournement ou No Trade\n\n"
    "Max 250 mots total. Style renseignement operationnel."
)


def _call_groq(prompt, system):
    if not GROQ_API_KEY or not GROQ_API_KEY.startswith("gsk_"):
        return ""
    try:
        import requests
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": "Bearer " + GROQ_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 300,
                "temperature": 0.1,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning("Groq erreur: %s", e)
        return ""


def _call_gemini(prompt, system):
    if not GEMINI_API_KEY:
        return ""
    import requests
    full = system + "\n\n" + prompt
    for model in ["gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash"]:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + model + ":generateContent?key=" + GEMINI_API_KEY
        )
        try:
            resp = requests.post(
                url,
                json={
                    "contents": [{"parts": [{"text": full}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 800},
                },
                timeout=30,
            )
            if resp.status_code in (404, 429):
                logger.warning("Gemini %s indispo (%s)", model, resp.status_code)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            err = str(e).lower()
            if any(x in err for x in ["429", "quota", "404", "not found"]):
                logger.warning("Gemini %s: %s", model, e)
                continue
            logger.warning("Gemini erreur: %s", e)
            return ""
    logger.warning("Gemini - tous les modeles epuises")
    return ""


def _parse_groq(raw):
    try:
        s = raw.find("{"); e = raw.rfind("}") + 1
        if s >= 0 and e > s:
            return json.loads(raw[s:e])
    except Exception:
        pass
    return {"verdict": "WATCH", "confidence": "LOW", "reason": "Validation indisponible", "risk_alert": None}


def _pyramid(tf_scores):
    lines = []
    for tf in ["MN", "W1", "D1", "H4", "H1", "M15"]:
        d = tf_scores.get(tf, {})
        lines.append("  " + tf.ljust(4) + ": " + str(d.get("score", 0)).rjust(3) + "/100  [" + d.get("verdict", "NO_TRADE") + "]")
    return "\n".join(lines)


def render_war_room(symbol, pair_data):
    st.markdown("---")
    st.markdown("### War Room - Analyse IA Institutionnelle")

    has_groq   = bool(GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"))
    has_gemini = bool(GEMINI_API_KEY)

    if not has_groq and not has_gemini:
        st.warning("Aucune cle API - ajoutez GROQ_API_KEY et/ou GEMINI_API_KEY dans .env")
        return

    col_btn, col_info = st.columns([3, 7])
    with col_btn:
        generate = st.button("Generer le War Room", key="wr_" + symbol, type="primary", use_container_width=True)
    with col_info:
        p = []
        if has_groq:   p.append("Groq " + GROQ_MODEL)
        if has_gemini: p.append("Gemini")
        st.caption("IA : " + " + ".join(p))

    cache_key = "wrc_" + symbol
    if cache_key not in st.session_state:
        st.session_state[cache_key] = None

    if not generate and st.session_state[cache_key]:
        _show(st.session_state[cache_key])
        return
    if not generate:
        st.info("Cliquez sur 'Generer le War Room' pour l'analyse IA complete.")
        return

    score     = pair_data.get("best_score", 0)
    grade     = pair_data.get("grade", "F")
    verdict   = pair_data.get("verdict", "NO_TRADE")
    direction = pair_data.get("direction", "NEUTRAL")
    htf_bias  = pair_data.get("htf_bias", "NEUTRAL")
    pd_zone   = str(pair_data.get("pd_zone", "UNKNOWN"))
    session   = str(pair_data.get("session", "UNKNOWN"))
    in_kz     = "OUI" if pair_data.get("in_killzone") else "NON"
    rr        = pair_data.get("rr", 0.0)
    entry     = str(pair_data.get("entry") or "N/A")
    sl_val    = str(pair_data.get("sl") or "N/A")
    tp_val    = str(pair_data.get("tp") or "N/A")
    conf_text = ", ".join(
        c.get("name", str(c)) if isinstance(c, dict) else str(c)
        for c in pair_data.get("confluences", [])
    ) or "Aucune"
    ks_text = ", ".join(
        k.get("id", str(k)) if isinstance(k, dict) else str(k)
        for k in pair_data.get("_killswitches", [])
    ) or "Aucun"

    prompt_war = WAR_ROOM_TEMPLATE.format(
        symbol=symbol, score=score, grade=grade, verdict=verdict,
        direction=direction, htf_bias=htf_bias, pd_zone=pd_zone,
        session=session, in_killzone=in_kz, rr=rr,
        pyramid=_pyramid(pair_data.get("tf_scores", {})),
        entry=entry, sl=sl_val, tp=tp_val,
        confluences=conf_text, killswitches=ks_text,
    )
    prompt_groq = (
        "Signal KB5 - " + symbol + " Score:" + str(score) + "/100"
        + " Direction:" + direction + " Verdict:" + verdict
        + " RR:" + str(rr) + "x KZ:" + in_kz
        + " Confluences:" + conf_text
    )

    groq_result = gemini_result = None
    if has_groq:
        with st.spinner("Groq - validation rapide..."):
            raw = _call_groq(prompt_groq, SYSTEM_GROQ)
            groq_result = _parse_groq(raw) if raw else None
    if has_gemini:
        with st.spinner("Gemini - redaction du War Room..."):
            gemini_result = _call_gemini(prompt_war, SYSTEM_GEMINI)

    result = {
        "symbol": symbol, "score": score, "grade": grade,
        "verdict": verdict, "groq": groq_result, "gemini": gemini_result,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    st.session_state[cache_key] = result
    _show(result)


def _show(result):
    symbol    = result.get("symbol", "")
    score     = result.get("score", 0)
    grade     = result.get("grade", "F")
    verdict   = result.get("verdict", "NO_TRADE")
    groq      = result.get("groq")
    gemini    = result.get("gemini", "")
    timestamp = result.get("timestamp", "")

    VC = {"EXECUTE": "#00ff88", "WATCH": "#f0b429", "NO_TRADE": "#ef5350", "BLOCKED": "#848e9c"}
    sc = VC.get(verdict, "#848e9c")

    st.html(
        "<div style='background:rgba(20,24,35,0.9);border:1px solid rgba(41,98,255,0.3);"
        "border-radius:12px;padding:14px 20px;margin-bottom:16px;display:flex;"
        "align-items:center;gap:24px;flex-wrap:wrap;'>"
        "<div><div style='font-size:0.7rem;color:#848e9c;'>SYMBOLE</div>"
        "<div style='font-size:1.1rem;font-weight:800;color:#4dabff;'>" + symbol + "</div></div>"
        "<div><div style='font-size:0.7rem;color:#848e9c;'>SCORE</div>"
        "<div style='font-size:1.1rem;font-weight:800;color:" + sc + ";'>" + str(score) + "/100 " + grade + "</div></div>"
        "<div><div style='font-size:0.7rem;color:#848e9c;'>VERDICT</div>"
        "<div style='font-size:1.1rem;font-weight:800;color:" + sc + ";'>" + verdict + "</div></div>"
        "<div style='margin-left:auto;font-size:0.75rem;color:#848e9c;'>" + timestamp + "</div>"
        "</div>"
    )

    if groq:
        gv = groq.get("verdict", "WATCH")
        gc = groq.get("confidence", "LOW")
        gr = groq.get("reason", "")
        gk = groq.get("risk_alert", "")
        gvc = VC.get(gv, "#848e9c")
        cc  = {"HIGH": "#00ff88", "MEDIUM": "#f0b429", "LOW": "#ef5350"}.get(gc, "#848e9c")
        risk_html = "<div style='color:#f0b429;font-size:0.82rem;margin-top:6px;'>" + str(gk) + "</div>" if gk else ""
        st.html(
            "<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);"
            "border-radius:10px;padding:14px 18px;margin-bottom:12px;'>"
            "<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>"
            "<span style='color:#848e9c;font-size:0.75rem;font-weight:600;text-transform:uppercase;'>Groq Validation</span>"
            "<span style='background:" + gvc + "22;border:1px solid " + gvc + ";color:" + gvc + ";"
            "border-radius:6px;padding:2px 10px;font-size:0.8rem;font-weight:700;'>" + gv + "</span>"
            "<span style='background:" + cc + "22;border:1px solid " + cc + ";color:" + cc + ";"
            "border-radius:6px;padding:2px 8px;font-size:0.75rem;'>Conf : " + gc + "</span>"
            "</div>"
            "<div style='color:#d1d4dc;font-size:0.9rem;'>" + str(gr) + "</div>"
            + risk_html + "</div>"
        )

    if gemini:
        st.markdown("**Gemini - War Room Report**")
        st.markdown(gemini)
    elif not groq:
        st.error("Aucune reponse IA - verifiez vos cles API dans .env")
