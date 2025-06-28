# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Modular Session Creation**: Moved session.json creation from launchers to post-acquisition for better extensibility
- **Session Creator**: New `SessionCreator` class for standardized session.json generation
- **Session Enhancer Framework**: Launcher-specific enhancement system (e.g., `session_enhancer_bonsai.py`)
- **Improved Metadata Organization**: Runtime state files now organized in `launcher_metadata/` directory
- **Enhanced Test Coverage**: Comprehensive test suite with 158 passing tests (56% code coverage)
- **Post-Acquisition Template**: Standardized template for creating new post-acquisition tools

### Changed
- **BREAKING**: Session creation moved from launchers to post-acquisition workflow
- **File Organization**: 
  - `end_state.json` moved to `launcher_metadata/end_state.json`
  - `debug_state.json` moved to `launcher_metadata/debug_state.json`
  - Log files moved to `launcher_metadata/launcher.log`
- **Session Data Structure**: End state now uses nested structure with `session_info`, `launcher_info`, `experiment_data` sections
- **Import Paths**: Updated all imports for aind-data-schema compatibility
- **Launcher Metadata**: Enhanced metadata collection and storage for reproducibility

### Fixed
- **Import Errors**: Resolved aind-data-schema import compatibility issues
- **Stream Validation**: Fixed stream duplication and validation issues in session creation
- **Test Suite**: Updated all tests to match new architecture and file structure
- **Software Field Population**: Session.json now includes complete Software field with launcher metadata

### Removed
- **Legacy Session Creation**: Removed session creation methods from launcher classes
- **Old State Persistence**: Removed legacy state persistence system in favor of new metadata approach
- **Obsolete Tests**: Cleaned up outdated test files and skipped tests

### Documentation
- **Updated Badges**: Corrected test count (158 passed) and coverage (56%)
- **Post-Acquisition Guide**: Enhanced documentation for new session creation workflow
- **Architecture Documentation**: Updated to reflect modular post-acquisition design

## Architecture Changes

This release represents a major architectural improvement with these key changes:

1. **Session Creation Separation**: Session.json creation is now handled in post-acquisition, allowing for:
   - Better testability and modularity
   - Launcher-specific enhancements without coupling
   - Standalone session creation from existing data

2. **Improved File Organization**: Runtime files are now organized in a dedicated `launcher_metadata/` directory for cleaner session folders

3. **Enhanced Metadata**: More comprehensive metadata collection and storage for better experiment reproducibility

4. **Modular Design**: Post-acquisition tools follow a consistent template pattern for easier maintenance and extension
