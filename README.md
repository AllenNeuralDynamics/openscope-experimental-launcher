# openscope-experimental-launcher

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Code Style](https://img.shields.io/badge/code%20style-black-black)
[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)
![Interrogate](https://img.shields.io/badge/interrogate-100.0%25-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-70.88%25-green?logo=codecov)
![Python](https://img.shields.io/badge/python->=3.8-blue?logo=python)
![Platform](https://img.shields.io/badge/platform-Windows-blue?logo=windows)

**Windows-only experimental launcher for OpenScope Bonsai workflows with metadata generation and session tracking.**

## Overview

This package provides a Windows-specific launcher for Bonsai-based neuroscience experiments in the OpenScope project. It handles:

- **Bonsai Process Management**: Start, monitor, and manage Bonsai workflow execution
- **Parameter Management**: Load and pass parameters to Bonsai workflows
- **Session Tracking**: Generate unique session IDs and track experiment metadata
- **Git Repository Management**: Clone and manage workflow repositories
- **Process Monitoring**: Monitor memory usage and handle runaway processes
- **Windows Integration**: Uses Windows-specific APIs for robust process control

## System Requirements

- **Operating System**: Windows 10 or Windows 11
- **Python**: 3.8 or higher
- **Dependencies**: 
  - Bonsai (installed separately)
  - Git (for repository management)
  - Windows-specific libraries (pywin32)

## Installation

To install for usage:
```bash
pip install -e .
```

To install for development:
```bash
pip install -e .[dev]
```

**Note**: This package requires Windows and will not work on Linux or macOS due to its use of Windows-specific APIs and process management features.

## Usage

### Basic Experiment Launcher

```python
from openscope_experimental_launcher.base.experiment import BaseExperiment

# Create experiment instance
experiment = BaseExperiment()

# Run with parameter file
success = experiment.run("path/to/parameters.json")
```

### SLAP2 Experiment Launcher

```python
from openscope_experimental_launcher.slap2.launcher import SLAP2Experiment

# Create SLAP2 experiment instance
experiment = SLAP2Experiment()

# Run with SLAP2-specific parameters
success = experiment.run("path/to/slap2_parameters.json")
```

### Parameter File Format

Create a JSON parameter file with your experiment configuration:

```json
{
    "subject_id": "test_mouse_001",
    "user_id": "researcher_name",
    "bonsai_path": "path/to/workflow.bonsai",
    "OutputFolder": "C:/experiment_data",
    "repository_url": "https://github.com/example/workflow.git",
    "repository_commit_hash": "main"
}
```

### Command Line Usage

You can also run experiments directly from the command line:

```bash
python -m openscope_experimental_launcher.base.experiment --params parameters.json
```

## Features

### Session Builder Architecture (New!)

The package now includes a modular session builder architecture that allows reuse across different rigs:

- **BaseSessionBuilder**: Core session building functionality that can be extended
- **Rig-specific implementations**: Custom session builders for each rig type (e.g., SLAP2)
- **Backward compatibility**: Existing code continues to work unchanged
- **Easy extensibility**: Simple to add support for new rig types

#### Creating a New Rig Session Builder

```python
from openscope_experimental_launcher.base.session_builder import BaseSessionBuilder

class MyRigSessionBuilder(BaseSessionBuilder):
    def __init__(self):
        super().__init__("MyRig")
    
    def _create_stimulus_epoch(self, start_time, end_time, params, bonsai_software, script_software, **kwargs):
        # Implement rig-specific stimulus epoch creation
        pass
    
    def _create_data_streams(self, params, **kwargs):
        # Implement rig-specific data stream creation
        pass
```

See `docs/session_builder_refactoring.md` for detailed documentation and examples.

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

The package consists of several key components:

- **BaseExperiment**: Core experiment launcher with Bonsai process management
- **SLAP2Experiment**: Specialized launcher for SLAP2 imaging experiments
- **ConfigLoader**: CamStim-compatible configuration file handling
- **GitManager**: Repository management and version control
- **ProcessMonitor**: Memory monitoring and process health checks
- **BonsaiInterface**: Bonsai workflow and process management

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
