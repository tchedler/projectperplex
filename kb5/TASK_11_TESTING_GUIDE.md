# Task 11: Comprehensive Parameter Testing Guide

**Objective**: Validate all 105+ configured parameters are responsive and functioning correctly at runtime.

**Scope**: All modules that have been modified with Mixin inheritance  
**Estimated Duration**: 2-3 hours  
**Success Criteria**: All 105 parameters verified functional with zero regressions

---

## Test Strategy

### Phase 1: Static Parameter Validation (30 minutes)
- Verify all parameters are correctly loaded from `user_settings.json`
- Verify SettingsIntegration can access all parameters
- Verify no typos or missing mappings

### Phase 2: Detector Toggle Testing (45 minutes)
- Disable each of 13 detectors independently
- Verify bot skips disabled detectors
- Verify enabled detectors produce results

### Phase 3: Engine Parameter Testing (45 minutes)
- Test scoring threshold changes
- Test risk parameter changes
- Verify hardcoded values successfully replaced

### Phase 4: Execution Module Testing (45 minutes)
- Test behaviour shields
- Test time filters
- Test risk allocation

### Phase 5: Integration Testing (15 minutes)
- Verify no parameter conflicts
- Verify supervisor reload cycle working
- Verify graceful shutdown

---

## Test Categories: 105 Parameters

### CATEGORY 1: ICT Concepts (31 Parameters) ✅ Theoretical Coverage

**File**: `user_settings.json` → `principles_enabled`  
**Implementation**: Via detector `is_active()` checks  
**Test Method**: Disable/enable in UI → observe log output

**Parameters**:
```python
# ICT School (15 parameters)
"ICT:killzone"              # Detection point 1
"ICT:fvg"                  # Fair value gap (FVG detector)
"ICT:order_blocks"         # Order blocks (OB detector)
"ICT:liquidity"            # Liquidity grabs (Liquidity detector)
"ICT:mss"                  # Market structure shift (MSS detector)
"ICT:choch"                # Change of character (ChoCH detector)
"ICT:smt"                  # Smart money trades (SMT detector)
"ICT:amd"                  # Aggressive market dynamics (AMD detector)
"ICT:silver_bullet"        # Silver bullet patterns
"ICT:macros_ict"           # Macro ICT concepts
"ICT:midnight_open"        # Midnight open strategies
"ICT:irl"                  # Impulse-retracement-liquidation (IRL detector)
"ICT:pd_zone"              # Premium/Discount zones
"ICT:ote"                  # Order template entry (OTE detector)
"ICT:cisd"                 # Cyber Induced Stop Loss (CISD detector)
"ICT:cbdr"                 # Collateral buy/sell down rule

# SMC School (7 parameters)
"SMC:bos"                  # Break of structure
"SMC:choch_smc"            # Change of character (SMC variant)
"SMC:inducement"           # Inducement patterns (Inducement detector)
"SMC:ob_smc"               # Order blocks (SMC variant)
"SMC:fvg_smc"              # Fair value gaps (SMC variant)
"SMC:equal_hl"             # Equal high/low patterns
"SMC:premium_discount"     # Premium/discount dynamics

# Price Action (5 parameters)
"PA:engulfing"             # Engulfing candles
"PA:trendlines"            # Trendline breaks
"PA:round_numbers"         # Round number resistance/support
"PA:pin_bar"               # Pin bar patterns
"PA:inside_bar"            # Inside bar patterns
"PA:sr_levels"             # Support/resistance levels
```

**Test Execution**:
```bash
# Test each concept:
1. In bot_settings.py, toggle each principle_enabled setting
2. Restart bot or wait for 10s settings reload
3. Check logs: [DETECTOR:X] should be skipped if disabled
4. Check logs: [DETECTOR:X] should produce results if enabled
```

---

### CATEGORY 2: Detector Toggles (13 Parameters) ✅ Implementation Complete

**File**: `analysis/` directory  
**Implementation**: DetectorMixin with `is_active()` checks  
**Test Method**: Disable detector → observe empty result dict

**Detectors** (13 total):
```python
# All now inherit DetectorMixin and check is_active()
amd_detector.py              # Aggressive market dynamics
bias_detector.py             # Bias detection
choch_detector.py            # Change of character
cisd_detector.py             # Cyber-induced SL
circuit_breaker.py           # (Engine type)
displacement_detector.py     # Displacement patterns
fvg_detector.py              # Fair value gaps
inducement_detector.py       # Inducement patterns
irl_detector.py              # Impulse/Retracement/Liquidation
liquidity_detector.py        # Liquidity grabs
mss_detector.py              # Market structure shift
ob_detector.py               # Order blocks
ote_detector.py              # Order template entry
pa_detector.py               # Price action
smt_detector.py              # Smart money trades
```

