# openscope-experimental-launcher

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Python](https://img.shields.io/badge/python->=3.8-blue?logo=python)
![Platform](https://img.shields.io/badge/platform-Windows-blue?logo=windows)
[![Documentation](https://img.shields.io/badge/docs-latest-blue)](https://allenneuraldynamics.github.io/openscope-experimental-launcher/)

Windows-first orchestration for Allen Institute OpenScope experiments. The launcher merges rig configuration with JSON parameters, guides operators through prompts, executes Bonsai/MATLAB/Python workflows, and records a flattened metadata trail for downstream processing.

## Highlights

- **Single source of truth**: merge rig TOML, parameter JSON, and runtime prompts into `processed_parameters.json` before execution.
- **Metadata aware**: optional pre-acquisition modules call the Metadata Service to confirm subject, procedures, and project context.
- **Modular pipeline**: compose pre/post acquisition steps (notes workflow, session archiver, resource monitors) without changing launcher code.
- **Integrity logging**: every run emits `end_state.json`, optional debug traces, and post-acquisition archives with checksum verification and transfer speed metrics.

## Install

```bash
pip install -e .
```

Requirements: Python 3.8+, Windows 10 or 11, rig configuration TOML, and a parameter JSON file.

## Run a Session

1. Edit or copy `params/example_minimalist_params.json` and point to your script, output root, and subject information.
2. Launch:

   ```bash
   python run_launcher.py --param_file params/example_minimalist_params.json
   ```

3. Follow interactive prompts; the launcher writes results to `launcher_metadata/` inside the session folder.

## Common Pipelines

- **Metadata validation**: `params/example_metadata_pipeline.json` fetches subject data, procedures (with timeout override), and confirms project selection before acquisition—override `metadata_service_base_url` only if your deployment uses a different metadata host.
- **Experiment notes**: `params/experiment_notes_pipeline.json` previews operator notes pre-run and blocks on confirmation post-run.
- **Archiving**: post-acquisition `session_archiver` copies data to backup destinations, verifies checksums, and logs transfer throughput.

Use `python run_module.py --module_type <phase> --module_name <module> --param_file <file>` to dry-run a module in isolation.

## MATLAB Launcher

MATLAB workflows run via a shared MATLAB Engine session. A sample configuration
(`params/matlab_local_test_params.json`) and helper entry point are provided—see
`docs/matlab_launcher` for setup.

## Documentation

Full guides live at the [documentation site](https://allenneuraldynamics.github.io/openscope-experimental-launcher/) and in `docs/`:

- Configuring parameter files and rig placeholders
- Metadata service integrations and module reference
- Extending launchers and customizing end-state payloads

## License

MIT – see [LICENSE](LICENSE).

