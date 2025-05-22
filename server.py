"""Minecraft server management."""
import time
from pathlib import Path
from typing import Optional, Dict, Any

from utils import (
    run_command, get_command_output, screen_exists, send_to_screen,
    wait_for_condition, print_status, get_directory_size, format_bytes
)


class MinecraftServer:
    """Manages Minecraft server operations."""

    def __init__(self, config):
        self.config = config
        self.server_dir = Path(config.get("server_dir"))
        self.server_jar = config.get("server_jar")
        self.screen_name = config.get("screen_name")
        self.java_memory = config.get("java_memory")

    def is_running(self) -> bool:
        """Check if server is running."""
        return screen_exists(self.screen_name)

    def start(self, gui: bool = False, memory: Optional[str] = None) -> bool:
        """
        Start the Minecraft server.

        Args:
            gui: Start with GUI
            memory: Override memory setting

        Returns:
            True if started successfully
        """
        if self.is_running():
            print_status("Server is already running", "warning")
            return False

        # Validate server setup
        jar_path = self.server_dir / self.server_jar
        if not jar_path.exists():
            print_status(f"Server jar not found: {jar_path}", "error")
            return False

        # Build java command
        mem = memory or self.java_memory
        gui_flag = "" if gui else "nogui"

        java_cmd = f"java -Xmx{mem} -Xms{mem} -jar {self.server_jar} {gui_flag}"
        screen_cmd = f'screen -dmS {self.screen_name} {java_cmd}'

        print_status("Starting Minecraft server...")

        if not run_command(screen_cmd, cwd=str(self.server_dir)):
            print_status("Failed to start server", "error")
            return False

        # Wait for server to actually start
        print_status("Waiting for server to start...")
        if wait_for_condition(self.is_running, timeout=10):
            print_status(f"Server started successfully in screen '{self.screen_name}'", "success")
            print_status(f"Use 'screen -r {self.screen_name}' to attach (Ctrl+A+D to detach)", "info")
            return True
        else:
            print_status("Server failed to start properly", "error")
            return False

    def stop(self, timeout: int = 30) -> bool:
        """
        Stop the Minecraft server gracefully.

        Args:
            timeout: Maximum time to wait for shutdown

        Returns:
            True if stopped successfully
        """
        if not self.is_running():
            print_status("Server is not running", "warning")
            return True

        print_status("Stopping Minecraft server...")

        # Send stop command
        if not send_to_screen(self.screen_name, "stop"):
            print_status("Failed to send stop command", "error")
            return False

        # Wait for server to stop
        print_status("Waiting for server to shutdown...")
        if wait_for_condition(lambda: not self.is_running(), timeout=timeout):
            print_status("Server stopped successfully", "success")
            return True
        else:
            print_status("Server did not stop gracefully, force killing...", "warning")
            return self._force_stop()

    def _force_stop(self) -> bool:
        """Force stop the server by killing the screen session."""
        cmd = f'screen -S {self.screen_name} -X quit'
        if run_command(cmd):
            time.sleep(2)  # Give it a moment
            if not self.is_running():
                print_status("Server force stopped", "success")
                return True

        print_status("Failed to force stop server", "error")
        return False

    def restart(self, gui: bool = False, memory: Optional[str] = None) -> bool:
        """Restart the server."""
        print_status("Restarting Minecraft server...")

        if not self.stop():
            return False

        # Brief pause between stop and start
        time.sleep(3)

        return self.start(gui=gui, memory=memory)

    def send_command(self, command: str) -> bool:
        """
        Send a command to the running server.

        Args:
            command: Minecraft server command

        Returns:
            True if command was sent successfully
        """
        if not self.is_running():
            print_status("Server is not running", "warning")
            return False

        if send_to_screen(self.screen_name, command):
            print_status(f"Command sent: {command}", "success")
            return True
        else:
            print_status(f"Failed to send command: {command}", "error")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get server status information."""
        status = {
            "running": self.is_running(),
            "screen_session": self.screen_name,
            "server_dir": str(self.server_dir),
            "server_jar": self.server_jar,
        }

        if status["running"]:
            # Try to get process info
            pid_output = get_command_output(f"pgrep -f '{self.server_jar}'")
            if pid_output:
                pids = [p.strip() for p in pid_output.split('\n') if p.strip()]
                if pids:
                    # Get stats for the first Java process found
                    pid = pids[0]
                    ps_output = get_command_output(f"ps -p {pid} -o %cpu,%mem,etime --no-headers")
                    if ps_output:
                        parts = ps_output.strip().split()
                        if len(parts) >= 3:
                            status["cpu_percent"] = parts[0]
                            status["memory_percent"] = parts[1]
                            status["uptime"] = " ".join(parts[2:])

        # Get server directory size
        try:
            size = get_directory_size(self.server_dir)
            status["directory_size"] = format_bytes(size)
        except Exception as error:
            print(error)
            status["directory_size"] = "Unknown"

        return status

    def print_status(self):
        """Print formatted server status."""
        status = self.get_status()

        print("\nMinecraft Server Status")
        print("=" * 30)

        if status["running"]:
            print_status("Server: RUNNING", "success")
        else:
            print_status("Server: STOPPED", "error")

        print(f"Screen Session: {status['screen_session']}")
        print(f"Server Directory: {status['server_dir']}")
        print(f"Server Jar: {status['server_jar']}")
        print(f"Directory Size: {status['directory_size']}")

        if status["running"]:
            if "cpu_percent" in status:
                print(f"CPU Usage: {status['cpu_percent']}%")
                print(f"Memory Usage: {status['memory_percent']}%")
                print(f"Uptime: {status['uptime']}")

            print_status(f"Attach with: screen -r {status['screen_session']}", "info")

    def watch(self, interval: int = None) -> None:
        """
        Watch server and restart if it crashes.

        Args:
            interval: Check interval in seconds
        """
        check_interval = interval or self.config.get("watchdog_interval", 30)

        print_status(f"Starting server watchdog (checking every {check_interval}s)", "info")
        print_status("Press Ctrl+C to stop watching", "info")

        try:
            while True:
                if not self.is_running():
                    print_status("Server is down! Attempting restart...", "warning")
                    if self.start():
                        print_status("Server restarted successfully", "success")
                    else:
                        print_status("Failed to restart server", "error")
                        break

                time.sleep(check_interval)

        except KeyboardInterrupt:
            print_status("\nWatchdog stopped", "info")
