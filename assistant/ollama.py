import os
import subprocess
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Ollama host fix for Windows: 0.0.0.0 is an invalid destination address for client sockets
if os.environ.get("OLLAMA_HOST") in ("0.0.0.0", "0.0.0.0:11434"):
    os.environ["OLLAMA_HOST"] = "127.0.0.1"

import ollama as o
from rich.panel import Panel


def ensure_ollama_running(console, model: str | None = None) -> bool:
    try:
        console.print("[grey]Checking if Ollama server is working...[/]")
        o.list()
        if model:
            o.chat(model, keep_alive=500.0)
        return True
    except Exception:
        console.print("[bright_red]Ollama server [bold red3]not[/bold red3] detected[/]")
        console.print("[yellow3]Attempting to start Ollama server...[/]")
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            with console.status("[bold yellow]Waiting for server...[/]"):
                for _ in range(30):
                    time.sleep(0.5)
                    try:
                        o.list()
                        if model:
                            o.chat(model, keep_alive=500.0)
                        console.print("[bold green]✓ Ollama server successfully started.[/]")
                        return True
                    except Exception:
                        pass
        except FileNotFoundError:
            console.print(
                Panel(
                    "[bold red1]Error: 'ollama' executable not found.[/]\n"
                    "Please install Ollama from [link]https://ollama.com[/link] and add it to your PATH.",
                    title="Missing Dependency",
                    border_style='red'
                )
            )
            return False
        except Exception as e:
            console.print(f"[red1]Failed to start Ollama server: {e}[/]")

        console.print(
            Panel(
                "[bold red1]Could not connect to Ollama server.[/]\n"
                "Please start it manually (e.g., run 'ollama serve' or open the Ollama app).",
                title="Connection Error",
                border_style='red'
            )
        )
        return False
