# Session Builder Refactoring

## Overview

The session building logic has been refactored to support reusability across different rigs. The new architecture consists of:

1. **BaseSessionBuilder** - A base class in `openscope_experimental_launcher.base.session_builder`
2. **Rig-specific implementations** - That extend the base class (e.g., SLAP2SessionBuilder)

## Architecture

### BaseSessionBuilder

The `BaseSessionBuilder` class provides:
- Common session building logic
- Abstract methods that must be implemented by rig-specific classes
- Helper methods for creating common configurations (lasers, detectors, etc.)
- Standardized parameter handling

### Key Abstract Methods

Rig-specific implementations must implement:

```python
def _create_stimulus_epoch(self, start_time, end_time, params, bonsai_software, script_software, **kwargs):
    """Create stimulus epoch for the experiment."""
    pass

def _create_data_streams(self, params, **kwargs):
    """Create data streams for the experiment."""
    pass
```

### Optional Override Methods

```python
def _get_session_type(self, params):
    """Get the session type for this rig."""
    
def _get_rig_id(self, params):
    """Get the rig ID for this rig."""
    
def _get_additional_script_parameters(self, params):
    """Get additional rig-specific script parameters."""
```

## Creating a New Rig Session Builder

### Step 1: Create the Session Builder Class

```python
from openscope_experimental_launcher.base.session_builder import BaseSessionBuilder

class MyRigSessionBuilder(BaseSessionBuilder):
    def __init__(self):
        super().__init__("MyRig")  # Rig name
    
    def _create_stimulus_epoch(self, start_time, end_time, params, bonsai_software, script_software, **kwargs):
        # Create rig-specific stimulus epoch
        return StimulusEpoch(
            stimulus_start_time=start_time,
            stimulus_end_time=end_time,
            stimulus_name=params.get("stimulus_name", "My Rig Stimulus"),
            stimulus_modalities=[StimulusModality.VISUAL],
            software=[bonsai_software],
            script=script_software,
            trials_total=params.get("num_trials", 100),
            trials_finished=params.get("num_trials", 100),
            notes=params.get("stimulus_notes", "My rig experiment")
        )
    
    def _create_data_streams(self, params, **kwargs):
        # Create rig-specific data streams
        return []  # Or actual Stream objects
```

### Step 2: Use in Your Launcher

```python
from .session_builder import MyRigSessionBuilder

class MyRigLauncher(BaseExperiment):
    def __init__(self):
        super().__init__()
        self.session_builder = MyRigSessionBuilder()
    
    def build_session(self):
        return self.session_builder.build_session(
            start_time=self.start_time,
            end_time=self.stop_time,
            params=self.params,
            mouse_id=self.mouse_id,
            user_id=self.user_id,
            session_uuid=self.session_uuid,
            # Add any rig-specific parameters as kwargs
        )
```

## SLAP2 Example

The SLAP2 implementation demonstrates:
- Backward compatibility with existing interfaces
- Rig-specific parameters (slap_fovs)
- Custom helper methods for hardware configuration

```python
# The SLAP2 build_session method maintains backward compatibility
session = builder.build_session(
    start_time=datetime.now(),
    end_time=datetime.now(),
    params=experiment_params,
    mouse_id="mouse123",
    user_id="user456",
    session_uuid="uuid-123",
    slap_fovs=field_of_views  # SLAP2-specific parameter
)
```

## Benefits

1. **Code Reuse** - Common session building logic is shared
2. **Consistency** - All rigs use the same base structure
3. **Maintainability** - Updates to common logic benefit all rigs
4. **Extensibility** - Easy to add new rigs
5. **Backward Compatibility** - Existing code continues to work

## Helper Methods

The base class provides helper methods for common configurations:

```python
# Create laser configuration
laser_config = self._create_laser_config(
    name="My Laser",
    wavelength=920,
    power=15.0
)

# Create detector configuration
detector_config = self._create_detector_config(
    name="My Detector",
    exposure_time=1.0,
    trigger_type="External"
)
```

## Testing

Each rig implementation should include tests that verify:
- Proper initialization
- Correct session building with rig-specific parameters
- Error handling
- Backward compatibility (if applicable)

See `tests/test_base_session_builder.py` and `tests/test_slap2_session_builder_refactored.py` for examples.
