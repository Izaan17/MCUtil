import argparse
import json
import os
import subprocess
import sys
import shutil
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Initialize rich console
console = Console()

CONFIG_PATH = os.path.expanduser("~/.mcserverconfig.json")

# === Default Config Template ===
DEFAULT_CONFIG = {
    "SERVER_JAR": "server.jar",
    "SERVER_DIR": os.path.expanduser("~/minecraft-server"),
    "BACKUP_DIR": os.path.expanduser("~/minecraft-backups"),
    "JAVA_OPTIONS": "-Xmx2G -Xms1G",
    "SCREEN_NAME": "minecraft",
    "MAX_BACKUPS": "5",
    "WATCHDOG_INTERVAL": "60",  # Check every minute
    "AUTO_BACKUP_INTERVAL": "720",  # 12 hours in minutes
}

# === Utility Functions ===

def print_header(title):
    console.print(Panel(f"[bold]{title}[/bold]", expand=False))

def print_success(message):
    console.print(f"[bold green]✅ {message}[/bold green]")

def print_warning(message):
    console.print(f"[bold yellow]⚠️ {message}[/bold yellow]")

def print_error(message):
    console.print(f"[bold red]❌ {message}[/bold red]")

def print_info(message):
    console.print(message)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print_error("Config not found. Run 'setup' to create one.")
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    missing = [k for k in DEFAULT_CONFIG if k not in cfg or not cfg[k]]
    if missing:
        print_warning(f"Missing config values: {', '.join(missing)}. Run 'setup' again.")
        sys.exit(1)
    return cfg

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)
    print_success(f"Config saved to {CONFIG_PATH}")

def run_command(command, cwd=None, silent=False):
    try:
        result = subprocess.run(command, shell=True, cwd=cwd,
                                stdout=None if not silent else subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print_error(f"Command failed: {command}")
            if result.stderr:
                print_error(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print_error(f"Exception running command: {e}")
        return False

def screen_session_exists(screen_name):
    result = subprocess.run(f"screen -ls | grep -q '\\.{screen_name}'", shell=True)
    return result.returncode == 0

def validate_config(cfg):
    # Check if directories exist
    for dir_key in ["SERVER_DIR", "BACKUP_DIR"]:
        if not os.path.isdir(cfg[dir_key]):
            try:
                os.makedirs(cfg[dir_key], exist_ok=True)
                print_success(f"Created directory: {cfg[dir_key]}")
            except:
                print_error(f"Cannot access or create directory: {cfg[dir_key]}")
                return False

    # Check if server JAR exists
    jar_path = os.path.join(cfg["SERVER_DIR"], cfg["SERVER_JAR"])
    if not os.path.isfile(jar_path):
        print_warning(f"Server JAR not found: {jar_path}")

    return True

def start_server(cfg):
    print_header("🟢 Starting Minecraft Server")
    if screen_session_exists(cfg["SCREEN_NAME"]):
        print_warning("Server is already running. Use 'status' to check.")
        return

    # Validate config before starting
    if not validate_config(cfg):
        print_warning("Configuration validation failed. Please check your settings.")
        return

    cmd = f'screen -dmS {cfg["SCREEN_NAME"]} java {cfg["JAVA_OPTIONS"]} -jar {cfg["SERVER_JAR"]} nogui'

    if run_command(cmd, cwd=cfg["SERVER_DIR"]):
        print_success("Server started.")
    else:
        print_error("Failed to start server.")

def stop_server(cfg):
    print_header("🔴 Stopping Minecraft Server")
    if not screen_session_exists(cfg["SCREEN_NAME"]):
        print_warning("Server is not running.")
        return

    cmd = f'screen -S {cfg["SCREEN_NAME"]} -X stuff "stop\\n"'
    if run_command(cmd):
        print_success("Stop signal sent. Waiting for server to shut down...")

        # Show progress with rich
        with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]Waiting for server to stop...[/bold green]"),
                console=console
        ) as progress:
            task = progress.add_task("Stopping...", total=30)
            for i in range(30):
                if not screen_session_exists(cfg["SCREEN_NAME"]):
                    break
                progress.update(task, advance=1)
                time.sleep(1)

        if not screen_session_exists(cfg["SCREEN_NAME"]):
            print_success("Server stopped successfully.")
        else:
            print_warning("Server did not stop in time. You may need to force stop it.")
    else:
        print_error("Failed to send stop signal.")

