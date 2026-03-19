#!/usr/bin/env python
# Quick test to verify BiasDetector instantiation with settings_integration

import sys
sys.path.insert(0, '.')

from datastore.data_store import DataStore
from config.settings_integration import SettingsIntegration
from analysis.fvg_detector import FVGDetector
from analysis.ob_detector import OBDetector
from analysis.bias_detector import BiasDetector

print("Testing BiasDetector instantiation...")

try:
    ds = DataStore()
    si = SettingsIntegration()
    
    # Create FVG and OB detectors first (dependencies)
    fvg = FVGDetector(data_store=ds, settings_integration=si)
    print("[OK] FVGDetector instantiated")
    
    ob = OBDetector(data_store=ds, settings_integration=si)
    print("[OK] OBDetector instantiated")
    
    # Now BiasDetector with settings_integration
    bias = BiasDetector(
        data_store=ds,
        fvg_detector=fvg,
        ob_detector=ob,
        settings_integration=si
    )
    print("[OK] BiasDetector instantiated with settings_integration")
    
    # Verify it's callable
    result = bias.analyze_pair("EURUSD")
    print("[OK] BiasDetector.analyze_pair() works - returned: " + type(result).__name__)
    
    print("\n[SUCCESS] ALL TESTS PASSED!")
    sys.exit(0)
    
except Exception as e:
    print("\n[ERROR] TEST FAILED: " + str(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)
