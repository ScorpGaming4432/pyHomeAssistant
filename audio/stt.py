import os
import shutil
import subprocess
from typing import Any

_WHISPER_MODEL = None


def find_recorder_executable() -> str | None:
    candidates = [
        os.path.join(".", "audio_device.exe"),
        os.path.join(".", "mic-wav", "audio_device.exe"),
        os.path.join(os.path.dirname(__file__), "..", "audio_device.exe"),
        os.path.join(os.path.dirname(__file__), "..", "mic-wav", "audio_device.exe"),
    ]
    for candidate in candidates:
        norm = os.path.normpath(candidate)
        if os.path.isfile(norm):
            return norm
    return shutil.which("audio_device")


def ensure_whisper(console=None, model_name: str = "medium.en"):
    global _WHISPER_MODEL
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL
    try:
        import whisper
        if console:
            with console.status(f"[bold yellow]Loading Whisper model ({model_name})...[/]"):
                _WHISPER_MODEL = whisper.load_model(model_name)
        else:
            _WHISPER_MODEL = whisper.load_model(model_name)
        return _WHISPER_MODEL
    except Exception as e:
        if console:
            console.print(f"[dim red]Failed to load Whisper: {e}[/]")
        return None


def record_audio(output_file: str = "input.wav", recorder_path: str | None = None) -> bool:
    exe = recorder_path or find_recorder_executable()
    if not exe:
        return False

    try:
        code = subprocess.call([exe])
        return code == 0 and os.path.exists(output_file)
    except Exception:
        return False


def transcribe_audio(whisper_model: Any, audio_path: str = "input.wav") -> str:
    if not os.path.exists(audio_path):
        return ""
    try:
        result = whisper_model.transcribe(audio_path)
        return result.get("text", "").strip()
    except Exception:
        return ""
