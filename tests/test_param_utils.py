import io
import sys
import json
import builtins
import pytest
from openscope_experimental_launcher.utils import param_utils

def test_load_parameters_from_file(tmp_path):
    param_file = tmp_path / "params.json"
    param_file.write_text(json.dumps({"foo": 1, "bar": "baz"}))
    params = param_utils.load_parameters(str(param_file))
    assert params["foo"] == 1
    assert params["bar"] == "baz"


def test_load_parameters_from_mapping():
    params = param_utils.load_parameters({"foo": 1, "bar": "baz"})
    assert params["foo"] == 1
    assert params["bar"] == "baz"

def test_load_parameters_with_overrides(tmp_path):
    param_file = tmp_path / "params.json"
    param_file.write_text(json.dumps({"foo": 1}))
    params = param_utils.load_parameters(str(param_file), overrides={"foo": 2, "bar": "baz"})
    assert params["foo"] == 2
    assert params["bar"] == "baz"

def test_load_parameters_prompt(monkeypatch):
    # Simulate user pressing Enter (accept default)
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    params = param_utils.load_parameters(
        param_file=None,
        overrides=None,
        required_fields=["foo"],
        defaults={"foo": "bar"},
        help_texts={"foo": "help for foo"},
    )
    assert params["foo"] == "bar"

def test_load_parameters_prompt_custom(monkeypatch):
    # Simulate user entering a value
    monkeypatch.setattr("builtins.input", lambda prompt: "42")
    params = param_utils.load_parameters(
        param_file=None,
        overrides=None,
        required_fields=["foo"],
        defaults={"foo": 0},
        help_texts={"foo": "help for foo"},
        prompt_func=lambda prompt, default: int(input(prompt)) if default == 0 else input(prompt)
    )
    assert params["foo"] == 42
