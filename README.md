# openscope-experimental-launcher

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Interrogate](https://img.shields.io/badge/interrogate-100.0%25-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-61%25-orange?logo=codecov)
![Python](https://img.shields.io/badge/python->=3.8-blue?logo=python)
![Platform](https://img.shields.io/badge/platform-Windows-blue?logo=windows)
[![Documentation](https://img.shields.io/badge/docs-latest-blue?logo=gitbook)](https://allenneuraldynamics.github.io/openscope-experimental-launcher/)

**Modular experimental launcher for OpenScope with support for Bonsai, MATLAB, and Python workflows.**

## Overview

This package provides a modular, extensible launcher for neuroscience experiments in the OpenScope project. It features clean architectural separation between interface-specific process creation and common launcher functionality.

### Key Features

- **Multi-Interface Support**: Bonsai, MATLAB, and Python experiment execution
- **Modular Architecture**: Clean separation between common logic and interface-specific process creation
- **Process Management**: Comprehensive process monitoring, memory tracking, and cleanup
- **Session Tracking**: Generate unique session IDs and comprehensive experiment metadata
- **Automated Session Files**: Creates standardized `session.json` files using AIND data schema
- **Git Repository Management**: Automatic cloning and version tracking for reproducibility
- **Runtime Data Collection**: Interactive prompts for protocol confirmation and animal weight collection
- **Project Flexibility**: Custom launchers via scripts without modifying core code

## Quick Start

### Installation
```bash
pip install -e .
```

### Basic Usage

**Bonsai Experiments:**
```python
from openscope_experimental_launcher.launchers import BonsaiLauncher

launcher = BonsaiLauncher()
success = launcher.run("path/to/parameters.json")
```

**MATLAB Experiments:**
```python
from openscope_experimental_launcher.launchers import MatlabLauncher

launcher = MatlabLauncher()
success = launcher.run("path/to/parameters.json")
```

**Python Experiments:**
```python
from openscope_experimental_launcher.launchers import PythonLauncher

launcher = PythonLauncher()
success = launcher.run("path/to/parameters.json")
```

## Configuration System

The launcher uses a **three-tier configuration system** that cleanly separates rig-specific settings from experiment parameters:

1. **Rig Config** (`rig_config.toml`) - Hardware/setup constants (rig_id, data paths)
2. **Parameter Files** (`*.json`) - Experiment-specific settings (subject_id, protocols)  
3. **Runtime Prompts** - Interactive collection of missing values

```python
# Normal usage - clean and simple
launcher = BonsaiLauncher()
launcher.initialize_launcher(param_file="experiment.json")  # Uses default rig config
```

**[📖 Complete Configuration Guide →](docs/configuration-guide.md)**

### Basic Parameter File
```json
{
    "subject_id": "test_mouse_001",
    "user_id": "researcher_name", 
    "script_path": "path/to/workflow.bonsai",
    "OutputFolder": "C:/experiment_data",
    "collect_mouse_runtime_data": true,
    "protocol_id": ["protocol_001"]
}
```

**Using Project Scripts:**
```bash
python scripts/slap2_launcher.py path/to/slap2_parameters.json
python scripts/minimalist_launcher.py scripts/example_minimalist_params.json
```

## Architecture Overview

The launcher uses a modular architecture with clean separation of concerns:

```
src/openscope_experimental_launcher/
├── launchers/               # Interface-specific launchers
├── interfaces/              # Stateless interface functions  
└── utils/                   # Shared utilities
scripts/                     # Project-specific launcher scripts
```

**Design Principles:**
- **Interface Separation**: Clean separation between launchers and interfaces
- **Stateless Functions**: Interface modules provide pure functions with no global state
- **Project Flexibility**: Custom launchers via scripts without modifying core code

## System Requirements

- **Operating System**: Windows 10 or Windows 11 (primary support)
- **Python**: 3.8 or higher
- **Dependencies**: Bonsai, MATLAB, or Python environments as needed

## Documentation

For complete documentation, tutorials, and examples:

📖 **[Full Documentation](https://allenneuraldynamics.github.io/openscope-experimental-launcher/)**

- **[Configuration Guide](docs/configuration-guide.md)** - Complete configuration system guide and best practices
- **[Installation Guide](docs/source/installation.rst)** - Detailed setup instructions and troubleshooting
- **[Quick Start Tutorial](docs/source/quickstart.rst)** - Step-by-step first experiment walkthrough  
- **[Parameter Reference](docs/source/parameter_files.rst)** - Complete parameter documentation and examples
- **[Launcher Guide](docs/source/rig_launchers.rst)** - Architecture details and launcher customization

## Session Files and Metadata

All experiments automatically generate comprehensive `session.json` files using the AIND data schema format, containing:

- Session start/end times and unique IDs
- Subject and experimenter information  
- Data stream details and software provenance
- Runtime collected data (weights, protocol confirmations)
- Complete parameter sets used during experiments

## Contributing

For development installation and contribution guidelines, see the [full documentation](https://allenneuraldynamics.github.io/openscope-experimental-launcher/).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
