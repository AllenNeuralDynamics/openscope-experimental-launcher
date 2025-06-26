import os
import glob
import json
from datetime import datetime
from typing import Optional
import h5py
import pandas as pd
from pathlib import Path
import logging

try:
    from aind_data_schema.core.session import Stream, SlapFieldOfView
    from aind_data_schema_models.modalities import Modality as StreamModality
    AIND_AVAILABLE = True
except ImportError:
    AIND_AVAILABLE = False

try:
    from openscope_experimental_launcher.post_processing.pp_stimulus_converter import get_timing_data
except ImportError:
    get_timing_data = None

# Configure logging at the top of the file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
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

def create_slap2_stream(plane: str, meta_path: str, summary_path: str, session_start_time=None, harp_folder=None) -> dict:
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
    logger.info(f"Reading summary mat fields from: {summary_path}")
    Z, analyzeHz = read_summary_mat_fields(summary_path)
    analyzeHz = _extract_scalar(analyzeHz) if analyzeHz is not None else None
    frame_rate = float(analyzeHz) if analyzeHz is not None else None
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
    if frame_rate is not None:
        slap_fov_kwargs['frame_rate'] = frame_rate
    # Always set required units and static fields if schema requires
    slap_fov_kwargs['dilation_unit'] = "pixel"
    slap_fov_kwargs['imaging_depth_unit'] = "micrometer"
    slap_fov_kwargs['fov_size_unit'] = "pixel"
    slap_fov_kwargs['fov_scale_factor_unit'] = "micrometer/pixel"
    slap_fov_kwargs['frame_rate_unit'] = "hertz"
    slap_fov_kwargs['power_unit'] = "percent"
    slap_fov_kwargs['scanfield_z_unit'] = "micrometer"

    # Only set static fields if schema requires (otherwise skip)
    slap_fov_kwargs['targeted_structure'] = "VISp"
    slap_fov_kwargs['fov_coordinate_ml'] = 0.0
    slap_fov_kwargs['fov_coordinate_ap'] = 0.0
    slap_fov_kwargs['fov_coordinate_unit'] = "micrometer"
    slap_fov_kwargs['fov_reference'] = "bregma"
    slap_fov_kwargs['magnification'] = "20x"
    slap_fov_kwargs['fov_scale_factor'] = 1.0

    # Add required fields for SlapFieldOfView if not present, but only if not misleading
    # session_type and path_to_array_of_frame_rates are required by schema
    slap_fov_kwargs['session_type'] = "Parent" if plane == "DMD1" else "Branch"
    slap_fov_kwargs['path_to_array_of_frame_rates'] = ""  # Only if you do not have real data, else skip FOV
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


def enhance_session_with_slap2_streams(root_dir: str, session_path: str = None):
    logger.info("Starting SLAP2 session enhancement for root_dir=%s, session_path=%s", root_dir, session_path)
    logger.info(f"Finding most recent DMD1.meta, DMD2.meta, Summary-*.mat, .harp folder, and session.json in {root_dir}")
    # Find most recent files
    dmd1_meta = find_most_recent('acquisition_*_DMD1.meta', root_dir)
    dmd2_meta = find_most_recent('acquisition_*_DMD2.meta', root_dir)
    summary_mat = find_most_recent('Summary-*.mat', root_dir)
    harp_folder = find_harp_folder(root_dir)
    session_json_path = session_path or find_session_json(root_dir)

    if not (dmd1_meta and dmd2_meta and summary_mat):
        logger.error("Could not find all required SLAP2 files.")
        return
    if not harp_folder:
        logger.error("Could not find .harp folder.")
        return
    if not session_json_path:
        logger.error("Could not find session.json file.")
        return

    # Load session
    logger.info(f"Loading session from {session_json_path}")
    session = load_session(session_json_path)
    session_start_time = session.get('session_start_time')

    # Create streams with HARP timing
    stream_dmd1 = create_slap2_stream('DMD1', dmd1_meta, summary_mat, session_start_time=session_start_time, harp_folder=harp_folder)
    stream_dmd2 = create_slap2_stream('DMD2', dmd2_meta, summary_mat, session_start_time=session_start_time, harp_folder=harp_folder)

    # Append to session (update this logic to match your session schema)
    if 'streams' not in session:
        session['streams'] = []
    if stream_dmd1:
        session['streams'].append(stream_dmd1)
    if stream_dmd2:
        session['streams'].append(stream_dmd2)

    # Save session
    save_session(session, session_json_path)
    logger.info("Added SLAP2 streams to %s", session_json_path)


def read_summary_mat_fields(summary_path):
    """Read Z and analyzeHz from a v7.3 .mat file using h5py."""
    Z = None
    analyzeHz = None
    with h5py.File(summary_path, 'r') as f:
        # Try to read Z and analyzeHz at the root or in subgroups
        if 'Z' in f:
            Z = f['Z'][()]
        if 'analyzeHz' in f:
            analyzeHz = f['analyzeHz'][()]
        # If not found at root, search recursively
        if Z is None or analyzeHz is None:
            def recursive_search(group):
                nonlocal Z, analyzeHz
                for k, v in group.items():
                    if isinstance(v, h5py.Dataset):
                        if k == 'Z' and Z is None:
                            Z = v[()]
                        if k == 'analyzeHz' and analyzeHz is None:
                            analyzeHz = v[()]
                    elif isinstance(v, h5py.Group):
                        recursive_search(v)
            recursive_search(f)
    # Convert to Python scalars if possible
    if hasattr(Z, 'tolist'):
        Z = Z.tolist()
    if hasattr(analyzeHz, 'tolist'):
        analyzeHz = analyzeHz.tolist()
    return Z, analyzeHz


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Enhance session.json with SLAP2 streams.")
    parser.add_argument("root_dir", help="Root directory to search for SLAP2 files")
    parser.add_argument("session_path", help="Path to session.json file")
    args = parser.parse_args()
    enhance_session_with_slap2_streams(args.root_dir, args.session_path)
