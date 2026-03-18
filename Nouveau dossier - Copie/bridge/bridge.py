"""
bridge/bridge.py — Pont DataStore → Interface Streamlit
========================================================
VERSION CORRIGÉE — lit exactement le format réel du market_state.pkl

Format réel du pkl (vérifié en production) :
  data[pair] = {
      "candles":        list[dict]          # 200 bougies H1
      "kb5_result":     dict                # pyramid_scores, entry_model, confluences
      "scoring_output": dict                # score global, verdict, grade, direction
      "bias_result":    dict                # biais HTF détaillé
      "last_update":    str
  }
  data["bot_status"]        = "Actif" | "Arrêté"
  data["equity"]            = float
  data["last_global_update"] = str ISO
  data["open_positions"]    = list[dict]
"""

import os
import pickle
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Couleurs Circuit Breaker ─────────────────────────────────
CB_COLORS = {
    0: "#00ff88",
    1: "#f0b429",
    2: "#ef5350",
    3: "#b71c1c",
}

CB_LABELS = {
    0: "✅ NOMINAL — Trading autorisé",
    1: "⚠️ WARNING — Taille réduite 50%",
    2: "🚫 PAUSE — Plus de nouveaux trades",
    3: "🛑 HALT — Fermeture forcée",
}

VERDICT_COLORS = {
    "EXECUTE":  "#00ff88",
    "WATCH":    "#f0b429",
    "NO_TRADE": "#ef5350",
    "BLOCKED":  "#848e9c",
}

VERDICT_LABELS = {
    "EXECUTE":  "🚀 EXÉCUTION",
    "WATCH":    "👁 SURVEILLER",
    "NO_TRADE": "⛔ NO TRADE",
    "BLOCKED":  "🔒 BLOQUÉ",
}

# Ordre de la pyramide KB5
PYRAMID_ORDER = ["MN", "W1", "D1", "H4", "H1", "M15", "M5"]

# Poids pyramide (pour affichage visuel)
PYRAMID_WEIGHTS = {
    "MN":  0.30,
    "W1":  0.20,
    "D1":  0.20,
    "H4":  0.12,
    "H1":  0.08,
    "M15": 0.05,
    "M5":  0.05,
}


def _safe_float(val, default=0.0) -> float:
    """Convertit une valeur en float sans planter."""
    try:
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val, default=0) -> int:
    """Convertit une valeur en int sans planter."""
    try:
        if val is None:
            return default
        return int(float(val))
    except (TypeError, ValueError):
        return default


def _extract_bias_direction(bias_result: dict) -> str:
    """
    Extrait la direction HTF depuis bias_result.
    Priorité : alignment > daily_bias > sod_bias
    """
    if not bias_result:
        return "NEUTRAL"
    
    # 1. Alignment global (le plus fiable)
    alignment = bias_result.get("alignment", {})
    if isinstance(alignment, dict):
        direction = alignment.get("direction", "NEUTRAL")
        if direction and direction != "NEUTRAL":
            return direction
    
    # 2. Daily bias
    daily = bias_result.get("daily_bias", {})
    if isinstance(daily, dict):
        direction = daily.get("direction", "NEUTRAL")
        if direction and direction != "NEUTRAL":
            return direction
    
    # 3. SOD bias
    sod = bias_result.get("sod_bias", {})
    if isinstance(sod, dict):
        direction = sod.get("direction", "NEUTRAL")
        if direction and direction != "NEUTRAL":
            return direction
    
    return "NEUTRAL"


