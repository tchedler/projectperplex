"""Analysis Reporter — Génère rapports détaillés par paire et timeframe.

Pour chaque paire analysée :
- Détecte le type (Forex/Crypto/Indices)
- Analyse chaque timeframe indépendamment (MN → M1)
- Génère rapport structuré avec tous les concepts ICT
- Sauvegarde dans data/reports/{pair}/{tf}/
- Produit rapport récapitulatif pour le bot
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone

from analysis.kb5_engine import KB5Engine
from config.constants import PYRAMID_ORDER

class AnalysisReporter:
    """Générateur de rapports d'analyse ICT par paire/timeframe."""

    def __init__(self, kb5_engine: KB5Engine | None = None):
        # Le KB5Engine n'est pas strictement requis pour générer des rapports
        # de type “mock” / summaries. Il peut être injecté si nécessaire.
        self.kb5 = kb5_engine
        self.reports_dir = Path("data/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def detect_asset_type(self, pair: str) -> str:
        """Détecte le type d'actif : Forex, Crypto, Indices."""
        pair_upper = pair.upper()
        if "BTC" in pair_upper or "ETH" in pair_upper or "XRP" in pair_upper:
            return "CRYPTO"
        elif "USTEC" in pair_upper or "US30" in pair_upper or "NAS100" in pair_upper:
            return "INDICES"
        else:
            return "FOREX"

    def analyze_pair(self, pair: str) -> Dict[str, Any]:
        """Analyse complète d'une paire : tous timeframes + récap."""

        asset_type = self.detect_asset_type(pair)
        print(f"🔍 Analyse {pair} ({asset_type}) — {len(PYRAMID_ORDER)} timeframes")

        # Créer dossier paire
        pair_dir = self.reports_dir / pair
        pair_dir.mkdir(exist_ok=True)

        # Analyser chaque TF indépendamment
        tf_reports = {}
        for tf in PYRAMID_ORDER:
            print(f"  📊 {tf}...")
            tf_report = self.analyze_timeframe(pair, tf, asset_type)
            tf_reports[tf] = tf_report

            # Sauvegarder rapport TF
            tf_dir = pair_dir / tf
            tf_dir.mkdir(exist_ok=True)
            with open(tf_dir / "analysis_report.json", "w", encoding="utf-8") as f:
                json.dump(tf_report, f, indent=2, ensure_ascii=False)

        # Rapport récapitulatif
        summary = self.generate_summary(pair, asset_type, tf_reports)
        with open(pair_dir / "summary_report.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"✅ Rapports sauvegardés dans {pair_dir}")
        return summary

    def analyze_timeframe(self, pair: str, tf: str, asset_type: str) -> Dict[str, Any]:
        """Analyse un timeframe spécifique."""

        # Si le KB5Engine est disponible, utiliser les vraies données
        if self.kb5:
            # Calculer le score et récupérer les structures
            # Note: analyze() retourne un KB5_RESULT complet
            kb5_result = self.kb5.analyze(pair)
            tf_details = kb5_result.get("tf_details", {}).get(tf, {})
            
            report = {
                "metadata": {
                    "pair": pair,
                    "timeframe": tf,
                    "asset_type": asset_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "ict_applicable": self._is_ict_applicable(asset_type, tf)
                },
                "structures": {
                    "order_blocks": self.kb5._ob.get_all_ob(pair, tf),
                    "fair_value_gaps": self.kb5._fvg.get_all_fvg(pair, tf),
                    "swing_points": self._detect_swings(pair, tf),
                    "liquidity_levels": self.kb5._liq.get_all_levels(pair) if self.kb5._liq else {}
                },
                "narrative": self._generate_narrative(pair, tf, asset_type, kb5_result),
                "score": {
                    "total": tf_details.get("score", 0),
                    "components": tf_details.get("components", {}),
                    "grade": self._get_grade(tf_details.get("score", 0)),
                    "verdict": kb5_result.get("direction", "NEUTRAL")
                },
                "recommendations": kb5_result.get("entry_model", {})
            }
        else:
            # Fallback mock si engine absent (ne devrait pas arriver en prod)
            report = {
                "metadata": {
                    "pair": pair,
                    "timeframe": tf,
                    "asset_type": asset_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "ict_applicable": self._is_ict_applicable(asset_type, tf)
                },
                "structures": {
                    "order_blocks": [],
                    "fair_value_gaps": [],
                    "swing_points": {},
                    "liquidity_levels": {}
                },
                "narrative": "KB5Engine not initialized.",
                "score": {"total": 0, "verdict": "NEUTRAL"},
                "recommendations": []
            }

        return report

    def _get_grade(self, score: float) -> str:
        if score >= 85: return "A+"
        if score >= 75: return "A"
        if score >= 65: return "B"
        if score >= 50: return "C"
        return "D"

    def _is_ict_applicable(self, asset_type: str, tf: str) -> bool:
        """Certains concepts ICT ne s'appliquent pas aux cryptos."""
        if asset_type == "CRYPTO":
            # Cryptos ont moins de sessions fixes, mais FVG/OB/Swings oui
            return tf in ["D1", "H4", "H1", "M15", "M5", "M1"]  # Pas MN/W1 pour crypto
        return True

    def _detect_order_blocks(self, pair: str, tf: str) -> List[Dict]:
        """Détection Order Blocks."""
        # Mock pour l'instant
        return [
            {
                "type": "BULLISH_OB",
                "price_range": {"low": 50000, "high": 51000},
                "quality": "HIGH",
                "status": "VALID",
                "confluence_count": 3
            }
        ]

    def _detect_fvgs(self, pair: str, tf: str) -> List[Dict]:
        """Détection Fair Value Gaps."""
        return [
            {
                "direction": "BULLISH",
                "gap_size": 500,
                "quality": "STRONG",
                "filled": False,
                "time_range": {"start": "2024-01-01", "end": "2024-01-02"}
            }
        ]

    def _detect_swings(self, pair: str, tf: str) -> Dict:
        """Points de swing."""
        return {
            "highs": [52000, 53000],
            "lows": [48000, 49000],
            "trend": "BULLISH"
        }

    def _detect_liquidity(self, pair: str, tf: str, asset_type: str) -> Dict:
        """Niveaux de liquidité."""
        if asset_type == "CRYPTO":
            return {
                "support": [45000, 47000],
                "resistance": [55000, 57000],
                "equal_high": 60000,
                "equal_low": 40000
            }
        # Forex/Indices ont plus de niveaux
        return {
            "support": [1.0500, 1.0450],
            "resistance": [1.0650, 1.0700],
            "sessions": ["LONDON_HIGH", "NY_LOW"]
        }

    def _generate_narrative(self, pair: str, tf: str, asset_type: str, kb5_result: Dict = None) -> str:
        """Narration algorithmique."""
        if kb5_result:
            direction = kb5_result.get("direction", "NEUTRAL")
            score = kb5_result.get("final_score", 0)
            return f"Analyse {tf} pour {pair}: Biais {direction} (Score KB5 {score}/100). Structures détectées: {len(kb5_result.get('structures', {}).get('fvg', []))} FVG, {len(kb5_result.get('structures', {}).get('ob', []))} OB."
        return f"Analyse {tf} pour {pair} ({asset_type}): En attente des données du moteur KB5."

    def _calculate_score(self, pair: str, tf: str) -> Dict:
        """Score ICT."""
        return {
            "total": 75,
            "components": {
                "structure": 20,
                "momentum": 15,
                "liquidity": 25,
                "bias": 15
            },
            "grade": "B+",
            "verdict": "WATCH"
        }

    def _get_timeframe_specific_concepts(self, tf: str, asset_type: str) -> List[str]:
        """Concepts spécifiques au timeframe."""
        concepts = []
        if tf == "MN":
            concepts.extend(["Macro Trends", "Intermarket Analysis"])
        elif tf == "W1":
            concepts.extend(["Weekly Bias", "Seasonality"])
        elif tf in ["H4", "H1"]:
            concepts.extend(["Session Overlaps", "Killzones"])
        elif tf in ["M15", "M5", "M1"]:
            concepts.extend(["Scalp Patterns", "Micro Structure"])

        if asset_type == "CRYPTO":
            concepts.extend(["Volatility Clusters", "News Impact"])
        elif asset_type == "INDICES":
            concepts.extend(["Economic Data", "Fed Speeches"])

        return concepts

    def _get_recommendations(self, pair: str, tf: str, asset_type: str) -> List[str]:
        """Recommandations basées sur l'analyse."""
        return [
            f"Surveiller le OB à {tf} pour entrée longue",
            f"Attendre remplissage FVG avant position",
            f"Vérifier confluence avec timeframe supérieur"
        ]

    def generate_summary(self, pair: str, asset_type: str, tf_reports: Dict) -> Dict[str, Any]:
        """Rapport récapitulatif pour le bot."""
        # Agréger les scores et verdicts
        scores = [r["score"]["total"] for r in tf_reports.values() if r["score"]]
        avg_score = sum(scores) / len(scores) if scores else 0

        # Direction dominante
        directions = [r["score"].get("verdict", "NEUTRAL") for r in tf_reports.values()]
        dominant_direction = max(set(directions), key=directions.count) if directions else "NEUTRAL"

        return {
            "pair": pair,
            "asset_type": asset_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timeframes_analyzed": list(tf_reports.keys()),
            "summary_score": {
                "average": avg_score,
                "dominant_verdict": dominant_direction,
                "best_tf": max(tf_reports, key=lambda x: tf_reports[x]["score"]["total"])
            },
            "key_insights": [
                f"Score moyen: {avg_score:.1f}/100",
                f"Direction dominante: {dominant_direction}",
                f"Timeframe le plus fort: {max(tf_reports, key=lambda x: tf_reports[x]['score']['total'])}"
            ],
            "bot_recommendations": {
                "primary_tf": "H1",  # Exemple
                "risk_level": "MEDIUM",
                "entry_conditions": ["OB + FVG confluence", "Bias alignment"]
            }
        }