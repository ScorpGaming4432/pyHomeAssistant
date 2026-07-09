import os
import subprocess
import time

import ollama as o


def ensure_ollama_running(console) -> bool:
    # Fix for Windows
    if os.environ.get("OLLAMA_HOST") == "0.0.0.0":
        os.environ["OLLAMA_HOST"] = "127.0.0.1"

    try:
        console.print("[grey]Checking if Ollama server is working...[/]")
        o.list()
        return True
    except Exception:
        console.print("[bright_red]Ollama server [bold red3]not[/bold red3] detected[/]")
        console.print("[yellow3]Attempting to start Ollama server...[/]")
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for _ in range(30):
                time.sleep(1.0)
                try:
                    o.list()
                    console.print("[bold green]✓ Ollama server successfully started.[/]")
                    return True
                except Exception:
                    console.print("[grey46]Waiting...[/]")
        except FileNotFoundError:
            console.print(
                "[bold red1]Error: The 'ollama' executable was not found on your system.[/]\n[red]Please install Ollama (https://ollama.com) and make sure it is added to your PATH.[/]"
            )
            return False
        except Exception as e:
            console.print(f"[red1]Failed to start Ollama server automatically: {e}[/]")

        console.print("[bold red1]Error: Could not connect to Ollama server.[/]\n[red1]Please start Ollama manually (e.g., by running 'ollama serve' or opening the Ollama application).[/]")
        return False
