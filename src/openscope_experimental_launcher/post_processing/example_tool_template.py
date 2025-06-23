#!/usr/bin/env python3
"""
Example template for creating new post-processing tools.

This template shows the recommended structure for post-processing tools.
Copy this file and modify it to create new tools.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional


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


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Example post-processing tool template",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python example_tool_template.py /path/to/session_folder
  python example_tool_template.py /path/to/session_folder /path/to/output
        """
    )
    
    parser.add_argument(
        "session_folder",
        help="Path to session folder containing experiment data"
    )
    
    parser.add_argument(
        "output_folder",
        nargs='?',
        help="Optional output folder (default: session_folder/tool_output)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Process the session
    success = process_session(args.session_folder, args.output_folder)
    
    if success:
        logging.info("Processing completed successfully")
    else:
        logging.error("Processing failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