def _build_tf_scores_from_kb5(kb5_result: dict, scoring_output: dict) -> dict:
    """
    Construit les scores par TF depuis kb5_result.pyramid_scores.
    
    kb5_result contient :
      pyramid_scores: {"MN": 8, "W1": 0, "D1": 8, "H4": 15, "H1": 15, "M15": 0}
      tf_details: {"MN": {...}, "W1": {...}, ...}
      direction: "BULLISH"
    """
    tf_scores = {}
    
    if not kb5_result:
        # Fallback : tout à 0
        for tf in PYRAMID_ORDER:
            tf_scores[tf] = {
                "score":   0,
                "verdict": "NO_TRADE",
                "direction": "NEUTRAL",
                "grade": "F",
                "rr": 0.0,
                "entry": None,
                "sl": None,
                "tp": None,
                "confluences": [],
                "color": VERDICT_COLORS["NO_TRADE"],
                "label": VERDICT_LABELS["NO_TRADE"],
            }
        return tf_scores
    
    pyramid_scores = kb5_result.get("pyramid_scores", {})
    tf_details     = kb5_result.get("tf_details", {})
    direction      = kb5_result.get("direction", "NEUTRAL")
    entry_model    = kb5_result.get("entry_model", {})
    
    # Score global du scoring_engine (pour les TF exécutables)
    global_score   = _safe_int(scoring_output.get("score", 0))
    global_verdict = scoring_output.get("verdict", "NO_TRADE")
    
    for tf in PYRAMID_ORDER:
        raw_score = _safe_int(pyramid_scores.get(tf, 0))
        
        # Déterminer le verdict par TF selon le score
        if raw_score >= 80:
            verdict = "EXECUTE"
        elif raw_score >= 50:
            verdict = "WATCH"
        elif raw_score > 0:
            verdict = "NO_TRADE"
        else:
            verdict = "NO_TRADE"
        
        # Sur H1 et M15 : utiliser le verdict global du scoring_engine
        if tf in ("H1", "M15") and global_verdict in ("EXECUTE", "WATCH", "BLOCKED"):
            verdict = global_verdict
        
        # Récupérer les détails TF si disponibles
        tf_detail = tf_details.get(tf, {}) if tf_details else {}
        
        # Entry/SL/TP depuis entry_model (disponibles sur tous TF)
        entry = _safe_float(entry_model.get("entry")) or None
        sl    = _safe_float(entry_model.get("sl")) or None
        tp    = _safe_float(entry_model.get("tp")) or None
        rr    = _safe_float(entry_model.get("rr", 0.0))
        
        # Grade selon score
        if raw_score >= 90:
            grade = "A+"
        elif raw_score >= 80:
            grade = "A"
        elif raw_score >= 70:
            grade = "B+"
        elif raw_score >= 60:
            grade = "B"
        elif raw_score >= 50:
            grade = "C"
        else:
            grade = "F"
        
        tf_scores[tf] = {
            "score":      raw_score,
            "verdict":    verdict,
            "direction":  direction,
            "grade":      grade,
            "rr":         rr,
            "entry":      entry if entry and entry > 0 else None,
            "sl":         sl    if sl    and sl > 0    else None,
            "tp":         tp    if tp    and tp > 0    else None,
            "confluences": tf_detail.get("confluences", []),
            "color":      VERDICT_COLORS.get(verdict, "#848e9c"),
            "label":      VERDICT_LABELS.get(verdict, verdict),
            "weight":     PYRAMID_WEIGHTS.get(tf, 0.05),
        }
    
    return tf_scores


