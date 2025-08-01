"""
Bonsai interface for OpenScope experimental launchers.

This module provides stateless functions for managing Bonsai process
interactions, package management, and workflow execution.
"""

import os
import logging
import subprocess
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any


def setup_bonsai_environment(params: Dict[str, Any]) -> bool:
    """
    Set up Bonsai environment including installation if needed.
    
    Args:
        params: Parameter dictionary containing Bonsai configuration
        
    Returns:
        True if setup successful, False otherwise
    """
    # Check if Bonsai is installed
    bonsai_exe_path = params.get('bonsai_exe_path')
    if not bonsai_exe_path:
        logging.error("No Bonsai executable path specified in parameters")
        return False
        
    if not check_installation(bonsai_exe_path):
        # Try to install if setup script is provided
        setup_script = params.get('bonsai_setup_script')
        if setup_script:
            logging.info("Bonsai not found, attempting installation...")
            if not install_bonsai(setup_script):
                logging.error("Failed to install Bonsai")
                return False
        else:
            logging.error("Bonsai not found and no setup script provided")
            return False
    
    # Verify packages if config file is provided
    config_path = params.get('bonsai_config_path')
    if config_path and os.path.exists(config_path):
        logging.info("Verifying Bonsai packages...")
        bonsai_install_dir = os.path.dirname(bonsai_exe_path)
        if not verify_packages(config_path, bonsai_install_dir):
            logging.warning("Package verification failed, but continuing...")
    
    return True


def check_installation(bonsai_exe_path: str) -> bool:
    """
    Check if Bonsai is installed at the specified location.
    
    Args:
        bonsai_exe_path: Path to Bonsai executable
        
    Returns:
        True if Bonsai is found, False otherwise
    """
    if os.path.exists(bonsai_exe_path):
        logging.info(f"Bonsai executable found at: {bonsai_exe_path}")
        return True
    else:
        logging.info(f"Bonsai executable not found at: {bonsai_exe_path}")
        return False


