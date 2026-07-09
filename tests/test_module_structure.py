import importlib
import sys
import types


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
