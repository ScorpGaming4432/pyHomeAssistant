import mistune
import html
from rich.traceback import install
# from whisper import Whisper

install(show_locals=True)

import os
import shutil
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

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

console = Console()

# Ollama host fix for Windows
if os.environ.get('OLLAMA_HOST') == '0.0.0.0':
    os.environ['OLLAMA_HOST'] = '127.0.0.1'

import ollama as o
from ollama_func import AVAILABLE_FUNCTIONS

# ----------------------------------------------------------------------
# Utility functions
# ----------------------------------------------------------------------
class Renderer(mistune.BaseRenderer):
    def render_children(self, children, state):
        return "".join(self.render_token(child, state) for child in children)

    def header(self, token, state):
        return self.heading(token, state)

    def heading(self, token, state):
        text = self.render_children(token.get("children", []), state)
        return f"<p><emphasis level=\"moderate\">{text}</emphasis></p>\n"

    def emphasis(self, token, state):
        text = self.render_children(token.get("children", []), state)
        return f"<emphasis level=\"moderate\">{text}</emphasis>"

    def strong(self, token, state):
        text = self.render_children(token.get("children", []), state)
        return f"<emphasis level=\"strong\">{text}</emphasis>"

    def linebreak(self, token, state):
        return "<break time=\"400ms\"/>\n"

    def thematic_break(self, token, state):
        return "<break time=\"600ms\"/>\n"

    def image(self, token, state):
        alt_text = token.get("alt") or token.get("text") or "image"
        return f"image of {alt_text}"

    def paragraph(self, token, state):
        text = self.render_children(token.get("children", []), state)
        return f"<p>{text}</p>\n"

    def blank_line(self, token, state):
        return ""

    def list(self, token, state):
        return self.render_children(token.get("children", []), state)

    def list_item(self, token, state):
        text = self.render_children(token.get("children", []), state)
        return f"- {text}.\n"

    def block_text(self, token, state):
        return self.render_children(token.get("children", []), state)

    def footnote_ref(self, token, state):
        return token.get("key") or ""

    def autolink(self, token, state):
        return ""

    def link(self, token, state):
        return self.render_children(token.get("children", []), state)

    def text(self, token, state):
        return html.escape(token.get("raw", ""))

    def block_code(self, token, state):
        return f"<p>{self.text(token, state)}</p>\n"

    def codespan(self, token, state):
        return self.text(token, state)
    
    def softbreak(self, token, state):
        return ".\n"


