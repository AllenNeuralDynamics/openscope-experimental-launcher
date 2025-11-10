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
   - Place pre-acquisition modules in ``src/openscope_experimental_launcher/pre_acquisition/``.
   - Place post-acquisition modules in ``src/openscope_experimental_launcher/post_acquisition/``.
   - Each module should accept a ``param_file`` argument and return 0 for success, 1 for failure.
3. **Register your module in your parameter file:**
   - Add the module name to the ``pre_acquisition_pipeline`` or ``post_acquisition_pipeline`` list in your JSON param file.
4. **Write or update tests.**
5. **Submit a pull request.**

Example: Adding a Pre-Acquisition Module
----------------------------------------
.. code-block:: python

   # src/openscope_experimental_launcher/pre_acquisition/my_custom_module.py
   def main(param_file):
       # Your logic here
       return 0  # success

Example: Using Your Module in a Pipeline
----------------------------------------
.. code-block:: json

   {
     "pre_acquisition_pipeline": ["my_custom_module"],
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
