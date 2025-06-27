#!/usr/bin/env python3
"""
Example template for creating new post-processing tools.

This template shows the recommended structure for post-processing tools.
Copy this file and modify it to create new tools.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional
from openscope_experimental_launcher.utils import param_utils


def process_session(session_folder: str, output_folder: Optional[str] = None) -> bool:
    """
    Process session data - REPLACE THIS WITH YOUR ACTUAL PROCESSING LOGIC.
    
    Args:
        session_folder: Path to session folder containing experiment data
        output_folder: Optional output folder (defaults to session_folder/tool_output)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        session_path = Path(session_folder)
        if not session_path.exists():
            logging.error(f"Session folder does not exist: {session_folder}")
            return False
            
        # Set up output directory
        if output_folder is None:
            output_folder = session_path / "tool_output"  # Change this name
        output_path = Path(output_folder)
        output_path.mkdir(exist_ok=True)
        
        logging.info(f"Processing session: {session_path}")
        logging.info(f"Output directory: {output_path}")
        
        # TODO: Add your processing logic here
        # For example:
        # 1. Look for specific input files in session_path
        # 2. Process the data
        # 3. Write output files to output_path
        # 4. Generate a report

        logging.info(f"Processing completed successfully")
        return True
        
    except Exception as e:
        logging.error(f"Processing failed: {e}")
        return False

def run_postprocessing(param_file: str = None, overrides: dict = None) -> int:
    """
    Main entry point for example post-processing tool.
    Loads parameters, prompts for missing fields, and runs processing.
    Returns 0 on success, nonzero on error.
    """
    import logging
    from pathlib import Path
    from openscope_experimental_launcher.utils import param_utils
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    required_fields = ["output_session_folder"]
    defaults = {}
    help_texts = {"output_session_folder": "Session output folder (from launcher)"}
    params = param_utils.load_parameters(
        param_file=param_file,
        overrides=overrides,
        required_fields=required_fields,
        defaults=defaults,
        help_texts=help_texts
    )
    session_folder = params["output_session_folder"]
    if not Path(session_folder).exists():
        logging.error(f"Session folder does not exist: {session_folder}")
        return 1
    # Call the main processing logic
    if not process_session(session_folder):
        logging.error("Processing failed")
        return 1
    logging.info("Processing completed successfully")
    return 0

if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser(
        description="Example post-processing tool template (now using unified parameter file)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python example_tool_template.py processed_parameters.json
        """
    )
    parser.add_argument("param_file", help="Path to processed_parameters.json from the launcher")
    args = parser.parse_args()
    sys.exit(run_postprocessing(param_file=args.param_file))