def find_espeak_executable(configured_path: str | None = None) -> str | None:
    if configured_path and os.path.exists(configured_path):
        return configured_path
    env_path = os.environ.get("ESPEAK_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    which_path = shutil.which("espeak-ng") or shutil.which("espeak")
    if which_path:
        return which_path
    for candidate in [
        r"C:\Program Files\eSpeak NG\espeak-ng.exe",
        r"C:\Program Files (x86)\eSpeak NG\espeak-ng.exe",
        r"C:\Program Files\eSpeak\command_line\espeak.exe",
    ]:
        if os.path.exists(candidate):
            return candidate
    return None


def play_tts(words: str | None = None, markdown: bool = True, path: str | None = None) -> bool:
    if words is None:
        text_to_speak = "\n".join(sys.stdin.readlines())
    else:
        text_to_speak = str(words)

    if not text_to_speak.strip():
        return False

    exe_path = find_espeak_executable(path)
    if not exe_path:
        console.print("[dim red]eSpeak executable not found on system.[/]")
        return False

    if markdown:
        renderer = Renderer()
        try:
            md = mistune.create_markdown(renderer=renderer)
        except AttributeError:
            md = mistune.Markdown(renderer=renderer)
        out_text = md(text_to_speak)
    else:
        out_text = html.escape(text_to_speak)

    ssml = f"<speak>{out_text}</speak>"

    try:
        proc = subprocess.run(
            [exe_path, "-v", "en-us", "-m", "-b", "1"],
            input=ssml.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        return proc.returncode == 0
    except Exception:
        return False
        

def ensure_ollama_running() -> bool:
    try:
        console.print("[cyan]Checking if Ollama server is working...[/]")
        o.list()
        # o.chat(summ_model, keep_alive=500.0)
        o.chat(ai_model, keep_alive=500.0)
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

_WHISPER_MODEL = None


def ensure_whisper():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL
    try:
        import whisper
        with console.status("[bold yellow]Loading Whisper model (medium.en)...[/]"):
            _WHISPER_MODEL = whisper.load_model("medium.en")
        return _WHISPER_MODEL
    except Exception as e:
        console.print(f"[dim red]Failed to load Whisper: {e}[/]")
        return None


QUIT_COMMANDS = frozenset({'\\q', 'bye', 'exit', 'quit'})


def is_quit_command(user_text: str) -> bool:
    return user_text.strip().lower() in QUIT_COMMANDS


# def usr_wants_quits(user_text: str):
#     if is_quit_command(user_text):
#         raise KeyboardInterrupt('Good-bye!')
#     return {'role': 'user', 'content': user_text}

def show_welcome():
    welcome = Panel(
        "[bold cyan]🤖 Dozo Assistant[/]\n"
        "Your knowledgeable, helpful AI companion.\n\n"
        "Type [bright_yellow]\\q[/] or [bright_yellow]bye[/] to exit.\n"
        "Use [bright_yellow]/options[/] to tweak the AI settings, or [bright_yellow]/concise[/] for compact replies.\n"
        "To use microphone input, type [bright_yellow]/stt[/] [bright_black](it might be useful with the [yellow]/concise[/] option)[/]",
        title="Welcome",
        border_style='blue',
        padding=(1, 2)
    )
    console.print(welcome)

def show_goodbye():
    
    console.print("\n",
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
    'user': os.environ.get('ASSISTANT_USER_NAME', 'User'),
    'pref_pronouns': os.environ.get('ASSISTANT_USER_PRONOUNS', 'they/them'),
    'lang_dependant_pronouns': os.environ.get('ASSISTANT_LANG_PRONOUNS', 'she/her'),
    'location': os.environ.get('ASSISTANT_USER_LOCATION', 'Unknown location'),
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
- User name: {debug_environment_info_system['user']} ({debug_environment_info_system['pref_pronouns']})
Past this line additional instructions may follow.""",
}

ai_model = os.environ.get('AI_MODEL', 'laguna-xs-2.1')
summ_model = os.environ.get('SUMM_MODEL', 'phi4-mini-reasoning:latest')
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
            console.print("exit")
            show_goodbye()
            break

            
        user_input_trimmed = user_input.strip()
        if not user_input_trimmed:
            continue

        if user_input_trimmed.startswith('/'):
            command = user_input_trimmed.lower()

            if command == '/options':
                active_chat_options = configure_chat_options(
                    active_chat_options or dict(DEFAULT_CHAT_OPTIONS),
                    console,
                )
                continue

            elif command in {'/concise', '/compact'}:
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

            elif command == '/normal':
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

            elif command == '/stt':
                whisper_model = ensure_whisper()
                if not whisper_model:
                    console.print("[red]Unable to load Whisper model.[/]")
                    continue

                recorder = ".\\audio_device.exe" if os.path.exists(".\\audio_device.exe") else "audio_device.exe"
                if not os.path.exists(recorder):
                    console.print("[bold red]Recording executable (audio_device.exe) not found.[/]")
                    continue

                console.print("[bold cyan]Whisper engaged! Recording...[/]")
                subprocess.call([recorder])

                if not os.path.exists("input.wav"):
                    console.print("[bold red]Recording file 'input.wav' was not created.[/]")
                    continue

                try:
                    transcription = whisper_model.transcribe("input.wav").get('text', '').strip()
                except Exception as e:
                    console.print(f"[bold red]Transcription failed: {e}[/]")
                    continue

                if not transcription:
                    console.print("[yellow]No speech detected in recording.[/]")
                    continue

                user_input = transcription
                console.print(f"[cyan]<<< : [/]{user_input}")

            else:
                console.print("[bold red]Command not found.[/]")
                continue

        if is_quit_command(user_input):
            show_goodbye()
            break

        history.append({'role': 'user', 'content': user_input})

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
                        append_tool_result_to_history(history, tool.function.name, str(output))
                    else:
                        err_msg = f"Function {tool.function.name} not found"
                        console.print(f"[red1]{err_msg}[/]")
                        append_tool_result_to_history(history, tool.function.name, err_msg)
                console.print("[dim]----- Sending result back to model -----[/]\n")
                continue
            break
        console.print("[cyan]Playing back the content...[/]")
        if not play_tts(words=history[-1]['content'], markdown=True): console.print("[red]Something went wrong inside tts![/]")
        


if __name__ == "__main__":
    run_chat_loop()