import logging
from typing import Any, Mapping


_DEFAULT_PROMPT = (
    "Waiting for operator input before proceeding.\n"
    "Confirm the rig is ready, then press Enter to continue..."
)


def run_pre_acquisition(params: Mapping[str, Any]) -> int:
    """Pause the launcher until an operator confirms readiness.

    Intended use: add to `pre_acquisition_pipeline` to block before starting Bonsai
    on an instrument rig.

        Module parameters (set via `module_parameters`):
        - `prompt` (str): Prompt shown to the operator.
        - `fail_if_no_input` (bool): If True, return non-zero when stdin is unavailable
            (non-interactive).

    Returns:
        int: 0 on success; 1 on failure.
    """

    prompt = params.get("prompt") or _DEFAULT_PROMPT
    fail_if_no_input = bool(params.get("fail_if_no_input", False))

    logging.info("Pre-acquisition: waiting for operator confirmation.")
    try:
        # Block until the user hits Enter.
        input(str(prompt) + "\n")
        logging.info("Pre-acquisition: operator confirmed; proceeding.")
        return 0
    except (EOFError, OSError):
        msg = "Pre-acquisition: stdin unavailable; cannot wait for operator input."
        if fail_if_no_input:
            logging.error(msg)
            return 1
        logging.warning(msg + " Proceeding without confirmation.")
        return 0
