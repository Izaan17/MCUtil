"""
MCUtil - Simple Minecraft Server Manager

A clean, reliable tool for managing Minecraft servers with automated backups.
"""

import argparse
import sys

from backup import BackupManager
from config import Config
from scheduler import start_scheduler, stop_scheduler, scheduler_status
from server import MinecraftServer
from utils import print_status, confirm


def cmd_setup():
    """Setup MCUtil configuration."""
    config = Config()
    config.setup_interactive()


def cmd_server(args):
    """Handle server commands."""
    config = Config()

    if not config.validate():
        print_status("Configuration is invalid. Run 'mcutil setup' first.", "error")
        return False

    server = MinecraftServer(config)

    if args.server_action == "start":
        return server.start(gui=args.gui, memory=args.memory)
    elif args.server_action == "stop":
        return server.stop()
    elif args.server_action == "restart":
        return server.restart(gui=args.gui, memory=args.memory)
    elif args.server_action == "status":
        server.print_status()
        return True
    elif args.server_action == "watch":
        server.watch()
        return True
    return None


def cmd_backup(args):
    """Handle backup commands."""
    config = Config()

    if not config.validate():
        print_status("Configuration is invalid. Run 'mcutil setup' first.", "error")
        return False

    backup_manager = BackupManager(config)

    if args.backup_action == "create":
        backup_path = backup_manager.create_backup(
            backup_type=args.type,
            custom_name=args.name
        )
        return backup_path is not None

    elif args.backup_action == "list":
        backup_manager.print_backup_list()
        return True

    elif args.backup_action == "delete":
        if not args.name:
            print_status("Backup name is required for delete", "error")
            return False

        # Confirm deletion
        if confirm(f"Delete backup '{args.name}'?"):
            return backup_manager.delete_backup(args.name)
        else:
            print_status("Deletion cancelled", "info")
            return True

    elif args.backup_action == "info":
        backup_manager.print_backup_list()
        stats = backup_manager.get_backup_stats()

        print("\nBackup Statistics")
        print("=" * 20)
        print(f"Total backups: {stats['total_backups']}")
        print(f"Quick backups: {stats['quick_backups']}")
        print(f"Full backups: {stats['full_backups']}")
        print(f"Total size: {stats['total_size_formatted']}")
        if stats['latest_backup']:
            print(f"Latest: {stats['latest_backup'].strftime('%Y-%m-%d %H:%M:%S')}")

        return True
    return None


def cmd_scheduler(args):
    """Handle scheduler commands."""
    config = Config()

    if not config.validate():
        print_status("Configuration is invalid. Run 'mcutil setup' first.", "error")
        return False

    if args.scheduler_action == "start":
        return start_scheduler()
    elif args.scheduler_action == "stop":
        return stop_scheduler()
    elif args.scheduler_action == "status":
        scheduler_status()
        return True
    return None


def cmd_send(args):
    """Send command to the server."""
    config = Config()

    if not config.validate():
        print_status("Configuration is invalid. Run 'mcutil setup' first.", "error")
        return False

    server = MinecraftServer(config)
    return server.send_command(args.command)


def cmd_config(args):
    """Handle configuration commands."""
    config = Config()

    if args.config_action == "show":
        print("\nCurrent Configuration")
        print("=" * 25)
        for key, value in config.data.items():
            print(f"{key}: {value}")
        return True

    elif args.config_action == "set":
        if not args.key or not args.value:
            print_status("Both key and value are required", "error")
            return False

        config.set(args.key, args.value)
        if config.save():
            print_status(f"Set {args.key} = {args.value}", "success")
            return True
        else:
            print_status("Failed to save configuration", "error")
            return False

    elif args.config_action == "validate":
        if config.validate():
            print_status("Configuration is valid", "success")
            return True
        else:
            return False
    return None


