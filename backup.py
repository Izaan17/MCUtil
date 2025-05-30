"""Backup management for Minecraft server with enhanced progress reporting."""
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import time

from utils import (
    print_status, get_directory_size, format_bytes
)


class BackupManager:
    """Manages server backups with metadata tracking."""

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
                "logs", "crash-reports", "*.log",
                "backup_scheduler.py", "__pycache__"
            ]
        }
    }

    def __init__(self, config):
        self.config = config
        self.server_dir = Path(config.get("server_dir"))
        self.backup_dir = Path(config.get("backup_dir"))
        self.retention = config.get("backup_retention", 7)

    def _get_date_dir(self, date: datetime = None) -> Path:
        """Get the backup directory for a specific date."""
        if date is None:
            date = datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        return self.backup_dir / date_str

    @staticmethod
    def _get_metadata_file(date_dir: Path) -> Path:
        """Get the metadata file path for a date directory."""
        return date_dir / "backups.json"

    def _load_metadata(self, date_dir: Path) -> Dict[str, Any]:
        """Load backup metadata for a specific date."""
        metadata_file = self._get_metadata_file(date_dir)
        if not metadata_file.exists():
            return {"backups": []}

        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"backups": []}

    def _save_metadata(self, date_dir: Path, metadata: Dict[str, Any]):
        """Save backup metadata for a specific date."""
        metadata_file = self._get_metadata_file(date_dir)
        try:
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
        except IOError as e:
            print_status(f"Warning: Could not save metadata: {e}", "warning")

    def _get_next_backup_number(self, date_dir: Path) -> int:
        """Get the next backup number for the date."""
        metadata = self._load_metadata(date_dir)
        if not metadata["backups"]:
            return 1
        return max(backup["number"] for backup in metadata["backups"]) + 1

    def _count_files_to_backup(self, backup_type: str) -> tuple:
        """Count files that will be backed up and estimate total size."""
        backup_info = self.BACKUP_TYPES[backup_type]
        file_count = 0
        total_size = 0

        print_status("Scanning files to backup...", "info")

        if "*" in backup_info["include"]:
            # Full backup - count everything except excluded
            exclude_patterns = backup_info.get("exclude", [])

            for item in self.server_dir.rglob("*"):
                if item.is_file():
                    relative_path = item.relative_to(self.server_dir)
                    if not self._should_exclude(str(relative_path), exclude_patterns):
                        file_count += 1
                        try:
                            total_size += item.stat().st_size
                        except (OSError, IOError):
                            pass

                        # Show progress every 100 files
                        if file_count % 100 == 0:
                            print_status(f"  Scanned {file_count} files ({format_bytes(total_size)})...", "info")
        else:
            # Selective backup
            for item_name in backup_info["include"]:
                item_path = self.server_dir / item_name
                if item_path.exists():
                    if item_path.is_file():
                        file_count += 1
                        total_size += item_path.stat().st_size
                    else:
                        # Count files in directory
                        for file_path in item_path.rglob("*"):
                            if file_path.is_file():
                                file_count += 1
                                try:
                                    total_size += file_path.stat().st_size
                                except (OSError, IOError):
                                    pass

        return file_count, total_size

    def create_backup(self, backup_type: str = "quick",
                      custom_name: Optional[str] = None) -> Optional[Path]:
        """
        Create a server backup with metadata tracking and progress reporting.

        Args:
            backup_type: Type of backup ('quick' or 'full')
            custom_name: Custom backup name (optional)

        Returns:
            Path to the created backup file or None if failed
        """
        start_time = time.time()

        if backup_type not in self.BACKUP_TYPES:
            print_status(f"Invalid backup type: {backup_type}", "error")
            return None

        if not self.server_dir.exists():
            print_status(f"Server directory not found: {self.server_dir}", "error")
            return None

        backup_info = self.BACKUP_TYPES[backup_type]
        now = datetime.now()

        # Create a date-based directory
        date_dir = self._get_date_dir(now)
        date_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename
        backup_number = self._get_next_backup_number(date_dir)
        if custom_name:
            backup_filename = f"{custom_name}.zip"
        else:
            backup_filename = f"backup_{backup_number:03d}_{backup_type}.zip"

        backup_path = date_dir / backup_filename

        print_status(f"=== Starting {backup_type} backup ===", "info")
        print_status(f"Type: {backup_info['description']}", "info")
        print_status(f"Destination: {backup_path}", "info")

        try:
            # Count files and estimate size
            file_count, estimated_size = self._count_files_to_backup(backup_type)
            print_status(f"Total files to backup: {file_count}", "info")
            print_status(f"Estimated size: {format_bytes(estimated_size)}", "info")

            # Create the backup with progress reporting
            print_status("Creating backup archive...", "info")
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                files_added = self._add_files_to_zip_with_progress(
                    zipf, backup_type, file_count, estimated_size
                )

            # Verify backup was created
            if backup_path.exists():
                actual_size = backup_path.stat().st_size
                compression_ratio = 100 * (1 - actual_size / estimated_size) if estimated_size > 0 else 0

                # Create metadata entry
                backup_metadata = {
                    "number": backup_number,
                    "filename": backup_filename,
                    "type": backup_type,
                    "description": backup_info["description"],
                    "created": now.isoformat(),
                    "size": actual_size,
                    "files_count": files_added,
                    "custom_name": custom_name
                }

                # Save metadata
                metadata = self._load_metadata(date_dir)
                metadata["backups"].append(backup_metadata)
                self._save_metadata(date_dir, metadata)

                # Calculate duration
                duration = time.time() - start_time
                minutes, seconds = divmod(int(duration), 60)

                print_status("=== Backup completed successfully! ===", "success")
                print_status(f"Files backed up: {files_added}", "success")
                print_status(f"Original size: {format_bytes(estimated_size)}", "info")
                print_status(f"Compressed size: {format_bytes(actual_size)}", "info")
                print_status(f"Compression ratio: {compression_ratio:.1f}%", "info")
                print_status(f"Time taken: {minutes}m {seconds}s", "info")
                print_status(f"Backup saved as: {backup_filename}", "success")

                # Clean up old backups
                print_status("Checking for old backups to clean up...", "info")
                self._cleanup_old_backups()

                return backup_path
            else:
                print_status("Backup file was not created", "error")
                return None

        except Exception as e:
            print_status(f"Backup failed: {e}", "error")
            # Clean up partial backup
            try:
                backup_path.unlink()
            except FileNotFoundError:
                pass
            return None

    def _add_files_to_zip_with_progress(self, zipf: zipfile.ZipFile, backup_type: str,
                                        total_files: int, total_size: int) -> int:
        """Add files to zip archive with progress reporting."""
        backup_info = self.BACKUP_TYPES[backup_type]
        files_added = 0
        bytes_processed = 0
        last_progress_time = time.time()

        def update_progress(current_file: str = None):
            """Update progress display."""
            nonlocal last_progress_time
            current_time = time.time()

            # Update every 0.5 seconds
            if current_time - last_progress_time >= 0.5 or files_added == total_files:
                if total_files > 0:
                    progress_percent = (files_added / total_files) * 100
                else:
                    progress_percent = 0

                if total_size > 0:
                    size_percent = (bytes_processed / total_size) * 100
                else:
                    size_percent = 0

                status_msg = f"  Progress: {files_added}/{total_files} files ({progress_percent:.1f}%)"
                status_msg += f" | {format_bytes(bytes_processed)}/{format_bytes(total_size)} ({size_percent:.1f}%)"

                if current_file:
                    # Truncate long filenames
                    display_name = current_file if len(current_file) <= 50 else "..." + current_file[-47:]
                    status_msg += f" | Current: {display_name}"

                print(f"\r{status_msg}", end='', flush=True)
                last_progress_time = current_time

        if "*" in backup_info["include"]:
            # Full backup - add everything except excluded items
            exclude_patterns = backup_info.get("exclude", [])

            for item in self.server_dir.rglob("*"):
                if item.is_file():
                    # Check if the file should be excluded
                    relative_path = item.relative_to(self.server_dir)
                    if not self._should_exclude(str(relative_path), exclude_patterns):
                        try:
                            file_size = item.stat().st_size
                            zipf.write(item, relative_path)
                            files_added += 1
                            bytes_processed += file_size
                            update_progress(str(relative_path))
                        except (OSError, IOError) as e:
                            print()  # New line after progress
                            print_status(f"Warning: Could not backup {relative_path}: {e}", "warning")
        else:
            # Selective backup - add only specified items
            for item_name in backup_info["include"]:
                item_path = self.server_dir / item_name
                if item_path.exists():
                    added, size = self._add_item_to_zip_with_progress(
                        zipf, item_path, item_name, update_progress
                    )
                    files_added += added
                    bytes_processed += size
                else:
                    print()  # New line after progress
                    print_status(f"Warning: {item_name} not found", "warning")

        print()  # Final newline after progress bar
        return files_added

    def _add_item_to_zip_with_progress(self, zipf: zipfile.ZipFile, item_path: Path,
                                       archive_name: str, progress_callback) -> tuple:
        """Add a single item to the zip with progress updates."""
        files_added = 0
        bytes_added = 0

        if item_path.is_file():
            try:
                file_size = item_path.stat().st_size
                zipf.write(item_path, archive_name)
                files_added = 1
                bytes_added = file_size
                progress_callback(archive_name)
            except (OSError, IOError) as e:
                print()  # New line after progress
                print_status(f"Warning: Could not backup {archive_name}: {e}", "warning")
        elif item_path.is_dir():
            for file_path in item_path.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(self.server_dir)
                    try:
                        file_size = file_path.stat().st_size
                        zipf.write(file_path, relative_path)
                        files_added += 1
                        bytes_added += file_size
                        progress_callback(str(relative_path))
                    except (OSError, IOError) as e:
                        print()  # New line after progress
                        print_status(f"Warning: Could not backup {relative_path}: {e}", "warning")

        return files_added, bytes_added

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
        """Remove old backup directories beyond the retention limit."""
        if self.retention <= 0:
            return

        print_status(f"Cleaning up old backups (keeping {self.retention} most recent days)...", "info")

        # Get all date directories
        date_dirs = [d for d in self.backup_dir.iterdir()
                     if d.is_dir() and len(d.name) == 10 and d.name.count('-') == 2]

        if len(date_dirs) <= self.retention:
            print_status("No old backups to clean up", "info")
            return

        # Sort by date (newest first)
        date_dirs.sort(key=lambda x: x.name, reverse=True)

        # Remove old directories
        removed_count = 0
        for old_dir in date_dirs[self.retention:]:
            try:
                shutil.rmtree(old_dir)
                print_status(f"  Removed old backup directory: {old_dir.name}", "info")
                removed_count += 1
            except OSError as e:
                print_status(f"  Warning: Could not remove {old_dir}: {e}", "warning")

        if removed_count > 0:
            print_status(f"Cleaned up {removed_count} old backup directories", "success")

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups with metadata."""
        all_backups = []

        if not self.backup_dir.exists():
            return all_backups

        # Get all date directories
        date_dirs = [d for d in self.backup_dir.iterdir()
                     if d.is_dir() and len(d.name) == 10 and d.name.count('-') == 2]

        for date_dir in sorted(date_dirs, reverse=True):
            metadata = self._load_metadata(date_dir)

            for backup_info in metadata.get("backups", []):
                backup_path = date_dir / backup_info["filename"]

                # Verify the file still exists
                if backup_path.exists():
                    backup_info["path"] = backup_path
                    backup_info["date"] = date_dir.name
                    backup_info["created_datetime"] = datetime.fromisoformat(backup_info["created"])
                    backup_info["size_formatted"] = format_bytes(backup_info["size"])
                    all_backups.append(backup_info)

        return all_backups

    def print_backup_list(self):
        """Print a formatted list of backups."""
        backups = self.list_backups()

        if not backups:
            print_status("No backups found", "warning")
            return

        print("\nAvailable Backups")
        print("=" * 80)

        current_date = None
        for backup in backups:
            # Print date header if changed
            if backup["date"] != current_date:
                current_date = backup["date"]
                print(f"\n📅 {current_date}")
                print("-" * 40)

            created_str = backup["created_datetime"].strftime("%H:%M:%S")
            type_icon = "⚡" if backup["type"] == "quick" else "💾"

            print(f"{type_icon} {backup['filename']}")
            print(f"   Type: {backup['type']} - {backup['description']}")
            print(f"   Size: {backup['size_formatted']} ({backup['files_count']} files)")
            print(f"   Created: {created_str}")
            if backup.get("custom_name"):
                print(f"   Custom name: {backup['custom_name']}")
            print()

    def delete_backup(self, backup_identifier: str) -> bool:
        """Delete a specific backup by filename or date/number."""
        backups = self.list_backups()

        # Find backup by filename or identifier
        target_backup = None
        for backup in backups:
            if (backup["filename"] == backup_identifier or
                    backup["filename"] == f"{backup_identifier}.zip" or
                    backup_identifier in backup["filename"]):
                target_backup = backup
                break

        if not target_backup:
            print_status(f"Backup not found: {backup_identifier}", "error")
            return False

        try:
            # Remove the file
            target_backup["path"].unlink()

            # Update metadata
            date_dir = target_backup["path"].parent
            metadata = self._load_metadata(date_dir)
            metadata["backups"] = [
                b for b in metadata["backups"]
                if b["filename"] != target_backup["filename"]
            ]
            self._save_metadata(date_dir, metadata)

            # Remove empty date directory if no backups left
            if not metadata["backups"] and len(list(date_dir.glob("*.zip"))) == 0:
                metadata_file = self._get_metadata_file(date_dir)
                if metadata_file.exists():
                    metadata_file.unlink()
                if not any(date_dir.iterdir()):
                    date_dir.rmdir()

            print_status(f"Deleted backup: {target_backup['filename']}", "success")
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

        # Count backup days
        backup_days = len(set(b["date"] for b in backups))

        return {
            "total_backups": len(backups),
            "quick_backups": len(quick_backups),
            "full_backups": len(full_backups),
            "backup_days": backup_days,
            "total_size": total_size,
            "total_size_formatted": format_bytes(total_size),
            "latest_backup": backups[0]["created_datetime"] if backups else None,
            "backup_dir": str(self.backup_dir)
        }