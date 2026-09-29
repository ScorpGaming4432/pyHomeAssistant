import os
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def build_system_prompt() -> dict[str, str]:
    user = os.environ.get("ASSISTANT_USER_NAME", "User")
    pronouns = os.environ.get("ASSISTANT_USER_PRONOUNS", "they/them")
    location = os.environ.get("ASSISTANT_USER_LOCATION", "Unknown location")

    return {
        "role": "system",
        "content": f"""You are Dozo. You are a helpful home assistant with access to internet and tools that can help you complete simple and advanced tasks.
When receiving questions, you answer them using correct terminology given the context.
When receiving instructions, you execute them to the best of your abilities.
All of your responses must be as correct as you can provide them, making sure to only respond with information you know is factual.
When your safeguard catches a guideline violation, provide the best shortest answer on the topic that conforms to the guidelines.
Use the internet to fetch up-to-date information. Summarize the found content in concise language and highlight key findings. Present short balanced viewpoints on complex topics.
Use in-built functions when possible.
This is a debugging environment. Additional information about your environment include:
- User name: {user} ({pronouns})
- Location: {location}
Past this line additional instructions may follow.""",
    }


def build_chat_request_kwargs(
    history: list[dict[str, Any]],
    available_functions: dict[str, Any],
    ai_model: str,
    stream: bool,
    use_custom_options: bool | dict[str, Any],
    options_override: dict[str, Any] | None = None,
    output_style: str = "default",
    default_options: dict[str, Any] | None = None,
    concise_output_prompt: str | None = None,
    concise_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": ai_model,
        "stream": stream,
        "messages": list(history),
        "tools": list(available_functions.values()),
        "think": True,
        "keep_alive": 300.0,
    }
    if output_style == "concise" and concise_output_prompt is not None:
        kwargs["messages"] = [
            {"role": "system", "content": concise_output_prompt},
            *kwargs["messages"],
        ]
    if isinstance(use_custom_options, dict):
        kwargs["options"] = dict(use_custom_options)
    elif use_custom_options:
        kwargs["options"] = dict(options_override or (default_options or {}))
    return kwargs
