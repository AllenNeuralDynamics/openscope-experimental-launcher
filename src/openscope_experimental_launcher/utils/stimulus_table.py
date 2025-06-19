"""
Functional stimulus table generation utilities.

This module provides functions for creating trial-by-trial stimulus tables
from SLAP2 experiment data, replacing the class-based approach.
"""

import os
import logging
import pandas as pd
from typing import Dict, List, Optional, Any


def generate_slap2_stimulus_table(params: Dict[str, Any], 
                                 session_output_path: str) -> Optional[pd.DataFrame]:
    """
    Generate a stimulus table for SLAP2 experiments from parameters or Bonsai output.
    
    Args:
        params: Experiment parameters
        session_output_path: Path to session output file
        
    Returns:
        DataFrame containing stimulus table or None if generation failed
    """
    try:
        # Try to load existing Bonsai output first
        bonsai_output_table = _load_bonsai_output(session_output_path, params)
        
        if bonsai_output_table is not None:
            logging.info("Using stimulus table from Bonsai output")
            return bonsai_output_table
        else:
            logging.info("Generating mock stimulus table from parameters")
            return _generate_mock_stimulus_table(params)
        
    except Exception as e:
        logging.error(f"Failed to generate stimulus table: {e}")
        return None


def save_stimulus_table(stimulus_table: pd.DataFrame, output_path: str) -> bool:
    """
    Save stimulus table to CSV file.
    
    Args:
        stimulus_table: DataFrame containing stimulus table
        output_path: Path to save the CSV file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        stimulus_table.to_csv(output_path, index=False)
        logging.info(f"Stimulus table saved to: {output_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to save stimulus table: {e}")
        return False


def get_trial_statistics(stimulus_table: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate trial statistics from stimulus table.
    
    Args:
        stimulus_table: DataFrame containing stimulus table
        
    Returns:
        Dictionary containing trial statistics
    """
    try:
        stats = {
            'total_trials': len(stimulus_table),
            'successful_trials': stimulus_table.get('success', pd.Series([True] * len(stimulus_table))).sum(),
            'trial_types': stimulus_table.get('stimulus_type', pd.Series(['unknown'] * len(stimulus_table))).value_counts().to_dict(),
            'average_trial_duration': 0.0,
            'total_experiment_duration': 0.0
        }
        
        # Calculate timing statistics if available
        if 'stimulus_start_time' in stimulus_table.columns and 'stimulus_end_time' in stimulus_table.columns:
            durations = stimulus_table['stimulus_end_time'] - stimulus_table['stimulus_start_time']
            stats['average_trial_duration'] = durations.mean()
            
            if len(stimulus_table) > 0:
                stats['total_experiment_duration'] = (
                    stimulus_table['stimulus_end_time'].iloc[-1] - 
                    stimulus_table['stimulus_start_time'].iloc[0]
                )
        
        return stats
        
    except Exception as e:
        logging.error(f"Failed to calculate trial statistics: {e}")
        return {'error': str(e)}


