import argparse

from backup import backup_world, list_backup_types
from config import load_config, save_config, DEFAULT_CONFIG
from monitor import watch_server, start_scheduled_backups
from server import start_server, stop_server, restart_server, send_command, show_status
from utils import print_header


def setup_config():
    print_header("Setup Configuration")
    config = {}
    for key, default in DEFAULT_CONFIG.items():
        value = input(f"{key} [{default}]: ").strip()
        config[key] = value or default
    save_config(config)


def main():
    parser = argparse.ArgumentParser(description="Minecraft Server Utility")
    subparsers = parser.add_subparsers(dest="action")

    subparsers.add_parser("setup", help="Setup configuration")

    start_parser = subparsers.add_parser("start", help="Start the server")
    start_parser.add_argument("--gui", action="store_true")
    start_parser.add_argument("--ram", help="RAM override (e.g. 2G)")

    restart_parser = subparsers.add_parser("restart", help="Restart the server")
    restart_parser.add_argument("--gui", action="store_true")
    restart_parser.add_argument("--ram", help="RAM override")

    subparsers.add_parser("stop", help="Stop the server")
    subparsers.add_parser("status", help="Show server status")

    backup_parser = subparsers.add_parser("backup", help="Backup the server")
    backup_parser.add_argument("--type",
                               choices=["regular", "medium", "hard"],
                               default="regular",
                               help="Backup type: soft (minimal), regular (standard), medium (comprehensive), hard (complete)")
    backup_parser.add_argument("--include", help="Items to include (comma-separated, overrides type)")
    backup_parser.add_argument("--exclude", help="Items to exclude from the selected type")
    backup_parser.add_argument("--compress", help="Compression level 0-9 (0=fastest, 9=smallest)")

    subparsers.add_parser("backup-types", help="List available backup types and their contents")

    subparsers.add_parser("watch", help="Start server watchdog")
    subparsers.add_parser("schedule-backups", help="Run automatic backups")

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
                             exclude_list=args.exclude,
                             compression_level=args.compress)
            case "watch":
                watch_server(cfg)
            case "schedule-backups":
                start_scheduled_backups(cfg)
            case "cmd":
                send_command(cfg, args.command)
            case _:
                parser.print_help()


if __name__ == "__main__":
    main()