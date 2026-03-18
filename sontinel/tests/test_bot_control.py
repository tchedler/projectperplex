import sys
import os
# Add the root directory to path to import interface.bot_settings
sys.path.insert(0, os.getcwd())
from interface.bot_settings import start_bot_process, is_bot_running, get_bot_pid, stop_bot_process
import time

print("Testing bot startup mechanism...")
if is_bot_running():
    print("Bot already running, stopping first...")
    stop_bot_process()
    time.sleep(1)

print("Starting bot...")
success = start_bot_process()
print(f"Startup success: {success}")

if success:
    time.sleep(2)
    running = is_bot_running()
    pid = get_bot_pid()
    print(f"Is running verify: {running}")
    print(f"PID tracked: {pid}")
    
    if running:
        print("Stopping bot...")
        stop_bot_process()
        time.sleep(1)
        print(f"Is running after stop: {is_bot_running()}")
else:
    print("Failed to start bot process.")
