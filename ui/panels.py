from rich.markdown import Markdown
from rich.panel import Panel
from rich.style import Style


WELCOME_STYLE = Style(color="blue")
GOODBYE_STYLE = Style(color="green")
THINKING_STYLE = Style(color="yellow")
STREAMING_RESPONSE_STYLE = Style(color="cyan")
ANSWER_STYLE = Style(color="green")
SETTINGS_STYLE = Style(color="cyan")
SETTINGS_SAVED_STYLE = Style(color="green")
CONCISE_MODE_STYLE = Style(color="green")
NORMAL_MODE_STYLE = Style(color="cyan")
TOOL_CALL_STYLE = Style(color="magenta")
TOOL_OUTPUT_STYLE = Style(color="green")
TOOL_ERROR_STYLE = Style(color="red")
DEPENDENCY_ERROR_STYLE = Style(color="red")
CONNECTION_ERROR_STYLE = Style(color="red")


def show_welcome(console) -> None:
    welcome = Panel(
        "[bold cyan]🤖 Dozo Assistant[/]\n"
        "Your knowledgeable, helpful AI companion.\n\n"
        "Type [yellow]\\q[/] or [yellow]bye[/] to exit.\n"
        "Use [yellow]/options[/] to tweak the AI settings, or [yellow]/concise[/] for compact replies.",
        title="Welcome",
        border_style=WELCOME_STYLE,
        padding=(1, 2),
    )
    console.print(welcome)


def show_goodbye(console) -> None:
    console.print('\n',
        Panel(
            "[bold green]👋 Thanks for chatting! Have a great day.[/]",
            border_style=GOODBYE_STYLE,
            padding=(1, 2),
        )
    )


def render_thinking_panel(text: str, console) -> None:
    console.print(Panel(text, title="🧠 Thinking", border_style=THINKING_STYLE))


def render_answer_panel(text: str, console) -> None:
    console.print(Panel(Markdown(text), title="💬 Answer", border_style=ANSWER_STYLE))
