"""Shared utilities for MCUtil."""
import subprocess
import time
from pathlib import Path
from typing import Optional


def run_command(command: str, cwd: Optional[str] = None, timeout: int = 30) -> bool:
    """
    Run a shell command safely with timeout.
    
    Args:
        command: Command to run
        cwd: Working directory
        timeout: Command timeout in seconds
    
    Returns:
        True if command succeeded, False otherwise
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def get_command_output(command: str, cwd: Optional[str] = None) -> Optional[str]:
    """
    Get output from a shell command.
    
    Args:
        command: Command to run
        cwd: Working directory
    
    Returns:
        Command output or None if failed
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass
    return None


def format_bytes(bytes_value: int) -> str:
    """Convert bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def get_directory_size(path: Path) -> int:
    """Get total size of directory in bytes."""
    total = 0
    try:
        for file_path in path.rglob('*'):
            if file_path.is_file():
                try:
                    total += file_path.stat().st_size
                except (OSError, IOError):
                    continue
    except (OSError, IOError):
        pass
    return total


def screen_exists(session_name: str) -> bool:
    """Check if a screen session exists."""
    output = get_command_output("screen -ls")
    if output:
        return f".{session_name}" in output
    return False


def send_to_screen(session_name: str, command: str) -> bool:
    """Send a command to a screen session."""
    return run_command(f'screen -S {session_name} -X stuff "{command}\\n"')


def wait_for_condition(condition_func, timeout: int = 30, interval: float = 1.0) -> bool:
    """
    Wait for a condition to become true.
    
    Args:
        condition_func: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Check interval in seconds
    
    Returns:
        True if condition was met, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    return False


def print_status(message: str, status: str = "info"):
    """Print colored status message."""
    colors = {
        "info": "\033[94m",  # Blue
        "success": "\033[92m",  # Green
        "warning": "\033[93m",  # Yellow
        "error": "\033[91m",  # Red
        "reset": "\033[0m"  # Reset
    }

    symbols = {
        "info": "ℹ",
        "success": "✓",
        "warning": "⚠",
        "error": "✗"
    }

    color = colors.get(status, colors["info"])
    symbol = symbols.get(status, symbols["info"])
    reset = colors["reset"]

    print(f"{color}{symbol} {message}{reset}")


def confirm(message: str, default: bool = False) -> bool:
    """Ask for user confirmation."""
    suffix = " [Y/n]" if default else " [y/N]"
    response = input(message + suffix + ": ").strip().lower()

    if not response:
        return default

    return response in ['y', 'yes']