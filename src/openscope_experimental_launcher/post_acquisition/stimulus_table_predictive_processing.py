#!/usr/bin/env python3
"""
Predictive Processing Stimulus Table Post-Acquisition Tool

Simple script to convert orientation data from SLAP2 experiments into 
standardized stimulus tables for the OpenScope Predictive Processing project.

This does the essential work without all the launcher complexity:
- Reads orientation CSV files
- Loads HARP timing data if available  
- Creates comprehensive stimulus tables
- Generates analysis reports

Usage:
    python stimulus_table_predictive_processing.py <session_folder> [output_folder]
"""

# This file has been renamed. Please use stimulus_table_predictive_processing.py for all future development.

import os
import sys
import logging
from typing import Dict, Optional
from pathlib import Path
import pandas as pd
import numpy as np
import harp
import requests
import yaml
import io
from openscope_experimental_launcher.utils import param_utils

# HARP utility functions for timing alignment
def _get_who_am_i_list(url: str = "https://raw.githubusercontent.com/harp-tech/protocol/main/whoami.yml"):
    response = requests.get(url, allow_redirects=True, timeout=5)
    content = response.content.decode("utf-8")
    content = yaml.safe_load(content)
    devices = content["devices"]
    return devices

def _get_yml_from_who_am_i(who_am_i: int, release: str = "main") -> io.BytesIO:
    try:
        device = _get_who_am_i_list()[who_am_i]
    except KeyError as e:
        raise KeyError(f"WhoAmI {who_am_i} not found in whoami.yml") from e

    repository_url = device.get("repositoryUrl", None)

    if (repository_url is None):
        raise ValueError("Device's repositoryUrl not found in whoami.yml")
    else:  # attempt to get the device.yml from the repository
        _repo_hint_paths = [
            "{repository_url}/{release}/device.yml",
            "{repository_url}/{release}/software/bonsai/device.yml",
        ]

        yml = None
        for hint in _repo_hint_paths:
            url = hint.format(repository_url=repository_url, release=release)
            if "github.com" in url:
                url = url.replace("github.com", "raw.githubusercontent.com")
            response = requests.get(url, allow_redirects=True, timeout=5)
            if response.status_code == 200:
                yml = io.BytesIO(response.content)
                break
        if yml is None:
            raise FileNotFoundError("device.yml not found in any repository")
        else:
            return yml

def fetch_yml(harp_path):
    with open(harp_path / 'Behavior_0.bin', mode='rb') as reg_0:
        who_am_i = int(harp.read(reg_0).values[0][0])
        yml_bytes = _get_yml_from_who_am_i(who_am_i)
    yaml_content = yml_bytes.getvalue()
    with open(harp_path / "device.yml", "wb") as f:
        f.write(yaml_content)
    return harp_path / "device.yml"


def get_timing_data(harp_path: Path) -> Optional[Dict]:
    """
    Extract timing data from HARP files
    
    Parameters
    ----------
    harp_path : str or Path
        Path to the HARP data directory
    
    Returns
    -------
    timing_data : dict
        Dictionary containing timing information:
        - start_trial: Array of SLAP2 trial start times
        - end_trial: Array of SLAP2 trial end times
        - start_gratings: Array of stimulus presentation start times
        - time_reference: Reference time (time_0) for alignment
        - gratings_per_trial: List of arrays with grating start times for each trial
    """
    harp_path = Path(harp_path)
    
    # Ensure device.yml exists
    if not (harp_path / "device.yml").exists():
        logging.info("device.yml not found, fetching from the web")
        fetch_yml(harp_path)
    
    # Create HARP reader
    reader = harp.create_reader(harp_path)
    
    # Get photodiode and wheel data (analog inputs)
    analog_data = reader.AnalogData.read()
    analog_times = analog_data.index.to_numpy()
    photodiode_arr = analog_data["AnalogInput0"].to_numpy()
    wheel_arr = analog_data["Encoder"].to_numpy()
    
    # Get SLAP2 trial start times
    PulseDO0 = reader.PulseDO0.read()
    do0_arr = PulseDO0["PulseDO0"].to_numpy()
    do0_times = PulseDO0["PulseDO0"].index.to_numpy()
    
    # Get SLAP2 trial end times
    PulseDO1 = reader.PulseDO1.read()
    do1_arr = PulseDO1["PulseDO1"].to_numpy()
    do1_times = PulseDO1.index.to_numpy()
    
    # Get drifting grating start times
    PulseDO2 = reader.PulseDO2.read()
    do2_arr = PulseDO2["PulseDO2"].to_numpy()
    do2_times = PulseDO2.index.to_numpy()
    
    # Apply corrections for specific data issues (based on your original code)
    # Remove the first grating time as it's an edge case
    start_gratings = do2_times[1:]
    
    # Remove the first two pulses which are off due to edge issues
    start_trial = do0_times[2:]
    end_trial = do1_times[2:]
    
    # Set the time reference (time_0)
    time_reference = start_trial[0]
    
    # Calculate normalized times
    normalized_start_gratings = start_gratings - time_reference
    normalized_start_trial = start_trial - time_reference
    normalized_end_trial = end_trial - time_reference
    normalized_analog_times = analog_times - time_reference

    # Additional useful timing data
    photodiode_data = {
        'times': normalized_analog_times,
        'values': photodiode_arr
    }
    
    wheel_data = {
        'times': normalized_analog_times,
        'values': wheel_arr
    }
    
    timing_data = {
        'start_trial': start_trial,
        'end_trial': end_trial,
        'start_gratings': start_gratings,
        'time_reference': time_reference,
        'normalized_start_trial': normalized_start_trial,
        'normalized_end_trial': normalized_end_trial,
        'normalized_start_gratings': normalized_start_gratings,
        'photodiode': photodiode_data,
        'wheel': wheel_data
    }
    
    return timing_data


