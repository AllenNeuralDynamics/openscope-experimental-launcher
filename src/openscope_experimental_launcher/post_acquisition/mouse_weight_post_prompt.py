import logging
import json
import sys
import os
from datetime import datetime
from openscope_experimental_launcher.utils import param_utils

def run_post_acquisition(param_file):
    """
    Post-acquisition module to prompt for and record mouse weight after the experiment.
    Appends the weight to mouse_weight.csv in the session folder.
    Args:
        param_file (str): Path to the parameter JSON file.
    Returns:
        int: 0 if weight was collected and saved, 1 otherwise.
    """
    try:
        params = param_utils.load_parameters(param_file=param_file)
        weight = param_utils.get_user_input("Enter animal weight AFTER experiment [g]", default=None, cast_func=float)
        session_folder = params.get('output_session_folder') or params.get('output_root_folder')
        if not session_folder:
            logging.error("No session or output folder found in parameters.")
            return 1
        weight_file = os.path.join(session_folder, "mouse_weight.csv")
        # If file does not exist, create and write header
        write_header = not os.path.exists(weight_file)
        with open(weight_file, 'a') as f:
            if write_header:
                f.write("timestamp,stage,weight_g\n")
            f.write(f"{datetime.now().isoformat()},post,{weight}\n")
        logging.info(f"Post-acquisition: Collected mouse weight {weight}g and appended to {weight_file}.")
        return 0
    except Exception as e:
        logging.error(f"Post-acquisition: Failed to collect mouse weight: {e}")
        return 1
