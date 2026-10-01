import importlib
import sys
import types

from rich.style import Style


def test_modular_ui_and_chat_modules_are_importable():
    fake_ollama = types.ModuleType("ollama")
    fake_ollama.list = lambda: []
    fake_ollama.chat = lambda *args, **kwargs: []
    sys.modules["ollama"] = fake_ollama

    fake_ollama_func = types.ModuleType("ollama_func")
    fake_ollama_func.AVAILABLE_FUNCTIONS = {}
    sys.modules["ollama_func"] = fake_ollama_func

    ui_console = importlib.import_module("ui.console")
    ui_panels = importlib.import_module("ui.panels")
    assistant_ollama = importlib.import_module("assistant.ollama")
    assistant_chat = importlib.import_module("assistant.chat")

    assert hasattr(ui_console, "get_console")
    assert hasattr(ui_panels, "show_welcome")
    assert hasattr(assistant_ollama, "ensure_ollama_running")
    assert hasattr(assistant_chat, "run_chat_loop")


def test_panel_helpers_use_shared_rich_styles():
    from ui import panels

    class RecordingConsole:
        renderable = None

        def print(self, *renderables):
            self.renderable = renderables[-1]

    style_names = (
        "WELCOME_STYLE",
        "GOODBYE_STYLE",
        "THINKING_STYLE",
        "STREAMING_RESPONSE_STYLE",
        "ANSWER_STYLE",
        "SETTINGS_STYLE",
        "SETTINGS_SAVED_STYLE",
        "CONCISE_MODE_STYLE",
        "NORMAL_MODE_STYLE",
        "TOOL_CALL_STYLE",
        "TOOL_OUTPUT_STYLE",
        "TOOL_ERROR_STYLE",
        "DEPENDENCY_ERROR_STYLE",
        "CONNECTION_ERROR_STYLE",
    )
    assert all(isinstance(getattr(panels, name), Style) for name in style_names)

    panel_helpers = (
        (panels.show_welcome, None, panels.WELCOME_STYLE),
        (panels.show_goodbye, None, panels.GOODBYE_STYLE),
        (panels.render_thinking_panel, "Thinking", panels.THINKING_STYLE),
        (panels.render_answer_panel, "Answer", panels.ANSWER_STYLE),
    )
    for helper, text, expected_style in panel_helpers:
        console = RecordingConsole()
        if text is None:
            helper(console)
        else:
            helper(text, console)
        assert console.renderable.border_style is expected_style