def restart_server(cfg):
    print_header("🔄 Restarting Minecraft Server")
    stop_server(cfg)
    start_server(cfg)

def backup_world(cfg):
    print_header("💾 Creating Full Server Backup")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"server_backup_{timestamp}"
    backup_path = os.path.join(cfg["BACKUP_DIR"], backup_name)

    # List of folders and files you want to include
    include_items = [
        "world", "world_nether", "world_the_end",
        "server.properties", "banned-ips.json", "banned-players.json",
        "ops.json", "whitelist.json", "mods", "config", "scripts", "plugins"
    ]

    try:
        # Ensure backup directory exists
        os.makedirs(cfg["BACKUP_DIR"], exist_ok=True)

        temp_dir = os.path.join(cfg["BACKUP_DIR"], f"_temp_backup_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)

        # Rich progress display for backup process
        with Progress() as progress:
            task = progress.add_task("[green]Backing up server...", total=len(include_items) + 2)

            # Copy items into temporary backup folder
            for item in include_items:
                src = os.path.join(cfg["SERVER_DIR"], item)
                dst = os.path.join(temp_dir, item)
                if os.path.exists(src):
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                else:
                    print_warning(f"Skipping missing item: {item}")
                progress.update(task, advance=1)

            # Create zip file from temp dir
            progress.update(task, description="[yellow]Creating ZIP archive...")
            shutil.make_archive(backup_path, 'zip', temp_dir)
            progress.update(task, advance=1)

            # Clean up
            progress.update(task, description="[yellow]Cleaning up...")
            shutil.rmtree(temp_dir)
            progress.update(task, advance=1)

        print_success(f"Full server backup saved as {backup_path}.zip")

        # Rotate old backups
        max_backups = int(cfg.get("MAX_BACKUPS", 5))
        if max_backups > 0:
            backups = sorted([os.path.join(cfg["BACKUP_DIR"], f) for f in os.listdir(cfg["BACKUP_DIR"])
                              if f.startswith("server_backup_") and f.endswith(".zip")])
            while len(backups) > max_backups:
                oldest = backups.pop(0)
                os.remove(oldest)
                print_info(f"🗑️  Removed old backup: {os.path.basename(oldest)}")

    except Exception as e:
        print_error(f"Backup failed: {e}")

def show_logs(cfg):
    print_header("📜 Latest Server Logs")
    log_path = os.path.join(cfg["SERVER_DIR"], "logs", "latest.log")
    if not os.path.exists(log_path):
        print_error("Log file not found.")
        return

    with open(log_path, 'r') as f:
        log_content = f.read()

    console.print(Panel.fit(log_content, title="Server Log", border_style="blue"))

def show_recent_logs(cfg, lines=20):
    log_path = os.path.join(cfg["SERVER_DIR"], "logs", "latest.log")
    if not os.path.exists(log_path):
        print_error("Log file not found.")
        return

    with open(log_path, 'r') as f:
        all_lines = f.readlines()
        recent = all_lines[-lines:] if len(all_lines) >= lines else all_lines

    for line in recent:
        if "ERROR" in line or "WARN" in line:
            console.print(line.strip(), style="bold red")
        else:
            console.print(line.strip())

def send_command(cfg, cmd):
    print_header("📡 Sending Command")
    if not screen_session_exists(cfg["SCREEN_NAME"]):
        print_warning("Server is not running.")
        return False

    full_cmd = f'screen -S {cfg["SCREEN_NAME"]} -X stuff "{cmd}\\n"'
    success = run_command(full_cmd)
    if success:
        print_success(f"Sent: {cmd}")
    return success

def show_status(cfg):
    print_header("📊 Server Status")

    table = Table(title="Minecraft Server Status")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")

    if screen_session_exists(cfg["SCREEN_NAME"]):
        table.add_row("Status", "[bold green]RUNNING[/bold green]")
        table.add_row("Screen Name", cfg["SCREEN_NAME"])

        # Try to get uptime
        try:
            cmd = f"ps -o etime= -p $(pgrep -f '{cfg['SERVER_JAR']}')"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout.strip():
                table.add_row("Uptime", result.stdout.strip())
        except:
            pass

        # Memory usage
        try:
            cmd = f"ps -o %mem= -p $(pgrep -f '{cfg['SERVER_JAR']}')"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout.strip():
                table.add_row("Memory Usage", f"{result.stdout.strip()}%")
        except:
            pass
    else:
        table.add_row("Status", "[bold red]STOPPED[/bold red]")

    console.print(table)

def setup_config():
    print_header("🛠️  Setup Configuration")

    # First check if config exists, load it as defaults
    existing_config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            existing_config = json.load(f)

    config = {}
    for key, default in DEFAULT_CONFIG.items():
        current = existing_config.get(key, default)

        console.print(f"[cyan]{key}[/cyan] [[yellow]{current}[/yellow]]: ", end="")
        value = input().strip()
        config[key] = value or current

    # Validate directories
    for dir_key in ["SERVER_DIR", "BACKUP_DIR"]:
        if not os.path.isdir(config[dir_key]):
            console.print(f"Directory [yellow]{config[dir_key]}[/yellow] does not exist. Create? [y/N]: ", end="")
            create = input().strip()
            if create.lower() == 'y':
                try:
                    os.makedirs(config[dir_key], exist_ok=True)
                    print_success(f"Created directory: {config[dir_key]}")
                except Exception as e:
                    print_error(f"Error creating directory: {e}")

    save_config(config)

def watch_server(cfg):
    print_header("👀 Starting Server Watchdog")
    check_interval = int(cfg.get("WATCHDOG_INTERVAL", 60))

    print_info(f"Server watchdog started. Checking every {check_interval} seconds.")
    print_info("Press Ctrl+C to stop the watchdog")

    try:
        with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]Monitoring server...[/bold green]"),
                console=console
        ) as progress:
            task = progress.add_task("Checking...", total=None)
            while True:
                if not screen_session_exists(cfg["SCREEN_NAME"]):
                    progress.update(task, description="[bold red]Server offline! Restarting...[/bold red]")
                    start_server(cfg)
                    progress.update(task, description="[bold green]Monitoring server...[/bold green]")
                time.sleep(check_interval)
    except KeyboardInterrupt:
        print_info("\n👋 Watchdog stopped.")

