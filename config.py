"""Configuration management for MCUtil."""
import json
from pathlib import Path
from typing import Dict, Any


class Config:
    """Manages application configuration."""

    CONFIG_FILE = Path.home() / ".mcutil.json"

    DEFAULTS = {
        "server_dir": str(Path.home() / "minecraft-server"),
        "server_jar": "server.jar",
        "backup_dir": str(Path.home() / "minecraft-backups"),
        "java_memory": "4G",
        "screen_name": "minecraft",
        "backup_retention": 7,
        "backup_interval": 60,  # minutes
        "watchdog_interval": 30,  # seconds
    }

    def __init__(self):
        self.data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create with defaults."""
        if not self.CONFIG_FILE.exists():
            return self.DEFAULTS.copy()

        try:
            with open(self.CONFIG_FILE, 'r') as f:
                config = json.load(f)
            # Merge with defaults to ensure all keys exist
            merged = self.DEFAULTS.copy()
            merged.update(config)
            return merged
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")
            return self.DEFAULTS.copy()

    def save(self) -> bool:
        """Save configuration to file."""
        try:
            self.CONFIG_FILE.parent.mkdir(exist_ok=True)
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value."""
        self.data[key] = value

    def setup_interactive(self):
        """Interactive configuration setup."""
        print("MCUtil Configuration Setup")
        print("=" * 30)

        for key, default in self.DEFAULTS.items():
            current = self.data.get(key, default)
            prompt = f"{key.replace('_', ' ').title()} [{current}]: "

            value = input(prompt).strip()
            if value:
                # Convert to the appropriate type
                if isinstance(default, int):
                    try:
                        value = int(value)
                    except ValueError:
                        print(f"Invalid number, using default: {default}")
                        value = default
                self.data[key] = value

        if self.save():
            print("\nConfiguration saved successfully!")
        else:
            print("\nError saving configuration!")

    def validate(self) -> bool:
        """Validate configuration paths and settings."""
        errors = []

        # Check server directory
        server_dir = Path(self.get("server_dir"))
        if not server_dir.exists():
            errors.append(f"Server directory does not exist: {server_dir}")

        # Check server jar
        server_jar = server_dir / self.get("server_jar")
        if not server_jar.exists():
            errors.append(f"Server jar not found: {server_jar}")

        # Check backup directory is writable
        backup_dir = Path(self.get("backup_dir"))
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            errors.append(f"Cannot create backup directory: {backup_dir}")

        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True
