"""
bridge.py — Pont entre le DataStore d'App2 et l'interface Streamlit
====================================================================
Ce fichier lit les données du cerveau KB5 (App2) et les traduit
dans le format attendu par l'interface Streamlit (App1).

Il ne modifie RIEN dans App2. Il lit seulement.
Appelé par main.py Streamlit à chaque refresh.

Données exposées :
  - Scores et verdicts par paire et timeframe
  - Biais HTF (BULLISH / BEARISH / NEUTRAL)
  - Positions actives (entry, SL, TP, PnL)
  - Circuit Breaker (niveau CB0→CB3)
  - KillSwitches actifs
  - Équité du compte
  - Statut global du bot
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Couleurs Circuit Breaker pour l'interface ────────────────
CB_COLORS = {
    0: "#00ff88",   # Vert  — CB0 NOMINAL
    1: "#f0b429",   # Jaune — CB1 WARNING
    2: "#ef5350",   # Rouge — CB2 PAUSE
    3: "#b71c1c",   # Rouge foncé — CB3 HALT
}

CB_LABELS = {
    0: "✅ NOMINAL — Trading autorisé",
    1: "⚠️ WARNING — Taille réduite 50%",
    2: "🚫 PAUSE — Plus de nouveaux trades",
    3: "🛑 HALT — Fermeture forcée",
}

# ── Mapping verdict → couleur interface ─────────────────────
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


class DashboardBridge:
    """
    Pont principal entre App2 et l'interface Streamlit.

    Usage dans main.py Streamlit :
        from bridge.bridge import DashboardBridge
        bridge = DashboardBridge(data_store, scoring_engine, supervisor)
        data = bridge.get_dashboard_data()
    """

    def __init__(self,
                 data_store=None,
                 scoring_engine=None,
                 supervisor=None):
        self._ds      = data_store
        self._scoring = scoring_engine
        self._sup     = supervisor

    # ══════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE — appelée par Streamlit
    # ══════════════════════════════════════════════════════

    def get_dashboard_data(self) -> dict:
        """
        Retourne toutes les données nécessaires au dashboard Streamlit.
        Un seul appel suffit pour rendre toute l'interface.

        Returns:
            dict complet avec toutes les sections du dashboard
        """
        return {
            "bot_status":    self._get_bot_status(),
            "pairs":         self._get_pairs_data(),
            "scores_summary": self._get_scores_summary(),
            "positions":     self._get_positions(),
            "circuit_breaker": self._get_circuit_breaker(),
            "killswitches":  self._get_killswitches(),
            "equity":        self._get_equity(),
            "timestamp":     datetime.now(timezone.utc).isoformat(),
        }

    # ══════════════════════════════════════════════════════
    # STATUT GLOBAL DU BOT
    # ══════════════════════════════════════════════════════

    def _get_bot_status(self) -> dict:
        """
        Retourne le statut global du Supervisor.
        Compatible avec le format attendu par bot_monitor.py d'App1.
        """
        try:
            if self._sup is not None:
                snap = self._sup.get_snapshot()
                return {
                    "bot_is_running":  snap.get("running", False),
                    "is_paused":       snap.get("paused", False),
                    "last_heartbeat":  snap.get("timestamp", "---"),
                    "session":         snap.get("session", "OFF_SESSION"),
                    "active_pairs":    snap.get("pairs", []),
                    "cycles":          snap.get("cycles", 0),
                    "execute_count":   snap.get("execute", 0),
                    "error_count":     snap.get("errors", 0),
                    "cb_level":        snap.get("cb_level", 0),
                    "cb_name":         snap.get("cb_name", "NOMINAL"),
                    "equity":          snap.get("equity", 0.0),
                }
        except Exception as e:
            logger.debug(f"Bridge — get_bot_status erreur : {e}")

        # Fallback si supervisor non disponible
        return {
            "bot_is_running": False,
            "last_heartbeat": "---",
            "session":        "INCONNU",
            "active_pairs":   [],
        }

    # ══════════════════════════════════════════════════════
    # DONNÉES PAR PAIRE
    # ══════════════════════════════════════════════════════

    def _get_pairs_data(self) -> dict:
        """
        Retourne les données complètes de toutes les paires analysées.
        Format compatible avec le render_analysis_for_symbol() d'App1.
        """
        result = {}

        try:
            if self._ds is None:
                return result

            pairs = self._ds.get_all_pairs()

            for pair in pairs:
                pair_data = self._get_single_pair_data(pair)
                if pair_data:
                    result[pair] = pair_data

        except Exception as e:
            logger.error(f"Bridge — get_pairs_data erreur : {e}")

        return result

    def _get_single_pair_data(self, pair: str) -> Optional[dict]:
        """Données complètes d'une seule paire."""
        try:
            # Biais HTF depuis D1
            htf_bias = self._ds.get_daily_bias(pair) if self._ds else "NEUTRAL"

            # Scores par timeframe
            timeframes = ["MN", "W1", "D1", "H4", "H1", "M15", "M5"]
            tf_scores = {}
            best_score = 0
            best_tf = "H1"

            for tf in timeframes:
                score   = self._ds.get_latest_score(pair, tf) if self._ds else 0
                verdict = self._ds.get_latest_verdict(pair, tf) if self._ds else "NO_TRADE"
                analysis = self._ds.get_analysis(pair, tf) if self._ds else {}

                tf_scores[tf] = {
                    "score":     score,
                    "verdict":   verdict,
                    "direction": analysis.get("direction", "NEUTRAL"),
                    "grade":     analysis.get("grade", "C"),
                    "rr":        analysis.get("rr", 0.0),
                    "entry":     analysis.get("entry"),
                    "sl":        analysis.get("sl"),
                    "tp":        analysis.get("tp"),
                    "confluences": analysis.get("confluences", []),
                    "kb5_result":  analysis.get("kb5_result", {}),
                    "color":     VERDICT_COLORS.get(verdict, "#848e9c"),
                    "label":     VERDICT_LABELS.get(verdict, verdict),
                }

                if score > best_score:
                    best_score = score
                    best_tf    = tf

            # Scoring global depuis ScoringEngine
            scoring_snap = {}
            if self._scoring is not None:
                try:
                    scoring_snap = self._scoring.get_snapshot(pair)
                except Exception:
                    pass

            return {
                "pair":       pair,
                "htf_bias":   htf_bias,
                "bias_color": "#00ff88" if "BULL" in htf_bias else (
                              "#ef5350" if "BEAR" in htf_bias else "#848e9c"),
                "tf_scores":  tf_scores,
                "best_score": best_score,
                "best_tf":    best_tf,
                "verdict":    scoring_snap.get("verdict", "NO_TRADE"),
                "direction":  scoring_snap.get("direction", "NEUTRAL"),
                "grade":      scoring_snap.get("grade", "C"),
                "rr":         scoring_snap.get("rr", 0.0),
                "entry":      scoring_snap.get("entry"),
                "sl":         scoring_snap.get("sl"),
                "tp":         scoring_snap.get("tp"),
                "in_killzone": scoring_snap.get("in_killzone", False),
                "aligned":    scoring_snap.get("aligned", False),
            }

        except Exception as e:
            logger.debug(f"Bridge — {pair} erreur : {e}")
            return None

    # ══════════════════════════════════════════════════════
    # RÉSUMÉ SCORES (sidebar App1)
    # ══════════════════════════════════════════════════════

    def _get_scores_summary(self) -> dict:
        """
        Résumé compact des scores pour la sidebar Streamlit.
        Format : {pair: score} — identique à scores_summary d'App1.
        """
        summary = {}
        try:
            if self._scoring is not None:
                verdicts = self._scoring.get_all_verdicts()
                for pair, data in verdicts.items():
                    summary[pair] = data.get("score", 0)
            elif self._ds is not None:
                for pair in self._ds.get_all_pairs():
                    # Meilleur score parmi tous les TF
                    best = 0
                    for tf in ["H4", "H1", "M15"]:
                        s = self._ds.get_latest_score(pair, tf)
                        if s > best:
                            best = s
                    summary[pair] = best
        except Exception as e:
            logger.debug(f"Bridge — scores_summary erreur : {e}")

        return summary

    # ══════════════════════════════════════════════════════
    # POSITIONS ACTIVES
    # ══════════════════════════════════════════════════════

    def _get_positions(self) -> list:
        """
        Retourne les positions actives depuis le DataStore.
        Format compatible avec le bandeau trades d'App1.
        """
        try:
            if self._ds is not None:
                raw = self._ds.get_positions_cache()
                positions = []
                for pos in raw:
                    # Normaliser le format pour Streamlit
                    positions.append({
                        "symbol":        pos.get("symbol", ""),
                        "direction":     pos.get("direction", ""),
                        "entry":         pos.get("entry", 0.0),
                        "current_price": pos.get("current_price", 0.0),
                        "sl":            pos.get("sl", 0.0),
                        "tp":            pos.get("tp", 0.0),
                        "lot_size":      pos.get("lot_size", 0.01),
                        "pnl":           pos.get("profit", 0.0),
                        "ticket":        pos.get("ticket", 0),
                        "volume":        pos.get("volume", 0.01),
                    })
                return positions
        except Exception as e:
            logger.debug(f"Bridge — positions erreur : {e}")

        return []

    # ══════════════════════════════════════════════════════
    # CIRCUIT BREAKER
    # ══════════════════════════════════════════════════════

    def _get_circuit_breaker(self) -> dict:
        """
        État du Circuit Breaker avec couleurs et labels pour l'interface.
        """
        try:
            if self._ds is not None:
                cb = self._ds.get_cb_state()
                level = cb.get("level", 0)
                return {
                    "level":      level,
                    "status":     cb.get("status", "CB_CLEAR"),
                    "pct_drop":   cb.get("pct_drop", 0.0),
                    "is_blocking": self._ds.is_cb_blocking(),
                    "color":      CB_COLORS.get(level, "#848e9c"),
                    "label":      CB_LABELS.get(level, "Inconnu"),
                }
        except Exception as e:
            logger.debug(f"Bridge — circuit_breaker erreur : {e}")

        return {
            "level": 0,
            "status": "CB_CLEAR",
            "pct_drop": 0.0,
            "is_blocking": False,
            "color": "#00ff88",
            "label": CB_LABELS[0],
        }

    # ══════════════════════════════════════════════════════
    # KILLSWITCHES
    # ══════════════════════════════════════════════════════

    def _get_killswitches(self) -> list:
        """
        Liste des KillSwitches actifs avec leurs raisons.
        Affiché dans le dashboard monitoring d'App1.
        """
        try:
            if self._ds is not None:
                return self._ds.get_active_ks_list()
        except Exception as e:
            logger.debug(f"Bridge — killswitches erreur : {e}")

        return []

    # ══════════════════════════════════════════════════════
    # ÉQUITÉ
    # ══════════════════════════════════════════════════════

    def _get_equity(self) -> float:
        """Équité actuelle du compte depuis le DataStore."""
        try:
            if self._ds is not None:
                return self._ds.get_equity()
        except Exception as e:
            logger.debug(f"Bridge — equity erreur : {e}")

        return 0.0

    # ══════════════════════════════════════════════════════
    # UTILITAIRES
    # ══════════════════════════════════════════════════════

    def is_ready(self) -> bool:
        """True si le bridge a accès au DataStore."""
        return self._ds is not None

    def get_active_pairs(self) -> list:
        """Liste des paires avec au moins une analyse disponible."""
        try:
            if self._ds is not None:
                return self._ds.get_all_pairs()
        except Exception:
            pass
        return []

    def get_pair_score(self, pair: str, tf: str = "H1") -> int:
        """Raccourci — score d'une paire sur un TF donné."""
        try:
            if self._ds is not None:
                return int(self._ds.get_latest_score(pair, tf))
        except Exception:
            pass
        return 0

    def get_pair_verdict(self, pair: str) -> str:
        """Raccourci — verdict global d'une paire."""
        try:
            if self._scoring is not None:
                return self._scoring.get_verdict(pair)
        except Exception:
            pass
        return "NO_TRADE"


