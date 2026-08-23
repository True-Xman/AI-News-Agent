import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def check_env():
    keys = ["GOOGLE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL_ID"]
    status = {}
    for k in keys:
        val = os.environ.get(k)
        status[k] = bool(val and len(val.strip()) > 0)
    return status

if __name__ == "__main__":
    env_status = check_env()
    print("ENVIRONMENT_CHECK:", env_status)
