from rich.console import Console
from rich.panel import Panel

console = Console()


def print_header(title):
    console.print(Panel(f"[bold]{title}[/bold]", expand=False, border_style="dim"))


def print_success(message):
    console.print(f"[green]✓ {message}[/green]")


def print_warning(message):
    console.print(f"[yellow]! {message}[/yellow]")


def print_error(message):
    console.print(f"[red]× {message}[/red]")


def print_info(message):
    console.print(message)
