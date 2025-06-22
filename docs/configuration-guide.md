# OpenScope Configuration System Guide

The OpenScope experimental launcher uses a three-tier configuration system designed to separate rig-specific settings from experiment-specific parameters.

## Configuration Types

### 1. Rig Configuration (TOML file)
**Purpose**: Hardware and setup-specific settings that remain constant for a physical rig.

**Default Location**: 
- Windows: `C:/RigConfig/rig_config.toml`
- Linux: `/opt/rigconfig/rig_config.toml`

**Contains**:
- `rig_id`: Unique identifier for this rig (defaults to hostname)
- `data_root_directory`: Base path for experiment data storage
- Hardware-specific settings (camera configs, sync settings, etc.)

**Example**:
```toml
# OpenScope Rig Configuration
rig_id = "rig-001-behavior"
data_root_directory = "C:/experiment_data"
```

### 2. Experiment Parameters (JSON file)
**Purpose**: Experiment-specific settings that change per experiment or session.

**Contains**:
- `subject_id`: Subject being tested
- `user_id`: User running the experiment
- `protocol_id`: Experimental protocol being run
- Stimulus parameters, session settings, etc.

**Example**:
```json
{
    "subject_id": "mouse_001",
    "user_id": "researcher",
    "protocol_id": ["detection_of_change"],
    "OutputFolder": "C:/experiment_data/2024-01-15/mouse_001",
    "stimulus_params": {
        "contrast": 0.8,
        "spatial_frequency": 0.04
    }
}
```

### 3. Runtime Information
**Purpose**: Fill in any missing required values through interactive prompts.

**Collected when**:
- Required values are missing from both rig config and experiment parameters
- User needs to confirm or override certain settings

## Configuration Priority

When the same parameter appears in multiple places, the priority is:

1. **Runtime prompts** (highest priority) - can override anything
2. **JSON experiment parameters** - override rig config for overlapping keys
3. **Rig configuration** (lowest priority) - provides base defaults

## Usage Guidelines

### Normal Operation
- **DO**: Create JSON parameter files for each experiment
- **DO**: Leave rig_config_path parameter as None to use default location
- **DON'T**: Put experiment-specific values in rig config
- **DON'T**: Override rig_config_path unless absolutely necessary

### Special Cases
The `rig_config_path` parameter in `initialize_launcher()` should **ONLY** be used for:
- Testing with custom rig configurations
- Non-standard rig setups
- Development and debugging

### What Goes Where?

| Setting Type | Rig Config | JSON Parameters | Runtime Prompts |
|--------------|------------|-----------------|-----------------|
| rig_id | ✅ | ❌ | ❌ |
| data_root_directory | ✅ | ❌ | ❌ |
| subject_id | ❌ | ✅ | ✅ (if missing) |
| user_id | ❌ | ✅ | ✅ (if missing) |
| protocol_id | ❌ | ✅ | ❌ |
| OutputFolder | ❌ | ✅ | ❌ |
| stimulus_params | ❌ | ✅ | ❌ |

## Code Examples

### Basic Usage
```python
# Normal operation - uses default rig config location
experiment = MyExperiment()
experiment.initialize_launcher(param_file="experiment_params.json")
```

### Testing with Custom Rig Config
```python
# Special case - custom rig config for testing
experiment = MyExperiment() 
experiment.initialize_launcher(
    param_file="test_params.json",
    rig_config_path="/path/to/test_rig_config.toml"  # Only for special cases!
)
```

## File Structure Example
```
C:/RigConfig/
├── rig_config.toml              # Rig-specific settings

C:/experiments/
├── daily_experiments/
│   ├── 2024-01-15_mouse001.json # Today's experiment parameters
│   ├── 2024-01-15_mouse002.json 
│   └── ...
├── protocol_templates/
│   ├── detection_of_change.json # Reusable protocol templates
│   ├── visual_behavior.json
│   └── ...
```

## Troubleshooting

### "rig_id not found" Error
- Check that rig config file exists at the default location
- Verify the rig config file contains a valid `rig_id` field
- For testing, create a custom rig config with a test rig_id

### "Configuration key not found" Error
- Check if the key should be in rig config (hardware/setup) or JSON parameters (experiment)
- Verify the parameter file contains all required experiment-specific settings
- Check if the value should be collected at runtime instead

### Performance Issues
- Don't override `rig_config_path` unnecessarily - it's optimized for the default location
- Use JSON parameter templates for similar experiments rather than recreating files

## Best Practices

1. **Keep rig config minimal** - only hardware/setup constants
2. **Use descriptive JSON parameter files** - name them by date/subject/protocol
3. **Create parameter templates** - reuse common configurations
4. **Let runtime prompts handle missing values** - don't hardcode everything
5. **Use version control for parameter templates** - track protocol changes
6. **Document custom rig settings** - comment your rig config file
