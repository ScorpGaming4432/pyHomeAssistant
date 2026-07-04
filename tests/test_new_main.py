import importlib.util
import io
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "new_main.py"


class FakeStreamChunk:
    def __init__(self, content="", thinking="", tool_calls=None):
        self.message = types.SimpleNamespace(
            content=content,
            thinking=thinking,
            tool_calls=tool_calls or [],
        )


class RecordingLive:
    instances = []

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.updates = []
        RecordingLive.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def update(self, renderable, refresh=False):
        self.updates.append((renderable, refresh))


class RenderStreamingResponseTests(unittest.TestCase):
    def setUp(self):
        RecordingLive.instances = []

        fake_ollama = types.ModuleType("ollama")
        fake_ollama.list = lambda: []
        fake_ollama.chat = lambda *args, **kwargs: []
        sys.modules["ollama"] = fake_ollama

        fake_ollama_func = types.ModuleType("ollama_func")
        fake_ollama_func.AVAILABLE_FUNCTIONS = {}
        sys.modules["ollama_func"] = fake_ollama_func

        spec = importlib.util.spec_from_file_location("new_main_under_test", MODULE_PATH)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_render_streaming_response_keeps_output_visible(self):
        stream = [
            FakeStreamChunk(content="Hello"),
            FakeStreamChunk(content=" world"),
        ]

        with patch.object(self.module, "Live", RecordingLive):
            content, thinking, tool_calls = self.module.render_streaming_response(
                stream,
                console=object(),
            )

        self.assertEqual(content, "Hello world")
        self.assertEqual(thinking, "")
        self.assertEqual(tool_calls, [])
        self.assertEqual(len(RecordingLive.instances), 1)
        self.assertFalse(RecordingLive.instances[0].kwargs["transient"])

    def test_build_chat_request_kwargs_uses_custom_options_only_when_enabled(self):
        default_kwargs = self.module.build_chat_request_kwargs(False, self.module.DEFAULT_CHAT_OPTIONS)
        custom_kwargs = self.module.build_chat_request_kwargs(True, self.module.DEFAULT_CHAT_OPTIONS)

        self.assertNotIn("options", default_kwargs)
        self.assertEqual(custom_kwargs["options"], self.module.DEFAULT_CHAT_OPTIONS)

    def test_configure_chat_options_updates_values_from_prompt(self):
        console = self.module.Console(file=io.StringIO(), force_terminal=False, color_system=None)

        with patch.object(self.module.Prompt, "ask", side_effect=["0.8", "12", "0.9", "2048", "1024"]):
            updated_options = self.module.configure_chat_options(self.module.DEFAULT_CHAT_OPTIONS.copy(), console)

        self.assertEqual(updated_options["temperature"], 0.8)
        self.assertEqual(updated_options["top_k"], 12)
        self.assertEqual(updated_options["top_p"], 0.9)
        self.assertEqual(updated_options["num_ctx"], 2048)
        self.assertEqual(updated_options["num_predict"], 1024)

    def test_tool_result_history_uses_name_field(self):
        history = []
        self.module.append_tool_result_to_history(history, "get_weather_forecast", "sunny")

        self.assertEqual(history[-1]["role"], "tool")
        self.assertEqual(history[-1]["name"], "get_weather_forecast")
        self.assertEqual(history[-1]["content"], "sunny")


if __name__ == "__main__":
    unittest.main()