def convert_orientation_to_stimulus_table(session_folder: str, output_folder: Optional[str] = None) -> bool:
    """
    Convert orientation data to stimulus table - this is the core functionality.
    
    Args:
        session_folder: Path to session data folder
        output_folder: Optional output folder (defaults to session_folder/stimulus_table_output)
        
    Returns:
        True if successful, False otherwise
    """
    logging.info(f"Converting orientation data to stimulus table: {session_folder}")
    
    session_path = Path(session_folder)
    if not session_path.exists():
        logging.error(f"Session folder does not exist: {session_folder}")
        return False
    
    # Create output folder
    if output_folder is None:
        output_folder = session_path 
    output_path = Path(output_folder)
    output_path.mkdir(exist_ok=True)
    
    # Look for orientation data files
    orientation_files = [
        session_path / "orientations_orientations0.csv",
        session_path / "orientations_logger.csv"
    ]
    
    # Look for HARP timing data
    harp_path = session_path / ".harp"
    timing_data = None
    
    if harp_path.exists():
        try:
            logging.info(f"Found HARP data directory: {harp_path}")
            timing_data = get_timing_data(harp_path)
            if timing_data:
                logging.info(f"Loaded HARP timing data with {len(timing_data['normalized_start_gratings'])} presentations")
        except Exception as e:
            logging.warning(f"Failed to load HARP timing data: {e}")
            timing_data = None
    else:
        logging.info("No HARP data directory found")
    
    # Process orientation files
    stimulus_table = None
    
    for orientation_file in orientation_files:
        if orientation_file.exists():
            logging.info(f"Processing orientation data: {orientation_file}")
            
            try:
                # Load orientation data
                orientation_df = pd.read_csv(orientation_file, header=None)
                logging.info(f"Loaded {len(orientation_df)} orientation records")
                
                # Convert to stimulus table
                stimulus_presentations = []
                
                for i, row in orientation_df.iterrows():
                    # Extract grating parameters from CSV columns
                    # Column mapping for typical SLAP2 orientation data:
                    # 0: stimulus_id, 1: duration, 2: duration2?, 3: diameter,
                    # 4: x_pos, 5: y_pos, 6: contrast, 7: spatial_freq, 8: temporal_freq, 9: orientation
                    
                    stimulus_id = row.iloc[0] if len(row) > 0 else i
                    duration = row.iloc[1] if len(row) > 1 else 1.0
                    diameter = row.iloc[3] if len(row) > 3 else 360  # degrees
                    x_position = row.iloc[4] if len(row) > 4 else 0
                    y_position = row.iloc[5] if len(row) > 5 else 0
                    contrast = row.iloc[6] if len(row) > 6 else 1.0
                    spatial_frequency = row.iloc[7] if len(row) > 7 else 0.04  # cycles/degree
                    temporal_frequency = row.iloc[8] if len(row) > 8 else 2.0  # Hz
                    orientation = row.iloc[9] if len(row) > 9 else 0  # radians
                    
                    # Convert orientation from radians to degrees
                    orientation_degrees = np.degrees(orientation) if orientation > 6.28 else orientation * 180 / np.pi
                    
                    # Calculate timing
                    if timing_data is not None and i < len(timing_data['normalized_start_gratings']):
                        start_time = float(timing_data['normalized_start_gratings'][i])
                        stop_time = start_time + duration
                    else:
                        raise ValueError("Timing data not available or insufficient for all presentations")
                    
                    # Create stimulus presentation record
                    presentation = {
                        'stimulus_id': int(stimulus_id),
                        'start_time': start_time,
                        'stop_time': stop_time,
                        'duration': float(duration),
                        'orientation': float(orientation),
                        'orientation_degrees': float(orientation_degrees),
                        'diameter': float(diameter),
                        'x_position': float(x_position),
                        'y_position': float(y_position),
                        'contrast': float(contrast),
                        'spatial_frequency': float(spatial_frequency),
                        'temporal_frequency': float(temporal_frequency),
                        'trial': 1
                    }
                    stimulus_presentations.append(presentation)
                
                stimulus_table = pd.DataFrame(stimulus_presentations)
                break  # Found and processed data successfully
                
            except Exception as e:
                logging.warning(f"Failed to process {orientation_file}: {e}")
                continue
    
    if stimulus_table is None:
        logging.error("No usable orientation data found")
        return False
    
    # Save stimulus table
    csv_path = output_path / "stimulus_table.csv"
    stimulus_table.to_csv(csv_path, index=False)
    logging.info(f"Stimulus table saved to: {csv_path}")
    return True


def run_post_acquisition(param_file: str = None, overrides: dict = None) -> int:
    """
    Main entry point for stimulus table conversion post-acquisition.
    Loads parameters, prompts for missing fields, and runs conversion.
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
    # Call the main conversion logic
    if not convert_orientation_to_stimulus_table(session_folder):
        logging.error("Failed to convert orientation data to stimulus table")
        return 1
    logging.info("Stimulus table conversion completed successfully for session: %s", session_folder)
    return 0
