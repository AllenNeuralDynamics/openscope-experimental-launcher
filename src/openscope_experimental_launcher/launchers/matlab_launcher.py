"""MATLAB launcher built on the shared MATLAB Engine integration."""

from __future__ import annotations

import logging

from .base_launcher import BaseLauncher
from ..interfaces import matlab_interface


class MatlabLauncher(BaseLauncher):
    """
    Launcher for MATLAB-based OpenScope experiments using MATLAB Engine.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._matlab_engine = None
        self._matlab_request = None
    
    def _get_launcher_type_name(self) -> str:
        """Get the name of the launcher type for logging."""
        return "MATLAB"
    
    def create_process(self):
        """Connect to the shared MATLAB engine and invoke the entry point."""

        request = matlab_interface.build_launch_request(self.params, self.output_session_folder)
        if request is None:
            raise RuntimeError("Unable to prepare MATLAB launch request")

        self._matlab_request = request
        self._matlab_engine = matlab_interface.connect_shared_engine(request)

        def engine_connector():
            return matlab_interface.connect_shared_engine(request)

        process = matlab_interface.start_matlab_function(
            self._matlab_engine,
            request,
            engine_connector=engine_connector,
        )
        return process

    def stop(self):
        """Stop acquisition and release MATLAB engine resources."""

        result = super().stop()
        try:
            keep_alive = True
            if self._matlab_request is not None:
                keep_alive = self._matlab_request.keep_engine_alive
            process_engine = None
            if getattr(self, "process", None) is not None:
                resume_attempts = getattr(self.process, "resume_attempts", 0)
                if resume_attempts:
                    logging.info(
                        "MATLAB acquisition resumed %d time(s) during this session",
                        resume_attempts,
                    )
                process_engine = getattr(self.process, "current_engine", None)
            if process_engine is not None:
                self._matlab_engine = process_engine
            matlab_interface.cleanup_engine(
                self._matlab_engine,
                getattr(self, "process", None),
                keep_engine_alive=keep_alive,
            )
        finally:
            self._matlab_engine = None
            self._matlab_request = None
        return result

def run_from_params(param_file):
    """
    Module-level entry point for the unified launcher wrapper.
    Calls MatlabLauncher.run_from_params.
    """
    return MatlabLauncher.run_from_params(param_file)