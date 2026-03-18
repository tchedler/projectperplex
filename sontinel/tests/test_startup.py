import bot_settings
print("Starting bot process...")
res = bot_settings.start_bot_process()
print("Result:", res)
import time
time.sleep(2)
print("Is running?", bot_settings.is_bot_running())
with open("data/bot.pid", "r") as f:
    pid = f.read().strip()
print("PID:", pid)
