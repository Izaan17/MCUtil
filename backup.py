"""Backup management for Minecraft server."""
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from utils import (
    print_status, get_directory_size, format_bytes, cleanup_old_files
)


class BackupManager:
    """Manages server backups."""

    # Define what gets backed up for each type
    BACKUP_TYPES = {
        "quick": {
            "description": "Essential files only (worlds, configs)",
            "include": [
                "world", "world_nether", "world_the_end",
                "server.properties", "ops.json", "whitelist.json",
                "banned-players.json", "banned-ips.json"
            ]
        },
        "full": {
            "description": "Complete server backup",
            "include": ["*"],  # Everything
            "exclude": [
                "logs", "crash-reports", "*.log", ".DS_STORE"
            ]
        }
    }

    def __init__(self, config):
        self.config = config
        self.server_dir = Path(config.get("server_dir"))
        self.backup_dir = Path(config.get("backup_dir"))
        self.retention = config.get("backup_retention", 7)

    def create_backup(self, backup_type: str = "quick",
                      custom_name: Optional[str] = None) -> Optional[Path]:
        """
        Create a server backup.
        
        Args:
            backup_type: Type of backup ('quick' or 'full')
            custom_name: Custom backup name
        
        Returns:
            Path to the created backup file or None if failed
        """
        if backup_type not in self.BACKUP_TYPES:
            print_status(f"Invalid backup type: {backup_type}", "error")
            return None

        if not self.server_dir.exists():
            print_status(f"Server directory not found: {self.server_dir}", "error")
            return None

        backup_info = self.BACKUP_TYPES[backup_type]

        # Create a backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = custom_name or f"minecraft_backup_{backup_type}_{timestamp}"
        backup_path = self.backup_dir / f"{name}.zip"

        print_status(f"Creating {backup_type} backup: {backup_info['description']}")
        print_status(f"Backup location: {backup_path}")

        try:
            # Estimate backup size
            total_size = self._estimate_backup_size(backup_type)
            print_status(f"Estimated size: {format_bytes(total_size)}")

            # Create the backup
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                files_added = self._add_files_to_zip(zipf, backup_type)

            # Verify backup was created
            if backup_path.exists():
                actual_size = backup_path.stat().st_size
                print_status(f"Backup created successfully!", "success")
                print_status(f"Final size: {format_bytes(actual_size)}")
                print_status(f"Files included: {files_added}")

                # Clean up old backups
                self._cleanup_old_backups()

                return backup_path
            else:
                print_status("Backup file was not created", "error")
                return None

        except Exception as e:
            print_status(f"Backup failed: {e}", "error")
            # Clean up partial backup
            if backup_path.exists():
                try:
                    backup_path.unlink()
                except FileNotFoundError:
                    pass
            return None

    def _estimate_backup_size(self, backup_type: str) -> int:
        """Estimate the size of the backup."""
        backup_info = self.BACKUP_TYPES[backup_type]
        total_size = 0

        if "*" in backup_info["include"]:
            # Full backup - calculate entire directory
            total_size = get_directory_size(self.server_dir)
        else:
            # Calculate size of specific items
            for item in backup_info["include"]:
                item_path = self.server_dir / item
                if item_path.exists():
                    if item_path.is_file():
                        total_size += item_path.stat().st_size
                    else:
                        total_size += get_directory_size(item_path)

        return total_size

    def _add_files_to_zip(self, zipf: zipfile.ZipFile, backup_type: str) -> int:
        """Add files to zip archive based on backup type."""
        backup_info = self.BACKUP_TYPES[backup_type]
        files_added = 0

        if "*" in backup_info["include"]:
            # Full backup - add everything except excluded items
            exclude_patterns = backup_info.get("exclude", [])

            for item in self.server_dir.rglob("*"):
                if item.is_file():
                    # Check if the file should be excluded
                    relative_path = item.relative_to(self.server_dir)
                    if not self._should_exclude(str(relative_path), exclude_patterns):
                        try:
                            zipf.write(item, relative_path)
                            files_added += 1
                        except (OSError, IOError) as e:
                            print_status(f"Warning: Could not backup {relative_path}: {e}", "warning")
        else:
            # Selective backup - add only specified items
            for item_name in backup_info["include"]:
                item_path = self.server_dir / item_name
                if item_path.exists():
                    files_added += self._add_item_to_zip(zipf, item_path, item_name)
                else:
                    print_status(f"Warning: {item_name} not found", "warning")

        return files_added

    def _add_item_to_zip(self, zipf: zipfile.ZipFile, item_path: Path, archive_name: str) -> int:
        """Add a single item (file or directory) to the zip."""
        files_added = 0

        if item_path.is_file():
            try:
                zipf.write(item_path, archive_name)
                files_added = 1
            except (OSError, IOError) as e:
                print_status(f"Warning: Could not backup {archive_name}: {e}", "warning")
        elif item_path.is_dir():
            for file_path in item_path.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(self.server_dir)
                    try:
                        zipf.write(file_path, relative_path)
                        files_added += 1
                    except (OSError, IOError) as e:
                        print_status(f"Warning: Could not backup {relative_path}: {e}", "warning")

        return files_added

    @staticmethod
    def _should_exclude(path: str, exclude_patterns: List[str]) -> bool:
        """Check if a path should be excluded based on patterns."""
        for pattern in exclude_patterns:
            if pattern in path or path.endswith(pattern.replace("*", "")):
                return True
        return False

    def _cleanup_old_backups(self):
        """Remove old backup files beyond the retention limit."""
        if self.retention <= 0:
            return

        print_status(f"Cleaning up old backups (keeping {self.retention} most recent)")
        cleanup_old_files(self.backup_dir, "*.zip", self.retention)

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups."""
        if not self.backup_dir.exists():
            return []

        backups = []
        for backup_file in self.backup_dir.glob("*.zip"):
            try:
                stat = backup_file.stat()
                backups.append({
                    "name": backup_file.name,
                    "path": backup_file,
                    "size": stat.st_size,
                    "size_formatted": format_bytes(stat.st_size),
                    "created": datetime.fromtimestamp(stat.st_mtime),
                    "type": self._detect_backup_type(backup_file.name)
                })
            except OSError:
                continue

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created"], reverse=True)
        return backups

    @staticmethod
    def _detect_backup_type(filename: str) -> str:
        """Detect backup type from filename."""
        if "_quick_" in filename:
            return "quick"
        elif "_full_" in filename:
            return "full"
        else:
            return "unknown"

    def print_backup_list(self):
        """Print a formatted list of backups."""
        backups = self.list_backups()

        if not backups:
            print_status("No backups found", "warning")
            return

        print("\nAvailable Backups")
        print("=" * 50)

        for backup in backups:
            created_str = backup["created"].strftime("%Y-%m-%d %H:%M:%S")
            print(f"{backup['name']}")
            print(f"  Type: {backup['type']}")
            print(f"  Size: {backup['size_formatted']}")
            print(f"  Created: {created_str}")
            print()

    def delete_backup(self, backup_name: str) -> bool:
        """Delete a specific backup."""
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            backup_path = self.backup_dir / f"{backup_name}.zip"

        if not backup_path.exists():
            print_status(f"Backup not found: {backup_name}", "error")
            return False

        try:
            backup_path.unlink()
            print_status(f"Deleted backup: {backup_path.name}", "success")
            return True
        except OSError as e:
            print_status(f"Failed to delete backup: {e}", "error")
            return False

    def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup statistics."""
        backups = self.list_backups()

        total_size = sum(b["size"] for b in backups)
        quick_backups = [b for b in backups if b["type"] == "quick"]
        full_backups = [b for b in backups if b["type"] == "full"]

        return {
            "total_backups": len(backups),
            "quick_backups": len(quick_backups),
            "full_backups": len(full_backups),
            "total_size": total_size,
            "total_size_formatted": format_bytes(total_size),
            "latest_backup": backups[0]["created"] if backups else None,
            "backup_dir": str(self.backup_dir)
        }
