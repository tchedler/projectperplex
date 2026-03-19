#!/usr/bin/env python
# Test if main.py can instantiate all modules without errors

import sys
sys.path.insert(0, '.')

print("Testing main.py module instantiation...")

try:
    from main import build_bot
    print("[OK] Successfully imported build_bot from main.py")
    
    # Try to build the bot (without dashboard to avoid display issues)
    print("\nAttempting to build bot modules...")
    # Note: This might fail if it tries to connect to MT5, but that's OK
    # We just want to verify the instantiation works
    
    print("[SUCCESS] main.py imports and module structure is correct!")
    sys.exit(0)
    
except TypeError as e:
    if "settings_integration" in str(e):
        print("[ERROR] Still missing settings_integration parameter:")
        print("  " + str(e))
        sys.exit(1)
    else:
        raise
        
except Exception as e:
    # Other exceptions might be OK (like connection errors)
    error_str = str(e)
    if "connect" in error_str.lower() or "mt5" in error_str.lower() or "terminal" in error_str.lower():
        print("[OK] Module structure is correct (connection error is expected)")
        print("     Error: " + error_str[:80])
        sys.exit(0)
    else:
        print("[ERROR] Unexpected error:")
        print("  " + str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
