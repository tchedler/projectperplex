"""
tests/test_agents_critiques.py — M10 FIX : Tests unitaires pour les 3 agents critiques.
Mocks alignés sur les vraies structures de données des agents.

Lancement :  python -m pytest tests/test_agents_critiques.py -v
"""
import sys
import os
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# DONNÉES MOCK PARTAGÉES — alignées sur les vraies structures internes
# ============================================================

def make_df(n=200, trend="bull") -> pd.DataFrame:
    """DataFrame OHLCV factice."""
    dates = [datetime(2026, 1, 2) + timedelta(minutes=i * 15) for i in range(n)]
    close = np.linspace(1900, 2000 if trend == "bull" else 1800, n)
    noise = np.random.normal(0, 3, n)
    close = close + noise
    df = pd.DataFrame({
        "Open":   close - 2,
        "High":   close + 6,
        "Low":    close - 6,
        "Close":  close,
        "Volume": np.random.randint(100, 10000, n),
    }, index=pd.DatetimeIndex(dates))
    return df


def make_clock(kz="NY_AM", tradable=True, friday=False):
    return {
        "killzone":       kz,
        "macro":          "NONE",
        "is_tradable":    tradable,
        "is_high_prob":   True,
        "friday_no_trade": friday,
        "day":            "MARDI",
        "ny_time":        "09:30",
        "silver_bullet":  "NONE",
    }


def make_bias(htf="BULLISH_EXPANSION"):
    """Bias aligné sur les clés utilisées par checklist_expert._calculate_score_v4."""
    return {
        "htf_bias": htf,
        "draw_on_liquidity": {
            "name":  "BSL",
            "price": 2000.0,
            "dist":  0.002,   # clé requise par SECTION A et SECTION C
        },
        "midnight_open": 1950.0,
    }


def make_smc_result():
    """SMC aligné sur les clés réelles du checklist (_calculate_score_v4)."""
    return {
        "structure": {
            "mode": "MSS",
            "swh":  1980.0,
            "swl":  1940.0,
            "mss":  True,
            "bos":  False,
        },
        "displacement": {
            "is_displaced": True, 
            "factor": 2.5,
            "velocity": "HIGH",
            "power_ratio": 3.0,
        },
        # checklist_expert utilise smc['fvgs'] (liste plate)
        "fvgs": [
            {"high": 1970.0, "low": 1965.0, "top": 1970.0, "bot": 1965.0, "ce": 1967.5, "type": "BISI", "quality": "FRESH"}
        ],
        # checklist_expert utilise aussi fvgs_pd_arrays pour AISupremeJudge
        "fvgs_pd_arrays": {
            "all_fvgs": [{"high": 1970.0, "low": 1965.0, "top": 1970.0, "bot": 1965.0, "type": "BISI", "quality": "FRESH"}],
            "bprs": [],
            "ifvgs": [],
            "mitigation_blocks": []
        },
        "institutional_blocks": [
            {
                "high": 1955.0, "low": 1950.0,
                "type": "OB_BULL", "quality_score": 8, "quality": 8,
                "refined_zone": [1950.0, 1955.0],
            }
        ],
        "boolean_sweep_erl": {"value": True, "sweep_type": "BULLISH_SWEEP"},
        "protected_levels": [],
        "rejections": {"bull_wick_ce": 0, "bear_wick_ce": 0},
    }


def make_liq():
    """Liquidité alignée sur checklist_expert._calculate_score_v4 SECTION C."""
    return {
        "erl":  {"high": 1990.0, "low": 1920.0},
        # eqh/eql doivent être des LISTES de dicts (pas de simples floats)
        "eqh": [{"price": 1985.0, "quality": "SMOOTH", "swept": False}],
        "eql": [{"price": 1925.0, "quality": "SMOOTH", "swept": False}],
        "lrlr_hrlr": {
            "bull": {"type": "LRLR", "label": "Low Resistance"},
            "bear": {"type": "HRLR", "label": "High Resistance"},
        },
        "proximal_liquidity": 1985.0,  # Doit être un float (TypeError: dict.__format__)
    }


def make_exe():
    """ExécutionPrécision alignée sur checklist_expert SECTION D."""
    return {
        "ote": {
            "lvl_624": 1960.0, "lvl_705": 1955.0,
            "lvl_786": 1948.0, "valid": True,
        },
        "equilibrium": {
            "percent": 68.0,       # dans la zone OTE 62-79%
            "zone": "DISCOUNT",
        },
        "premium_discount": "DISCOUNT",
        "rr_ratio": 2.5,
        "setup_name": "MMXM_DISCOUNT",
    }


def make_mmxm():
    """MMXM aligné sur checklist_expert SECTION D (turtle_soup requis)."""
    return {
        "po3_phase":   "DISTRIBUTION",
        "mmxm_cycle":  "EXPANSION",           # au lieu de "cycle"
        "turtle_soup": "NONE",
        "midnight_open": 1950.0,
        "silver_bullet": "NONE",
    }


# ============================================================
# TESTS — SMCSpecialist
# ============================================================

