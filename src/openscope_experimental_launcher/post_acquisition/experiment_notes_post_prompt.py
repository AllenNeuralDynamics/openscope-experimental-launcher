"""
Post-acquisition module to collect experiment notes from the user and save to the session folder.

This module prompts the user for final experiment notes/observations and appends them to a notes file (or session metadata) in the output session folder.
"""
import os
import datetime
from ..utils import param_utils

def run_post_acquisition(param_file):
    """
    Post-acquisition module to collect experiment notes from the user and save to the session folder.
    Args:
        param_file (str): Path to the parameter JSON file.
    Returns:
        int: 0 if notes were collected and saved, 1 otherwise.
    """
    try:
        params = param_utils.load_parameters(param_file=param_file)
        session_folder = params.get('output_session_folder') or params.get('output_root_folder')
        if not session_folder:
            print("No session or output folder found in parameters.")
            return 1
        notes = param_utils.get_user_input(
            "Enter final experiment notes/observations (optional)", default="", cast_func=str
        )
        if not notes:
            print("No notes entered.")
            return 0
        notes_file = os.path.join(session_folder, "experiment_notes.txt")
        timestamp = datetime.datetime.now().isoformat()
        with open(notes_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {notes}\n")
        print(f"Experiment notes saved to {notes_file}")
        return 0
    except Exception as e:
        print(f"Post-acquisition: Failed to collect experiment notes: {e}")
        return 1
