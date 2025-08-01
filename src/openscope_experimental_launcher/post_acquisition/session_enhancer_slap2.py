"""
SLAP2 Session Enhancement Post-Acquisition Tool
Enhances existing session.json files with SLAP2-specific information
by adding SLAP2 stream objects and populating required fields.

This module is intended to be used as a command-line tool, but the
enhance_existing_slap2_session function can be used directly to enhance
sessions programmatically.

Usage:
  python session_enhancer_slap2.py processed_parameters.json

Arguments:
  processed_parameters.json  Path to the processed_parameters.json file
  containing output folder and other parameters.

Description:
  This script enhances existing session.json files with SLAP2-specific
  information, including adding SLAP2 stream objects and populating
  required fields. It is intended to be used as a command-line tool,
  but the enhance_existing_slap2_session function can also be used
  directly to enhance sessions programmatically.

  The script performs the following steps:
  - Finds the most recent DMD1 and DMD2 meta files, Summary.mat file,
    and .harp folder under the session folder.
  - Loads the session.json file and extracts the session start time.
  - Extracts timing data from the HARP folder if available.
  - Reads DMD dilation, raster size, and z-slice information from the
    meta files.
  - Creates SLAP2 stream objects for DMD1 and DMD2 by populating the
    required fields in the aind-data-schema SlapFieldOfView and Stream
    objects.
  - Adds the SLAP2 streams to the session.json file and saves it.

  The script also provides a run_post_acquisition function that serves as
  a unified entry point for SLAP2 session enhancement. It loads
  parameters, prompts for missing fields, and runs the enhancement
  process.

  Example:
    python session_enhancer_slap2.py processed_parameters.json

  This will enhance the session.json file in the specified output folder
  with SLAP2 streams for DMD1 and DMD2.

  Note:
    - This module requires the aind-data-schema and
      openscope_experimental_launcher packages.
    - The session_folder parameter must contain the output_session_folder
      field in its parameters.json file.
"""

import os
import glob
import json
from datetime import datetime
from typing import Optional
import h5py
import pandas as pd
from pathlib import Path
import logging
from openscope_experimental_launcher.utils import param_utils

try:
    from aind_data_schema.core.session import Stream, SlapFieldOfView
    from aind_data_schema_models.modalities import Modality as StreamModality
    AIND_AVAILABLE = True
except ImportError:
    AIND_AVAILABLE = False

try:
    from openscope_experimental_launcher.post_acquisition.stimulus_table_predictive_processing import get_timing_data
except ImportError:
    get_timing_data = None

logger = logging.getLogger(__name__)

def find_most_recent(pattern: str, root: str) -> Optional[str]:
    """Recursively find the most recent file matching pattern under root."""
    matches = [os.path.join(dp, f)
               for dp, dn, filenames in os.walk(root)
               for f in filenames if glob.fnmatch.fnmatch(f, pattern)]
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


def load_session(session_path: str) -> dict:
    with open(session_path, 'r') as f:
        return json.load(f)


def save_session(session: dict, session_path: str):
    with open(session_path, 'w') as f:
        json.dump(session, f, indent=2)

def read_pixel_dilation(meta_path):
    """Read pixelDilationXY from AcquisitionContainer/ScannerParameters in a .meta (HDF5) file."""
    x, y = None, None
    with h5py.File(meta_path, 'r') as f:
        if 'AcquisitionContainer' in f:
            acq = f['AcquisitionContainer']
            if 'ScannerParameters' in acq:
                scanner_params = acq['ScannerParameters']
                if 'pixelDilationXY' in scanner_params:
                    arr = scanner_params['pixelDilationXY'][()]
                    if hasattr(arr, 'tolist'):
                        arr = arr.tolist()
                    if isinstance(arr, (list, tuple)) and len(arr) == 2:
                        x, y = arr[0], arr[1]
    return x, y

def _extract_scalar(val):
    """Recursively extract a scalar from arbitrarily nested lists/arrays."""
    while isinstance(val, (list, tuple)) and len(val) == 1:
        val = val[0]
    # If it's still a list/tuple, try to get the first element that is not a list/tuple
    if isinstance(val, (list, tuple)):
        for v in val:
            if not isinstance(v, (list, tuple)):
                return v
        # fallback: just return the first element
        return val[0]
    return val

def read_dmd_index(meta_path):
    """Read DMD index from AcquisitionContainer/ScannerParameters/dmdIndex in a .meta (HDF5) file."""
    idx = None
    with h5py.File(meta_path, 'r') as f:
        if 'AcquisitionContainer' in f:
            acq = f['AcquisitionContainer']
            if 'ScannerParameters' in acq:
                scanner_params = acq['ScannerParameters']
                if 'dmdIndex' in scanner_params:
                    arr = scanner_params['dmdIndex'][()]
                    if hasattr(arr, 'tolist'):
                        arr = arr.tolist()
                    if isinstance(arr, (list, tuple)) and len(arr) >= 1:
                        idx = arr[0]
                    else:
                        idx = arr
    return idx