class TestSMCSpecialist:
    def setup_method(self):
        from agents.smc_specialist import SMCSpecialist
        # SMCSpecialist requiert 'symbol' comme argument
        self.smc = SMCSpecialist("XAUUSD")

    def test_analyze_bull_returns_dict(self):
        df = make_df(200, trend="bull")
        result = self.smc.analyze(df, make_clock())
        assert isinstance(result, dict), "Le résultat doit être un dict"
        assert "structure" in result
        assert "boolean_sweep_erl" in result

    def test_analyze_bear_returns_dict(self):
        df = make_df(200, trend="bear")
        result = self.smc.analyze(df, make_clock())
        assert isinstance(result, dict)

    def test_analyze_too_few_bars_returns_none(self):
        """Moins de 60 bougies → retourne None (protection défensive)."""
        df = make_df(30, trend="bull")
        result = self.smc.analyze(df, make_clock())
        assert result is None, "Moins de 60 bougies → None attendu"

    def test_pdh_pdl_monday_no_crash(self):
        """I3 FIX test : La détection PDH/PDL du lundi ne doit pas planter."""
        df = make_df(200, trend="bull")
        # Simuler un lundi (pas de données dimanche)
        monday_dates = [datetime(2026, 1, 5) + timedelta(minutes=i * 15) for i in range(200)]
        df.index = pd.DatetimeIndex(monday_dates)
        result = self.smc.analyze(df, make_clock())
        assert result is not None
        sweep = result.get("boolean_sweep_erl", {})
        assert "value" in sweep, "boolean_sweep_erl doit contenir 'value'"

    def test_boolean_sweep_erl_present(self):
        df = make_df(200, trend="bull")
        result = self.smc.analyze(df, make_clock())
        assert "boolean_sweep_erl" in result
        assert "value" in result["boolean_sweep_erl"]
        assert isinstance(result["boolean_sweep_erl"]["value"], bool)


# ============================================================
# TESTS — ChecklistExpert
# ============================================================

class TestChecklistExpert:
    def setup_method(self):
        from agents.checklist_expert import ChecklistExpert
        self.expert = ChecklistExpert()

    def test_generate_returns_tuple(self):
        smc   = make_smc_result()
        liq   = make_liq()
        bias  = make_bias()
        exe   = make_exe()
        mmxm  = make_mmxm()
        clock = make_clock()
        html, score, verdict = self.expert.generate("M15", smc, liq, bias, exe, mmxm, clock)
        assert isinstance(score, (int, float))
        assert isinstance(verdict, str)
        assert isinstance(html, str)

    def test_score_in_valid_range(self):
        """C3 FIX test : Le score doit être entre -50 et 100."""
        html, score, verdict = self.expert.generate(
            "M15", make_smc_result(), make_liq(), make_bias(),
            make_exe(), make_mmxm(), make_clock()
        )
        assert -50 <= score <= 100, f"Score hors limites : {score}"

    def test_friday_no_trade_returns_zero(self):
        """FIX-O : Vendredi après 14h → score = 0."""
        clock = make_clock(friday=True)
        _, score, _ = self.expert.generate(
            "M15", make_smc_result(), make_liq(), make_bias(),
            make_exe(), make_mmxm(), clock
        )
        assert score == 0, f"Vendredi après 14h → score attendu 0, reçu {score}"

    def test_outside_session_low_score(self):
        """Hors killzone → score réduit (pénalité -10)."""
        clock = make_clock(kz="NONE", tradable=False)
        _, score_out, _ = self.expert.generate(
            "M15", make_smc_result(), make_liq(), make_bias(),
            make_exe(), make_mmxm(), clock
        )
        clock_in = make_clock(kz="NY_AM", tradable=True)
        _, score_in, _ = self.expert.generate(
            "M15", make_smc_result(), make_liq(), make_bias(),
            make_exe(), make_mmxm(), clock_in
        )
        assert score_out <= score_in, "Score hors session doit être ≤ score en session"

    def test_cbdr_not_asia(self):
        """M13 FIX test : generate() ne plante pas avec killzone=ASIA."""
        clock = make_clock(kz="ASIA")
        html, score, verdict = self.expert.generate(
            "M15", make_smc_result(), make_liq(), make_bias(),
            make_exe(), make_mmxm(), clock
        )
        assert len(html) > 0, "HTML ne doit pas être vide"

    def test_score_negative_capped(self):
        """C3 FIX test : Score très négatif capé à -50."""
        # Pas de sweep, hors session, bear bias → score très négatif
        bear_smc = make_smc_result()
        bear_smc["boolean_sweep_erl"] = {"value": False}
        bear_smc["displacement"] = {
            "is_displaced": False, 
            "factor": 0.5,
            "velocity": "LOW",
            "power_ratio": 1.0,
        }
        bear_bias = make_bias("NEUTRAL")
        clock = make_clock(kz="NONE", tradable=False)
        _, score, _ = self.expert.generate(
            "M15", bear_smc, make_liq(), bear_bias,
            make_exe(), make_mmxm(), clock
        )
        assert score >= -50, f"Score ne doit pas descendre en dessous de -50, reçu {score}"