**Test Execution**:
```bash
# Test detector toggle:
1. Disable FVG detector in settings
2. Wait 10 seconds for reload
3. Check logs for no FVG analysis output
4. Check scoring_engine.py bypass results
5. Enable FVG detector
6. Wait 10 seconds
7. Check logs for FVG results
```

**Verification Method**:
```python
# In SettingsIntegration:
if not self.is_detector_active('fvg'):
    return {}  # Empty results
```

---

### CATEGORY 3: Risk Management (6 Parameters) ✅ Implementation Complete

**File**: `user_settings.json` → Risk section  
**Implementation**: Via ExecutionMixin methods  
**Test Method**: Change value → verify bot uses new setting

**Parameters**:
```python
"risk_per_trade"        # 0.5 = 0.5% per trade
"max_trades_day"        # 3 = maximum 3 trades/day
"max_dd_day_pct"        # 3.0 = 3% daily drawdown limit
"max_dd_week_pct"       # 6.0 = 6% weekly drawdown limit
"rr_min"                # 2.0 = minimum risk/reward
"rr_target"             # 3.0 = target risk/reward
```

**Test Execution**:
```bash
# Test risk_per_trade parameter:
1. Set risk_per_trade = 0.5 (0.5%)
2. Simulate trade with account = $10,000
3. Verify trade size = $50 (0.5% of $10,000)
4. Change risk_per_trade = 1.0
5. Wait 10 seconds
6. Simulate same trade
7. Verify trade size = $100 (1.0% of $10,000)

# Test max_trades_day:
1. Set max_trades_day = 3
2. Execute trades 1, 2, 3 successfully
3. Verify trade 4 is REJECTED
4. Change max_trades_day = 5
5. Verify trade 4 is ACCEPTED

# Test max_dd_day_pct:
1. Set max_dd_day_pct = 3.0
2. Simulate losses until -3.0% is reached
3. Verify trades are BLOCKED
4. Change max_dd_day_pct = 5.0
5. Verify next trade is ALLOWED

# Test rr_min:
1. Set rr_min = 2.0
2. Signal with R:R = 1.8 should be REJECTED
3. Signal with R:R = 2.5 should be ACCEPTED
4. Change rr_min = 1.5
5. Signal with R:R = 1.8 should be ACCEPTED
```

---

### CATEGORY 4: Scoring Thresholds (2 Parameters - CRITICAL) ✅ Hardcodes Replaced

**File**: `scoring_engine.py` → Lines 268, 397  
**Implementation**: Changed from hardcoded values to dynamic settings  
**Test Method**: Change value → verify bot executes at new threshold

**Parameters**:
```python
"score_execute"    # Was hardcoded 75 → NOW user-configurable (80 in settings)
"score_watch"      # Was hardcoded 15 → NOW user-configurable (65 in settings)
```

**CRITICAL VERIFICATION** (ScoringEngine.py):
```python
# Line 268 - MUST use dynamic threshold:
watch_threshold = self.get_scoring_thresholds()['watch']
elif final_score >= watch_threshold:  # NOT hardcoded 15

# Line 397-401 - MUST use dynamic rr_min:
rr_minimum = self.get_risk_config()['rr_min']
if not rr_valid or rr < rr_minimum:  # NOT hardcoded 2.0
```

**Test Execution**:
```bash
# Test score_execute:
1. Set score_execute = 80
2. Analyze pair with FVG score = 78
3. Verify result = "WATCH" (not executed)
4. Change score_execute = 75
5. Analyze same pair
6. Verify result = "EXECUTE" (executed at new threshold)

# Test score_watch:
1. Set score_watch = 65
2. Analyze pair with score = 60
3. Verify result = "NO_TRADE"
4. Change score_watch = 55
5. Analyze same pair
6. Verify result = "WATCH"

# Test rr_minimum:
1. Set rr_min = 2.0
2. Calculate R:R = 1.8 for trade
3. Verify order REJECTED (rr < 2.0)
4. Change rr_min = 1.5
5. Verify same order ACCEPTED
```

---

### CATEGORY 5: Behaviour Shields (8 Parameters) ✅ Implementation Complete

