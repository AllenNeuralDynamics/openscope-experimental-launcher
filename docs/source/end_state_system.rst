End State and Debug State System
=================================

The OpenScope Experimental Launcher uses a clean separation between runtime state and post-acquisition to ensure extensibility and debuggability.

Design Principles
-----------------

1. **Session Creation as Post-Acquisition**: Session files are created by reading experiment output folders, not during runtime. This allows session files to be regenerated after the fact.

2. **Debug State for Crash Analysis**: When experiments crash, the launcher saves its current state to help with debugging.

3. **Extensible End State**: Different launcher subclasses can add their own end state data without conflicts.

Architecture Overview
--------------------

The system creates several files in each experiment output folder:

- ``end_state.json``: Runtime information saved at experiment completion
- ``launcher_metadata.json``: Launcher configuration and parameters
- ``debug_state.json``: Launcher state when crashes occur (debugging only)
- ``session.json``: Created by post-acquisition tools from the above files

End State System
----------------

Basic Usage
~~~~~~~~~~~

The base launcher automatically saves end state information:

.. code-block:: python

    # In your launcher subclass
    def run(self):
        try:
            # ... experiment logic ...
            return True
        except Exception as e:
            # Debug state is automatically saved here
            raise

Custom End State Data
~~~~~~~~~~~~~~~~~~~~

Subclasses can add their own end state data:

.. code-block:: python

    class MyCustomLauncher(BaseLauncher):
        def __init__(self):
            super().__init__()
            self.custom_metric = 0
            self.trial_results = []
        
        def get_custom_end_state_data(self):
            return {
                "custom_metric": self.custom_metric,
                "trial_count": len(self.trial_results),
                "success_rate": self.calculate_success_rate(),
                "launcher_version": "v2.1",
                "analysis_pipeline": "custom_analysis_v1"
            }

The custom data is automatically merged with the base end state data and saved to ``end_state.json``.

Debug State System
------------------

When an experiment crashes, the launcher automatically saves debug information:

.. code-block:: json

    {
        "crash_time": "2024-01-01T12:30:45",
        "exception_type": "ValueError",
        "exception_message": "Invalid parameter value",
        "launcher_class": "MyCustomLauncher",
        "launcher_attributes": {
            "subject_id": "mouse_123",
            "custom_metric": 42,
            "trial_results": [...]
        },
        "process_info": {
            "pid": 1234,
            "returncode": null
        }
    }

This information helps developers debug crashes by seeing the exact state when the error occurred.

Session Creation Post-Acquisition
-------------------------------

Session files are created by the ``session_creator.py`` post-acquisition tool:

.. code-block:: bash

    # Create session.json from experiment data
    python -m openscope_experimental_launcher.post_acquisition.session_creator /path/to/output

    # Force overwrite existing session.json
    python -m openscope_experimental_launcher.post_acquisition.session_creator /path/to/output --force

The session creator reads:

- ``end_state.json``: For timing, subject info, and custom data
- ``launcher_metadata.json``: For launcher configuration
- Output folder contents: To determine data streams

Multiple Developer Workflow
---------------------------

This design handles multiple developers creating launcher subclasses:

1. **Namespace Separation**: Each launcher's custom data is clearly identified by class name
2. **Backwards Compatibility**: New end state fields don't break existing tools
3. **Extensible Post-Acquisition**: New post-acquisition tools can read the same end state files

Example: Multiple Research Groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Group A: Vision research
    class VisionLauncher(BaseLauncher):
        def get_custom_end_state_data(self):
            return {
                "visual_stimuli_count": self.stimuli_count,
                "contrast_levels": self.contrast_levels,
                "vision_research_version": "v1.2"
            }

    # Group B: Auditory research  
    class AuditoryLauncher(BaseLauncher):
        def get_custom_end_state_data(self):
            return {
                "tone_frequencies": self.frequencies,
                "volume_levels": self.volumes,
                "auditory_protocol": "standard_v2"
            }

Both groups' data appears in their respective ``end_state.json`` files without conflicts.

Custom Post-Acquisition Tools
----------------------------

Researchers can create custom post-acquisition tools that read the end state data:

.. code-block:: python

    # Custom analysis tool
    def analyze_vision_experiment(output_folder):
        with open(f"{output_folder}/end_state.json") as f:
            end_state = json.load(f)
        
        if "visual_stimuli_count" in end_state:
            # Process vision-specific data
            analyze_vision_data(end_state)
        
        # Generate custom reports, plots, etc.

Benefits
--------

1. **Reproducible**: Session files can be regenerated from experiment data
2. **Debuggable**: Crash state is preserved for analysis
3. **Extensible**: New launchers can add custom data without conflicts
4. **Modular**: Post-acquisition is separate from runtime
5. **Backwards Compatible**: Existing code continues to work

Migration from Old System
-------------------------

The old ``create_session_file()`` method is deprecated but still present for backwards compatibility. It now logs a warning and returns ``True`` without creating files.

To migrate:

1. Remove calls to ``create_session_file()`` from your code
2. Use the ``session_creator.py`` post-acquisition tool instead  
3. Add custom end state data via ``get_custom_end_state_data()`` if needed

Example Scripts
---------------

See ``examples/custom_launcher_example.py`` for a complete working example showing:

- How to create custom launcher subclasses
- How to add custom end state data
- How the end state files look
- How post-acquisition tools use the data
