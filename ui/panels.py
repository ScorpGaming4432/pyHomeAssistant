from rich.markdown import Markdown
from rich.panel import Panel


def show_welcome(console) -> None:
    welcome = Panel(
        "[bold cyan]🤖 Dozo Assistant[/]\n"
        "Your knowledgeable, helpful AI companion.\n\n"
        "Type [yellow]\\q[/] or [yellow]bye[/] to exit.\n"
        "Use [yellow]/options[/] to tweak the AI settings, or [yellow]/concise[/] for compact replies.",
        title="Welcome",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(welcome)


def show_goodbye(console) -> None:
    console.print(
        Panel(
            "[bold green]👋 Thanks for chatting! Have a great day.[/]",
            border_style="green",
            padding=(1, 2),
        )
    )


def render_thinking_panel(text: str, console) -> None:
    console.print(Panel(text, title="🧠 Thinking", border_style="yellow"))


def render_answer_panel(text: str, console) -> None:
    console.print(Panel(Markdown(text), title="💬 Answer", border_style="green"))