# ============================================================
# TESTS — TradingJudge
# ============================================================

class TestTradingJudge:
    def setup_method(self):
        from agents.trading_judge import TradingJudge
        self.judge = TradingJudge(config={
            "score_execute": 75,
            "score_limit":   60,
            "risk_pct":      1.0,
            "max_positions": 3,
        })

    def test_evaluate_returns_signal(self):
        from agents.trading_judge import TradeSignal
        signal = self.judge.evaluate(
            "XAUUSD", "M15",
            make_clock(), make_bias(), make_smc_result(),
            make_liq(), make_exe(), make_mmxm(),
            {"score": 80, "verdict": "🚀 EXÉCUTION A+", "html": ""},
            open_positions=0, session_losses=0, session_trades=0
        )
        assert isinstance(signal, TradeSignal)
        assert signal.action in ("EXECUTE", "LIMIT", "NO_TRADE"), f"Action inconnue: {signal.action}"

    def test_c5_fix_mmxm_accumulation_blocks(self):
        """C5 FIX : mmxm en ACCUMULATION → NO_TRADE (règle absolue ICT)."""
        mmxm_acc = {"po3_phase": "ACCUMULATION", "cycle": "RANGING", "turtle_soup": "NONE"}
        try:
            signal = self.judge.evaluate(
                "XAUUSD", "M15",
                make_clock(), make_bias(), make_smc_result(),
                make_liq(), make_exe(), mmxm_acc,
                {"score": 90, "verdict": "🚀 EXÉCUTION A+", "html": ""},
            )
            assert signal.action == "NO_TRADE", "Phase ACCUMULATION → NO_TRADE attendu"
        except NameError as e:
            pytest.fail(f"NameError détecté — C5 non corrigé : {e}")

    def test_friday_blocked(self):
        """Vendredi après 14h → NO_TRADE quelle que soit le score."""
        clock = make_clock(friday=True, tradable=True)
        signal = self.judge.evaluate(
            "XAUUSD", "M15",
            clock, make_bias(), make_smc_result(),
            make_liq(), make_exe(), make_mmxm(),
            {"score": 95, "verdict": "🚀 EXÉCUTION A+", "html": ""},
        )
        assert signal.action == "NO_TRADE", "Vendredi après 14h → NO_TRADE attendu"

    def test_max_losses_blocked(self):
        """2 pertes consécutives → NO_TRADE (règle discipline ICT)."""
        signal = self.judge.evaluate(
            "XAUUSD", "M15",
            make_clock(), make_bias(), make_smc_result(),
            make_liq(), make_exe(), make_mmxm(),
            {"score": 95, "verdict": "🚀 EXÉCUTION A+", "html": ""},
            session_losses=2
        )
        assert signal.action == "NO_TRADE", "2 pertes consécutives → NO_TRADE attendu"

    def test_out_of_session_blocked(self):
        """Hors session (is_tradable=False) → NO_TRADE."""
        clock = make_clock(kz="NONE", tradable=False)
        signal = self.judge.evaluate(
            "XAUUSD", "M15",
            clock, make_bias(), make_smc_result(),
            make_liq(), make_exe(), make_mmxm(),
            {"score": 95, "verdict": "🚀 EXÉCUTION A+", "html": ""},
        )
        assert signal.action == "NO_TRADE", "Hors session → NO_TRADE attendu"

    def test_signal_has_symbol_and_timeframe(self):
        """Le signal retourné doit toujours avoir symbol et timeframe définis."""
        signal = self.judge.evaluate(
            "EURUSD", "H1",
            make_clock(), make_bias(), make_smc_result(),
            make_liq(), make_exe(), make_mmxm(),
            {"score": 85, "verdict": "🚀 EXÉCUTION A+", "html": ""},
        )
        assert signal.symbol == "EURUSD"
        assert signal.timeframe == "H1"


# ============================================================
# TESTS — Constants (M6)
# ============================================================

class TestConstants:
    def test_pip_size_all_symbols_present(self):
        from core.constants import PIP_SIZE
        required = ["EURUSD", "GBPUSD", "XAUUSD", "NAS100", "USDJPY", "BTCUSD"]
        for sym in required:
            assert sym in PIP_SIZE, f"'{sym}' manquant dans PIP_SIZE"

    def test_pip_value_all_symbols_present(self):
        from core.constants import PIP_VALUE_PER_LOT
        required = ["EURUSD", "XAUUSD", "NAS100"]
        for sym in required:
            assert sym in PIP_VALUE_PER_LOT, f"'{sym}' manquant dans PIP_VALUE_PER_LOT"

    def test_bot_magic_number_correct(self):
        from core.constants import BOT_MAGIC_NUMBER
        assert BOT_MAGIC_NUMBER == 20260001, "Magic number incorrect"

    def test_tf_order_complete(self):
        from core.constants import TF_ORDER_ALL
        for tf in ["MN", "W1", "D1", "H4", "H1", "M15", "M5", "M1"]:
            assert tf in TF_ORDER_ALL, f"TF '{tf}' manquant dans TF_ORDER_ALL"
