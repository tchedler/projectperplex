import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.trading_judge import TradingJudge

def run_tests():
    print("="*60)
    print("DEBUT DU TEST DES SCENARIOS ICT (TRADING JUDGE)")
    print("="*60)

    # Configuration du Juge (identique à l'interface)
    config = {
        "score_execute": 80,
        "score_limit": 65,
        "risk_pct": 1.0,
        "account_balance": 10000,
        "max_positions": 3
    }
    judge = TradingJudge(config)

    symbol = "XAUUSD"
    tf = "M5"

    # Bases communes
    bias_bull = {
        "htf_bias": "BULL_STRONG",
        "draw_on_liquidity": {"price": 2040.0, "name": "BSL"}
    }
    smc_bull = {
        "trend": "BULL",
        "structure": {"mode": "MSS_BULL", "swl": 1990.0, "swh": 2020.0},
        "fvgs": [
            {"type": "BISI", "quality": "FRESH", "ce": 1999.0, "top": 2000.0, "bottom": 1998.0}
        ],
        "institutional_blocks": []
    }
    liq = {
        "erl": {"high": 2030.0, "low": 1980.0}
    }
    mmxm = {"po3_phase": "EXPANSION"}
    exe = {"ote": {"lvl_705": 1998.85}} # Niveau 70.5% du retracement

    # -----------------------------------------------------------------
    # SCÉNARIO 1 : SETUP A+ (Attendu : EXECUTE)
    # -----------------------------------------------------------------
    print("\n[SCENARIO 1] : Le Super Setup A+ (Score 95/100 en Killzone)")
    clock_sz1 = {"is_tradable": True, "killzone": "NY_AM", "macro": "MACRO_0950"}
    chk_sz1 = {"score": 95, "verdict": "EXECUTE"}
    
    signal1 = judge.evaluate(symbol, tf, clock_sz1, bias_bull, smc_bull, liq, exe, mmxm, chk_sz1)
    
    print(f"  Action      : {signal1.action}")
    print(f"  Direction   : {signal1.direction}")
    print(f"  Entry Price : {signal1.entry}")
    print(f"  Stop L. (SL): {signal1.sl}")
    print(f"  Take P. (TP): {signal1.tp2}")
    print(f"  Raison      : {signal1.reason}")

    # -----------------------------------------------------------------
    # SCÉNARIO 2 : SETUP MOYEN / ANTICIPATION (Attendu : LIMIT)
    # -----------------------------------------------------------------
    print("\n[SCENARIO 2] : Anticipation (Score 72/100 en Killzone)")
    clock_sz2 = {"is_tradable": True, "killzone": "LONDON", "macro": "NONE"}
    chk_sz2 = {"score": 72, "verdict": "LIMIT"}
    
    signal2 = judge.evaluate(symbol, tf, clock_sz2, bias_bull, smc_bull, liq, exe, mmxm, chk_sz2)
    
    print(f"  Action      : {signal2.action}")
    print(f"  Direction   : {signal2.direction}")
    print(f"  Entry Price : {signal2.entry}")
    print(f"  Stop L. (SL): {signal2.sl}")
    print(f"  Take P. (TP): {signal2.tp2}")
    print(f"  Raison      : {signal2.reason}")

    # -----------------------------------------------------------------
    # SCÉNARIO 3 : PIÈGE HORS KILLZONE (Attendu : NO_TRADE)
    # -----------------------------------------------------------------
    print("\n[SCENARIO 3] : Piege Hors Session (Score 98/100 mais 12h30 NY)")
    clock_sz3 = {"is_tradable": False, "killzone": "NONE", "macro": "NONE"}
    chk_sz3 = {"score": 98, "verdict": "EXECUTE"}
    
    signal3 = judge.evaluate(symbol, tf, clock_sz3, bias_bull, smc_bull, liq, exe, mmxm, chk_sz3)
    
    print(f"  Action      : {signal3.action}")
    print(f"  Raison      : {signal3.reason}")

    print("\n"+"="*60)
    print("FIN DU TEST")
    print("="*60)

if __name__ == "__main__":
    run_tests()