def read_raster_size_and_z(meta_path):
    """Read rasterSizeXY and zs from AcquisitionContainer/ParsePlan in a .meta (HDF5) file."""
    raster_size = None
    zs = None
    with h5py.File(meta_path, 'r') as f:
        if 'AcquisitionContainer' in f:
            acq = f['AcquisitionContainer']
            if 'ParsePlan' in acq:
                parse_plan = acq['ParsePlan']
                if 'rasterSizeXY' in parse_plan:
                    arr = parse_plan['rasterSizeXY'][()]
                    if hasattr(arr, 'tolist'):
                        arr = arr.tolist()
                    raster_size = arr
                if 'zs' in parse_plan:
                    arr = parse_plan['zs'][()]
                    if hasattr(arr, 'tolist'):
                        arr = arr.tolist()
                    zs = arr
    return raster_size, zs

def create_slap2_stream(plane: str, meta_path: str, session_start_time=None, harp_folder=None, targeted_structure=None, fov_coordinate_ml=None, fov_coordinate_ap=None, fov_coordinate_unit=None, fov_reference=None, magnification=None, fov_scale_factor=None, session_type=None) -> dict:
    """Create a SLAP2 Stream for a given plane using aind-data-schema objects (only required fields)."""
    if not AIND_AVAILABLE:
        raise ImportError("aind-data-schema is not available")
    from datetime import datetime
    logger.info(f"Reading pixel dilation from: {meta_path}")
    dmd_dilation_x, dmd_dilation_y = read_pixel_dilation(meta_path)
    dmd_dilation_x = _extract_scalar(dmd_dilation_x) if dmd_dilation_x is not None else None
    dmd_dilation_y = _extract_scalar(dmd_dilation_y) if dmd_dilation_y is not None else None
    logger.info(f"Reading raster size and zs from: {meta_path}")
    raster_size, zs = read_raster_size_and_z(meta_path)
    # Use _extract_scalar to ensure raster_size values are scalars
    fov_width = int(_extract_scalar(raster_size[0])) if raster_size and len(raster_size) > 0 and _extract_scalar(raster_size[0]) is not None else None
    fov_height = int(_extract_scalar(raster_size[1])) if raster_size and len(raster_size) > 1 and _extract_scalar(raster_size[1]) is not None else None
    imaging_depth = int(_extract_scalar(zs[0])) if zs and len(zs) > 0 and _extract_scalar(zs[0]) is not None else None

    if session_start_time is not None and harp_folder is not None and get_timing_data is not None:
        logger.info(f"Extracting timing data from HARP folder: {harp_folder}")
        timing_data = get_timing_data(Path(harp_folder))
        if timing_data and 'normalized_start_trial' in timing_data and 'normalized_end_trial' in timing_data:
            start_times = timing_data['normalized_start_trial']
            end_times = timing_data['normalized_end_trial']
            if len(start_times) > 0 and len(end_times) > 0:
                slap2_start_offset = float(start_times[0])
                slap2_end_offset = float(end_times[-1])
                stream_start_time = pd.to_datetime(session_start_time).replace(microsecond=0) + pd.Timedelta(seconds=slap2_start_offset)
                stream_end_time = pd.to_datetime(session_start_time).replace(microsecond=0) + pd.Timedelta(seconds=slap2_end_offset)

    dmd_index = read_dmd_index(meta_path)
    logger.info(f"DMD index: {dmd_index}")
    # Build kwargs for SlapFieldOfView, only including real data
    slap_fov_kwargs = {}
    if dmd_dilation_x is not None:
        slap_fov_kwargs['dmd_dilation_x'] = int(dmd_dilation_x)
    if dmd_dilation_y is not None:
        slap_fov_kwargs['dmd_dilation_y'] = int(dmd_dilation_y)
    # Set index based on plane name if not found in meta
    if dmd_index is not None:
        slap_fov_kwargs['index'] = int(dmd_index)
    else:
        if plane.upper() == "DMD1":
            slap_fov_kwargs['index'] = 1
            logger.info("DMD index missing in meta, using plane name to set index=1 for DMD1.")
        elif plane.upper() == "DMD2":
            slap_fov_kwargs['index'] = 2
            logger.info("DMD index missing in meta, using plane name to set index=2 for DMD2.")
        else:
            logger.warning("Unknown plane name '%s', cannot set index.", plane)
    if imaging_depth is not None:
        slap_fov_kwargs['imaging_depth'] = imaging_depth
    if fov_width is not None:
        slap_fov_kwargs['fov_width'] = fov_width
    if fov_height is not None:
        slap_fov_kwargs['fov_height'] = fov_height
    # Always set required units and static fields if schema requires
    slap_fov_kwargs['dilation_unit'] = "pixel"
    slap_fov_kwargs['imaging_depth_unit'] = "micrometer"
    slap_fov_kwargs['fov_size_unit'] = "pixel"
    slap_fov_kwargs['fov_scale_factor_unit'] = "micrometer/pixel"
    slap_fov_kwargs['scanfield_z_unit'] = "micrometer"

    # Remove hardcoded values, use passed-in arguments
    if targeted_structure is not None:
        slap_fov_kwargs['targeted_structure'] = targeted_structure
    if fov_coordinate_ml is not None:
        slap_fov_kwargs['fov_coordinate_ml'] = fov_coordinate_ml
    if fov_coordinate_ap is not None:
        slap_fov_kwargs['fov_coordinate_ap'] = fov_coordinate_ap
    if fov_coordinate_unit is not None:
        slap_fov_kwargs['fov_coordinate_unit'] = fov_coordinate_unit
    if fov_reference is not None:
        slap_fov_kwargs['fov_reference'] = fov_reference
    if magnification is not None:
        slap_fov_kwargs['magnification'] = magnification
    if fov_scale_factor is not None:
        slap_fov_kwargs['fov_scale_factor'] = fov_scale_factor

    slap_fov_kwargs['session_type'] = session_type

    # Add required fields for SlapFieldOfView if not present, but only if not misleading
    # session_type and path_to_array_of_frame_rates are required by schema
    slap_fov_kwargs['path_to_array_of_frame_rates'] = "unavailable"  # Only if you do not have real data, else skip FOV
    if 'index' not in slap_fov_kwargs:
        logger.warning("Required field 'index' missing, skipping SlapFieldOfView for %s.", plane)
        return None
    if 'dmd_dilation_x' not in slap_fov_kwargs or 'dmd_dilation_y' not in slap_fov_kwargs:
        logger.warning("Required DMD dilation fields missing, skipping SlapFieldOfView for %s.", plane)
        return None
    logger.info("Creating SlapFieldOfView for %s with fields: %s", plane, slap_fov_kwargs)
    slap_fov = SlapFieldOfView(**slap_fov_kwargs)

    # Ensure stream_start_time and stream_end_time are always ISO strings
    if hasattr(stream_start_time, 'isoformat'):
        stream_start_time = stream_start_time.isoformat()
    if hasattr(stream_end_time, 'isoformat'):
        stream_end_time = stream_end_time.isoformat()

    stream = Stream(
        stream_start_time=stream_start_time,
        stream_end_time=stream_end_time,
        slap_fovs=[slap_fov],
        stream_modalities=[StreamModality.SLAP]
    )
    # Use model_dump with mode='json' for full JSON compatibility (Pydantic v2+)
    return stream.model_dump(mode='json', exclude_none=True)


