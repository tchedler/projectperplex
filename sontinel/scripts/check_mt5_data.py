import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.market_state_cache import MarketStateCache
import pandas as pd
m = MarketStateCache()
d = m.load()
for sym in d.keys():
    print("SYMBOL:", sym)
    if not isinstance(d[sym], dict) or 'timeframes' not in d[sym]:
        continue
    for tf in d[sym].get('timeframes', {}).keys():
        df = d[sym]['timeframes'][tf].get('data', {}).get('df')
        if df is not None and not df.empty:
            print(f"  {tf} -> len: {len(df)}, start: {df.index[0]}, end: {df.index[-1]}")
        else:
            print(f"  {tf} -> empty or no df")
