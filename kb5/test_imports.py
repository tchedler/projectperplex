#!/usr/bin/env python
"""Quick import test for all detectors"""

import sys
import traceback

detectors = [
    'liquidity_detector.LiquidityDetector',
    'amd_detector.AMDDetector',
    'ote_detector.OTEDetector',
    'displacement_detector.DisplacementDetector',
    'fvg_detector.FVGDetector',
    'ob_detector.OBDetector',
    'smt_detector.SMTDetector',
    'bias_detector.BiasDetector',
    'choch_detector.CHoCHDetector',
    'cisd_detector.CISDDetector',
    'irl_detector.IRLDetector',
    'inducement_detector.InducementDetector',
    'mss_detector.MSSDetector',
    'pa_detector.PADetector',
]

failed = []
success = []

for detector_path in detectors:
    module_name, class_name = detector_path.split('.')
    try:
        module = __import__(f'analysis.{module_name}', fromlist=[class_name])
        cls = getattr(module, class_name)
        success.append(f"✅ {class_name}")
    except Exception as e:
        failed.append(f"❌ {class_name}: {e}")
        traceback.print_exc()

print("\n".join(success))
if failed:
    print("\n".join(failed))
    print(f"\nFailed: {len(failed)}/{len(detectors)}")
    sys.exit(1)
else:
    print(f"\n✅ All {len(detectors)} detectors imported successfully!")
    sys.exit(0)
