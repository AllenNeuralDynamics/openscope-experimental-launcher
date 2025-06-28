"""
Generic runner for pre- or post-acquisition pipeline modules.

Usage:
    python run_module.py --module_type <module_type> --module_name <module_name> --param_file <param_file>

- <module_type>: Type of the module to run (pre_acquisition or post_acquisition)
- <module_name>: Name of the module to run (e.g., mouse_weight_post_prompt)
- <param_file>: Path to the parameter JSON file

This script will import the specified module and call its run_pre_acquisition or run_post_acquisition function as appropriate.
"""
import argparse
import importlib
import logging
import sys


def main():
    parser = argparse.ArgumentParser(description="Generic runner for pre- or post-acquisition pipeline modules.")
    parser.add_argument("--module_type", required=True, choices=["pre_acquisition", "post_acquisition"], help="Type of module: pre_acquisition or post_acquisition")
    parser.add_argument("--module_name", required=True, help="Name of the module to run (e.g., mouse_weight_post_prompt)")
    parser.add_argument("--param_file", required=True, help="Path to parameter JSON file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        module = importlib.import_module(f"openscope_experimental_launcher.{args.module_type}.{args.module_name}")
        func_name = "run_pre_acquisition" if args.module_type == "pre_acquisition" else "run_post_acquisition"
        run_func = getattr(module, func_name, None)
    except ImportError:
        print(f"Could not import module '{args.module_name}' from {args.module_type}.")
        sys.exit(2)

    if not run_func:
        print(f"Module '{args.module_name}' does not have the expected entry point '{func_name}'.")
        sys.exit(2)

    try:
        result = run_func(param_file=args.param_file)
        sys.exit(result if isinstance(result, int) else 0)
    except Exception as e:
        logging.error(f"Error running module {args.module_name}: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main()
