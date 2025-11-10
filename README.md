# openscope-experimental-launcher

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Python](https://img.shields.io/badge/python->=3.8-blue?logo=python)
![Platform](https://img.shields.io/badge/platform-Windows-blue?logo=windows)
[![Documentation](https://img.shields.io/badge/docs-latest-blue)](https://allenneuraldynamics.github.io/openscope-experimental-launcher/)

Minimal, testable experiment orchestration for OpenScope: parameter merge (rig config + JSON + runtime prompts), subprocess launch, resource logging, and flattened metadata output (`end_state.json`, `debug_state.json`, `processed_parameters.json`).

## Quick Start

```bash
pip install -e .
python run_launcher.py --param_file params/example_minimalist_params.json
```

To run a pipeline module directly:

```bash
python run_module.py --module_type post_acquisition --module_name session_creator --param_file params/example_minimalist_params.json
```

## Rig Parameter Placeholders

Inject rig config values into `script_parameters`:

```
{rig_param:<key>}
```

Example snippet:
```json
{
	"script_parameters": {
		"PortName": "{rig_param:COM_port}",
		"RecordCameras": "{rig_param:RecordCameras}"
	}
}
```

Missing keys -> warning + empty string substitution.

## Metadata Outputs (Flattened)

- `end_state.json`: `{subject_id, user_id, session_uuid, start_time, stop_time, process_returncode, rig_config, experiment_data, custom_data}`
- `debug_state.json`: crash snapshot with `crash_info` and `launcher_state`.
- `processed_parameters.json`: unified parameters after prompting + rig merge.

## Full Documentation

See the comprehensive docs site or `docs/` folder for:

- Parameter & rig config reference
- Placeholder expansion details
- Post-acquisition tools (session_creator)
- Extending launcher via `get_custom_end_state()`

## License

MIT – see [LICENSE](LICENSE).

