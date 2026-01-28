import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

def get_user_input(prompt: str, default=None, cast_func=str):
    """
    Generic user input function for CLI, with default and type casting.
    Handles non-interactive environments by returning the default and logging a message.
    """
    try:
        val = input(f"{prompt} [{default}]: ")
        if val.strip() == "":
            return cast_func(default)
        return cast_func(val)
    except (EOFError, OSError):
        logging.info(f"Input not available for prompt '{prompt}', using default: {default}")
        return cast_func(default)


def load_parameters(
    param_file: Optional[Union[str, Path, Mapping[str, Any]]] = None,
    overrides: Optional[Dict[str, Any]] = None,
    required_fields: Optional[list] = None,
    defaults: Optional[Dict[str, Any]] = None,
    help_texts: Optional[Dict[str, str]] = None,
    prompt_func: Callable = get_user_input,
) -> Dict[str, Any]:
    """
    Flexible parameter loader for OpenScope workflows.
    Loads parameters from a JSON file, applies overrides, and prompts for missing required fields.
    Returns a dictionary of parameters.
    """
    params: Dict[str, Any] = {}
    if param_file:
        if isinstance(param_file, Mapping):
            params.update(param_file)
        else:
            with open(Path(param_file)) as f:
                params.update(json.load(f))
    if overrides:
        params.update(overrides)
    # Prompt for missing required fields
    if required_fields:
        for field in required_fields:
            if field not in params or params[field] is None:
                default = defaults.get(field, "") if defaults else ""
                help_text = help_texts.get(field, "") if help_texts else ""
                prompt = f"{field} ({help_text})" if help_text else field
                params[field] = prompt_func(prompt, default)
    return params
