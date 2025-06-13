"""
Metadata generator for OpenScope experimental launchers.

This module provides the MetadataGenerator class for creating and managing
experiment metadata in various formats.
"""

import os
import json
import logging
import datetime
import pickle
from typing import Dict, Any, Optional


class MetadataGenerator:
    """
    Generates and manages experiment metadata.
    
    Handles creation of metadata files, output data formatting,
    and compatibility with existing CamStim formats.
    """
    
    def __init__(self):
        """Initialize the metadata generator."""
        pass
    
    def create_output_data(self,
                          platform_info: Dict[str, Any],
                          start_time: datetime.datetime,
                          stop_time: Optional[datetime.datetime],
                          session_uuid: str,
                          params: Dict[str, Any],
                          config: Dict[str, Any],
                          mouse_id: str,
                          user_id: str,
                          script_checksum: Optional[str],
                          params_checksum: Optional[str],
                          bonsai_stdout: list,
                          bonsai_stderr: list,
                          bonsai_return_code: Optional[int]) -> Dict[str, Any]:
        """
        Create experiment output data in CamStim-compatible format.
        
        Args:
            platform_info: System platform information
            start_time: Experiment start time
            stop_time: Experiment stop time
            session_uuid: Unique session identifier
            params: Experiment parameters
            config: Hardware configuration
            mouse_id: Subject ID
            user_id: User ID
            script_checksum: Workflow file checksum
            params_checksum: Parameter file checksum
            bonsai_stdout: Bonsai stdout data
            bonsai_stderr: Bonsai stderr data
            bonsai_return_code: Bonsai process return code
            
        Returns:
            Dictionary containing formatted output data
        """
        if not stop_time:
            stop_time = datetime.datetime.now()
        
        # Create structure similar to CamStim's output format
        output_data = {
            # Top level experiment data
            'platform_info': platform_info,
            'start_time': start_time,
            'stop_time': stop_time,
            'duration': (stop_time - start_time).total_seconds(),
            'session_uuid': session_uuid,
            
            # Standard CamStim metadata fields
            'rig_id': os.environ.get('aibs_rig_id', platform_info.get('rig_id', 'undefined')),
            'comp_id': os.environ.get('aibs_comp_id', platform_info.get('computer_name', 'undefined')),
            'script': os.path.basename(params.get('bonsai_path', '')),
            'script_md5': script_checksum,
            'params_md5': params_checksum,
            
            # Store stdout and stderr data for debugging
            'bonsai_stdout': bonsai_stdout,
            'bonsai_stderr': bonsai_stderr,
            
            # Items field organizes components like behavior, stim, etc.
            'items': {
                'behavior': {
                    'config': config.get('Behavior', {}),
                    'mouse_id': mouse_id,
                    'user_id': user_id,
                    # Placeholder for behavior data coming from Bonsai
                    'bonsai_data': params.get('bonsai_output', {})
                },
                'stimulus': {
                    'config': {
                        'params': params,
                        'config': config
                    },
                    'name': params.get('workflow_name', os.path.basename(params.get('bonsai_path', ''))),
                    'workflow_path': params.get('bonsai_path', ''),
                    'return_code': bonsai_return_code
                }
            },
            
            # Config sections - for downstream compatibility
            'config': config,
            'params': params
        }
        
        return output_data
    
    def save_pickle_output(self, 
                          output_data: Dict[str, Any], 
                          output_path: str) -> bool:
        """
        Save output data as pickle file in CamStim-compatible format.
        
        Args:
            output_data: Dictionary containing output data
            output_path: Path to save the pickle file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Process through filter to remove unpickleable items
            pickled_data = self._filter_pickleable(output_data)
            
            # Create output directory if needed
            output_dir = os.path.dirname(output_path)
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)
            
            # Handle existing files
            if os.path.isfile(output_path):
                # Create timestamped backup name
                dt_str = datetime.datetime.now().strftime('%y%m%d%H%M%S')
                filename = os.path.basename(output_path)
                dirname = os.path.dirname(output_path)
                output_path = os.path.join(dirname, f"{dt_str}-{filename}")
                logging.warning(f"File path already exists, saving to: {output_path}")
            
            # Save as pickle
            with open(output_path, 'wb') as f:
                pickle.dump(pickled_data, f)
            
            logging.info(f"Experiment data saved to: {output_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to save experiment data: {e}")
            return False
    
    def create_config_file(self, 
                          param_file_path: str, 
                          session_params: Dict[str, Any],
                          hardware_config: Dict[str, Any],
                          session_metadata: Dict[str, Any],
                          bonsai_args: list) -> Optional[str]:
        """
        Save configuration data to a JSON file.
        
        Args:
            param_file_path: Path to the original parameter file
            session_params: Session parameters
            hardware_config: Hardware configuration
            session_metadata: Session metadata
            bonsai_args: Bonsai command-line arguments
            
        Returns:
            Path to saved config file or None if failed
        """
        if not param_file_path:
            logging.warning("No parameter file path provided, cannot save config file")
            return None
        
        try:
            # Parse the original filename and create the new config filename
            param_dir = os.path.dirname(param_file_path)
            param_basename = os.path.basename(param_file_path)
            param_name, param_ext = os.path.splitext(param_basename)
            
            # Create the config filename with '_config' suffix
            config_filename = f"{param_name}_config{param_ext}"
            config_file_path = os.path.join(param_dir, config_filename)
            
            # Create config data structure
            config_data = {
                'session_params': session_params,
                'hardware_config': hardware_config,
                'session_metadata': session_metadata,
                'bonsai_args': bonsai_args
            }
            
            # Save to JSON file
            with open(config_file_path, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            logging.info(f"Saved configuration to: {config_file_path}")
            return config_file_path
            
        except Exception as e:
            logging.error(f"Failed to save config file: {e}")
            return None
    
    def _filter_pickleable(self, datadict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter dictionary to remove unpickleable items.
        
        This is a reimplementation of CamStim's wecanpicklethat function.
        
        Args:
            datadict: Dictionary to filter
            
        Returns:
            Dictionary containing only pickleable items
        """
        pickleable = {}
        unpickleable = []
        
        for k, v in datadict.items():
            try:
                if not k.startswith("_"):  # Skip private counters
                    # Test if the item can be pickled
                    pickle.dumps(v)
                    pickleable[k] = v
            except Exception:
                unpickleable.append(k)
        
        pickleable['unpickleable'] = unpickleable
        return pickleable
    
    def create_backup_copy(self, 
                          source_path: str, 
                          backup_dir: str, 
                          mouse_id: str) -> bool:
        """
        Create a backup copy of the output file.
        
        Args:
            source_path: Path to source file
            backup_dir: Backup directory base path
            mouse_id: Mouse ID for organizing backups
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup directory structure
            mouse_backup_dir = os.path.join(backup_dir, mouse_id, "output")
            if not os.path.isdir(mouse_backup_dir):
                os.makedirs(mouse_backup_dir)
            
            # Create backup file path
            backup_path = os.path.join(mouse_backup_dir, os.path.basename(source_path))
            logging.info(f"Backing up file to: {backup_path}")
            
            # Copy the file
            import shutil
            shutil.copy2(source_path, backup_path)
            logging.info("Backup complete!")
            return True
            
        except Exception as e:
            logging.warning(f"Failed to create backup: {e}")
            return False