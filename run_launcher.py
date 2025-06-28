import argparse
import json
import sys
import os

# Map launcher names to their import paths and run functions
LAUNCHER_MAP = {
    "base": ("src.openscope_experimental_launcher.launchers.base_launcher", "run_from_params"),
    "bonsai": ("src.openscope_experimental_launcher.launchers.bonsai_launcher", "run_from_params"),
    "matlab": ("src.openscope_experimental_launcher.launchers.matlab_launcher", "run_from_params"),
    "python": ("src.openscope_experimental_launcher.launchers.python_launcher", "run_from_params"),
}

def main():
    parser = argparse.ArgumentParser(description="Unified OpenScope Launcher")
    parser.add_argument("--param_file", required=True, help="Path to parameter JSON file")
    args = parser.parse_args()

    # Load params
    with open(args.param_file, 'r') as f:
        params = json.load(f)

    # Determine launcher
    launcher_name = params.get("launcher")
    if not launcher_name:
        print("ERROR: 'launcher' key must be specified in the parameter file.")
        sys.exit(1)
    if launcher_name not in LAUNCHER_MAP:
        print(f"ERROR: Unknown launcher '{launcher_name}'. Valid options: {list(LAUNCHER_MAP.keys())}")
        sys.exit(1)

    module_path, func_name = LAUNCHER_MAP[launcher_name]
    # Dynamic import
    import importlib
    launcher_module = importlib.import_module(module_path)
    run_func = getattr(launcher_module, func_name)

    # Call the launcher
    run_func(args.param_file)

if __name__ == "__main__":
    main()
