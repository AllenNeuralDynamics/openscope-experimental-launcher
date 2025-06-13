"""
Bonsai interface for OpenScope experimental launchers.

This module provides the BonsaiInterface class for managing Bonsai process
interactions, package management, and workflow execution.
"""

import os
import logging
import subprocess
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any


class BonsaiInterface:
    """
    Interface for managing Bonsai installation, packages, and execution.
    
    Handles:
    - Bonsai installation verification
    - Package installation and verification
    - Workflow execution
    - Setup script management
    """
    
    def __init__(self):
        """Initialize the Bonsai interface."""
        self.bonsai_exe_path = None
        self.bonsai_install_dir = None
    
    def set_bonsai_path(self, bonsai_exe_path: str):
        """
        Set the path to the Bonsai executable.
        
        Args:
            bonsai_exe_path: Path to Bonsai.exe
        """
        self.bonsai_exe_path = bonsai_exe_path
        self.bonsai_install_dir = os.path.dirname(bonsai_exe_path)
    
    def check_installation(self) -> bool:
        """
        Check if Bonsai is installed at the expected location.
        
        Returns:
            True if Bonsai is found, False otherwise
        """
        if not self.bonsai_exe_path:
            logging.error("No Bonsai executable path specified")
            return False
        
        if os.path.exists(self.bonsai_exe_path):
            logging.info(f"Bonsai executable found at: {self.bonsai_exe_path}")
            return True
        else:
            logging.info(f"Bonsai executable not found at: {self.bonsai_exe_path}")
            return False
    
    def install_bonsai(self, setup_script_path: str) -> bool:
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
                
                # Verify installation
                if self.check_installation():
                    logging.info("Bonsai installation verified")
                    return True
                else:
                    logging.error("Bonsai installation verification failed")
                    return False
            else:
                logging.error(f"Bonsai installation failed with return code: {return_code}")
                return False
                
        except Exception as e:
            logging.error(f"Failed to execute Bonsai setup script: {e}")
            return False
        finally:
            os.chdir(original_dir)
    
    def parse_bonsai_config(self, config_path: str) -> Dict[str, str]:
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
    
    def get_installed_packages(self) -> Dict[str, str]:
        """
        Get list of currently installed Bonsai packages and their versions.
        
        Returns:
            Dictionary mapping package names to versions
        """
        if not self.bonsai_install_dir:
            logging.warning("Bonsai installation directory not set")
            return {}
        
        packages_dir = os.path.join(self.bonsai_install_dir, "Packages")
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
    
    def verify_packages(self, config_path: str) -> bool:
        """
        Verify that installed Bonsai packages match the requirements.
        
        Args:
            config_path: Path to Bonsai.config file
            
        Returns:
            True if packages match, False otherwise
        """
        if not os.path.exists(config_path):
            logging.warning(f"Bonsai.config file not found: {config_path}")
            return True  # Assume OK if no config
        
        # Parse required packages from config
        required_packages = self.parse_bonsai_config(config_path)
        if not required_packages:
            logging.warning("No required packages found in Bonsai.config")
            return True
        
        # Get currently installed packages
        installed_packages = self.get_installed_packages()
        
        # Compare required vs installed packages
        missing_packages = []
        version_mismatches = []
        
        for package_name, required_version in required_packages.items():
            if package_name not in installed_packages:
                missing_packages.append((package_name, required_version))
            elif not self._versions_match(required_version, installed_packages[package_name]):
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
    
    def _versions_match(self, required_version: str, installed_version: str) -> bool:
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
        norm_required = self._normalize_version(required_version)
        norm_installed = self._normalize_version(installed_version)
        
        return norm_required == norm_installed
    
    def _normalize_version(self, version: str) -> str:
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