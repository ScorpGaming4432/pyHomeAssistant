import os
import sys
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Ollama host fix for Windows: 0.0.0.0 is an invalid destination address for client sockets
if os.environ.get("OLLAMA_HOST") in ("0.0.0.0", "0.0.0.0:11434"):
    os.environ["OLLAMA_HOST"] = "127.0.0.1"

import ollama as o
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from assistant.ollama import ensure_ollama_running
from assistant.state import build_chat_request_kwargs, build_system_prompt
from ollama_func import AVAILABLE_FUNCTIONS
from ui.console import get_console
from ui.panels import render_answer_panel, render_thinking_panel, show_goodbye, show_welcome

console = get_console()

ai_model = os.environ.get("AI_MODEL", "laguna-xs-2.1")
summ_model = os.environ.get("SUMM_MODEL", "phi4-mini-reasoning:latest")
history: list[dict[str, Any]] = [build_system_prompt()]
stream = True

DEFAULT_CHAT_OPTIONS = {
    "temperature": 0.6,
    "num_ctx": 131072,
    "num_predict": 65536,
    "top_k": 5,
    "top_p": 0.7,
}

CONCISE_CHAT_OPTIONS = {
    "temperature": 0.25,
    "num_ctx": 32768,
    "num_predict": 400,
    "top_k": 15,
    "top_p": 0.6,
}

CONCISE_OUTPUT_PROMPT = (
    "When responding, keep the final answer compact and easy to read aloud. "
    "Prefer short, direct sentences or a few bullet points, and avoid filler."
)

OPTION_ORDER = ("temperature", "top_k", "top_p", "num_ctx", "num_predict")


def coerce_chat_option(name: str, raw_value: str, current_value: Any) -> Any:
    try:
        if name in {"temperature", "top_p"}:
            return float(raw_value)
        if name in {"top_k", "num_ctx", "num_predict"}:
            return int(raw_value)
    except (TypeError, ValueError):
        pass
    return current_value


def configure_chat_options(current_options: dict[str, Any], console_instance: Console) -> dict[str, Any]:
    updated_options = dict(current_options)
    console_instance.print(
        Panel(
            "[bold cyan]Adjust the model settings below.[/]\n"
            "Press Enter to keep the current value.",
            title="⚙️ AI Options",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    for option_name in OPTION_ORDER:
        prompt = f"{option_name} [{updated_options[option_name]}]"
        raw_value = Prompt.ask(prompt, default=str(updated_options[option_name]), console=console_instance)
        updated_options[option_name] = coerce_chat_option(option_name, raw_value, updated_options[option_name])

    console_instance.print(
        Panel(
            "[bold green]AI settings updated.[/]\n"
            + "\n".join(f"{name}: {updated_options[name]}" for name in OPTION_ORDER),
            title="✅ Options Saved",
            border_style="green",
            padding=(1, 2),
        )
    )
    return updated_options


def render_streaming_response(response, console_instance: Console) -> tuple[str, str, list]:
    thinking_parts: list[str] = []
    content_parts: list[str] = []
    tool_calls: list = []

    if stream:
        display_parts: list = []
        with Live(console=console_instance, refresh_per_second=10, transient=False) as live:
            for chunk in response:
                if getattr(chunk.message, "thinking", None):
                    thinking_parts.append(chunk.message.thinking)
                if getattr(chunk.message, "content", None):
                    content_parts.append(chunk.message.content)
                if getattr(chunk.message, "tool_calls", None):
                    for tool in chunk.message.tool_calls:
                        if not any(
                                t.function.name == tool.function.name and t.function.arguments == tool.function.arguments
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
        render_thinking_panel(thinking, console_instance)
    if getattr(response.message, "content", None):
        content = response.message.content
        render_answer_panel(content, console_instance)
    if getattr(response.message, "tool_calls", None):
        tool_calls = response.message.tool_calls

    return getattr(response.message, "content", ""), getattr(response.message, "thinking", ""), tool_calls


def append_tool_result_to_history(history: list[dict[str, Any]], tool_name: str, output: Any) -> None:
    history.append({"role": "tool", "name": tool_name, "content": str(output)})


QUIT_COMMANDS = frozenset({"\\q", "bye", "exit", "quit"})


def is_quit_command(user_text: str) -> bool:
    return user_text.strip().lower() in QUIT_COMMANDS


def usr_wants_quits(user_text: str):
    if is_quit_command(user_text):
        raise KeyboardInterrupt("Good-bye!")
    return {"role": "user", "content": user_text}


def run_chat_loop() -> None:
    if not ensure_ollama_running(console, ai_model):
        sys.exit(1)

    show_welcome(console)
    active_chat_options: dict[str, Any] | None = None
    active_output_style = "default"

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]>>> [/ ]", console=console)
        except (KeyboardInterrupt, EOFError):
            show_goodbye(console)
            break

        user_input_trimmed = user_input.strip()
        if not user_input_trimmed:
            continue

        if user_input_trimmed.startswith("/"):
            command = user_input_trimmed.lower()

            if command == "/options":
                active_chat_options = configure_chat_options(active_chat_options or dict(DEFAULT_CHAT_OPTIONS), console)
                continue

            if command in {"/concise", "/compact"}:
                active_chat_options = dict(CONCISE_CHAT_OPTIONS)
                active_output_style = "concise"
                console.print(
                    Panel(
                        "[bold green]Compact reply mode enabled.[/]\n"
                        "Future answers will stay short and TTS-friendly.",
                        title="🗣️ Concise Mode",
                        border_style="green",
                        padding=(1, 2),
                    )
                )
                continue

            if command == "/normal":
                active_chat_options = None
                active_output_style = "default"
                console.print(
                    Panel(
                        "[bold cyan]Normal reply mode enabled.[/]",
                        title="🔄 Mode Reset",
                        border_style="cyan",
                        padding=(1, 2),
                    )
                )
                continue

            console.print("[bold red]Command not found.[/]")
            continue

        if is_quit_command(user_input):
            show_goodbye(console)
            break

        history.append({"role": "user", "content": user_input})

        while True:
            try:
                with console.status("[bold bright_black]🧠 Thinking...[/]"):
                    response = o.chat(
                        **build_chat_request_kwargs(
                            history,
                            AVAILABLE_FUNCTIONS,
                            ai_model,
                            stream,
                            active_chat_options or False,
                            options_override=active_chat_options,
                            output_style=active_output_style,
                            default_options=DEFAULT_CHAT_OPTIONS,
                            concise_output_prompt=CONCISE_OUTPUT_PROMPT,
                            concise_options=CONCISE_CHAT_OPTIONS,
                        )
                    )
            except Exception as e:
                console.print(f"[red1]Error during chat: {e}[/]")
                break

            full_content, thinking_text, tool_calls = render_streaming_response(response, console)

            assistant_msg: dict[str, Any] = {"role": "assistant", "content": full_content}
            if thinking_text:
                assistant_msg["thinking"] = thinking_text
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls

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