def start_scheduled_backups(cfg):
    print_header("⏰ Starting Scheduled Backups")
    interval_minutes = int(cfg.get("AUTO_BACKUP_INTERVAL", 720))

    print_info(f"Scheduled backups every {interval_minutes} minutes")
    print_info("Press Ctrl+C to stop scheduled backups")

    try:
        while True:
            backup_world(cfg)
            print_info(f"Next backup in {interval_minutes} minutes")

            # Sleep with countdown
            with Progress(
                    TextColumn("[bold blue]Next backup in: [/bold blue]"),
                    console=console
            ) as progress:
                task = progress.add_task("Waiting...", total=interval_minutes)
                for _ in range(interval_minutes):
                    time.sleep(60)  # 1 minute
                    progress.update(task, advance=1)
    except KeyboardInterrupt:
        print_info("\n👋 Scheduled backups stopped.")

def list_players(cfg):
    print_header("👥 Online Players")
    if not screen_session_exists(cfg["SCREEN_NAME"]):
        print_warning("Server is not running.")
        return

    send_command(cfg, "list")
    # Wait for command to execute and return result
    time.sleep(1)
    show_recent_logs(cfg, lines=3)

def show_server_stats(cfg):
    print_header("📊 Server Statistics")
    if not screen_session_exists(cfg["SCREEN_NAME"]):
        print_warning("Server is not running.")
        return

    table = Table(title="Server Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    # Get server process info
    try:
        cmd = f"ps aux | grep [{cfg['SCREEN_NAME']}] | grep java"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.stdout:
            ps_info = result.stdout.strip().split()
            table.add_row("CPU Usage", f"{ps_info[2]}%")
            table.add_row("Memory Usage", f"{ps_info[3]}%")
    except:
        pass

    # Show disk usage
    try:
        du_cmd = f"du -sh {cfg['SERVER_DIR']}/world"
        du_result = subprocess.run(du_cmd, shell=True, capture_output=True, text=True)
        if du_result.stdout:
            table.add_row("World Size", f"{du_result.stdout.strip()}")
    except:
        pass

    console.print(table)

    # Add player count
    print_info("\nPlayer Information:")
    send_command(cfg, "list")
    time.sleep(1)
    show_recent_logs(cfg, lines=3)

def print_caffeinate_help():
    print_header("☕ How to Prevent System Sleep")

    panel = Panel(
        "[bold]To prevent your system from sleeping while running the server:[/bold]\n\n"
        "[cyan]macOS:[/cyan]\n"
        "  caffeinate -s mcutil start\n\n"
        "[cyan]Linux:[/cyan]\n"
        "  systemd-inhibit --what=sleep --why='Minecraft Server' mcutil start\n\n"
        "[cyan]Windows:[/cyan]\n"
        "  1. Open Power Options in Control Panel\n"
        "  2. Select 'High Performance' plan\n"
        "  3. Change plan settings > Change advanced settings\n"
        "  4. Set 'Sleep > Sleep after' to 'Never'\n\n"
        "[yellow]Example for 24/7 operation:[/yellow]\n"
        "  [macOS] caffeinate -s mcutil watch &\n"
        "  [Linux] systemd-inhibit --what=sleep mcutil watch &",
        title="Sleep Prevention Guide",
        border_style="green"
    )
    console.print(panel)

# === Main Function ===

def main():
    parser = argparse.ArgumentParser(description="🧰 Minecraft Server Utility Script")
    subparsers = parser.add_subparsers(dest="action", help="Available commands")

    subparsers.add_parser("setup", help="Create or update configuration")
    subparsers.add_parser("start", help="Start the server")
    subparsers.add_parser("stop", help="Stop the server")
    subparsers.add_parser("restart", help="Restart the server")
    subparsers.add_parser("backup", help="Backup the world folder")
    subparsers.add_parser("logs", help="Print latest logs")
    subparsers.add_parser("status", help="Check if server is running")
    subparsers.add_parser("watch", help="Monitor and auto-restart server if it crashes")
    subparsers.add_parser("schedule-backups", help="Start scheduled backup daemon")
    subparsers.add_parser("players", help="List online players")
    subparsers.add_parser("stats", help="Show server statistics")
    subparsers.add_parser("caffeinate-help", help="Show instructions for preventing system sleep")

    parser_cmd = subparsers.add_parser("cmd", help="Send command to server")
    parser_cmd.add_argument("cmd", help="Command to send (e.g. 'say Hello world')")

    parser_say = subparsers.add_parser("say", help="Broadcast a message to all players")
    parser_say.add_argument("msg", help="Message to send")

    args = parser.parse_args()

    # === Command Dispatcher ===

    if args.action == "setup":
        setup_config()
    elif args.action == "caffeinate-help":
        print_caffeinate_help()
    elif args.action:
        cfg = load_config()
        match args.action:
            case "start": start_server(cfg)
            case "stop": stop_server(cfg)
            case "restart": restart_server(cfg)
            case "backup": backup_world(cfg)
            case "logs": show_logs(cfg)
            case "status": show_status(cfg)
            case "cmd": send_command(cfg, args.cmd)
            case "say": send_command(cfg, f"say {args.msg}")
            case "watch": watch_server(cfg)
            case "schedule-backups": start_scheduled_backups(cfg)
            case "players": list_players(cfg)
            case "stats": show_server_stats(cfg)
    else:
        console.print(Panel.fit(
            "[bold cyan]MCUtil - Minecraft Server Utility[/bold cyan]\n\n"
            "Run [yellow]mcutil setup[/yellow] to configure your server\n"
            "Run [yellow]mcutil start[/yellow] to start the server\n"
            "Run [yellow]mcutil status[/yellow] to check server status\n\n"
            "For sleep prevention use:\n"
            "  [yellow]caffeinate -s mcutil start[/yellow] (macOS)\n"
            "  [yellow]mcutil caffeinate-help[/yellow] for more info",
            title="Welcome to MCUtil", border_style="green"
        ))
        parser.print_help()

if __name__ == "__main__":
    main()