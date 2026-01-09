import builtins

from openscope_experimental_launcher.pre_acquisition import wait_for_user_input


def test_wait_for_user_input_blocks_and_continues(monkeypatch):
    captured = {}

    def fake_input(prompt: str):
        captured["prompt"] = prompt
        return ""

    monkeypatch.setattr(builtins, "input", fake_input)

    custom_prompt = "Ready to start Bonsai? Press Enter"
    exit_code = wait_for_user_input.run_pre_acquisition({"prompt": custom_prompt})
    assert exit_code == 0
    assert custom_prompt in captured["prompt"]


def test_wait_for_user_input_noninteractive_defaults_to_continue(monkeypatch):
    def raising_input(_prompt: str):
        raise EOFError("stdin closed")

    monkeypatch.setattr(builtins, "input", raising_input)

    exit_code = wait_for_user_input.run_pre_acquisition({"fail_if_no_input": False})
    assert exit_code == 0


def test_wait_for_user_input_noninteractive_can_fail(monkeypatch):
    def raising_input(_prompt: str):
        raise EOFError("stdin closed")

    monkeypatch.setattr(builtins, "input", raising_input)

    exit_code = wait_for_user_input.run_pre_acquisition({"fail_if_no_input": True})
    assert exit_code == 1