def find_harp_folder(root_dir: str) -> Optional[str]:
    """Recursively find the first .harp folder under root_dir."""
    for dp, dn, filenames in os.walk(root_dir):
        for d in dn:
            if d == '.harp':
                return os.path.join(dp, d)
    return None


def find_session_json(root_dir: str) -> Optional[str]:
    """Recursively find the first session.json under root_dir."""
    for dp, dn, filenames in os.walk(root_dir):
        for f in filenames:
            if f == 'session.json':
                return os.path.join(dp, f)
    return None


def enhance_existing_slap2_session(session_folder: str, targeted_structure=None, fov_coordinate_ml=None, fov_coordinate_ap=None, fov_coordinate_unit=None, fov_reference=None, magnification=None, fov_scale_factor=None, session_type=None) -> bool:
    """
    Enhance an existing session.json with SLAP2 streams.
    Args:
        session_folder: Path to session folder containing experiment data
        targeted_structure, fov_coordinate_ml, fov_coordinate_ap, fov_coordinate_unit, fov_reference: CLI or prompt values
    Returns:
        True if enhancement successful, False otherwise
    """
    logger.info("Starting SLAP2 session enhancement for session_folder=%s", session_folder)
    session_json_path = os.path.join(session_folder, "session.json")
    dmd1_meta = find_most_recent('acquisition_*_DMD1.meta', session_folder)
    dmd2_meta = find_most_recent('acquisition_*_DMD2.meta', session_folder)
    summary_mat = find_most_recent('Summary-*.mat', session_folder)
    harp_folder = find_harp_folder(session_folder)

    if not (dmd1_meta and dmd2_meta and summary_mat):
        logger.error("Could not find all required SLAP2 files.")
        return False
    if not harp_folder:
        logger.error("Could not find .harp folder.")
        return False
    if not os.path.exists(session_json_path):
        logger.error("Could not find session.json file at %s", session_json_path)
        return False

    session = load_session(session_json_path)
    session_start_time = session.get('session_start_time')

    # All required parameters are now loaded and prompted via param_utils.load_parameters
    # Use params['targeted_structure'], params['fov_coordinate_ml'], etc. directly

    # Pass these to create_slap2_stream
    stream_dmd1 = create_slap2_stream('DMD1', dmd1_meta, session_start_time=session_start_time, harp_folder=harp_folder,
        targeted_structure=targeted_structure, fov_coordinate_ml=fov_coordinate_ml, fov_coordinate_ap=fov_coordinate_ap, fov_coordinate_unit=fov_coordinate_unit, fov_reference=fov_reference, magnification=magnification, fov_scale_factor=fov_scale_factor, session_type=session_type)
    stream_dmd2 = create_slap2_stream('DMD2', dmd2_meta, session_start_time=session_start_time, harp_folder=harp_folder,
        targeted_structure=targeted_structure, fov_coordinate_ml=fov_coordinate_ml, fov_coordinate_ap=fov_coordinate_ap, fov_coordinate_unit=fov_coordinate_unit, fov_reference=fov_reference, magnification=magnification, fov_scale_factor=fov_scale_factor, session_type=session_type)

    if 'streams' not in session:
        session['streams'] = []
    if stream_dmd1:
        session['streams'].append(stream_dmd1)
    if stream_dmd2:
        session['streams'].append(stream_dmd2)

    save_session(session, session_json_path)
    logger.info("Added SLAP2 streams to %s", session_json_path)
    return True