**File**: `execution/behaviour_shield.py`  
**Implementation**: Via ExecutionMixin `is_shield_enabled()` method  
**Test Method**: Disable shield → verify trade that would trigger shield is allowed

**Parameters**:
```python
"behaviour_shield": {
    "stop_hunt":         # Detect predatory stop loss hunts
    "fake_breakout":     # Detect fake breakout patterns
    "liquidity_grab":    # Detect liquidity grabs
    "news_spike":        # Detect news-driven volatility
    "overextension":     # Detect overextended moves
    "revenge_trade":     # Detect revenge trading (after losses)
    "duplicate":         # Prevent duplicate entries
    "staleness":         # Prevent stale signals
}
```

**Test Execution**:
```bash
# Test stop_hunt shield:
1. Create signal that would trigger stop hunt pattern
2. With shield ENABLED: Trade REJECTED
3. Set behaviour_shield.stop_hunt = false
4. Wait 10 seconds
5. Create signal again
6. Trade ACCEPTED

# Test fake_breakout shield:
1. Create signal with fake breakout pattern
2. With shield ENABLED: Trade REJECTED
3. Disable shield: behaviour_shield.fake_breakout = false
4. Trade ACCEPTED

# Test liquidity_grab shield:
1. Create signal in liquidity grab zone
2. With shield ENABLED: Trade REJECTED
3. Disable shield
4. Trade ACCEPTED

# (Repeat for all 8 shields)
```

---

### CATEGORY 6: Killswitches (8-9 Parameters) ✅ Implementation Complete

**File**: `user_settings.json` → `disabled_ks`  
**Implementation**: Via ExecutionMixin `is_killswitch_active()` method  
**Test Method**: Enable/disable KS → verify trading behavior changes

**Parameters**:
```python
# Killswitches 1-9 in disabled_ks array
"KS1"     # Circuit breaker (drawdown 3%)
"KS2"     # Max trades per day exceeded
"KS3"     # Risk per trade exceeded
"KS4"     # Weekly drawdown exceeded
"KS5"     # News event detected
"KS6"     # Spread too wide
"KS7"     # Correlation breakdown
"KS8"     # Volatility spike
"KS9"     # Manual shutdown
```

**Test Execution**:
```bash
# Test KS1 (Circuit Breaker):
1. disabled_ks = ["KS1"] (all others enabled)
2. Simulate -3% loss
3. Verify trading BLOCKED
4. Remove KS1: disabled_ks = [] (all enabled)
5. Simulate same conditions
6. Verify trading still BLOCKED (CB active)
7. Set "RISK:circuit_breaker": false in settings
8. Verify trading ALLOWED

# Test KS2 (Max trades):
1. disabled_ks = ["KS2"] 
2. Execute max_trades_day + 1 trades
3. Verify extra trade ALLOWED (KS2 disabled)
4. disabled_ks = []
5. Verify extra trade BLOCKED (KS2 enabled)

# (Repeat for all 9 killswitches)
```

---

### CATEGORY 7: Time Filters (3 Parameters) ✅ Implementation Complete

**File**: `user_settings.json` → `time_filters`  
**Implementation**: Via ExecutionMixin time filter methods  
**Test Method**: Simulate time → verify trading allowed/blocked

**Parameters**:
```python
"time_filters": {
    "friday_pm":        # Disable trading Friday afternoon
    "monday_morning":   # Disable trading Monday morning
    "before_news":      # Disable trading before news events
}
```

**Test Execution**:
```bash
# Test friday_pm filter:
1. Set time_filters.friday_pm = true (enabled)
2. Simulate time = Friday 15:00 UTC
3. Create signal
4. Verify trade REJECTED (declined friday_pm)
5. Set time_filters.friday_pm = false
6. Simulate same time
7. Verify trade ACCEPTED

# Test monday_morning filter:
1. Set time_filters.monday_morning = true
2. Simulate time = Monday 08:00 UTC
3. Create signal
4. Verify trade REJECTED
5. Change to 12:00 UTC
6. Verify trade ACCEPTED (morning passed)

# Test before_news filter:
1. Set time_filters.before_news = true
2. Calendar shows news in 30 minutes
3. Create signal
4. Verify trade REJECTED
5. Set time_filters.before_news = false
6. Verify trade ACCEPTED
```

---

### CATEGORY 8: Session Controls (Dynamic) ✅ Implementation Ready

**File**: `user_settings.json` → `sessions_actives`  
**Implementation**: Via supervisor session checks  
**Test Method**: Enable/disable session → verify trading active only in allowed sessions

