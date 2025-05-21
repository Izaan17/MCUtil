import json
from pathlib import Path

from utils import print_error, print_success, print_warning

CONFIG_PATH = Path.home() / ".mcserverconfig.json"

DEFAULT_CONFIG = {"SERVER_JAR": "server.jar", "SERVER_DIR": str(Path.home() / "minecraft-server"),
    "BACKUP_DIR": str(Path.home() / "minecraft-backups"), "JAVA_OPTIONS": "-Xmx2G -Xms1G", "SCREEN_NAME": "minecraft",
    "MAX_BACKUPS": "5", "WATCHDOG_INTERVAL": "60", "AUTO_BACKUP_INTERVAL": "720", }


def load_config():
    if not CONFIG_PATH.exists():
        print_error("Config not found. Run 'setup' to create one.")
        exit(1)
    with CONFIG_PATH.open() as f:
        cfg = json.load(f)
    missing = [k for k in DEFAULT_CONFIG if k not in cfg or not cfg[k]]
    if missing:
        print_warning(f"Missing config values: {', '.join(missing)}. Run 'setup' again.")
        exit(1)
    return cfg


def save_config(cfg):
    with CONFIG_PATH.open("w") as f:
        json.dump(cfg, f, indent=4)
    print_success("Configuration saved.")
