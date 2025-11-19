Contributing to OpenScope Experimental Launcher
=============================================

Thank you for your interest in contributing! Our goal is to provide a generic, robust launcher for neuroscience experiments, with all project- and experiment-specific logic handled by modular pipeline modules.

Philosophy
----------
- **Generic Launchers:** The core launchers (for Bonsai, MATLAB, Python, etc.) are designed to be as generic as possible.
- **Modular Pipelines:** All pre- and post-acquisition steps (e.g., mouse weight prompts, experiment notes) are implemented as standalone modules, not in the launcher core.
- **Extensibility:** New modules can be added for any experiment-specific or project-specific operation, without modifying the launcher code.

How to Contribute
-----------------
1. **Fork the repository and create a branch.**
2. **Add or improve a module:**
   - **Launcher modules** live in ``src/openscope_experimental_launcher/pre_acquisition`` or ``post_acquisition`` and typically expose ``run_pre_acquisition`` / ``run_post_acquisition`` (or ``run``) returning ``0`` on success.
   - **Script modules** stay with the workflow repository checked out via ``repository_url``; reference them using the structured ``module_type: "script_module"`` entry in your parameter file so they evolve alongside the main experiment code.
3. **Register your module in your parameter file:**
   - For launcher modules, add the name (without ``.py``) to ``pre_acquisition_pipeline`` or ``post_acquisition_pipeline``.
   - For script modules, add an object with ``module_type``, ``module_path`` (relative to the repo root), and optional ``module_parameters`` / ``function_args``. See :doc:`modules` for the full schema.
4. **Write or update tests.**
5. **Submit a pull request.**

Example: Adding a Pre-Acquisition Module
----------------------------------------
.. code-block:: python

   # src/openscope_experimental_launcher/pre_acquisition/my_custom_module.py
    def run_pre_acquisition(param_file):
       # Your logic here
       return 0  # success

Example: Using Your Module in a Pipeline
----------------------------------------
.. code-block:: json

   {
       "pre_acquisition_pipeline": [
          "my_custom_module",
          {
             "module_type": "script_module",
             "module_path": "code/custom_repo/pipeline/post_process.py",
             "module_parameters": {
                "function": "prepare_metadata",
                "function_args": {
                   "output_path": "{session_folder}/derived/metadata.json"
                }
             }
          }
       ],
     ...
   }

Guidelines
----------
- Keep modules focused and single-purpose.
- Do not add experiment-specific logic to the launcher core.
- Document your module's purpose and usage in its docstring.
- See the ``docs/`` folder for more details and best practices.

---
MIT License.
