# openscope-experimental-launcher

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Coverage](https://img.shields.io/badge/coverage-53%25-yellow?logo=codecov)
![Python](https://img.shields.io/badge/python->=3.8-blue?logo=python)
![Platform](https://img.shields.io/badge/platform-Windows-blue?logo=windows)
[![Documentation](https://img.shields.io/badge/docs-latest-blue?logo=gitbook)](https://allenneuraldynamics.github.io/openscope-experimental-launcher/)

**Modular, pipeline-driven experimental launcher for OpenScope.**

---

## Overview

- **Modular pre- and post-acquisition pipelines:** All experiment setup and teardown logic is handled by standalone modules, not the launcher core.
- **Multi-language support:** Launchers for Bonsai, MATLAB, and Python workflows.
- **Unified parameter files:** All modules and launchers use a single JSON parameter file for configuration.
- **Robust, testable, and extensible:** All modules return 0 for success, 1 for failure; pipeline is fully testable and easy to extend.
- **Clean architecture:** All details and advanced usage are documented in the `docs/` folder.

## Quick Start

```bash
pip install -e .
```

**Run an experiment:**
```bash
python run_launcher.py --param_file params/example_minimalist_params.json
```

**Run a pipeline module directly:**
```bash
python run_module.py --module_type post_acquisition --module_name example_post_acquisition_module --param_file params/example_minimalist_params.json
```

**Run tests and check coverage:**
```bash
pytest --cov=src/openscope_experimental_launcher --cov-report=term-missing
```

## Documentation

See the [docs/](docs/) folder or the [online documentation](https://allenneuraldynamics.github.io/openscope-experimental-launcher/) for:
- Full configuration and parameter file reference
- Pipeline module development
- Launcher customization
- Advanced usage and troubleshooting

---

MIT License. See [LICENSE](LICENSE) for details.
