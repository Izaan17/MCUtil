import os
import time
from datetime import datetime

from rich.progress import Progress, TextColumn, SpinnerColumn
from rich.table import Table

from backup import get_backup_stats, format_size
from server import screen_session_exists, start_server, run_command
from utils import print_info, print_header, print_success, print_warning, print_error


def watch_server(cfg):
    """Monitor server and restart if it crashes"""
    print_header("Server Watchdog")
    interval = int(cfg.get("WATCHDOG_INTERVAL", 60))
    print_info(f"Monitoring every {interval} seconds. Press Ctrl+C to stop.")
    try:
        with Progress(SpinnerColumn(), TextColumn("[green]Watching server..."), console=None) as progress:
            task = progress.add_task("watching", total=None)
            while True:
                if not screen_session_exists(cfg["SCREEN_NAME"]):
                    progress.update(task, description="[red]Server offline! Restarting...[/red]")
                    start_server(cfg)
                time.sleep(interval)
    except KeyboardInterrupt:
        print_info("Watchdog stopped.")


def create_scheduler_script(cfg):
    """Create the backup scheduler script"""
    regular_interval = int(cfg.get("AUTO_BACKUP_REGULAR_INTERVAL", 240))
    medium_interval = int(cfg.get("AUTO_BACKUP_MEDIUM_INTERVAL", 1440))
    hard_interval = int(cfg.get("AUTO_BACKUP_HARD_INTERVAL", 10080))

    script_content = f'''#!/usr/bin/env python3
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

# Add the script directory to Python path so we can import our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from backup import backup_world
    from utils import print_info, print_success, print_error
except ImportError as e:
    print(f"Error importing modules: {{e}}")
    print("Make sure this script is in the same directory as backup.py and utils.py")
    sys.exit(1)

CONFIG_PATH = Path.home() / ".mcserverconfig.json"

def load_config():
    with CONFIG_PATH.open() as f:
        return json.load(f)

def main():
    print("=" * 50)
    print("MCUtil Multi-Type Backup Scheduler Started")
    print("=" * 50)
    
    cfg = load_config()
    
    # Convert intervals to seconds
    regular_interval = {regular_interval} * 60
    medium_interval = {medium_interval} * 60
    hard_interval = {hard_interval} * 60
    
    print(f"Schedule:")
    print(f"  Regular backups: every {{regular_interval//60}} minutes ({{{regular_interval//3600:.1f}}}h)")
    print(f"  Medium backups:  every {{medium_interval//60}} minutes ({{{medium_interval//3600:.1f}}}h)")
    print(f"  Hard backups:    every {{hard_interval//60}} minutes ({{{hard_interval//3600//24:.1f}}}d)")
    print()
    
    # Track last backup times
    last_regular = 0
    last_medium = 0  
    last_hard = 0
    
    try:
        while True:
            current_time = time.time()
            
            # Check regular backups
            if current_time - last_regular >= regular_interval:
                print(f"[{{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}] Running regular backup...")
                if backup_world(cfg, "regular"):
                    print_success("Regular backup completed")
                else:
                    print_error("Regular backup failed")
                last_regular = current_time
                
            # Check medium backups  
            if current_time - last_medium >= medium_interval:
                print(f"[{{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}] Running medium backup...")
                if backup_world(cfg, "medium"):
                    print_success("Medium backup completed")
                else:
                    print_error("Medium backup failed")
                last_medium = current_time
                
            # Check hard backups
            if current_time - last_hard >= hard_interval:
                print(f"[{{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}] Running hard backup...")
                if backup_world(cfg, "hard"):
                    print_success("Hard backup completed")
                else:
                    print_error("Hard backup failed")
                last_hard = current_time
                
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print()
        print("Backup scheduler stopped by user")
    except Exception as e:
        print_error(f"Scheduler error: {{e}}")

if __name__ == "__main__":
    main()
'''
    return script_content


