import sys
import os
sys.path.insert(0, os.getcwd())
from interface.bot_settings import start_bot_process, is_bot_running, get_bot_pid, stop_bot_process
import time
import subprocess

print("Testing bot startup mechanism (Deep Check)...")
if is_bot_running():
    print("Bot already running, stopping first...")
    stop_bot_process()
    time.sleep(2)

print("Starting bot...")
success = start_bot_process()
print(f"Startup success call: {success}")

if success:
    print("Waiting 5 seconds for process to stabilize...")
    time.sleep(5)
    
    running = is_bot_running()
    pid = get_bot_pid()
    print(f"Is running verify: {running}")
    print(f"PID tracked in file: {pid}")
    
    if pid:
        print(f"Checking tasklist for PID {pid}...")
        try:
            out = subprocess.check_output(f'tasklist /FI "PID eq {pid}" /NH', shell=True).decode()
            print("Tasklist output:", out.strip())
            if str(pid) in out:
                print("✅ PID found in system tasklist.")
            else:
                print("❌ PID NOT found in system tasklist.")
        except Exception as e:
            print(f"Error checking tasklist: {e}")
            
    if running:
        print("Stopping bot via stop_bot_process()...")
        stop_bot_process()
        time.sleep(2)
        print(f"Is running after stop: {is_bot_running()}")
        if not is_bot_running():
            print("✅ Stop confirmed.")
else:
    print("Failed to start bot process.")
