State Persistence System
=======================

The OpenScope Experimental Launcher includes a robust state persistence system that allows experiments to be resumed after interruptions. This is particularly useful for long-running experiments or when debugging launcher configurations.

Overview
--------

The state persistence system provides:

- **Automatic state saving**: Launcher state is automatically saved at the end of each successful experiment
- **Namespace isolation**: Different launcher subclasses store their state in separate namespaces to avoid conflicts
- **Custom serialization**: Support for complex objects through custom serialization handlers
- **Backward compatibility**: Ability to load state from different versions or modules with the same class name
- **Error resilience**: Graceful handling of serialization errors and corrupted state files

Basic Usage
-----------

State persistence is enabled automatically. No additional configuration is required for basic usage.

When an experiment completes successfully, the launcher automatically saves its state to ``session_state.json`` in the output directory alongside the standard ``session.json`` file.

To resume an experiment from a previous state::

    launcher = MyCustomLauncher()
    launcher.load_session_state("/path/to/output/directory")
    # Launcher state is now restored

Creating Custom Launchers with State Persistence
------------------------------------------------

When creating custom launcher subclasses, the state persistence system automatically handles most basic Python types (strings, numbers, booleans, lists, dictionaries, datetime objects).

Simple Custom Launcher
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class MyCustomLauncher(BaseLauncher):
        def __init__(self, param_file=None, rig_config_path=None):
            super().__init__(param_file, rig_config_path)
            
            # These attributes will be automatically persisted
            self.experiment_phase = "initialization"
            self.trial_count = 0
            self.custom_settings = {"param1": "value1", "param2": 42}
            
        def create_process(self):
            # Your process creation logic here
            pass

All public attributes (those not starting with underscore) that contain basic Python types will be automatically saved and restored.

Advanced Custom Launcher with Custom Serialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For complex objects that need special handling, you can register custom serialization handlers:

.. code-block:: python

    class AdvancedCustomLauncher(BaseLauncher):
        def __init__(self, param_file=None, rig_config_path=None):
            super().__init__(param_file, rig_config_path)
            
            # Complex object that needs custom serialization
            self.protocol_config = ProtocolConfig()
            self.experiment_timeline = ExperimentTimeline()
            
            # Register custom serialization handlers
            self.register_state_handler(
                'protocol_config',
                serializer=lambda config: config.to_dict(),
                deserializer=lambda data: ProtocolConfig.from_dict(data)
            )
            
            self.register_state_handler(
                'experiment_timeline',
                serializer=self._serialize_timeline,
                deserializer=self._deserialize_timeline
            )
        
        def _serialize_timeline(self, timeline):
            """Custom serializer for timeline objects."""
            return {
                'events': [event.to_dict() for event in timeline.events],
                'start_time': timeline.start_time.isoformat() if timeline.start_time else None,
                'duration': timeline.duration
            }
        
        def _deserialize_timeline(self, data):
            """Custom deserializer for timeline objects."""
            timeline = ExperimentTimeline()
            timeline.events = [Event.from_dict(event) for event in data['events']]
            timeline.start_time = datetime.fromisoformat(data['start_time']) if data['start_time'] else None
            timeline.duration = data['duration']
            return timeline

Controlling What Gets Persisted
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can override the ``get_persistent_attributes()`` method to have fine-grained control over what gets saved:

.. code-block:: python

    class SelectivePersistenceLauncher(BaseLauncher):
        def __init__(self, param_file=None, rig_config_path=None):
            super().__init__(param_file, rig_config_path)
            self.important_state = "save_this"
            self.temporary_data = "don't_save_this"
        
        def get_persistent_attributes(self):
            """Override to control what gets persisted."""
            # Start with default attributes
            attrs = super().get_persistent_attributes()
            
            # Remove attributes we don't want to persist
            attrs.pop('temporary_data', None)
            
            # Add custom attributes with transformations
            attrs['important_state_backup'] = self.important_state
            
            return attrs
        
        def set_persistent_attributes(self, attrs):
            """Override to control how attributes are restored."""
            # Remove our custom backup attribute before calling super
            backup = attrs.pop('important_state_backup', None)
            
            # Restore normal attributes
            super().set_persistent_attributes(attrs)
            
            # Handle our custom backup
            if backup and not hasattr(self, 'important_state'):
                self.important_state = backup

Multi-Developer Safety Features
------------------------------