def _parse_pair_from_pkl(pair: str, pair_data: dict) -> dict:
    """
    Parse les données d'une paire depuis le pkl vers le format dashboard.
    
    Entrée (format pkl réel) :
      pair_data = {
          "candles":        list[dict],
          "kb5_result":     dict,
          "scoring_output": dict,
          "bias_result":    dict,
          "last_update":    str,
      }
    
    Sortie (format attendu par main_streamlit.py + bot_monitor.py)
    """
    scoring_output = pair_data.get("scoring_output", {})
    kb5_result     = pair_data.get("kb5_result", {})
    bias_result    = pair_data.get("bias_result", {})
    
    # ── Score et verdict global ───────────────────────────────
    score   = _safe_int(scoring_output.get("score", 0))
    verdict = scoring_output.get("verdict", "NO_TRADE")
    grade   = scoring_output.get("grade", "F")
    reason  = scoring_output.get("reason", [])
    if isinstance(reason, str):
        reason = [reason]
    
    # ── Direction ─────────────────────────────────────────────
    # Priorité : kb5_result > scoring_output
    direction = kb5_result.get("direction") or scoring_output.get("direction", "NEUTRAL")
    
    # ── Biais HTF ─────────────────────────────────────────────
    htf_bias = _extract_bias_direction(bias_result)
    bias_color = (
        "#00ff88" if "BULL" in htf_bias else
        "#ef5350" if "BEAR" in htf_bias else
        "#848e9c"
    )
    
    # ── Alignement ────────────────────────────────────────────
    alignment = bias_result.get("alignment", {})
    aligned   = alignment.get("aligned", False) if isinstance(alignment, dict) else False
    
    # ── Zone Premium/Discount ─────────────────────────────────
    pd_zone = (
        kb5_result.get("pd_zone") or
        bias_result.get("pd_zone", {}).get("zone", "UNKNOWN")
    )
    
    # ── Entry Model ───────────────────────────────────────────
    entry_model = kb5_result.get("entry_model", {})
    entry = _safe_float(entry_model.get("entry")) or None
    sl    = _safe_float(entry_model.get("sl"))    or None
    tp    = _safe_float(entry_model.get("tp"))    or None
    rr    = _safe_float(entry_model.get("rr", 0.0))
    
    if entry and entry <= 0:
        entry = None
    if sl and sl <= 0:
        sl = None
    if tp and tp <= 0:
        tp = None
    
    # ── Scores par TF (pyramide) ──────────────────────────────
    tf_scores  = _build_tf_scores_from_kb5(kb5_result, scoring_output)
    best_score = score  # Le score global est déjà le meilleur agrégé
    best_tf    = "H1"
    
    # Trouver le TF avec le meilleur score individuel
    if kb5_result:
        pyramid = kb5_result.get("pyramid_scores", {})
        if pyramid:
            best_tf = max(pyramid, key=lambda t: pyramid.get(t, 0), default="H1")
    
    # ── Confluences ───────────────────────────────────────────
    confluences = kb5_result.get("confluences", [])
    
    # ── Structures actives ────────────────────────────────────
    structures  = kb5_result.get("structures", [])
    irl_targets = kb5_result.get("irl_targets", [])
    
    # ── Session / Killzone ────────────────────────────────────
    session     = kb5_result.get("session") or bias_result.get("session", "INCONNU")
    in_killzone = kb5_result.get("in_killzone", False)
    
    # ── Grade global ─────────────────────────────────────────
    # Récupérer depuis scoring_output d'abord, sinon calculer
    if not grade or grade == "F":
        if score >= 90:
            grade = "A+"
        elif score >= 80:
            grade = "A"
        elif score >= 70:
            grade = "B+"
        elif score >= 60:
            grade = "B"
        elif score >= 50:
            grade = "C"
        else:
            grade = "F"
    
    return {
        # Identifiants
        "pair":         pair,
        
        # Score global
        "best_score":   score,
        "grade":        grade,
        "verdict":      verdict,
        "direction":    direction,
        "reason":       reason,
        
        # Biais HTF
        "htf_bias":     htf_bias,
        "bias_color":   bias_color,
        "aligned":      aligned,
        "pd_zone":      pd_zone,
        "session":      session,
        "in_killzone":  in_killzone,
        
        # Entry Model
        "entry":        entry,
        "sl":           sl,
        "tp":           tp,
        "rr":           rr,
        
        # Pyramide KB5 par TF
        "tf_scores":    tf_scores,
        "best_tf":      best_tf,
        
        # Confluences et structures
        "confluences":  confluences,
        "structures":   structures,
        "irl_targets":  irl_targets,
        
        # Bougies pour graphique
        "candles":      pair_data.get("candles", []),
        
        # Meta
        "last_update":  pair_data.get("last_update", "---"),
        "kb5_score":    _safe_int(kb5_result.get("final_score", 0)),
        "bias_score":   _safe_int(kb5_result.get("bias_score", 0)),
    }