def run_post_acquisition(param_file: str = None, overrides: dict = None) -> int:
    """
    Unified entry point for SLAP2 session enhancement.
    Loads parameters, prompts for missing fields, and runs enhancement.
    Returns 0 on success, 1 on error.
    """
    import logging
    from pathlib import Path
    from openscope_experimental_launcher.utils import param_utils
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    required_fields = [
        "output_session_folder", "session_type", "targeted_structure", "fov_coordinate_ml", "fov_coordinate_ap", "fov_coordinate_unit", "fov_reference", "magnification", "fov_scale_factor"
    ]
    defaults = {
        "session_type": "Branch",
        "targeted_structure": "VISp",
        "fov_coordinate_ml": 0.0,
        "fov_coordinate_ap": 0.0,
        "fov_coordinate_unit": "micrometer",
        "fov_reference": "bregma",
        "magnification": "20x",
        "fov_scale_factor": 1.0
    }
    help_texts = {
        "output_session_folder": "Session output folder",
        "session_type": "Session type ('Parent' or 'Branch')",
        "targeted_structure": "Targeted structure (e.g. VISp)",
        "fov_coordinate_ml": "FOV coordinate ML (float, e.g. 0.0)",
        "fov_coordinate_ap": "FOV coordinate AP (float, e.g. 0.0)",
        "fov_coordinate_unit": "FOV coordinate unit (e.g. micrometer)",
        "fov_reference": "FOV reference (e.g. bregma)",
        "magnification": "Magnification (e.g. 20x)",
        "fov_scale_factor": "FOV scale factor (float, e.g. 1.0)"
    }
    def _validate_session_type(val):
        val = str(val).strip().capitalize()
        if val not in ("Parent", "Branch"):
            raise ValueError("Session type must be 'Parent' or 'Branch'")
        return val
    def _prompt_func(prompt, default):
        if 'session type' in prompt.lower():
            return param_utils.get_user_input(prompt, default, cast_func=_validate_session_type)
        return param_utils.get_user_input(prompt, default)
    params = param_utils.load_parameters(
        param_file=param_file,
        overrides=overrides,
        required_fields=required_fields,
        defaults=defaults,
        help_texts=help_texts,
        prompt_func=_prompt_func
    )
    session_folder = params["output_session_folder"]
    session_type = params["session_type"]
    if not Path(session_folder).exists():
        logging.error(f"Session folder does not exist: {session_folder}")
        return 1
    try:
        ok = enhance_existing_slap2_session(
            session_folder,
            targeted_structure=params.get('targeted_structure'),
            fov_coordinate_ml=params.get('fov_coordinate_ml'),
            fov_coordinate_ap=params.get('fov_coordinate_ap'),
            fov_coordinate_unit=params.get('fov_coordinate_unit'),
            fov_reference=params.get('fov_reference'),
            magnification=params.get('magnification'),
            fov_scale_factor=params.get('fov_scale_factor'),
            session_type=session_type
        )
    except Exception as e:
        logging.error(f"Validation or runtime error: {e}")
        return 1
    if not ok:
        logging.error("Failed to enhance session with SLAP2 streams")
        return 1
    logging.info("SLAP2 session enhancement completed successfully")
    return 0