The state persistence system is designed to be safe when multiple developers are creating launcher subclasses:

Namespace Isolation
~~~~~~~~~~~~~~~~~~

Each launcher class stores its state in a separate namespace based on the module and class name. This prevents conflicts between different launcher implementations::

    # State is stored under namespace: "my_project.launchers.MyLauncher"
    # Even if another developer creates a class with the same name in a different module,
    # their state will be stored under: "other_project.launchers.MyLauncher"

Backward Compatibility
~~~~~~~~~~~~~~~~~~~~~

The system can load state from launchers with the same class name but different module paths. This helps when:

- Reorganizing code and moving classes between modules
- Loading state created by different versions of the same launcher
- Sharing experiment state between different development environments

Error Resilience
~~~~~~~~~~~~~~~

The system gracefully handles various error conditions:

- **Serialization errors**: If an attribute can't be serialized, it's skipped with a warning
- **Corrupted state files**: Invalid JSON or malformed state files are handled gracefully
- **Missing attributes**: If a restored attribute doesn't exist in the current launcher, it's added safely
- **Type mismatches**: Incompatible types are logged but don't crash the launcher

API Reference
-------------

State Persistence Methods
~~~~~~~~~~~~~~~~~~~~~~~~~

.. automethod:: openscope_experimental_launcher.launchers.base_launcher.BaseLauncher.save_session_state

.. automethod:: openscope_experimental_launcher.launchers.base_launcher.BaseLauncher.load_session_state

.. automethod:: openscope_experimental_launcher.launchers.base_launcher.BaseLauncher.get_session_state_info

.. automethod:: openscope_experimental_launcher.launchers.base_launcher.BaseLauncher.clear_session_state

Customization Methods
~~~~~~~~~~~~~~~~~~~~

.. automethod:: openscope_experimental_launcher.launchers.base_launcher.BaseLauncher.register_state_handler

.. automethod:: openscope_experimental_launcher.launchers.base_launcher.BaseLauncher.get_persistent_attributes

.. automethod:: openscope_experimental_launcher.launchers.base_launcher.BaseLauncher.set_persistent_attributes

State File Format
------------------

The ``session_state.json`` file has the following structure:

.. code-block:: json

    {
        "version": "1.0.0",
        "launcher_class": "MyCustomLauncher",
        "launcher_module": "my_project.launchers.my_launcher",
        "created_at": "2025-06-23T10:30:00.123456",
        "launcher_states": {
            "my_project.launchers.my_launcher.MyCustomLauncher": {
                "attributes": {
                    "experiment_phase": "data_collection",
                    "trial_count": 150,
                    "custom_settings": {"param1": "value1", "param2": 42}
                },
                "saved_at": "2025-06-23T10:30:00.123456"
            }
        }
    }

The nested structure allows multiple launcher types to coexist in the same state file, each in its own namespace.

Best Practices
--------------

1. **Use meaningful attribute names**: Since state is persisted across sessions, use clear, descriptive names for your attributes.

2. **Register custom serializers early**: Call ``register_state_handler()`` in your ``__init__`` method to ensure handlers are available when needed.

3. **Handle serialization errors gracefully**: Design your custom serializers to handle edge cases and provide meaningful error messages.

4. **Test state persistence**: Include tests that verify your launcher can save and restore its state correctly.

5. **Document your state**: If your launcher has complex state requirements, document what attributes are persisted and how they're used.

6. **Use version control**: If your launcher's state format changes over time, consider adding version information to your serialized data.

Example Test Case
-----------------

Here's a complete example of how to test state persistence in your custom launcher:

.. code-block:: python

    def test_my_launcher_state_persistence():
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create launcher and modify its state
            launcher = MyCustomLauncher()
            launcher.experiment_phase = "data_collection"
            launcher.trial_count = 100
            launcher.custom_settings = {"modified": True}
            
            # Save state
            assert launcher.save_session_state(tmpdir)
            
            # Create new launcher and load state
            new_launcher = MyCustomLauncher()
            assert new_launcher.load_session_state(tmpdir)
            
            # Verify state was restored correctly
            assert new_launcher.experiment_phase == "data_collection"
            assert new_launcher.trial_count == 100
            assert new_launcher.custom_settings == {"modified": True}

This ensures that your launcher's state persistence works correctly and provides confidence that experiments can be resumed reliably.
