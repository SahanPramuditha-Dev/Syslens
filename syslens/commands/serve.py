"""
``syslens serve`` / ``syslensd`` — Launch the FastAPI + WebSocket web dashboard.
"""
from syslens.commands._shared import console


def run() -> None:
    """Start the FastAPI uvicorn server on http://127.0.0.1:8000."""
    try:
        from syslens.dashboard.app import serve
        serve()
    except ImportError:
        console.print(
            "[red]Could not launch FastAPI dashboard. "
            "Install optional dependencies with:[/red]\n"
            "  [bold]pip install syslens[dashboard][/bold]"
        )