def get_dashboard_data_from_cache(cache_file: str = "market_state.pkl") -> dict:
    """
    Lit le market_state.pkl produit par App2 (KB5) et retourne
    toutes les données nécessaires au dashboard Streamlit.

    Format de sortie attendu par main_streamlit.py :
      {
        "bot_status":      dict   → bot_is_running, last_heartbeat, equity
        "pairs":           dict   → {symbol: pair_data}
        "scores_summary":  dict   → {symbol: score}
        "positions":       list   → positions MT5 actives
        "circuit_breaker": dict   → level, color, label
        "killswitches":    list   → KS actifs
        "equity":          float
        "timestamp":       str
      }
    """
    # ── Fichier absent ────────────────────────────────────────
    if not os.path.exists(cache_file):
        return _empty_dashboard("cache introuvable")

    # ── Lecture pickle ────────────────────────────────────────
    try:
        with open(cache_file, "rb") as f:
            raw = pickle.load(f)
    except Exception as e:
        logger.error(f"Bridge — erreur lecture pkl : {e}")
        return _empty_dashboard(f"erreur lecture : {e}")

    if not isinstance(raw, dict):
        return _empty_dashboard("format pkl invalide")

    # ── Extraction paires ─────────────────────────────────────
    pairs_data     = {}
    scores_summary = {}
    
    # Les clés qui NE sont PAS des paires
    META_KEYS = {"bot_status", "equity", "last_global_update",
                 "open_positions", "cb_state", "ks_state", "session"}
    
    for key, value in raw.items():
        if key in META_KEYS:
            continue
        if not isinstance(value, dict):
            continue
        # Une paire valide contient scoring_output ou kb5_result ou candles
        if not any(k in value for k in ("scoring_output", "kb5_result", "candles", "bias_result")):
            continue
        
        try:
            parsed = _parse_pair_from_pkl(key, value)
            pairs_data[key]     = parsed
            scores_summary[key] = parsed["best_score"]
        except Exception as e:
            logger.error(f"Bridge — erreur parsing paire {key} : {e}")
            continue

    # ── Positions actives ─────────────────────────────────────
    positions_raw = raw.get("open_positions", [])
    positions = []
    for pos in (positions_raw or []):
        if not isinstance(pos, dict):
            continue
        positions.append({
            "symbol":        pos.get("symbol", ""),
            "direction":     "BUY" if pos.get("type") == 0 else "SELL",
            "entry":         _safe_float(pos.get("price_open")),
            "current_price": _safe_float(pos.get("price_current")),
            "sl":            _safe_float(pos.get("sl")),
            "tp":            _safe_float(pos.get("tp")),
            "volume":        _safe_float(pos.get("volume"), 0.01),
            "pnl":           _safe_float(pos.get("profit")),
            "ticket":        pos.get("ticket", 0),
        })

    # ── Equity ────────────────────────────────────────────────
    equity = _safe_float(raw.get("equity", 0.0))

    # ── Statut bot ────────────────────────────────────────────
    raw_status   = raw.get("bot_status", "")
    bot_running  = isinstance(raw_status, str) and "actif" in raw_status.lower()
    last_update  = raw.get("last_global_update", "---")
    
    # Formater l'heure pour l'affichage
    if last_update and last_update != "---":
        try:
            dt = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
            last_hb = dt.strftime("%H:%M:%S")
        except Exception:
            last_hb = str(last_update)[:19]
    else:
        last_hb = "---"

    # ── Circuit Breaker ───────────────────────────────────────
    cb_state = raw.get("cb_state", {})
    if isinstance(cb_state, dict):
        cb_level = _safe_int(cb_state.get("level", 0))
    else:
        cb_level = 0

    circuit_breaker = {
        "level":       cb_level,
        "status":      cb_state.get("status", "CB_CLEAR") if isinstance(cb_state, dict) else "CB_CLEAR",
        "pct_drop":    _safe_float(cb_state.get("pct_drop", 0.0)) if isinstance(cb_state, dict) else 0.0,
        "is_blocking": cb_level > 0,
        "color":       CB_COLORS.get(cb_level, "#848e9c"),
        "label":       CB_LABELS.get(cb_level, "Inconnu"),
    }

    # ── KillSwitches actifs ───────────────────────────────────
    ks_state = raw.get("ks_state", {})
    killswitches = []
    if isinstance(ks_state, dict):
        for ks_id, ks_data in ks_state.items():
            if isinstance(ks_data, dict) and ks_data.get("active", False):
                killswitches.append({
                    "id":     ks_id,
                    "reason": ks_data.get("reason", ""),
                    "since":  ks_data.get("since", ""),
                })

    return {
        "bot_status": {
            "bot_is_running": bot_running,
            "last_heartbeat": last_hb,
            "raw_status":     raw_status,
            "equity":         equity,
        },
        "pairs":           pairs_data,
        "scores_summary":  scores_summary,
        "positions":       positions,
        "circuit_breaker": circuit_breaker,
        "killswitches":    killswitches,
        "equity":          equity,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "source":          "pickle_kb5",
        "pairs_count":     len(pairs_data),
    }


def _empty_dashboard(reason: str = "") -> dict:
    """Retourne un dashboard vide avec statut bot arrêté."""
    return {
        "bot_status": {
            "bot_is_running": False,
            "last_heartbeat": "---",
            "raw_status":     "Arrêté",
            "equity":         0.0,
        },
        "pairs":           {},
        "scores_summary":  {},
        "positions":       [],
        "circuit_breaker": {
            "level": 0, "status": "CB_CLEAR",
            "pct_drop": 0.0, "is_blocking": False,
            "color": "#00ff88", "label": CB_LABELS[0],
        },
        "killswitches": [],
        "equity":       0.0,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "source":       f"vide_{reason}",
        "pairs_count":  0,
    }


# ── Classe DashboardBridge (conservée pour compatibilité) ────
class DashboardBridge:
    """
    Pont live entre le DataStore d'App2 et Streamlit.
    Utilisé quand le bot tourne dans le même processus.
    """
    def __init__(self, data_store=None, scoring_engine=None, supervisor=None):
        self._ds      = data_store
        self._scoring = scoring_engine
        self._sup     = supervisor

    def is_ready(self) -> bool:
        return self._ds is not None

    def get_dashboard_data(self) -> dict:
        return get_dashboard_data_from_cache()
