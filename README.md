# openscope-experimental-launcher

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Code Style](https://img.shields.io/badge/code%20style-black-black)
[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)
![Interrogate](https://img.shields.io/badge/interrogate-100.0%25-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-70.88%25-green?logo=codecov)
![Python](https://img.shields.io/badge/python->=3.8-blue?logo=python)
![Platform](https://img.shields.io/badge/platform-Windows-blue?logo=windows)

**Modular experimental launcher for OpenScope with support for Bonsai, MATLAB, and Python workflows.**

## Overview

This package provides a modular, extensible launcher for neuroscience experiments in the OpenScope project. It features a clean architectural separation between interface-specific process creation and common launcher functionality.

### Key Features

- **Multi-Interface Support**: Bonsai, MATLAB, and Python experiment execution through dedicated launchers
- **Modular Architecture**: Clean separation between common logic (`BaseLauncher`) and interface-specific process creation
- **Stateless Design**: Interface modules provide pure functions with no global state
- **Process Management**: Comprehensive process monitoring, memory tracking, and cleanup
- **Parameter Management**: Unified parameter handling with `script_path` convention
- **Session Tracking**: Generate unique session IDs and comprehensive experiment metadata
- **Automated Session Files**: Creates standardized `session.json` files using AIND data schema for every experiment
- **Git Repository Management**: Automatic cloning and version tracking for reproducibility
- **Windows Integration**: Enhanced process control using Windows job objects (where available)
- **Project Flexibility**: Custom launchers via scripts without modifying core code

## Architecture Overview

The launcher uses a modular architecture with clear separation of concerns:

```
src/openscope_experimental_launcher/
├── launchers/               # Interface-specific launchers
│   ├── base_launcher.py     # Common launcher logic (interface-agnostic)
│   ├── bonsai_launcher.py   # Bonsai-specific launcher
│   ├── matlab_launcher.py   # MATLAB-specific launcher
│   └── python_launcher.py   # Python-specific launcher
├── interfaces/              # Stateless interface functions
│   ├── bonsai_interface.py  # Bonsai process creation utilities
│   ├── matlab_interface.py  # MATLAB process creation utilities
│   └── python_interface.py  # Python process creation utilities
└── utils/                   # Shared utilities
    ├── config_loader.py     # Configuration management
    ├── git_manager.py       # Repository management
    ├── session_builder.py   # Session metadata and AIND schema integration
    └── process_monitor.py   # Process monitoring

scripts/                     # Project-specific launcher scripts
├── slap2_launcher.py        # SLAP2 experiment launcher
├── predictive_processing_launcher.py  # Predictive processing launcher
├── minimalist_launcher.py   # Simple test launcher
├── example_matlab_launcher.py  # Example MATLAB launcher
└── example_python_launcher.py  # Example Python launcher
```

### Design Principles

1. **Interface Separation**: All interface-specific code (Bonsai, MATLAB, Python) is isolated in interface modules
2. **Stateless Functions**: Interface modules provide pure functions with no global state - only process creation utilities
3. **Single Responsibility**: Each launcher handles one interface type, each interface handles only process creation
4. **Project Flexibility**: Project-specific launchers live in `scripts/` for easy customization
5. **Common Base**: All launchers share functionality through `BaseLauncher` (process management, monitoring, logging)

## System Requirements

- **Operating System**: Windows 10 or Windows 11 (primary), partial support for other platforms
- **Python**: 3.8 or higher
- **Dependencies**: 
  - Bonsai (for Bonsai experiments)
  - MATLAB (for MATLAB experiments)
  - Git (for repository management)
  - Windows-specific libraries (pywin32) for enhanced process management

## Installation

To install for usage:
```bash
pip install -e .
```

To install for development:
```bash
pip install -e .[dev]
```

## Usage

### Using Interface Launchers Directly

#### Bonsai Experiments
```python
from openscope_experimental_launcher.launchers import BonsaiLauncher

# Create Bonsai launcher instance
launcher = BonsaiLauncher()

# Run with parameter file
success = launcher.run("path/to/parameters.json")
```

#### MATLAB Experiments
```python
from openscope_experimental_launcher.launchers import MatlabLauncher

# Create MATLAB launcher instance
launcher = MatlabLauncher()

# Run with parameter file
success = launcher.run("path/to/parameters.json")
```

#### Python Experiments
```python
from openscope_experimental_launcher.launchers import PythonLauncher

# Create Python launcher instance
launcher = PythonLauncher()

# Run with parameter file
success = launcher.run("path/to/parameters.json")
```

### Using Project-Specific Launchers

For project-specific experiments, use the launcher scripts in the `scripts/` folder:

#### SLAP2 Experiments
```bash
python scripts/slap2_launcher.py path/to/slap2_parameters.json
```

#### Predictive Processing Experiments
```bash
python scripts/predictive_processing_launcher.py path/to/pp_parameters.json
```

#### Minimalist Testing (BaseLauncher Demo)
```bash
python scripts/minimalist_launcher.py scripts/example_minimalist_params.json
```

This demonstrates pure BaseLauncher functionality with a simple mock process - perfect for testing the core framework without external dependencies.

#### Example Launchers
```bash
# MATLAB example
python scripts/example_matlab_launcher.py scripts/example_matlab_params.json

# Python example
python scripts/example_python_launcher.py scripts/example_python_params.json
```

### Creating Custom Launchers

To create a custom launcher for your project:

1. **Extend an Interface Launcher:**
```python
from openscope_experimental_launcher.launchers import BonsaiLauncher

class MyCustomLauncher(BonsaiLauncher):
    def __init__(self):
        super().__init__()
        # Add your custom initialization
    
    def post_experiment_processing(self) -> bool:
        # Add your custom post-processing
        return True
```

2. **Create a Script in `scripts/`:**
```python
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from your_custom_launcher import MyCustomLauncher

def main():
    return MyCustomLauncher.main(description="My custom experiment")

if __name__ == "__main__":
    sys.exit(main())
```

### Parameter File Formats

#### Bonsai Parameters
```json
{
    "subject_id": "test_mouse_001",
    "user_id": "researcher_name",
    "script_path": "workflows/experiment.bonsai",
    "bonsai_exe_path": "C:/Bonsai/Bonsai.exe",
    "OutputFolder": "C:/experiment_data",
    "repository_url": "https://github.com/example/bonsai-workflow.git",
    "script_parameters": {
        "StimDuration": 30,
        "ISI": 5
    }
}
```

#### MATLAB Parameters
```json
{
    "subject_id": "test_mouse_001",
    "user_id": "researcher_name",
    "script_path": "experiments/run_experiment.m",
    "matlab_exe_path": "matlab",
    "OutputFolder": "C:/experiment_data",
    "repository_url": "https://github.com/example/matlab-experiment.git",
    "script_arguments": ["-nosplash", "-nodesktop"]
}
```

#### Python Parameters
```json
{
    "subject_id": "test_mouse_001",
    "user_id": "researcher_name",
    "script_path": "experiments/experiment.py",
    "python_exe_path": "python",
    "python_venv_path": "C:/envs/experiment_env",
    "OutputFolder": "C:/experiment_data",
    "repository_url": "https://github.com/example/python-experiment.git",    "script_arguments": ["--verbose", "--save-plots"]
}
```

## Session Metadata and File Creation

### Automatic Session.json Creation

All experiments automatically generate a comprehensive `session.json` file in the output directory using the AIND data schema format. This file contains:

- **Session Information**: Start/end times, session UUID, subject and user IDs
- **Stimulus Epochs**: Details about the experimental stimuli with software information
- **Platform Details**: Rig identification, mouse platform configuration
- **Software Metadata**: Information about Bonsai, MATLAB, Python, and custom scripts used
- **Experiment Parameters**: Complete parameter sets used during the experiment
- **Session Notes**: Comprehensive notes combining user input and system-generated information

### Session File Structure

The generated `session.json` follows this structure:
```json
{
  "describedBy": "https://raw.githubusercontent.com/AllenNeuralDynamics/aind-data-schema/main/src/aind_data_schema/core/session.py",
  "schema_version": "1.1.2",
  "experimenter_full_name": ["researcher_name"],
  "session_start_time": "2025-06-20T00:22:54.742371-07:00",
  "session_end_time": "2025-06-20T00:22:56.856767-07:00",
  "session_type": "YourExperimentType",
  "rig_id": "your_rig_id",
  "subject_id": "test_mouse_001",
  "stimulus_epochs": [
    {
      "stimulus_name": "YourRig Stimulus",
      "software": [
        {
          "name": "Bonsai",
          "version": "2.8.5",
          "parameters": { /* complete parameter set */ }
        }
      ],
      "stimulus_modalities": ["Visual"],
      "stimulus_parameters": []
    }
  ],
  "notes": "Comprehensive session notes with experiment details"
}
```

### Extending Session Metadata

Custom launchers can extend session metadata by overriding the session builder methods:

```python
class MyCustomLauncher(BonsaiLauncher):
    def get_stimulus_epoch_builder(self):
        """Return custom stimulus epoch builder function."""
        def build_stimulus_epoch(start_time, end_time, params, bonsai_software, script_software, **kwargs):
            # Create custom stimulus epoch with rig-specific information
            return create_custom_stimulus_epoch(start_time, end_time, params, **kwargs)
        return build_stimulus_epoch
    
    def get_data_streams_builder(self):
        """Return custom data streams builder function.""" 
        def build_data_streams(params, **kwargs):
            # Create rig-specific data streams information
            return create_custom_data_streams(params, **kwargs)
        return build_data_streams
```

### Output Directory Structure

Each experiment creates a timestamped directory with complete experiment documentation:

```
subject_id_2025-06-20_00-22-54/
├── session.json                     # AIND schema session metadata
├── experiment_subject_id_*.log      # Complete experiment log
└── experiment_metadata/             # Additional metadata files
    ├── original_parameters.json     # Original parameter file
    ├── processed_parameters.json    # Processed parameters
    ├── command_line_arguments.json  # Command line used
    └── runtime_information.json     # System and runtime info
```


### Session Builder Architecture

The package includes a comprehensive session builder architecture for automatic metadata generation:

- **Automatic Integration**: Session files are created automatically by the `BaseLauncher` for all experiment types
- **AIND Schema Compliance**: Session files follow AIND data schema standards for interoperability
- **Functional Design**: Core session building functionality in `utils/session_builder.py`
- **Rig-specific Extensions**: Custom session builders can be implemented for specialized rig types
- **Graceful Fallback**: Works with or without aind-data-schema installed
- **Easy Extensibility**: Simple to add support for new experiment types and metadata

#### Customizing Session Metadata for Your Rig

```python
from openscope_experimental_launcher.launchers import BonsaiLauncher
from openscope_experimental_launcher.utils import session_builder

class MyRigLauncher(BonsaiLauncher):
    def _get_launcher_type_name(self):
        return "MyRig"
    
    def get_stimulus_epoch_builder(self):
        """Return custom stimulus epoch builder for MyRig."""
        def build_my_rig_stimulus_epoch(start_time, end_time, params, bonsai_software, script_software, **kwargs):
            # Use the session builder utilities with rig-specific customizations
            return session_builder.create_default_stimulus_epoch(
                start_time, end_time, params, bonsai_software, script_software, "MyRig"
            )
        return build_my_rig_stimulus_epoch
    
    def get_data_streams_builder(self):
        """Return custom data streams builder for MyRig."""
        def build_my_rig_data_streams(params, **kwargs):
            # Create rig-specific data streams
            return [
                session_builder.Stream(
                    stream_start_time=kwargs.get('start_time'),
                    stream_end_time=kwargs.get('end_time'),
                    stream_modalities=['Visual', 'Behavior'],
                    daq_names=['MyRig_DAQ'],
                    # Add more rig-specific stream information
                )
            ]
        return build_my_rig_data_streams
```

Session files are automatically created at the end of every experiment run, providing comprehensive metadata for data analysis and experiment reproducibility.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