def install_bonsai(setup_script_path: str) -> bool:
    """
    Install Bonsai using the setup script.
    
    Args:
        setup_script_path: Path to the Bonsai setup script
        
    Returns:
        True if installation successful, False otherwise
    """
    if not os.path.exists(setup_script_path):
        logging.error(f"Bonsai setup script not found at: {setup_script_path}")
        return False
    
    logging.info(f"Installing Bonsai using setup script: {setup_script_path}")
    
    try:
        # Change to the directory containing the setup script
        script_dir = os.path.dirname(setup_script_path)
        original_dir = os.getcwd()
        os.chdir(script_dir)
        
        # Execute the setup script
        process = subprocess.Popen(
            [setup_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True
        )
        
        # Monitor the installation process
        logging.info("Bonsai installation started...")
        stdout_lines = []
        stderr_lines = []
        
        # Read output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                stdout_lines.append(output.strip())
                logging.info(f"Setup: {output.strip()}")
        
        # Get any remaining stderr
        stderr_output = process.stderr.read()
        if stderr_output:
            stderr_lines.extend(stderr_output.split('\n'))
            for line in stderr_lines:
                if line.strip():
                    logging.warning(f"Setup stderr: {line.strip()}")
        
        # Wait for process to complete
        return_code = process.wait()
        
        if return_code == 0:
            logging.info("Bonsai installation completed successfully")
            return True
        else:
            logging.error(f"Bonsai installation failed with return code: {return_code}")
            return False
            
    except Exception as e:
        logging.error(f"Failed to execute Bonsai setup script: {e}")
        return False
    finally:
        os.chdir(original_dir)


def parse_bonsai_config(config_path: str) -> Dict[str, str]:
    """
    Parse a Bonsai.config XML file to extract package requirements.
    
    Args:
        config_path: Path to Bonsai.config file
        
    Returns:
        Dictionary mapping package names to versions
    """
    try:
        tree = ET.parse(config_path)
        root = tree.getroot()
        
        required_packages = {}
        packages_element = root.find('Packages')
        
        if packages_element is not None:
            for package in packages_element.findall('Package'):
                package_id = package.get('id')
                package_version = package.get('version')
                if package_id and package_version:
                    required_packages[package_id] = package_version
        
        logging.info(f"Found {len(required_packages)} required packages in Bonsai.config")
        return required_packages
        
    except Exception as e:
        logging.error(f"Failed to parse Bonsai.config file {config_path}: {e}")
        return {}


def get_installed_packages(bonsai_install_dir: str) -> Dict[str, str]:
    """
    Get list of currently installed Bonsai packages and their versions.
    
    Args:
        bonsai_install_dir: Bonsai installation directory
        
    Returns:
        Dictionary mapping package names to versions
    """
    packages_dir = os.path.join(bonsai_install_dir, "Packages")
    installed_packages = {}
    
    if not os.path.exists(packages_dir):
        logging.warning(f"Bonsai packages directory not found: {packages_dir}")
        return installed_packages
    
    try:
        # Look for package directories in the format: PackageName.Version
        for item in os.listdir(packages_dir):
            package_path = os.path.join(packages_dir, item)
            if os.path.isdir(package_path):
                # Parse package name and version from directory name
                parts = item.split('.')
                if len(parts) >= 2:
                    # Find where version starts (first part that looks like a version)
                    version_start_idx = -1
                    for i, part in enumerate(parts):
                        if part.isdigit() or (len(part) > 0 and part[0].isdigit()):
                            version_start_idx = i
                            break
                    
                    if version_start_idx > 0:
                        package_name = '.'.join(parts[:version_start_idx])
                        package_version = '.'.join(parts[version_start_idx:])
                        installed_packages[package_name] = package_version
                        
        logging.info(f"Found {len(installed_packages)} installed Bonsai packages")
        return installed_packages
        
    except Exception as e:
        logging.error(f"Failed to scan installed Bonsai packages: {e}")
        return {}


def _versions_match(required_version: str, installed_version: str) -> bool:
    """
    Check if two version strings are compatible.
    
    Args:
        required_version: Required version string
        installed_version: Installed version string
        
    Returns:
        True if versions match, False otherwise
    """
    if not required_version or not installed_version:
        return False
    
    # Normalize both versions (remove trailing .0)
    norm_required = _normalize_version(required_version)
    norm_installed = _normalize_version(installed_version)
    
    return norm_required == norm_installed


def _normalize_version(version: str) -> str:
    """
    Normalize version strings for comparison.
    
    Args:
        version: Version string to normalize
        
    Returns:
        Normalized version string
    """
    if not version:
        return version
    
    # Split version into parts
    parts = version.split('.')
    
    # Remove trailing zeros
    while len(parts) > 1 and parts[-1] == '0':
        parts.pop()
    
    return '.'.join(parts)


def verify_packages(config_path: str, bonsai_install_dir: str) -> bool:
    """
    Verify that installed Bonsai packages match the requirements.
    
    Args:
        config_path: Path to Bonsai.config file
        bonsai_install_dir: Bonsai installation directory
        
    Returns:
        True if packages match, False otherwise
    """
    if not os.path.exists(config_path):
        logging.warning(f"Bonsai.config file not found: {config_path}")
        return True  # Assume OK if no config
    
    # Parse required packages from config
    required_packages = parse_bonsai_config(config_path)
    if not required_packages:
        logging.warning("No required packages found in Bonsai.config")
        return True
    
    # Get currently installed packages
    installed_packages = get_installed_packages(bonsai_install_dir)
    
    # Compare required vs installed packages
    missing_packages = []
    version_mismatches = []
    
    for package_name, required_version in required_packages.items():
        if package_name not in installed_packages:
            missing_packages.append((package_name, required_version))
        elif not _versions_match(required_version, installed_packages[package_name]):
            version_mismatches.append((
                package_name, 
                required_version, 
                installed_packages[package_name]
            ))
    
    # Report results
    if not missing_packages and not version_mismatches:
        logging.info("All Bonsai packages are correctly installed and up to date")
        return True
    else:
        logging.warning("Bonsai package verification failed:")
        
        if missing_packages:
            logging.warning(f"Missing packages ({len(missing_packages)}):")
            for package_name, required_version in missing_packages[:10]:
                logging.warning(f"  - {package_name} (version {required_version})")
            if len(missing_packages) > 10:
                logging.warning(f"  ... and {len(missing_packages) - 10} more")
        
        if version_mismatches:
            logging.warning(f"Version mismatches ({len(version_mismatches)}):")
            for package_name, required, installed in version_mismatches[:10]:
                logging.warning(f"  - {package_name}: required {required}, installed {installed}")
            if len(version_mismatches) > 10:
                logging.warning(f"  ... and {len(version_mismatches) - 10} more")
        
        return False


def create_bonsai_property_arguments(params: Dict[str, Any]) -> List[str]:
    """
    Create command-line property arguments for Bonsai.
    
    Only passes properties that are explicitly requested in script_parameters
    to avoid conflicts with workflows that don't have these properties defined.
    
    Args:
        params: Parameter dictionary containing script_parameters
        
    Returns:
        List of -p arguments for Bonsai
    """
    bonsai_args = []
    # Only add parameters from script_parameters section - no automatic defaults
    script_parameters = params.get("script_parameters", {})
        
    if script_parameters:
        logging.info(f"Adding {len(script_parameters)} custom Bonsai parameters")
        for param_name, param_value in script_parameters.items():
            # Convert parameter value to string for Bonsai
            param_str = str(param_value)
            bonsai_args.extend(["-p", f"{param_name}={param_str}"])
            logging.info(f"Added Bonsai parameter: {param_name}={param_str}")
    else:
        logging.info("No custom Bonsai parameters specified - running workflow with defaults")
    
    logging.info(f"Created {len(bonsai_args) // 2} Bonsai property arguments")
    return bonsai_args


def construct_workflow_arguments(params: Dict[str, Any]) -> List[str]:
    """
    Construct command-line arguments for Bonsai workflow based on parameters.
    
    Args:
        params: Parameter dictionary
        
    Returns:
        List of command-line arguments
    """
    args = []
      # Add property arguments from script_parameters
    property_args = create_bonsai_property_arguments(params)
    if property_args:
        args.extend(property_args)
    
    # Add any custom command-line arguments (not properties)
    custom_args = params.get('script_arguments', [])
    if custom_args:
        args.extend(custom_args)
    
    return args


def start_workflow(workflow_path: str, bonsai_exe_path: str, arguments: List[str] = None, output_folder: str = None) -> subprocess.Popen:
    """
    Start a Bonsai workflow as a subprocess.
    
    Args:
        workflow_path: Path to the Bonsai workflow file
        bonsai_exe_path: Path to Bonsai executable
        arguments: Additional command-line arguments
        output_folder: Directory for output files
        
    Returns:
        Subprocess.Popen object for the running workflow
    """
    if not os.path.exists(workflow_path):
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")
    
    if not os.path.exists(bonsai_exe_path):
        raise FileNotFoundError(f"Bonsai executable not found: {bonsai_exe_path}")
    
    # Normalize both paths for Windows compatibility - ensure consistent path separators
    bonsai_exe_normalized = os.path.normpath(bonsai_exe_path)
    workflow_path_normalized = os.path.normpath(workflow_path)
    
    # Build command arguments
    cmd_args = [bonsai_exe_normalized, workflow_path_normalized]
    
    # Add essential arguments for non-interactive execution
    cmd_args.append("--start")
    cmd_args.append("--no-editor")
    
    if arguments:
        cmd_args.extend(arguments)
      # Set output directory if specified
    if output_folder:
        # Normalize the output folder path as well
        output_folder_normalized = os.path.normpath(output_folder)
        cmd_args.extend(["-p", f"OutputFolder={output_folder_normalized}"])
        logging.info(f"Output will be saved to: {output_folder_normalized}")
    
    logging.info(f"Starting Bonsai workflow: {' '.join(cmd_args)}")
    
    try:
        process = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        logging.info(f"Bonsai workflow started with PID: {process.pid}")
        return process
        
    except Exception as e:
        logging.error(f"Failed to start Bonsai workflow: {e}")
        raise
