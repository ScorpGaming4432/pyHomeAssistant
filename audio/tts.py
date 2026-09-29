import html
import os
import shutil
import subprocess
import sys
from typing import Any

import mistune


class Renderer(mistune.BaseRenderer):
    def render_children(self, children, state):
        return "".join(self.render_token(child, state) for child in children)

    def header(self, token, state):
        return self.heading(token, state)

    def heading(self, token, state):
        text = self.render_children(token.get("children", []), state)
        return f'<p><emphasis level="moderate">{text}</emphasis></p>\n'

    def emphasis(self, token, state):
        text = self.render_children(token.get("children", []), state)
        return f'<emphasis level="moderate">{text}</emphasis>'

    def strong(self, token, state):
        text = self.render_children(token.get("children", []), state)
        return f'<emphasis level="strong">{text}</emphasis>'

    def linebreak(self, token, state):
        return '<break time="400ms"/>\n'

    def thematic_break(self, token, state):
        return '<break time="600ms"/>\n'

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
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return proc.returncode == 0
    except Exception:
        return False