# ══════════════════════════════════════════════════════════
# FONCTION STANDALONE — lecture depuis fichier pickle
# Utilisée quand le bot tourne en processus séparé
# (même logique que market_state_cache.pkl d'App1)
# ══════════════════════════════════════════════════════════

def get_dashboard_data_from_cache(cache_file: str = "market_state.pkl") -> dict:
    """
    Lit les données depuis le fichier cache pickle d'App2.
    Utilisé par Streamlit quand il tourne séparément du bot.

    Args:
        cache_file: chemin vers market_state.pkl d'App2

    Returns:
        dict avec toutes les données du dashboard
    """
    import pickle
    import os

    if not os.path.exists(cache_file):
        return {
            "bot_status":      {"bot_is_running": False, "last_heartbeat": "---"},
            "pairs":           {},
            "scores_summary":  {},
            "positions":       [],
            "circuit_breaker": {"level": 0, "color": "#00ff88", "label": CB_LABELS[0]},
            "killswitches":    [],
            "equity":          0.0,
            "timestamp":       datetime.now(timezone.utc).isoformat(),
            "source":          "cache_vide",
        }

    try:
        with open(cache_file, "rb") as f:
            raw = pickle.load(f)

        # Normaliser les positions
        positions_raw = raw.get("open_positions", [])
        positions = []
        for pos in positions_raw:
            positions.append({
                "symbol":        pos.get("symbol", ""),
                "direction":     "BUY" if pos.get("type") == 0 else "SELL",
                "entry":         pos.get("price_open", 0.0),
                "current_price": pos.get("price_current", 0.0),
                "sl":            pos.get("sl", 0.0),
                "tp":            pos.get("tp", 0.0),
                "volume":        pos.get("volume", 0.01),
                "pnl":           pos.get("profit", 0.0),
                "ticket":        pos.get("ticket", 0),
            })

        # Reconstruire scores_summary depuis les paires
        scores_summary = {}
        pairs_data = {}
        for key, value in raw.items():
            if isinstance(value, dict) and "scoring_output" in value:
                pair = key
                scoring = value.get("scoring_output", {})
                scores_summary[pair] = scoring.get("score", 0)
                pairs_data[pair] = {
                    "pair":      pair,
                    "htf_bias":  value.get("bias_result", {}).get("direction", "NEUTRAL"),
                    "verdict":   scoring.get("verdict", "NO_TRADE"),
                    "score":     scoring.get("score", 0),
                    "grade":     scoring.get("grade", "C"),
                    "direction": scoring.get("direction", "NEUTRAL"),
                    "rr":        scoring.get("rr", 0.0),
                }

        return {
            "bot_status": {
                "bot_is_running": raw.get("bot_status") == "Actif",
                "last_heartbeat": raw.get("last_global_update", "---"),
            },
            "pairs":           pairs_data,
            "scores_summary":  scores_summary,
            "positions":       positions,
            "circuit_breaker": {"level": 0, "color": "#00ff88", "label": CB_LABELS[0]},
            "killswitches":    [],
            "equity":          raw.get("equity", 0.0),
            "timestamp":       datetime.now(timezone.utc).isoformat(),
            "source":          "pickle_cache",
        }

    except Exception as e:
        logger.error(f"Bridge — erreur lecture cache : {e}")
        return {
            "bot_status":      {"bot_is_running": False, "last_heartbeat": "Erreur lecture"},
            "pairs":           {},
            "scores_summary":  {},
            "positions":       [],
            "circuit_breaker": {"level": 0, "color": "#00ff88", "label": CB_LABELS[0]},
            "killswitches":    [],
            "equity":          0.0,
            "timestamp":       datetime.now(timezone.utc).isoformat(),
            "source":          "erreur",
        }
