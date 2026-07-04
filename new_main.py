from rich.traceback import install

install(show_locals=True)

import os
import subprocess
import sys
import time
from typing import Any, Iterator

from rich.console import Console, Group
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.prompt import Prompt
from rich.live import Live
from rich.status import Status
from rich.table import Table
from rich import box

console = Console()

# Ollama host fix for Windows
if os.environ.get('OLLAMA_HOST') == '0.0.0.0':
    os.environ['OLLAMA_HOST'] = '127.0.0.1'

import ollama as o
from ollama_func import AVAILABLE_FUNCTIONS

# ----------------------------------------------------------------------
# Utility functions
# ----------------------------------------------------------------------

def ensure_ollama_running() -> bool:
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
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            with console.status("[bold yellow]Waiting for server...[/]"):
                for _ in range(30):
                    time.sleep(0.5)
                    try:
                        o.list()
                        console.print("[bold green]✓ Ollama server successfully started.[/]")
                        return True
                    except Exception:
                        pass
        except FileNotFoundError:
            console.print(
                Panel(
                    "[bold red1]Error: 'ollama' executable not found.[/]\n"
                    "Please install Ollama from [link]https://ollama.com[/link] and add it to your PATH.",
                    title="❌ Missing Dependency",
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
                title="⚠️ Connection Error",
                border_style='red'
            )
        )
        return False

def usr_wants_quits(user_text: str):
    checks = frozenset({'\\q', 'bye'})
    if user_text.lower() in checks:
        raise KeyboardInterrupt('Good-bye!')
    return {'role': 'user', 'content': user_text}

def show_welcome():
    welcome = Panel(
        "[bold cyan]🤖 Dozo Assistant[/]\n"
        "Your knowledgeable, helpful AI companion.\n\n"
        "Type [yellow]\\q[/] or [yellow]bye[/] to exit.\n"
        "Use [yellow]/options[/] to tweak the AI settings, or [yellow]/concise[/] for compact replies.",
        title="Welcome",
        border_style='blue',
        padding=(1, 2)
    )
    console.print(welcome)

def show_goodbye():
    console.print(
        Panel(
            "[bold green]👋 Thanks for chatting! Have a great day.[/]",
            border_style='green',
            padding=(1, 2)
        )
    )

# ----------------------------------------------------------------------
# System prompt and model setup
# ----------------------------------------------------------------------
debug_environment_info_system = {
    'user': 'Dorpiee',
    'pref_pronouns': 'they/them',
    'lang_dependant_pronouns': 'she/her',
    'location': 'Chełm, Lubelskie, Poland',
    
}

system_prompt = {
    'role': 'system',
    'content': f"""You are Dozo. You are a helpful home assistant with access to internet and tools that can help you complete simple and advanced tasks.
When receiving questions, you answer them using correct terminology given the context.
When receiving instructions, you execute them to the best of your abilities.
All of your responses must be as correct as you can provide them, making sure to only respond with information you know is factual.
When your safeguard catches a guideline violation, provide the best shortest answer on the topic that conforms to the guidelines.
Use the internet to fetch up-to-date information. Summarize the found content in concise language and highlight key findings. Present short balanced viewpoints on complex topics.
Use in-built functions when possible.
This is a debugging environment. Additional information about your environment include:
- User name: {debug_environment_info_system['user']} ({debug_environment_info_system['pref_pronouns']}),
- Location information: {debug_environment_info_system['location']}
Past this line additional instructions may follow.""",
}

# ai_model = 'gemma4'
ai_model = 'laguna-xs-2.1'
history: list[dict[str, Any]] = [system_prompt]
stream = True   # keep streaming enabled for live updates
DEFAULT_CHAT_OPTIONS = {
    'temperature': 0.6,
    'num_ctx': 131072,
    'num_predict': 65536,
    'top_k': 5,
    'top_p': 0.7,
}

CONCISE_CHAT_OPTIONS = {
    'temperature': 0.25,
    'num_ctx': 32768,
    'num_predict': 400,
    'top_k': 15,
    'top_p': 0.6,
}

