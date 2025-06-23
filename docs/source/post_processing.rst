Post-Processing Tools
====================

The OpenScope Experimental Launcher includes a modular post-processing system designed to handle data transformation after experiment completion.

Overview
--------

Post-processing tools are standalone, focused utilities that transform raw experiment data. Each tool follows a consistent design pattern for maximum reusability and maintainability.

.. note::
   Post-processing tools are completely independent of the launcher system and can be run on any session folder, whether from a recent experiment or historical data.

Design Philosophy
-----------------

**Single Responsibility**
   Each tool performs one specific transformation or analysis task

**Session-Based Input**
   Tools operate on session folders containing experiment data

**Self-Contained**
   No dependencies on launcher classes or complex state management

**Command-Line Interface**
   Simple, scriptable interfaces for automation and batch processing


Integration with Launchers
---------------------------

Post-processing tools are automatically called by specific launchers after experiment completion:

**Automatic Integration:**

.. code-block:: python

   from openscope_experimental_launcher.launchers import PredictiveProcessingLauncher
   
   launcher = PredictiveProcessingLauncher()
   success = launcher.run("experiment_params.json")
   # Post-processing automatically runs after successful experiment

**Manual Execution:**

.. code-block:: python

   # Run post-processing independently
   from openscope_experimental_launcher.post_processing.pp_stimulus_converter import process_session
   
   success = process_session("/path/to/session/folder")


Adding New Tools
----------------

When creating new post-processing tools, follow this template structure:

**File Structure:**

.. code-block:: python

   def process_session(session_folder: str, output_folder: str = None) -> bool:
       """
       Main processing function.
       
       Args:
           session_folder: Path to session data folder
           output_folder: Optional output folder (defaults to session folder)
           
       Returns:
           True if successful, False otherwise
       """
       # Implementation here
       pass

   def main():
       """Command-line interface."""
       parser = argparse.ArgumentParser(description="Tool description")
       parser.add_argument("session_folder", help="Path to session folder")
       parser.add_argument("output_folder", nargs='?', help="Output folder (optional)")
       
       args = parser.parse_args()
       success = process_session(args.session_folder, args.output_folder)
       sys.exit(0 if success else 1)

   if __name__ == "__main__":
       main()


**Integration Steps:**

1. Create the tool in ``src/openscope_experimental_launcher/post_processing/``
2. Add command-line interface following the template
3. Update launcher's ``run_post_processing()`` method if automatic integration is needed