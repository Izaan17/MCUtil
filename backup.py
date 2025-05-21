import os
import shutil
import zipfile
from datetime import datetime

from rich.progress import Progress

from utils import print_info, print_success, print_warning, print_error


def backup_world(cfg, include_list=None, exclude_list=None, compression_level=None):
    print_info("Starting backup...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"server_backup_{timestamp}"
    backup_path = os.path.join(cfg["BACKUP_DIR"], backup_name)

    default_items = ["world", "world_nether", "world_the_end", "server.properties", "banned-ips.json",
        "banned-players.json", "ops.json", "whitelist.json", "mods", "config", "scripts", "plugins"]

    include_items = include_list.split(',') if include_list else default_items
    if exclude_list:
        exclude_items = exclude_list.split(',')
        include_items = [item for item in include_items if item not in exclude_items]
        print_info(f"Excluding: {exclude_list}")

    print_info(f"Backing up: {', '.join(include_items)}")

    try:
        os.makedirs(cfg["BACKUP_DIR"], exist_ok=True)
        temp_dir = os.path.join(cfg["BACKUP_DIR"], f"_temp_backup_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)

        with Progress() as progress:
            task = progress.add_task("[green]Backing up server...", total=len(include_items) + 3)
            for item in include_items:
                src = os.path.join(cfg["SERVER_DIR"], item)
                dst = os.path.join(temp_dir, item)
                if os.path.exists(src):
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                else:
                    print_warning(f"Missing: {item}")
                progress.update(task, advance=1)

            progress.update(task, description="[yellow]Creating ZIP archive...")
            zip_options = {}
            if compression_level is not None:
                try:
                    level = int(compression_level)
                    if 0 <= level <= 9:
                        zip_options['compression'] = zipfile.ZIP_DEFLATED
                        zip_options['compresslevel'] = level
                        print_info(f"Using compression level: {level}")
                except ValueError:
                    print_warning(f"Invalid compression level '{compression_level}', using default")

            shutil.make_archive(backup_path, 'zip', temp_dir, **zip_options)
            progress.update(task, advance=1)

            progress.update(task, description="[yellow]Cleaning up...")
            shutil.rmtree(temp_dir)
            progress.update(task, advance=1)

        print_success(f"Backup saved as {backup_path}.zip")
    except Exception as e:
        print_error(f"Backup failed: {e}")