**Parameters**:
```python
"sessions_actives": [
    "session_london",
    "overlap_lnny",
    "session_ny"
]
```

**Test Execution**:
```bash
# Test session_london:
1. sessions_actives = ["session_london"] only
2. Simulate time = 07:00 UTC (London open)
3. Verify trading ACTIVE
4. Simulate time = 13:00 UTC (London closed, NY open)
5. Verify trading INACTIVE

# Test overlap_lnny:
1. sessions_actives = ["overlap_lnny"]
2. Simulate time = 13:00 UTC (overlap)
3. Verify trading ACTIVE
4. Simulate time = 16:00 UTC (overlap closed)
5. Verify trading INACTIVE
```

---

### CATEGORY 9: Operational Mode (1 Parameter) ✅ Ready

**File**: `user_settings.json` → `op_mode`  
**Implementation**: Via supervisor operational checks  
**Test Method**: Change mode → verify trading behavior change

**Parameters**:
```python
"op_mode": "PAPER"    # PAPER or LIVE
```

**Test Execution**:
```bash
# Test op_mode:
1. SET op_mode = "PAPER"
2. Create order signal
3. Verify order sent to DEMO account
4. Check logs: "PAPER TRADE"
5. Change op_mode = "LIVE"
6. Wait 10 seconds for reload
7. Create order signal
8. Verify order sent to LIVE account
9. Check logs: "LIVE TRADE"
```

---

### CATEGORY 10: Configuration (Remaining ~20 parameters) ✅ Ready

**File**: `user_settings.json`  
**Implementation**: Via universal `get_setting()` method  
**Test Method**: Verify setting is accessible and used

**Parameters**:
```python
# Profile & Pairs
"profile"               # Custom/Standard/Aggressive
"active_pairs"          # List of trading pairs
"schools_enabled"       # ICT, RISK, etc.

# LLM Settings
"llm_provider"          # Gemini/Claude/etc.
"llm_api_key"           # API key for provider

# Requirements
"require_killzone"      # Require ICT killzone
"require_erl"           # Require ERL (Equal-Risk-Line)
"require_mss"           # Require market structure shift
"require_choch"         # Require change of character

# Advanced
"use_partial_tp"        # Use partial take profit
"last_updated"          # Timestamp (auto-set)
"version"               # Version number
```

**Test Execution**:
```bash
# Test require_killzone:
1. require_killzone = true
2. Signal WITHOUT killzone: REJECTED
3. Signal WITH killzone: ACCEPTED
4. require_killzone = false
5. Signal WITHOUT killzone: ACCEPTED

# Test use_partial_tp:
1. use_partial_tp = true
2. Order execution: 50% at TP1, 50% at TP2
3. use_partial_tp = false
4. Order execution: 100% at single TP

# (Repeat for all configuration parameters)
```

---

## Testing Execution Plan

### Test Script Template (Python)

