# openscope-experimental-launcher

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Python](https://img.shields.io/badge/python->=3.8-blue?logo=python)
![Platform](https://img.shields.io/badge/platform-Windows-blue?logo=windows)
[![Documentation](https://img.shields.io/badge/docs-latest-blue)](https://allenneuraldynamics.github.io/openscope-experimental-launcher/)

Windows-first orchestration for OpenScope experiments.

The launcher merges rig configuration with a JSON parameter file, prompts for missing values, executes an acquisition subprocess (Bonsai/MATLAB/Python), and writes `launcher_metadata/processed_parameters.json` plus end/debug state artifacts for downstream tooling.

## Install

```bash
pip install -e .
```

Requirements: Python 3.8+, Windows 10 or 11, rig configuration TOML, and a parameter JSON file.

## Run a Session

1. Start from a template in `params/` (for example `params/example_minimalist_params.json`).
2. Ensure your parameter file sets a `launcher` (one of: `base`, `bonsai`, `matlab`, `python`).
3. Launch:

   ```bash
   python run_launcher.py --param_file params/example_minimalist_params.json
   ```

The launcher creates a session folder under `output_root_folder` and writes metadata into `launcher_metadata/`.

## Documentation

Keep this README high level; the full guides live at:

- https://allenneuraldynamics.github.io/openscope-experimental-launcher/

## License

MIT – see [LICENSE](LICENSE).

