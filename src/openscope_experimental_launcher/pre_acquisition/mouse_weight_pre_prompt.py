import logging
import json
import sys
import os
from datetime import datetime
from openscope_experimental_launcher.utils import param_utils

def run_pre_acquisition(param_file):
    """
    Pre-acquisition module to prompt for and record mouse weight before the experiment.
    Saves the weight to mouse_weight.csv in the session folder.
    Args:
        param_file (str): Path to the parameter JSON file.
    Returns:
        int: 0 if weight was collected and saved, 1 otherwise.
    """
    try:
        params = param_utils.load_parameters(param_file=param_file)
        weight = param_utils.get_user_input("Enter animal weight PRIOR to experiment [g]", default=None, cast_func=float)
        session_folder = params.get('output_session_folder') or params.get('output_root_folder')
        if not session_folder:
            logging.error("No session or output folder found in parameters.")
            return 1
        # If output_root_folder, create a session subfolder with timestamp
        if not os.path.exists(session_folder):
            os.makedirs(session_folder, exist_ok=True)
        weight_file = os.path.join(session_folder, "mouse_weight.csv")
        with open(weight_file, 'w') as f:
            f.write("timestamp,stage,weight_g\n")
            f.write(f"{datetime.now().isoformat()},pre,{weight}\n")
        logging.info(f"Pre-acquisition: Collected mouse weight {weight}g and saved to {weight_file}.")
        return 0
    except Exception as e:
        logging.error(f"Pre-acquisition: Failed to collect mouse weight: {e}")
        return 1
