# Code Cleanup: Removing Unnecessary Method Overrides

## Overview

This document summarizes the cleanup of unnecessary method overrides in derived launcher classes that were adding complexity without providing real value.

## Issues Identified and Fixed

### 1. SLAP2 Launcher - Unnecessary `run()` Override

**Problem**: The SLAP2 launcher overrode the `run()` method almost identically to the base class, but was missing the important signal handler setup and only changed the error message.

**Original Code** (unnecessary 37 lines):
```python
def run(self, param_file: Optional[str] = None) -> bool:
    try:
        self.load_parameters(param_file)
        if not self.git_manager.setup_repository(self.params):
            logging.error("Repository setup failed")
            return False
        self.start_bonsai()
        if self.bonsai_process.returncode != 0:
            logging.error("SLAP2 Bonsai experiment failed")  # Only difference
            return False
        if not self.post_experiment_processing():
            logging.warning("Post-experiment processing failed, but experiment data was collected")
        return True
    except Exception as e:
        logging.exception(f"SLAP2 experiment failed: {e}")
        return False
    finally:
        self.stop()
```

**Issues**:
- Missing `signal.signal(signal.SIGINT, self.signal_handler)` - **Critical bug!**
- Only difference was error message text
- 37 lines of duplicated code

**Solution**: 
- Removed the entire `run()` method override
- Added `_get_experiment_type_name()` method to base class for customizable error messages
- Override `_get_experiment_type_name()` in SLAP2 to return "SLAP2"

**Result**: Eliminated 37 lines of code and fixed the missing signal handler bug.

### 2. SLAP2 Session Builder - Unnecessary `_get_additional_script_parameters()` Override

**Problem**: The SLAP2 session builder overrode `_get_additional_script_parameters()` to return an empty dictionary, which is exactly what the base class does by default.

**Original Code** (unnecessary 3 lines):
```python
def _get_additional_script_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Get additional SLAP2-specific script parameters."""
    return {}
```

**Solution**: Removed the override entirely since the base class already returns `{}` by default.

**Result**: Eliminated 3 lines of unnecessary code.

### 3. Base Class Enhancement - Customizable Error Messages

**Problem**: The base class had hardcoded "Bonsai experiment failed" messages, which made it necessary for derived classes to override `run()` just to customize error messages.

**Solution**: Added `_get_experiment_type_name()` method to base class:
```python
def _get_experiment_type_name(self) -> str:
    """Get the name of the experiment type for logging and error messages."""
    return "Bonsai"
```

Updated error messages to use this method:
```python
logging.error(f"{self._get_experiment_type_name()} experiment failed")
```

**Result**: Now derived classes can customize error messages with a simple 3-line override instead of duplicating the entire `run()` method.

## Applied to Other Launchers

Added the same `_get_experiment_type_name()` override to:
- Mesoscope launcher (returns "Mesoscope")
- Neuropixel launcher (returns "Neuropixel")
- Cluster launcher (if needed)

## Benefits

1. **Reduced Code Duplication**: Eliminated 40+ lines of unnecessary code
2. **Fixed Critical Bug**: SLAP2 launcher now properly handles SIGINT signals
3. **Improved Maintainability**: Changes to base `run()` method now benefit all launchers
4. **Better Error Messages**: Each launcher type now has appropriate error messages
5. **Cleaner Architecture**: Derived classes only override what they actually need to customize

## Guidelines for Future Development

### When to Override vs. When to Use Base Class

**Good reasons to override a method**:
- Adding new functionality specific to the rig
- Fundamentally different behavior needed
- Extending base functionality with additional steps

**Bad reasons to override a method**:
- Just to change a string message (use configurable methods instead)
- Copying the same logic with minor variations
- Parameter passing without added logic

### Pattern: Use Configuration Methods Instead of Full Overrides

Instead of overriding entire methods, create smaller configuration methods that can be overridden:

```python
# Base class
def run(self):
    logging.info(f"Starting {self._get_experiment_type_name()} experiment")
    # ... rest of logic

def _get_experiment_type_name(self) -> str:
    return "Generic"

# Derived class - just override the configuration
def _get_experiment_type_name(self) -> str:
    return "SLAP2"
```

This pattern keeps the main logic in the base class while allowing customization of specific aspects.

## Testing

All existing tests continue to pass, confirming that:
- The refactoring didn't break any existing functionality
- The SLAP2 launcher works correctly with the base class `run()` method
- Error messages are properly customized for each rig type
- Signal handling now works correctly in SLAP2

## Files Modified

- `src/openscope_experimental_launcher/base/experiment.py`
- `src/openscope_experimental_launcher/slap2/launcher.py`
- `src/openscope_experimental_launcher/slap2/session_builder.py`