def print_help():
    """Print help information."""
    help_text = """
MCUtil - Simple Minecraft Server Manager

SETUP:
  mcutil setup                 Interactive configuration setup

SERVER:
  mcutil start                 Start the server
  mcutil start --gui           Start with GUI
  mcutil start --memory 8G     Start with custom memory
  mcutil stop                  Stop the server
  mcutil restart               Restart the server
  mcutil status                Show server status
  mcutil watch                 Auto-restart if crashed
  mcutil send "command"        Send command to server

BACKUPS:
  mcutil backup                Create quick backup
  mcutil backup --type full    Create full backup
  mcutil backup --name myname  Create backup with custom name
  mcutil backup list           List all backups
  mcutil backup delete name    Delete a backup
  mcutil backup info           Show backup statistics

SCHEDULER:
  mcutil scheduler start       Start automatic backups
  mcutil scheduler stop        Stop automatic backups
  mcutil scheduler status      Show scheduler status

CONFIGURATION:
  mcutil config show           Show current configuration
  mcutil config set key value Set configuration value
  mcutil config validate      Validate configuration

Examples:
  mcutil setup                 # First-time setup
  mcutil start                 # Start server
  mcutil scheduler start       # Enable auto-backups
  mcutil backup --type full    # Manual full backup
  mcutil send "say Hello!"     # Send chat message
"""
    print(help_text)


def main():
    """Main entry point."""
    if len(sys.argv) == 1:
        print_help()
        return

    parser = argparse.ArgumentParser(
        description="MCUtil - Simple Minecraft Server Manager",
        add_help=False
    )

    # Add custom help
    parser.add_argument('-h', '--help', action='store_true', help='Show this help message')

    subparsers = parser.add_subparsers(dest='command')

    # Setup command
    subparsers.add_parser('setup', help='Setup configuration')

    # Server commands
    server_parser = subparsers.add_parser('server', help='Server management')
    server_parser.add_argument('server_action', choices=['start', 'stop', 'restart', 'status', 'watch'])
    server_parser.add_argument('--gui', action='store_true', help='Start with GUI')
    server_parser.add_argument('--memory', help='Override memory setting (e.g., 8G)')

    # Shorthand server commands
    start_parser = subparsers.add_parser('start', help='Start server')
    start_parser.add_argument('--gui', action='store_true', help='Start with GUI')
    start_parser.add_argument('--memory', help='Override memory setting')

    subparsers.add_parser('stop', help='Stop server')

    restart_parser = subparsers.add_parser('restart', help='Restart server')
    restart_parser.add_argument('--gui', action='store_true', help='Start with GUI')
    restart_parser.add_argument('--memory', help='Override memory setting')

    subparsers.add_parser('status', help='Show server status')
    subparsers.add_parser('watch', help='Watch server and auto-restart')

    # Send command
    send_parser = subparsers.add_parser('send', help='Send command to server')
    send_parser.add_argument('command', help='Command to send')

    # Backup commands
    backup_parser = subparsers.add_parser('backup', help='Backup management')
    backup_parser.add_argument('backup_action', nargs='?', default='create',
                               choices=['create', 'list', 'delete', 'info'])
    backup_parser.add_argument('--type', choices=['quick', 'full'], default='quick',
                               help='Backup type')
    backup_parser.add_argument('--name', help='Backup name (for create/delete)')

    # Scheduler commands
    scheduler_parser = subparsers.add_parser('scheduler', help='Backup scheduler')
    scheduler_parser.add_argument('scheduler_action', choices=['start', 'stop', 'status'])

    # Config commands
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_parser.add_argument('config_action', choices=['show', 'set', 'validate'])
    config_parser.add_argument('key', nargs='?', help='Configuration key')
    config_parser.add_argument('value', nargs='?', help='Configuration value')

    args = parser.parse_args()

    # Handle help
    if args.help or not args.command:
        print_help()
        return

    # Route commands
    success = True

    try:
        if args.command == 'setup':
            cmd_setup()

        elif args.command == 'server':
            success = cmd_server(args)

        elif args.command in ['start', 'stop', 'restart', 'status', 'watch']:
            # Shorthand server commands
            server_args = argparse.Namespace()
            server_args.server_action = args.command
            server_args.gui = getattr(args, 'gui', False)
            server_args.memory = getattr(args, 'memory', None)
            success = cmd_server(server_args)

        elif args.command == 'send':
            success = cmd_send(args)

        elif args.command == 'backup':
            success = cmd_backup(args)

        elif args.command == 'scheduler':
            success = cmd_scheduler(args)

        elif args.command == 'config':
            success = cmd_config(args)

        else:
            print_help()

    except KeyboardInterrupt:
        print_status("\nOperation cancelled", "info")
        success = False
    except Exception as e:
        print_status(f"Unexpected error: {e}", "error")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
