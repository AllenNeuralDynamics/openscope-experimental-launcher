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
    "repository_url": "https://github.com/example/python-experiment.git",
    "script_arguments": ["--verbose", "--save-plots"]
}
```

### Command Line Usage

All launchers support command line execution:

```bash
# Using interface launchers directly
python -c "from openscope_experimental_launcher.launchers import BonsaiLauncher; BonsaiLauncher.main()" parameters.json

# Using project-specific scripts
python scripts/slap2_launcher.py parameters.json
python scripts/predictive_processing_launcher.py parameters.json
```

## Features

### Modular Architecture

The package uses a clean, modular architecture that separates concerns:

- **Interface Separation**: Bonsai, MATLAB, and Python support through dedicated launchers
- **Stateless Functions**: Interface modules provide pure functions with no global state
- **Common Base Logic**: All launchers share session management, logging, and metadata through `BaseLauncher`
- **Project Flexibility**: Project-specific launchers in `scripts/` for easy customization

### Multi-Interface Support

#### Bonsai Workflows
- Full Bonsai workflow management and process control
- Package verification and installation support
- Parameter passing and property arguments
- Windows job object integration for robust process management

#### MATLAB Scripts  
- MATLAB script execution with virtual environment support
- Batch mode execution for non-interactive runs
- Custom argument passing and environment setup

#### Python Scripts
- Python script execution with virtual environment support
- Environment variable passing for output paths
- Cross-platform compatibility

### Session Builder Architecture

The package includes a modular session builder architecture for metadata generation:

- **Functional session builders**: Core session building functionality in `utils/session_builder.py`
- **Rig-specific implementations**: Custom session builders for each rig type (e.g., SLAP2)
- **AIND Schema Integration**: Compatible with AIND data schema standards
- **Easy extensibility**: Simple to add support for new rig types

#### Creating a New Rig Session Builder

```python
from openscope_experimental_launcher.utils import session_builder

def build_my_rig_session(params, experiment_config, **kwargs):
    """Build session metadata for MyRig."""
    # Use the functional session builder utilities
    session_data = session_builder.build_session(
        rig_name="MyRig",
        params=params,
        experiment_config=experiment_config,
        **kwargs
    )
    
    # Add rig-specific customizations
    session_data["my_rig_specific_field"] = "custom_value"
    
    return session_data
```

### Process Management
- Uses Windows job objects for robust process control
- Automatic memory monitoring and cleanup
- Graceful shutdown with fallback to force termination

### Session Tracking
- Unique session UUIDs for each experiment
- Automatic timestamp generation
- Parameter and workflow file checksums for provenance

### Git Integration
- Automatic repository cloning and management
- Version tracking for reproducibility
- Branch and commit tracking

### Metadata Generation
- AIND-compatible metadata schemas
- Automatic hardware configuration detection
- Session and experiment metadata collection

## Architecture

The package consists of several key components organized into a modular architecture:

### Core Launchers (`src/openscope_experimental_launcher/launchers/`)
- **BaseLauncher**: Common launcher logic shared across all interfaces (process management, monitoring, logging)
- **BonsaiLauncher**: Inherits from BaseLauncher, implements only Bonsai-specific process creation
- **MatlabLauncher**: Inherits from BaseLauncher, implements only MATLAB-specific process creation  
- **PythonLauncher**: Inherits from BaseLauncher, implements only Python-specific process creation

### Interface Modules (`src/openscope_experimental_launcher/interfaces/`)
- **bonsai_interface**: Stateless functions for creating Bonsai processes
- **matlab_interface**: Stateless functions for creating MATLAB processes
- **python_interface**: Stateless functions for creating Python processes

### Shared Utilities (`src/openscope_experimental_launcher/utils/`)
- **config_loader**: CamStim-compatible configuration file handling
- **git_manager**: Repository management and version control
- **process_monitor**: Memory monitoring and process health checks
- **session_builder**: Session metadata generation and AIND schema support

### Project Scripts (`scripts/`)
- **slap2_launcher.py**: SLAP2 imaging experiment launcher
- **predictive_processing_launcher.py**: Predictive processing experiment launcher
- **minimalist_launcher.py**: Simple test launcher
- **example_*_launcher.py**: Example launchers for each interface

### Design Benefits

1. **Separation of Concerns**: Interface-specific process creation is isolated from common launcher logic
2. **Testability**: Stateless interface functions are easy to unit test
3. **Extensibility**: New interfaces can be added without changing existing code
4. **Maintainability**: Bug fixes in common logic benefit all interfaces
5. **Project Flexibility**: Custom launchers can be created without modifying core code
6. **Code Reuse**: Only process creation differs between interfaces; all other logic is shared

## Contributing

### Development Setup

1. Clone the repository
2. Install in development mode:
```bash
pip install -e .[dev]
```

### Testing

Run the test suite:
```bash
pytest tests/ -v --cov=src/openscope_experimental_launcher
```

### Linting and Formatting

- **flake8** for code quality:
```bash
flake8 .
```

- **black** for code formatting:
```bash
black .
```

- **isort** for import sorting:
```bash
isort .
```

### Pull Requests

We use [Angular](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit) style commit messages:

```text
<type>(<scope>): <short summary>
```

**Types:**
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **test**: Adding or updating tests
- **refactor**: Code refactoring
- **perf**: Performance improvements
- **ci**: CI/CD changes

### Semantic Release

| Commit message | Release type |
|----------------|--------------|
| `fix(launcher): stop process hanging on shutdown` | Patch Release |
| `feat(slap2): add new imaging parameter support` | Feature Release |
| `feat(core): redesign parameter system`<br><br>`BREAKING CHANGE: Parameter format has changed.` | Breaking Release |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions or support, please contact the Allen Institute for Neural Dynamics team or open an issue on the GitHub repository.
