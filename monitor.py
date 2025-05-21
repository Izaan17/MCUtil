import time

from rich.progress import Progress, TextColumn, TimeRemainingColumn, SpinnerColumn

from backup import backup_world
from server import screen_session_exists, start_server
from utils import print_info, print_header


def watch_server(cfg):
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


def start_scheduled_backups(cfg):
    interval_minutes = int(cfg.get("AUTO_BACKUP_INTERVAL", 720))
    print_header("Scheduled Backups")
    print_info(f"Running every {interval_minutes} minutes. Ctrl+C to cancel.")
    try:
        while True:
            backup_world(cfg)
            with Progress(TextColumn("[blue]Next backup in:"), TimeRemainingColumn()) as progress:
                task = progress.add_task("waiting", total=interval_minutes * 60)
                for _ in range(interval_minutes * 60):
                    time.sleep(1)
                    progress.update(task, advance=1)
    except KeyboardInterrupt:
        print_info("Scheduled backups stopped.")