def start_scheduled_backups(cfg):
    """Start the multi-type backup scheduler in screen"""
    screen_name = cfg.get("BACKUP_SCHEDULER_SCREEN", "mcutil-backups")

    if screen_session_exists(screen_name):
        print_warning(f"Backup scheduler already running in screen '{{screen_name}}'")
        print_info("Use 'mcutil backup-status' to check status")
        print_info("Use 'mcutil stop-backups' to stop the scheduler")
        return

    print_header("Starting Backup Scheduler")

    # Get intervals (in minutes)
    regular_interval = int(cfg.get("AUTO_BACKUP_REGULAR_INTERVAL", 240))
    medium_interval = int(cfg.get("AUTO_BACKUP_MEDIUM_INTERVAL", 1440))
    hard_interval = int(cfg.get("AUTO_BACKUP_HARD_INTERVAL", 10080))

    print_info(f"Schedule configuration:")
    print_info(f"  Regular backups: every {regular_interval} minutes ({regular_interval//60}h)")
    print_info(f"  Medium backups:  every {medium_interval} minutes ({medium_interval//60}h)")
    print_info(f"  Hard backups:    every {hard_interval} minutes ({hard_interval//60//24}d)")

    # Create the scheduler script
    script_content = create_scheduler_script(cfg)

    # Save scheduler script in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scheduler_script_path = os.path.join(script_dir, "backup_scheduler.py")

    try:
        with open(scheduler_script_path, 'w') as f:
            f.write(script_content)
        os.chmod(scheduler_script_path, 0o755)  # Make executable
    except Exception as e:
        print_error(f"Failed to create scheduler script: {e}")
        return

    # Start in screen
    cmd = f'screen -dmS {screen_name} python3 "{scheduler_script_path}"'
    if run_command(cmd):
        print_success(f"Backup scheduler started in screen '{screen_name}'")
        print_info("Commands:")
        print_info("  mcutil backup-status  - Check scheduler status")
        print_info("  mcutil stop-backups   - Stop the scheduler")
        print_info(f"  screen -r {screen_name} - Attach to scheduler (Ctrl+A+D to detach)")
    else:
        print_error("Failed to start backup scheduler")
        # Clean up the script file
        try:
            os.remove(scheduler_script_path)
        except:
            pass


def stop_scheduled_backups(cfg):
    """Stop the backup scheduler"""
    screen_name = cfg.get("BACKUP_SCHEDULER_SCREEN", "mcutil-backups")

    if not screen_session_exists(screen_name):
        print_warning("Backup scheduler is not running")
        return

    print_header("Stopping Backup Scheduler")
    cmd = f'screen -S {screen_name} -X quit'
    if run_command(cmd):
        print_success("Backup scheduler stopped")

        # Clean up the scheduler script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scheduler_script_path = os.path.join(script_dir, "backup_scheduler.py")
        try:
            if os.path.exists(scheduler_script_path):
                os.remove(scheduler_script_path)
        except:
            pass
    else:
        print_error("Failed to stop backup scheduler")


def backup_scheduler_status(cfg):
    """Show backup scheduler status and recent backup information"""
    screen_name = cfg.get("BACKUP_SCHEDULER_SCREEN", "mcutil-backups")

    print_header("Backup System Status")

    # Check if scheduler is running
    if screen_session_exists(screen_name):
        print_success(f"Backup scheduler is RUNNING in screen '{screen_name}'")

        # Show intervals
        regular_interval = int(cfg.get("AUTO_BACKUP_REGULAR_INTERVAL", 240))
        medium_interval = int(cfg.get("AUTO_BACKUP_MEDIUM_INTERVAL", 1440))
        hard_interval = int(cfg.get("AUTO_BACKUP_HARD_INTERVAL", 10080))

        print_info(f"Schedule:")
        print_info(f"  Regular: every {regular_interval} minutes ({regular_interval//60}h)")
        print_info(f"  Medium:  every {medium_interval} minutes ({medium_interval//60}h)")
        print_info(f"  Hard:    every {hard_interval} minutes ({hard_interval//60//24}d)")
        print_info("")

    else:
        print_warning("Backup scheduler is NOT running")
        print_info("Use 'mcutil schedule-backups' to start the scheduler")
        print_info("")

    # Show backup statistics
    stats = get_backup_stats(cfg)

    table = Table(title="Backup Statistics")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Total Size", style="yellow")
    table.add_column("Latest Backup", style="magenta")

    for backup_type, stat in stats.items():
        latest_str = "Never"
        if stat["latest"] > 0:
            latest_time = datetime.fromtimestamp(stat["latest"])
            latest_str = latest_time.strftime("%Y-%m-%d %H:%M")

        table.add_row(
            backup_type.capitalize(),
            str(stat["count"]),
            format_size(stat["total_size"]),
            latest_str
        )

    from rich.console import Console
    console = Console()
    console.print(table)

    print_info("")
    print_info("Commands:")
    print_info("  mcutil backup --type [regular|medium|hard]  - Manual backup")
    if screen_session_exists(screen_name):
        print_info(f"  screen -r {screen_name}                      - View scheduler logs")
        print_info("  mcutil stop-backups                         - Stop scheduler")
    else:
        print_info("  mcutil schedule-backups                     - Start scheduler")