def _load_bonsai_output(session_output_path: str, 
                       params: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Load stimulus table from Bonsai output files.
    
    Args:
        session_output_path: Path to session output file
        params: Experiment parameters
        
    Returns:
        DataFrame from Bonsai output or None if not found/failed
    """
    try:
        # Look for Bonsai output files in the same directory
        output_dir = os.path.dirname(session_output_path)
        session_uuid = params.get("session_uuid", "")
        
        # Common Bonsai output file patterns
        possible_files = [
            os.path.join(output_dir, f"{session_uuid}_trials.csv"),
            os.path.join(output_dir, f"{session_uuid}_stimulus.csv"),
            os.path.join(output_dir, "trials.csv"),
            os.path.join(output_dir, "stimulus_table.csv"),
            os.path.join(output_dir, "trial_data.csv")
        ]
        
        for file_path in possible_files:
            if os.path.exists(file_path):
                logging.info(f"Found Bonsai output file: {file_path}")
                try:
                    df = pd.read_csv(file_path)
                    # Validate that it has expected columns
                    if _validate_bonsai_output(df):
                        return _standardize_bonsai_output(df)
                    else:
                        logging.warning(f"Bonsai output file {file_path} does not have expected format")
                except Exception as e:
                    logging.warning(f"Failed to read Bonsai output file {file_path}: {e}")
        
        return None
        
    except Exception as e:
        logging.error(f"Error loading Bonsai output: {e}")
        return None


def _validate_bonsai_output(df: pd.DataFrame) -> bool:
    """
    Validate that a DataFrame has the expected Bonsai output format.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Check for minimum required columns (flexible naming)
    required_columns_patterns = [
        ['trial', 'start', 'time'],  # trial info and timing
        ['stimulus', 'stim'],        # stimulus information
    ]
    
    columns_lower = [col.lower() for col in df.columns]
    
    for pattern in required_columns_patterns:
        found = False
        for col in columns_lower:
            if any(p in col for p in pattern):
                found = True
                break
        if not found:
            return False
    
    return True


def _standardize_bonsai_output(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize Bonsai output to our expected format.
    
    Args:
        df: Raw Bonsai output DataFrame
        
    Returns:
        Standardized DataFrame
    """
    # Create mapping from Bonsai columns to our standard columns
    column_mapping = {}
    columns_lower = {col.lower(): col for col in df.columns}
    
    # Map trial index
    for pattern in ['trial_index', 'trial_number', 'trial', 'index']:
        if pattern in columns_lower:
            column_mapping['trial_index'] = columns_lower[pattern]
            break
    
    # Map start time
    for pattern in ['start_time', 'trial_start', 'stimulus_start', 'start']:
        if pattern in columns_lower:
            column_mapping['stimulus_start_time'] = columns_lower[pattern]
            break
    
    # Map end time
    for pattern in ['end_time', 'trial_end', 'stimulus_end', 'end']:
        if pattern in columns_lower:
            column_mapping['stimulus_end_time'] = columns_lower[pattern]
            break
    
    # Map stimulus type
    for pattern in ['stimulus_type', 'stim_type', 'condition', 'stimulus']:
        if pattern in columns_lower:
            column_mapping['stimulus_type'] = columns_lower[pattern]
            break
    
    # Rename columns to standard format
    standardized_df = df.rename(columns=column_mapping)
    
    # Fill in missing columns with defaults
    if 'trial_index' not in standardized_df.columns:
        standardized_df['trial_index'] = range(len(standardized_df))
    
    if 'stimulus_type' not in standardized_df.columns:
        standardized_df['stimulus_type'] = 'unknown'
    
    return standardized_df


def _generate_mock_stimulus_table(params: Dict[str, Any]) -> pd.DataFrame:
    """
    Generate a mock stimulus table from experiment parameters.
    
    This is used when Bonsai output is not available. In practice,
    this would be replaced with actual trial data parsing.
    
    Args:
        params: Experiment parameters
        
    Returns:
        DataFrame containing mock stimulus table
    """
    # Create stimulus table structure
    stimulus_data = {
        'trial_index': [],
        'stimulus_start_time': [],
        'stimulus_end_time': [],
        'stimulus_type': [],
        'target_neuron': [],
        'target_branch': [],
        'laser_power': [],
        'frame_rate': [],
        'success': [],
        'response_time': [],
        'dmd_pattern': []
    }
    
    # Generate mock trial data
    num_trials = params.get("num_trials", 100)
    trial_duration = params.get("trial_duration", 1.0)
    inter_trial_interval = params.get("inter_trial_interval", 1.0)
    oddball_probability = params.get("oddball_probability", 0.1)
    
    for i in range(num_trials):
        stimulus_data['trial_index'].append(i)
        
        # Calculate timing
        start_time = i * (trial_duration + inter_trial_interval)
        end_time = start_time + trial_duration
        stimulus_data['stimulus_start_time'].append(start_time)
        stimulus_data['stimulus_end_time'].append(end_time)
        
        # Determine stimulus type (oddball paradigm)
        is_oddball = (i % int(1.0 / oddball_probability)) == 0 if oddball_probability > 0 else False
        stimulus_data['stimulus_type'].append("oddball" if is_oddball else "standard")
        
        # Target information
        stimulus_data['target_neuron'].append(f"neuron_{i % 10}")
        stimulus_data['target_branch'].append(f"branch_{i % 5}")
        
        # Laser parameters
        stimulus_data['laser_power'].append(params.get("laser_power", 10.0))
        stimulus_data['frame_rate'].append(params.get("frame_rate", 30.0))
        
        # Mock outcomes
        stimulus_data['success'].append(True)  # Assume all trials successful
        stimulus_data['response_time'].append(0.5 + (i % 3) * 0.1)  # Mock response times
        stimulus_data['dmd_pattern'].append(f"pattern_{i % 5}")  # Mock DMD patterns
    
    # Create DataFrame
    df = pd.DataFrame(stimulus_data)
    
    logging.info(f"Generated mock stimulus table with {len(df)} trials")
    return df
