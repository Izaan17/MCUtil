import subprocess
import time

from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from utils import print_info, print_warning, print_success, print_error, print_header


def screen_session_exists(screen_name):
    """Check if a screen session exists"""
    result = subprocess.run(f"screen -ls | grep -q '\\.{screen_name}'", shell=True)
    return result.returncode == 0


def run_command(command, cwd=None, silent=False):
    """Run a shell command and return success status"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd,
                                stdout=None if not silent else subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            if not silent:
                print_error(f"Command failed: {command}")
                if result.stderr:
                    print_error(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        if not silent:
            print_error(f"Exception running command: {e}")
        return False


def start_server(cfg, gui=False, ram=None):
    """Start the Minecraft server"""
    if screen_session_exists(cfg["SCREEN_NAME"]):
        print_warning("Server is already running. Use 'status' to check.")
        return

    print_header("Starting Minecraft Server")

    java_options = cfg["JAVA_OPTIONS"]
    if ram:
        java_options = f"-Xmx{ram} -Xms{ram}"
        print_info(f"Using RAM override: {ram}")

    gui_param = "" if gui else "nogui"
    cmd = f'screen -dmS {cfg["SCREEN_NAME"]} java {java_options} -jar {cfg["SERVER_JAR"]} {gui_param}'

    if run_command(cmd, cwd=cfg["SERVER_DIR"]):
        print_success("Server started.")
        print_info(f"Server running in screen session '{cfg['SCREEN_NAME']}'")
        print_info(f"Use 'screen -r {cfg['SCREEN_NAME']}' to attach (Ctrl+A+D to detach)")
    else:
        print_error("Failed to start server.")


def stop_server(cfg):
    """Stop the Minecraft server"""
    print_header("Stopping Minecraft Server")
    if not screen_session_exists(cfg["SCREEN_NAME"]):
        print_warning("Server is not running.")
        return

    cmd = f'screen -S {cfg["SCREEN_NAME"]} -X stuff "stop\\n"'
    if run_command(cmd):
        print_success("Stop signal sent. Waiting for server to shut down...")

        with Progress(SpinnerColumn(), TextColumn("[green]Waiting for server to stop...[/green]"), ) as progress:
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
            print_info(f"Try: screen -S {cfg['SCREEN_NAME']} -X quit")
    else:
        print_error("Failed to send stop signal.")


def restart_server(cfg, gui=False, ram=None):
    """Restart the Minecraft server"""
    print_header("Restarting Minecraft Server")
    stop_server(cfg)
    # Wait a moment for complete shutdown
    time.sleep(2)
    start_server(cfg, gui=gui, ram=ram)


def send_command(cfg, cmd):
    """Send a command to the running server"""
    if not screen_session_exists(cfg["SCREEN_NAME"]):
        print_warning("Server is not running.")
        return
    full_cmd = f'screen -S {cfg["SCREEN_NAME"]} -X stuff "{cmd}\\n"'
    if run_command(full_cmd):
        print_success(f"Sent command: {cmd}")
    else:
        print_error(f"Failed to send command: {cmd}")


def get_server_stats(cfg):
    """Get live server statistics"""
    table = Table(title="Minecraft Server Status (Live)")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    if screen_session_exists(cfg["SCREEN_NAME"]):
        table.add_row("Status", "🟢 RUNNING")
        table.add_row("Screen Session", cfg["SCREEN_NAME"])

        try:
            # Try to get process information
            pid_cmd = f"pgrep -f '{cfg['SERVER_JAR']}'"
            pid_result = subprocess.run(pid_cmd, shell=True, capture_output=True, text=True)

            if pid_result.stdout.strip():
                pids = pid_result.stdout.strip().split('\n')
                # Usually want the java process, not the screen process
                for pid in pids:
                    if pid.strip():
                        try:
                            cpu_cmd = f"ps -p {pid.strip()} -o %cpu=,%mem=,etime= --no-headers"
                            result = subprocess.run(cpu_cmd, shell=True, capture_output=True, text=True)
                            if result.stdout.strip():
                                parts = result.stdout.strip().split()
                                if len(parts) >= 3:
                                    cpu, mem, etime = parts[0], parts[1], ' '.join(parts[2:])
                                    table.add_row("CPU Usage", f"{cpu}%")
                                    table.add_row("Memory Usage", f"{mem}%")
                                    table.add_row("Uptime", etime)
                                    break
                        except:
                            continue

            # Check server directory size
            try:
                du_cmd = f"du -sh '{cfg['SERVER_DIR']}' 2>/dev/null"
                du_result = subprocess.run(du_cmd, shell=True, capture_output=True, text=True)
                if du_result.stdout.strip():
                    size = du_result.stdout.split()[0]
                    table.add_row("Server Size", size)
            except:
                pass

        except Exception as e:
            table.add_row("Stats Error", str(e))
    else:
        table.add_row("Status", "🔴 STOPPED")
        table.add_row("Screen Session", "Not running")

    return table


def show_status(cfg):
    """Show live server status monitor"""
    print_header("Live Server Status Monitor")
    print_info("Press Ctrl+C to stop monitoring")
    print()

    try:
        with Live(get_server_stats(cfg), refresh_per_second=1) as live:
            while True:
                time.sleep(1)
                live.update(get_server_stats(cfg))
    except KeyboardInterrupt:
        print_info("Stopped monitoring.")