CONCISE_OUTPUT_PROMPT = (
    "When responding, keep the final answer compact and easy to read aloud. "
    "Prefer short, direct sentences or a few bullet points, and avoid filler."
)

OPTION_ORDER = ('temperature', 'top_k', 'top_p', 'num_ctx', 'num_predict')


def coerce_chat_option(name: str, raw_value: str, current_value: Any) -> Any:
    try:
        if name in {'temperature', 'top_p'}:
            return float(raw_value)
        if name in {'top_k', 'num_ctx', 'num_predict'}:
            return int(raw_value)
    except (TypeError, ValueError):
        pass
    return current_value


def configure_chat_options(current_options: dict[str, Any], console: Console) -> dict[str, Any]:
    updated_options = dict(current_options)
    console.print(
        Panel(
            "[bold cyan]Adjust the model settings below.[/]\n"
            "Press Enter to keep the current value.",
            title="⚙️ AI Options",
            border_style='cyan',
            padding=(1, 2),
        )
    )

    for option_name in OPTION_ORDER:
        prompt = f"{option_name} [{updated_options[option_name]}]"
        raw_value = Prompt.ask(prompt, default=str(updated_options[option_name]), console=console)
        updated_options[option_name] = coerce_chat_option(option_name, raw_value, updated_options[option_name])

    console.print(
        Panel(
            "[bold green]AI settings updated.[/]\n"
            + "\n".join(f"{name}: {updated_options[name]}" for name in OPTION_ORDER),
            title="✅ Options Saved",
            border_style='green',
            padding=(1, 2),
        )
    )
    return updated_options

# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------

def render_streaming_response(response, console: Console) -> tuple[str, str, list]:
    thinking_parts: list[str] = []
    content_parts: list[str] = []
    tool_calls: list = []

    if stream:
        display_parts: list = []
        with Live(console=console, refresh_per_second=10, transient=False) as live:
            for chunk in response:
                if getattr(chunk.message, "thinking", None):
                    thinking_parts.append(chunk.message.thinking)
                if getattr(chunk.message, "content", None):
                    content_parts.append(chunk.message.content)
                if getattr(chunk.message, "tool_calls", None):
                    for tool in chunk.message.tool_calls:
                        if not any(
                            t.function.name == tool.function.name and
                            t.function.arguments == tool.function.arguments
                            for t in tool_calls
                        ):
                            tool_calls.append(tool)

                display_parts = []
                if thinking_parts:
                    display_parts.append(
                        Panel(
                            "".join(thinking_parts),
                            title="🧠 Thinking",
                            border_style="bright_black",
                            padding=(0, 1),
                        )
                    )
                if content_parts:
                    display_parts.append(
                        Panel(
                            "".join(content_parts),
                            title="💬 Response (streaming)",
                            border_style="cyan",
                            padding=(0, 1),
                        )
                    )
                if not display_parts:
                    display_parts.append("[dim]Waiting for response...[/]")
                live.update(Group(*display_parts), refresh=True)

            full_content = "".join(content_parts)
            if full_content:
                live.update(
                    Panel(
                        Markdown(full_content),
                        title="💬 Answer",
                        border_style="green",
                        padding=(1, 2),
                    ),
                    refresh=True,
                )
            else:
                live.update("[dim]No response content received.[/]", refresh=True)

        return full_content, "".join(thinking_parts), tool_calls

    if getattr(response.message, "thinking", None):
        thinking = response.message.thinking
        console.print(Panel(thinking, title="🧠 Thinking", border_style="yellow"))
    if getattr(response.message, "content", None):
        content = response.message.content
        console.print(Panel(Markdown(content), title="💬 Answer", border_style="green"))
    if getattr(response.message, "tool_calls", None):
        tool_calls = response.message.tool_calls

    return getattr(response.message, "content", ""), getattr(response.message, "thinking", ""), tool_calls


def append_tool_result_to_history(history: list[dict[str, Any]], tool_name: str, output: Any) -> None:
    history.append({
        'role': 'tool',
        'name': tool_name,
        'content': str(output),
    })


