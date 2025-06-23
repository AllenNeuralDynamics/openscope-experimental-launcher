# openscope-experimental-launcher

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Interrogate](https://img.shields.io/badge/interrogate-96.6%25-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-47%25-orange?logo=codecov)
![Tests](https://img.shields.io/badge/tests-140%20passed-brightgreen)
![Python](https://img.shields.io/badge/python->=3.8-blue?logo=python)
![Platform](https://img.shields.io/badge/platform-Windows-blue?logo=windows)
[![Documentation](https://img.shields.io/badge/docs-latest-blue?logo=gitbook)](https://allenneuraldynamics.github.io/openscope-experimental-launcher/)

**Modular experimental launcher for OpenScope with support for Bonsai, MATLAB, and Python workflows.**

## Overview

This package provides a modular, extensible launcher for neuroscience experiments in the OpenScope project. It features clean architectural separation between interface-specific process creation and common launcher functionality.

### Key Features

- **Multi-Interface Support**: Bonsai, MATLAB, and Python experiment execution
- **Modular Architecture**: Clean separation between common logic and interface-specific process creation
- **Post-Processing Pipeline**: Automated data transformation with standalone, reusable tools
- **Process Management**: Comprehensive process monitoring, memory tracking, and cleanup
- **Session Tracking**: Generate unique session IDs and comprehensive experiment metadata
- **Automated Session Files**: Creates standardized `session.json` files using AIND data schema
- **Git Repository Management**: Automatic cloning and version tracking for reproducibility
- **Runtime Data Collection**: Interactive prompts for protocol confirmation and animal weight collection
- **Project Flexibility**: Custom launchers via scripts without modifying core code

## Architecture Overview

The launcher uses a modular architecture with clean separation of concerns:

```
src/openscope_experimental_launcher/
├── launchers/               # Interface-specific launchers
├── interfaces/              # Stateless interface functions
├── post_processing/         # Standalone post-processing tools
└── utils/                   # Shared utilities
scripts/                     # Project-specific launcher scripts
```

**Design Principles:**
- **Interface Separation**: Clean separation between launchers and interfaces
- **Stateless Functions**: Interface modules provide pure functions with no global state
- **Modular Post-Processing**: Standalone tools for data transformation
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

launcher = BonsaiLauncher(param_file="path/to/parameters.json")
success = launcher.run()
```

**MATLAB Experiments:**
```python
from openscope_experimental_launcher.launchers import MatlabLauncher

launcher = MatlabLauncher(param_file="path/to/parameters.json")
success = launcher.run()
```

**Python Experiments:**
```python
from openscope_experimental_launcher.launchers import PythonLauncher

launcher = PythonLauncher(param_file="path/to/parameters.json")
success = launcher.run()
```

## Configuration System

The launcher uses a **three-tier configuration system** that cleanly separates rig-specific settings from experiment parameters:

1. **Rig Config** (`rig_config.toml`) - Hardware/setup constants (rig_id, data paths)
2. **Parameter Files** (`*.json`) - Experiment-specific settings (subject_id, protocols)  
3. **Runtime Prompts** - Interactive collection of missing values

```python
# Normal usage - clean and simple
launcher = BonsaiLauncher(param_file="experiment.json")  # Uses default rig config
success = launcher.run()
```

**[📖 Complete Configuration Guide →](docs/configuration-guide.md)**

### Basic Parameter File
```json
{
    "subject_id": "test_mouse_001",
    "user_id": "researcher_name", 
    "script_path": "path/to/workflow.bonsai",
    "output_root_folder": "C:/experiment_data",
    "collect_mouse_runtime_data": true,
    "protocol_id": ["protocol_001"]
}
```

**Using Project Scripts:**
```bash
python scripts/minimalist_launcher.py scripts/example_minimalist_params.json
python scripts/predictive_processing_launcher.py experiment_params.json
```

## Documentation

For complete documentation, tutorials, and examples:

📖 **[Full Documentation](https://allenneuraldynamics.github.io/openscope-experimental-launcher/)**

- **[Configuration Guide](docs/configuration-guide.md)** - Complete configuration system guide and best practices
- **[Installation Guide](docs/source/installation.rst)** - Detailed setup instructions and troubleshooting
- **[Quick Start Tutorial](docs/source/quickstart.rst)** - Step-by-step first experiment walkthrough  
- **[Parameter Reference](docs/source/parameter_files.rst)** - Complete parameter documentation and examples
- **[Launcher Guide](docs/source/rig_launchers.rst)** - Architecture details and launcher customization
- **[Post-Processing Guide](docs/source/post_processing.rst)** - Data transformation tools and workflows

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
