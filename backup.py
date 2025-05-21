import os
import shutil
from datetime import datetime

from rich.progress import Progress

from utils import print_info, print_success, print_warning, print_error

# Define backup types with their respective items
BACKUP_TYPES = {
    "regular": {
        "description": "Standard backup with worlds, and config",
        "items": [
            "world",
            "world_nether",
            "world_the_end",
            "server.properties",
            "banned-ips.json",
            "banned-players.json",
            "ops.json",
            "whitelist.json",
            "config"
        ]
    },
    "medium": {
        "description": "Comprehensive backup including user configs and caches",
        "items": [
            "world",
            "world_nether",
            "world_the_end",
            "server.properties",
            "banned-ips.json",
            "banned-players.json",
            "ops.json",
            "whitelist.json",
            "mods",
            "config",
            "defaultconfigs",
            "user_jvm_args.txt",
            "usercache.json",
            "usernamecache.json",
            "eula.txt"
        ]
    },
    "hard": {
        "description": "Complete backup with all server files",
        "items": [
            "all"
        ]
    }
}


def get_backup_size_estimate(cfg, items):
    """Estimate backup size by checking file/folder sizes"""
    total_size = 0
    for item in items:
        path = os.path.join(cfg["SERVER_DIR"], item)
        if os.path.exists(path):
            if os.path.isfile(path):
                total_size += os.stat(path).st_size
            elif os.path.isdir(path):
                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.stat(filepath).st_size
                        except (OSError, IOError):
                            continue
    return total_size


def format_size(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def backup_world(cfg, backup_type="regular", include_list=None, exclude_list=None):
    """
    Create a backup of the Minecraft server

    Args:
        cfg: Configuration dictionary
        backup_type: Type of backup (soft, regular, medium, hard)
        include_list: Custom comma-separated list of items to include
        exclude_list: Comma-separated list of items to exclude
    """

    # Validate backup type
    if backup_type not in BACKUP_TYPES:
        print_error(f"Invalid backup type '{backup_type}'. Available types: {', '.join(BACKUP_TYPES.keys())}")
        return False

    backup_info = BACKUP_TYPES[backup_type]
    print_info(f"Starting {backup_type} backup...")
    print_info(f"Type: {backup_info['description']}")

    # Create a date-based folder structure
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    date_folder = now.strftime("%Y-%m-%d")

    backup_name = f"server_backup_{backup_type}_{timestamp}"
    date_backup_dir = os.path.join(cfg["BACKUP_DIR"], date_folder)
    backup_path = os.path.join(date_backup_dir, backup_name)
    temp_dir = os.path.join(date_backup_dir, f"_temp_backup_{timestamp}")

    # Determine what to back up
    if include_list:
        include_items = include_list.split(',')
        print_info(f"Using custom include list: {include_list}")
    else:
        if backup_info["items"] == ["all"]:
            include_items = os.listdir(cfg["SERVER_DIR"])
        else:
            include_items = backup_info["items"].copy()

    # Apply exclusions
    if exclude_list:
        exclude_items = exclude_list.split(',')
        include_items = [item.strip() for item in include_items if item.strip() not in exclude_items]
        print_info(f"Excluding: {exclude_list}")

    print_info(f"Items to backup: {', '.join(include_items)}")
    print_info(f"Backup will be saved in the folder: {date_folder}")

    # Estimate backup size
    estimated_size = get_backup_size_estimate(cfg, include_items)
    print_info(f"Estimated backup size: {format_size(estimated_size)}")

    try:
        # Create backup directory structure (main backup dir and date folder)
        os.makedirs(cfg["BACKUP_DIR"], exist_ok=True)
        os.makedirs(date_backup_dir, exist_ok=True)

        os.makedirs(temp_dir, exist_ok=True)

        copied_items = []
        missing_items = []

        with Progress() as progress:
            task = progress.add_task("[green]Backing up server files...", total=len(include_items) + 3)

            for item in include_items:
                src = os.path.join(cfg["SERVER_DIR"], item.strip())
                dst = os.path.join(temp_dir, item.strip())

                if os.path.exists(src):
                    try:
                        if os.path.isdir(src):
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(dst), exist_ok=True)
                            shutil.copy2(src, dst)
                        copied_items.append(item.strip())
                    except Exception as e:
                        print_warning(f"Failed to copy {item}: {e}")
                        missing_items.append(item.strip())
                else:
                    print_warning(f"Missing: {item}")
                    missing_items.append(item.strip())

                progress.update(task, advance=1)

            progress.update(task, description="[yellow]Creating ZIP archive...")

            shutil.make_archive(backup_path, 'zip', temp_dir)
            progress.update(task, advance=1)

            progress.update(task, description="[yellow]Cleaning up temporary files...")
            shutil.rmtree(temp_dir)
            progress.update(task, advance=1)

        # Get the final backup size
        final_backup_path = f"{backup_path}.zip"
        actual_size = os.path.getsize(final_backup_path)

        print_success(f"Backup completed successfully!")
        print_success(f"Backup saved as: {final_backup_path}")
        print_success(f"Final size: {format_size(actual_size)}")
        print_info(f"Items backed up: {len(copied_items)}")

        if missing_items:
            print_warning(f"Missing items: {len(missing_items)} - {', '.join(missing_items)}")

        return True

    except Exception as e:
        print_error(f"Backup failed: {e}")
        # Clean up the temp directory if it exists
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

        return False


def list_backup_types():
    """Print information about available backup types"""
    print_info("Available backup types:")
    for backup_type, info in BACKUP_TYPES.items():
        print_info(f"  {backup_type}: {info['description']}")
        print_info(f"    Items: {', '.join(info['items'])}")
        print_info("")