def build_chat_request_kwargs(
    use_custom_options: bool | dict[str, Any],
    options_override: dict[str, Any] | None = None,
    output_style: str = "default",
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        'model': ai_model,
        'stream': stream,
        'messages': list(history),
        'tools': list(AVAILABLE_FUNCTIONS.values()),
        'think': True,
        'keep_alive': 300.0,
    }
    if output_style == "concise":
        kwargs['messages'] = [
            {'role': 'system', 'content': CONCISE_OUTPUT_PROMPT},
            *kwargs['messages'],
        ]
    if isinstance(use_custom_options, dict):
        kwargs['options'] = dict(use_custom_options)
    elif use_custom_options:
        kwargs['options'] = dict(options_override or DEFAULT_CHAT_OPTIONS)
    return kwargs


def run_chat_loop() -> None:
    if not ensure_ollama_running():
        sys.exit(1)

    show_welcome()
    active_chat_options: dict[str, Any] | None = None
    active_output_style = "default"

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]>>> [/ ]", console=console)
        except (KeyboardInterrupt, EOFError):
            show_goodbye()
            break

        command = user_input.strip().lower()

        if command == '/options':
            active_chat_options = configure_chat_options(
                active_chat_options or dict(DEFAULT_CHAT_OPTIONS),
                console,
            )
            continue

        if command in {'/concise', '/compact'}:
            active_chat_options = dict(CONCISE_CHAT_OPTIONS)
            active_output_style = 'concise'
            console.print(
                Panel(
                    "[bold green]Compact reply mode enabled.[/]\n"
                    "Future answers will stay short and TTS-friendly.",
                    title="🗣️ Concise Mode",
                    border_style='green',
                    padding=(1, 2),
                )
            )
            continue

        if command == '/normal':
            active_chat_options = None
            active_output_style = 'default'
            console.print(
                Panel(
                    "[bold cyan]Normal reply mode enabled.[/]",
                    title="🔄 Mode Reset",
                    border_style='cyan',
                    padding=(1, 2),
                )
            )
            continue

        try:
            user_msg = usr_wants_quits(user_input)
        except KeyboardInterrupt as e:
            console.print(e)
            show_goodbye()
            break

        history.append(user_msg)

        while True:
            try:
                with console.status("[bold bright_black]🧠 Thinking...[/]"):
                    response = o.chat(
                        **build_chat_request_kwargs(
                            active_chat_options or False,
                            options_override=active_chat_options,
                            output_style=active_output_style,
                        )
                    )
            except Exception as e:
                console.print(f"[red1]Error during chat: {e}[/]")
                break

            full_content, thinking_text, tool_calls = render_streaming_response(response, console)

            assistant_msg: dict[str, Any] = {'role': 'assistant', 'content': full_content}
            if thinking_text:
                assistant_msg['thinking'] = thinking_text
            if tool_calls:
                assistant_msg['tool_calls'] = tool_calls

            history.append(assistant_msg)

            if tool_calls:
                for tool in tool_calls:
                    function_to_call = AVAILABLE_FUNCTIONS.get(tool.function.name)
                    if function_to_call:
                        console.print(
                            Panel(
                                f"[bold]{tool.function.name}[/]\n[dim]Arguments: {tool.function.arguments}[/]",
                                title="🔧 Calling Function",
                                border_style="magenta",
                            )
                        )
                        try:
                            with console.status(f"[bold yellow]Executing {tool.function.name}...[/]"):
                                output = function_to_call(**tool.function.arguments)
                            console.print(
                                Panel(
                                    f"[green]{output}[/]",
                                    title="✅ Output",
                                    border_style="green",
                                )
                            )
                        except Exception as e:
                            output = f"Error: {e}"
                            console.print(
                                Panel(
                                    f"[red1]{output}[/]",
                                    title="❌ Error",
                                    border_style="red",
                                )
                            )
                        append_tool_result_to_history(history, tool.function.name, output)
                    else:
                        err_msg = f"Function {tool.function.name} not found"
                        console.print(f"[red1]{err_msg}[/]")
                        append_tool_result_to_history(history, tool.function.name, err_msg)
                console.print("[dim]----- Sending result back to model -----[/]\n")
                continue
            break


if __name__ == "__main__":
    run_chat_loop()