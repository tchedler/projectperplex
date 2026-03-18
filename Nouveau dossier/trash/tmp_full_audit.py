
import json
import logging
import os
import sys
from datetime import datetime

# Ajouter le chemin racine au sys.path pour les imports
sys.path.append(os.getcwd())

from datastore.data_store import DataStore
from gateway.candle_fetcher import CandleFetcher
from gateway.mt5_connector import MT5Connector
from analysis.fvg_detector import FVGDetector
from analysis.ob_detector import OBDetector
from analysis.smt_detector import SMTDetector
from analysis.bias_detector import BiasDetector
from analysis.liquidity_detector import LiquidityDetector
from analysis.kb5_engine import KB5Engine

PYRAMID_ORDER = ["MN", "W1", "D1", "H4", "H1", "M15"]

def run_full_report(pair="EURUSD"):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("FullAudit")
    
    # Init modules
    ds = DataStore()
    mt5 = MT5Connector()
    if not mt5.connect():
        print("Erreur: Impossible de se connecter à MT5.")
        return
        
    fetcher = CandleFetcher()
    fvg = FVGDetector(ds)
    ob = OBDetector(ds)
    smt = SMTDetector(ds)
    bias = BiasDetector(ds, fvg, ob)
    liq = LiquidityDetector(ds)
    engine = KB5Engine(ds, fvg, ob, smt, bias, liq)
    
    print(f"--- ANALYSE BRUTE POUR {pair} ---")
    
    # 1. Fetch data
    for tf in PYRAMID_ORDER:
        df = fetcher.fetch(pair, tf)
        if df is not None and not df.empty:
            ds.set_candles(pair, tf, df)
            print(f"[{tf}] {len(df)} bougies chargées.")
            
    # 2. Run analysis
    result = engine.analyze(pair)
    
    # 3. Output Full Detail Timeframe by Timeframe
    print("\n=== RAPPORT DÉTAILLÉ TF PAR TF ===")
    
    tf_details = result.get("tf_details", {})
    
    for tf in PYRAMID_ORDER:
        tf_data = tf_details.get(tf, {})
        # Accéder aux structures via la clé 'structures'
        structs = tf_data.get("structures", {})
        fvg_list = structs.get("fvg", [])
        ob_list  = structs.get("ob", [])
        bb_list  = structs.get("bb", [])

        print(f"\n>> TIMEFRAME: {tf}")
        print(f"   Score TF: {tf_data.get('score', 0)}/100")
        print(f"   [PD-ARRAYS]")
        print(f"   - FVG (all): {len(fvg_list)}")
        for f in fvg_list:
            print(f"     * {f.get('direction')} | Top: {f.get('top')} | Bottom: {f.get('bottom')}")
            
        # OB
        for o in ob_list:
            print(f"     * {o.get('status')} | Top: {o.get('top')} | Bottom: {o.get('bottom')} | Qualité: {o.get('quality')}")
            
        # BB
        list_bb = [b for b in structs.get("bb", []) if b.get("tf") == tf]
        print(f"   - Breaker Blocks: {len(list_bb)}")
        for b in list_bb:
            print(f"     * {b.get('direction')} | Top: {b.get('top')} | Bottom: {b.get('bottom')}")

    print("\n=== CONFLUENCES & VERDICT ===")
    print(f"Direction: {result.get('direction')}")
    print(f"Score Final: {result.get('final_score')}")
    print(f"Biais Aligné: {result.get('bias_aligned')}")
    print(f"Confluences: {len(result.get('confluences', []))}")
    for c in result.get("confluences", []):
        print(f" - {c.get('name')}: +{c.get('bonus')} pts")

if __name__ == "__main__":
    pair = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    run_full_report(pair)