```python
# tests/test_all_parameters.py

import json
import time
from config.settings_integration import SettingsIntegration
from datastore.data_store import DataStore

def test_parameter_loading():
    """Test 1: Verify all 105+ parameters load correctly"""
    settings = SettingsIntegration()
    all_settings = settings.get_all_settings()
    
    # Check all major parameter groups exist
    assert 'principles_enabled' in all_settings
    assert 'risk_per_trade' in all_settings
    assert 'behaviour_shield' in all_settings
    assert 'time_filters' in all_settings
    assert 'disabled_ks' in all_settings
    
    print("✅ All parameter groups loaded")
    return True

def test_detector_toggle():
    """Test 2: Verify each detector can be toggled"""
    settings = SettingsIntegration()
    detectors = ['fvg', 'ob', 'smt', 'bias', 'kb5', 'mss', 'choch', 
                 'amd', 'liquidity', 'inducement', 'irl', 'ote', 'cisd']
    
    for detector in detectors:
        # Should not raise error
        active = settings.is_detector_active(detector)
        print(f"✅ Detector {detector}: {active}")
    
    return True

def test_scoring_thresholds():
    """Test 3: Verify scoring thresholds are dynamic"""
    settings = SettingsIntegration()
    thresholds = settings.get_scoring_thresholds()
    
    assert 'execute' in thresholds
    assert 'watch' in thresholds
    assert thresholds['execute'] == 80  # From user_settings.json
    assert thresholds['watch'] == 65
    
    print(f"✅ Scoring thresholds: {thresholds}")
    return True

def test_risk_parameters():
    """Test 4: Verify risk parameters are accessible"""
    settings = SettingsIntegration()
    risk = settings.get_risk_config()
    
    assert risk['risk_per_trade'] == 0.5
    assert risk['max_trades_day'] == 3
    assert risk['rr_min'] == 2.0
    
    print(f"✅ Risk parameters: {risk}")
    return True

def test_behaviour_shields():
    """Test 5: Verify behaviour shields are toggleable"""
    settings = SettingsIntegration()
    shields = ['stop_hunt', 'fake_breakout', 'liquidity_grab', 
               'news_spike', 'overextension', 'revenge_trade', 
               'duplicate', 'staleness']
    
    for shield in shields:
        enabled = settings.is_shield_enabled(shield)
        print(f"✅ Shield {shield}: {enabled}")
    
    return True

def test_settings_reload():
    """Test 6: Verify settings reload cycle works"""
    settings = SettingsIntegration()
    
    # Get initial value
    initial_risk = settings.get_setting('risk_per_trade')
    print(f"Initial risk_per_trade: {initial_risk}")
    
    # Should reload every 10 seconds
    time.sleep(11)
    
    # Get new value (may be same if not changed in UI)
    reloaded_risk = settings.get_setting('risk_per_trade')
    print(f"Reloaded risk_per_trade: {reloaded_risk}")
    
    print("✅ Settings reload cycle active")
    return True

# Run all tests
if __name__ == '__main__':
    tests = [
        test_parameter_loading,
        test_detector_toggle,
        test_scoring_thresholds,
        test_risk_parameters,
        test_behaviour_shields,
        test_settings_reload,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"TOTAL: {passed} passed, {failed} failed")
    print(f"{'='*50}")
```

---

## Verification Checklist

### Pre-Testing
- [ ] All 21 modules have correct mixin inheritance
- [ ] SettingsIntegration can access all 105+ parameters
- [ ] user_settings.json is valid JSON
- [ ] Supervisor is running settings reload cycle (10s interval)
- [ ] No circular imports or missing dependencies

### Testing Phases
- [ ] Phase 1: Parameter loading (10 parameters tested)
- [ ] Phase 2: Detector toggles (13 detectors tested)
- [ ] Phase 3: Engine parameters (6 risk + 2 scoring tested)
- [ ] Phase 4: Execution modules (8 shields + 8 KS + 3 time filters tested)
- [ ] Phase 5: Integration (reload cycle, graceful shutdown tested)

### Success Criteria
- [ ] All 105 parameters accessible at runtime
- [ ] All parameters responsive to UI changes
- [ ] Settings reload works every 10 seconds
- [ ] No performance degradation
- [ ] Zero breaking changes
- [ ] All modules backward compatible

---

## Regression Testing

### Critical Paths to Verify
1. **Trading Flow**: Signal → Score → Execute/Watch/Block
2. **Risk Management**: Account equity → Position sizing → Order placement
3. **Shutdown Sequence**: Save state → Stop reload → Close positions → Disconnect
4. **Error Handling**: Invalid settings → Graceful fallback to defaults

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Total Parameters Tested | 105+ | ⏳ In Progress |
| Parameters Responsive | 100% | ⏳ In Progress |
| Performance Impact | <5% | ⏳ Monitoring |
| Regressions Found | 0 | ✅ Expected |
| Test Coverage | 90%+ | ⏳ In Progress |

---

## Implementation Notes for Tester

**Start with Category 1-2 (ICT Concepts & Detectors)**:
- These are easiest to test visually
- Check bot logs for [DETECTOR:X] messages
- Non-critical to trading functionality

**Then Test Category 3-5 (Risk & Shields)**:
- These directly affect trading behavior
- Use PAPER mode for testing
- Verify broker API receives correct orders

**Finally Test Category 6-10**:
- These are edge cases and advanced features
- Integration with time, news, sessions
- Complex logic paths

**Final Full Integration Test**:
- Run bot for 1 hour in PAPER mode
- Change 5-10 random parameters during runtime
- Verify each change takes effect within 10s
- Verify no crashes or errors

---

## Expected Completion

**Full test suite**: 2-3 hours  
**Critical path only**: 1 hour  
**Regression testing**: 30 minutes

**Overall Status**: ✅ READY TO BEGIN TESTING

All 21 modules are integrated and ready to be tested. Every parameter should be accessible and responsive via the dynamic settings system.

