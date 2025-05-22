import signal
import time
from datetime import datetime
from pathlib import Path

from backup import BackupManager
from config import Config
from utils import screen_exists, run_command, print_status


class BackupScheduler:
    """Simple backup scheduler that runs in the background."""

    def __init__(self, config):
        self.config = config
        self.backup_manager = BackupManager(config)
        self.running = False
        self.interval = config.get("backup_interval", 60) * 60  # Convert minutes to seconds
        self.last_backup = None
        self.scheduler_start_time = None

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, _, __):
        """Handle shutdown signals."""
        print_status("\nShutdown signal received, stopping scheduler...", "info")
        self.running = False

    def start(self):
        """Start the backup scheduler."""
        print_status("Starting backup scheduler", "info")
        print_status(f"Backup interval: {self.interval // 60} minutes", "info")
        print_status("Press Ctrl+C to stop", "info")

        self.running = True
        self.scheduler_start_time = time.time()

        # Do an initial backup
        print_status("Creating initial backup...", "info")
        self._create_backup()

        # Main scheduler loop
        while self.running:
            try:
                # Show the next backup time
                if self.last_backup:
                    next_backup_time = datetime.fromtimestamp(self.last_backup + self.interval)
                    time_until_next = int((self.last_backup + self.interval) - time.time())

                    if time_until_next > 0:
                        hours, remainder = divmod(time_until_next, 3600)
                        minutes, seconds = divmod(remainder, 60)

                        print_status(
                            f"Next backup at {next_backup_time.strftime('%H:%M:%S')} "
                            f"(in {hours}h {minutes}m {seconds}s)",
                            "info"
                        )

                # Sleep in small chunks so we can respond to signals faster
                for _ in range(60):  # 60 seconds total, 1-second chunks
                    if not self.running:
                        break
                    time.sleep(1)

                if self.running and self._should_backup():
                    print_status("Time for scheduled backup", "info")
                    self._create_backup()

            except KeyboardInterrupt:
                print_status("\nKeyboard interrupt received", "info")
                self.running = False
                break

        print_status("Backup scheduler stopped", "info")

    def _should_backup(self) -> bool:
        """Check if it's time for a backup."""
        if self.last_backup is None:
            return True

        time_since_backup = time.time() - self.last_backup
        return time_since_backup >= self.interval

    def _create_backup(self):
        """Create a scheduled backup."""
        try:
            backup_path = self.backup_manager.create_backup(
                "quick",
                custom_name=f"scheduled_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            if backup_path:
                self.last_backup = time.time()
                print_status(f"Scheduled backup completed: {backup_path.name}", "success")
            else:
                print_status("Scheduled backup failed", "error")
        except Exception as e:
            print_status(f"Backup error: {e}", "error")


def start_scheduler():
    """Start the backup scheduler in the background using the screen."""
    screen_name = "mcutil-scheduler"

    if screen_exists(screen_name):
        print_status("Backup scheduler is already running", "warning")
        print_status(f"Use 'screen -r {screen_name}' to view or 'mcutil scheduler stop' to stop", "info")
        return False

    # Create a simple scheduler script with timestamp tracking
    script_content = f'''#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from scheduler import BackupScheduler

# Track scheduler start time
SCHEDULER_STATE_FILE = Path.home() / ".mcutil_scheduler_state.json"

def save_scheduler_state(start_time):
    """Save scheduler state to file."""
    try:
        with open(SCHEDULER_STATE_FILE, 'w') as f:
            json.dump({{"start_time": start_time}}, f)
    except:
        pass

def cleanup_scheduler_state():
    """Remove scheduler state file."""
    try:
        if SCHEDULER_STATE_FILE.exists():
            SCHEDULER_STATE_FILE.unlink()
    except:
        pass

if __name__ == "__main__":
    config = Config()
    scheduler = BackupScheduler(config)
    
    # Save start time
    import time
    save_scheduler_state(time.time())
    
    try:
        scheduler.start()
    finally:
        cleanup_scheduler_state()
'''

    # Save scheduler script
    script_path = Path(__file__).parent / "run_scheduler.py"
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        script_path.chmod(0o755)
    except Exception as e:
        print_status(f"Failed to create scheduler script: {e}", "error")
        return False

    # Start in screen
    cmd = f'screen -dmS {screen_name} python3 "{script_path}"'
    if run_command(cmd):
        print_status(f"Backup scheduler started in screen '{screen_name}'", "success")
        print_status(f"View with: screen -r {screen_name}", "info")
        print_status("Stop with: mcutil scheduler stop", "info")
        return True
    else:
        print_status("Failed to start backup scheduler", "error")
        # Clean up the script
        script_path.unlink(missing_ok=True)
        return False


def stop_scheduler():
    """Stop the backup scheduler."""
    screen_name = "mcutil-scheduler"

    if not screen_exists(screen_name):
        print_status("Backup scheduler is not running", "warning")
        return False

    # Send quit signal to the screen
    cmd = f'screen -S {screen_name} -X quit'
    if run_command(cmd):
        print_status("Backup scheduler stopped", "success")

        # Clean up the scheduler script
        script_path = Path(__file__).parent / "run_scheduler.py"
        script_path.unlink(missing_ok=True)

        # Clean up the state file
        state_file = Path.home() / ".mcutil_scheduler_state.json"
        state_file.unlink(missing_ok=True)

        return True
    else:
        print_status("Failed to stop backup scheduler", "error")
        return False


def scheduler_status():
    """Show scheduler status with the next backup time."""
    screen_name = "mcutil-scheduler"

    print("\nBackup Scheduler Status")
    print("=" * 30)

    if screen_exists(screen_name):
        print_status("Scheduler: RUNNING", "success")
        print_status(f"Screen session: {screen_name}", "info")
        print_status(f"View logs: screen -r {screen_name}", "info")

        # Try to calculate the next backup time
        config = Config()
        interval = config.get("backup_interval", 60) * 60  # Convert to seconds

        # Check for scheduler state file
        state_file = Path.home() / ".mcutil_scheduler_state.json"
        if state_file.exists():
            try:
                import json
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    start_time = state.get("start_time")

                if start_time:
                    # Get the most recent backup
                    backup_manager = BackupManager(config)
                    backups = backup_manager.list_backups()

                    if backups:
                        # Find the most recent scheduled backup
                        scheduled_backups = [b for b in backups if 'scheduled_' in b.get('custom_name', '')]
                        if scheduled_backups:
                            latest_backup = scheduled_backups[0]  # Already sorted by date
                            last_backup_time = latest_backup['created_datetime'].timestamp()
                            next_backup_time = datetime.fromtimestamp(last_backup_time + interval)
                            time_until_next = int((last_backup_time + interval) - time.time())

                            if time_until_next > 0:
                                hours, remainder = divmod(time_until_next, 3600)
                                minutes, _ = divmod(remainder, 60)

                                print_status(
                                    f"Next backup: {next_backup_time.strftime('%Y-%m-%d %H:%M:%S')} "
                                    f"(in {hours}h {minutes}m)",
                                    "info"
                                )
                        else:
                            # If no scheduled backups yet, assume next is interval from start
                            next_backup_time = datetime.fromtimestamp(start_time + interval)
                            time_until_next = int((start_time + interval) - time.time())

                            if time_until_next > 0:
                                hours, remainder = divmod(time_until_next, 3600)
                                minutes, _ = divmod(remainder, 60)

                                print_status(
                                    f"Next backup: {next_backup_time.strftime('%Y-%m-%d %H:%M:%S')} "
                                    f"(in {hours}h {minutes}m)",
                                    "info"
                                )
            except:
                pass

        print_status(f"Backup interval: {config.get('backup_interval', 60)} minutes", "info")
    else:
        print_status("Scheduler: STOPPED", "error")
        print_status("Start with: mcutil scheduler start", "info")

    # Show backup stats
    config = Config()
    backup_manager = BackupManager(config)
    stats = backup_manager.get_backup_stats()

    print(f"\nBackup Statistics")
    print(f"Total backups: {stats['total_backups']}")
    print(f"Total size: {stats['total_size_formatted']}")
    if stats['latest_backup']:
        print(f"Latest backup: {stats['latest_backup'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backup directory: {stats['backup_dir']}")


if __name__ == "__main__":
    # This allows running the scheduler directly for testing
    config = Config()
    scheduler = BackupScheduler(config)
    scheduler.start()
