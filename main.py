import argparse

from backup import backup_world, list_backup_types
from config import load_config, save_config, DEFAULT_CONFIG
from monitor import watch_server, start_scheduled_backups, stop_scheduled_backups, backup_scheduler_status
from server import start_server, stop_server, restart_server, send_command, show_status
from utils import print_header


def setup_config():
    print_header("Setup Configuration")
    print("Setting up MCUtil configuration...")
    print("Press Enter to use default values shown in brackets.")
    print()

    config = {}
    for key, default in DEFAULT_CONFIG.items():
        if key.startswith("AUTO_BACKUP_") and key.endswith("_INTERVAL"):
            # Format backup interval descriptions
            backup_type = key.replace("AUTO_BACKUP_", "").replace("_INTERVAL", "").lower()
            hours = int(default) // 60
            days = hours // 24
            if days > 0:
                time_desc = f"{days} day{'s' if days != 1 else ''}"
            else:
                time_desc = f"{hours} hour{'s' if hours != 1 else ''}"
            prompt = f"{backup_type.capitalize()} backup interval - minutes [{default} = {time_desc}]: "
        elif key.startswith("MAX_") and key.endswith("_BACKUPS"):
            backup_type = key.replace("MAX_", "").replace("_BACKUPS", "").lower()
            prompt = f"Max {backup_type} backups to keep [{default}]: "
        else:
            prompt = f"{key} [{default}]: "

        value = input(prompt).strip()
        config[key] = value or default

    save_config(config)
    print()
    print("Configuration complete! You can now use MCUtil commands.")


def main():
    parser = argparse.ArgumentParser(description="Minecraft Server Utility")
    subparsers = parser.add_subparsers(dest="action")

    # Setup command
    subparsers.add_parser("setup", help="Setup configuration")

    # Server control commands
    start_parser = subparsers.add_parser("start", help="Start the server")
    start_parser.add_argument("--gui", action="store_true", help="Start with GUI")
    start_parser.add_argument("--ram", help="RAM override (e.g. 2G)")

    restart_parser = subparsers.add_parser("restart", help="Restart the server")
    restart_parser.add_argument("--gui", action="store_true", help="Restart with GUI")
    restart_parser.add_argument("--ram", help="RAM override")

    subparsers.add_parser("stop", help="Stop the server")
    subparsers.add_parser("status", help="Show server status")

    # Backup commands
    backup_parser = subparsers.add_parser("backup", help="Backup the server")
    backup_parser.add_argument("--type",
                               choices=["regular", "medium", "hard"],
                               default="regular",
                               help="Backup type: regular (standard), medium (comprehensive), hard (complete)")
    backup_parser.add_argument("--include", help="Items to include (comma-separated, overrides type)")
    backup_parser.add_argument("--exclude", help="Items to exclude from the selected type")

    subparsers.add_parser("backup-types", help="List available backup types and their contents")

    # Enhanced backup scheduler commands
    subparsers.add_parser("schedule-backups", help="Start automatic multi-type backup scheduler")
    subparsers.add_parser("stop-backups", help="Stop automatic backup scheduler")
    subparsers.add_parser("backup-status", help="Show backup scheduler status and statistics")

    # Monitoring commands
    subparsers.add_parser("watch", help="Start server watchdog")

    # Server command
    cmd_parser = subparsers.add_parser("cmd", help="Send command to server")
    cmd_parser.add_argument("command", help="Command to send")

    args = parser.parse_args()

    if args.action == "setup":
        setup_config()
    elif args.action == "backup-types":
        list_backup_types()
    else:
        cfg = load_config()
        match args.action:
            case "start":
                start_server(cfg, gui=args.gui, ram=args.ram)
            case "stop":
                stop_server(cfg)
            case "restart":
                restart_server(cfg, gui=args.gui, ram=args.ram)
            case "status":
                show_status(cfg)
            case "backup":
                backup_world(cfg,
                             backup_type=args.type,
                             include_list=args.include,
                             exclude_list=args.exclude)
            case "watch":
                watch_server(cfg)
            case "schedule-backups":
                start_scheduled_backups(cfg)
            case "stop-backups":
                stop_scheduled_backups(cfg)
            case "backup-status":
                backup_scheduler_status(cfg)
            case "cmd":
                send_command(cfg, args.command)
            case _:
                parser.print_help()


if __name__ == "__main__":
    main()