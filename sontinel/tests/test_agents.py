import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# Add parent directory to path to import agents
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.temporal_clock import TemporalClock
from agents.liquidity_tracker import LiquidityTracker

def test_temporal_clock_killzones():
    """Verify ICT killzones timing."""
    clock = TemporalClock()
    ny_tz = pytz.timezone('America/New_York')
    
    # Test London Open (02:00 NY)
    dt_london = datetime(2026, 3, 5, 2, 30, tzinfo=ny_tz)
    res_london = clock.analyze(dt_london)
    assert res_london['killzone'] == "LONDON"
    assert res_london['is_tradable'] == True

    # Test NY AM (10:00 NY)
    dt_ny_am = datetime(2026, 3, 5, 10, 15, tzinfo=ny_tz)
    res_ny_am = clock.analyze(dt_ny_am)
    assert res_ny_am['killzone'] == "NY_AM"
    
    # Test Dead Zone / Lunch (12:30 NY)
    dt_lunch = datetime(2026, 3, 5, 12, 30, tzinfo=ny_tz)
    res_lunch = clock.analyze(dt_lunch)
    assert res_lunch['killzone'] == "NONE"
    assert res_lunch['is_tradable'] == False

def test_temporal_clock_high_prob():
    """Verify high-probability conditions (Macro OR Silver Bullet)"""
    clock = TemporalClock()
    ny_tz = pytz.timezone('America/New_York')
    
    # 10:00 AM NY = NY AM Killzone + Silver Bullet (10-11)
    dt_sb = datetime(2026, 3, 5, 10, 30, tzinfo=ny_tz)
    res_sb = clock.analyze(dt_sb)
    assert res_sb['silver_bullet'] == "NY_AM_SB"
    assert res_sb['is_high_prob'] == True
    
    # 09:55 AM NY = NY AM Killzone + Macro 09:50-10:10
    dt_macro = datetime(2026, 3, 5, 9, 55, tzinfo=ny_tz)
    res_macro = clock.analyze(dt_macro)
    assert res_macro['macro'] == "MACRO_0950"
    assert res_macro['is_high_prob'] == True

def test_temporal_clock_friday_rule():
    """Verify No-Trade rule on Friday after 14:00 NY"""
    clock = TemporalClock()
    ny_tz = pytz.timezone('America/New_York')
    
    # Friday, 14:30 PM (No trade)
    dt_friday = datetime(2026, 3, 6, 14, 30, tzinfo=ny_tz)  # March 6, 2026 is a Friday
    res_friday = clock.analyze(dt_friday)
    assert res_friday['friday_no_trade'] == True
    assert res_friday['is_tradable'] == False

def test_liquidity_tracker_cbdr():
    """Verify CBDR and Flout calculations"""
    tracker = LiquidityTracker("XAUUSD")
    
    # Mock data with NY timezone index
    ny_tz = pytz.timezone('America/New_York')
    dates = [datetime(2026, 3, 5, h, 0, tzinfo=ny_tz) for h in range(12, 23)]
    
    # Create simple predictable data
    # 14h-19h (CBDR): High = 2020.0, Low = 2000.0
    # 15h-00h (Flout): High = 2030.0, Low = 1990.0
    df = pd.DataFrame(index=dates, data={
        "Open": [2010]*11, "Close": [2010]*11,
        "High": [2010, 2010, 2020, 2010, 2010, 2010, 2010, 2010, 2030, 2010, 2010],
        "Low":  [2010, 2010, 2010, 2010, 2000, 2010, 2010, 2010, 2010, 1990, 2010]
    })
    
    cbdr_data = tracker._compute_cbdr(df)
    
    assert cbdr_data['cbdr_high'] == 2020.0
    assert cbdr_data['cbdr_low'] == 2000.0
    assert cbdr_data['flout_high'] == 2030.0
    assert cbdr_data['flout_low'] == 1990.0

if __name__ == "__main__":
    pytest.main([__file__])
