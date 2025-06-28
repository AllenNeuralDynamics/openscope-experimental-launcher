import logging
import zmq
import time
import json

def run_pre_acquisition(param_file):
    """
    Pre-acquisition ZMQ publisher module for OpenScope.

    Publishes a 'pre_acquisition_ready' message over ZMQ to signal readiness.
    Wait time before publishing is configurable via param file (zmq_ready_publisher_wait, in seconds).

    Args:
        param_file (str): Path to the parameter JSON file.
    Returns:
        int: 0 if message published successfully, 1 for failure.
    """
    wait_time = 0.5
    try:
        with open(param_file, 'r') as f:
            params = json.load(f)
        wait_time = params.get('zmq_ready_publisher_wait', wait_time)
    except Exception as e:
        logging.warning(f"Could not read param file for wait time: {e}")
    try:
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.bind("tcp://*:5555")
        # Wait for subscribers to connect
        time.sleep(wait_time)
        socket.send_string("pre_acquisition_ready")
        logging.info(f"ZMQ: Published 'pre_acquisition_ready' on tcp://*:5555 after waiting {wait_time} seconds")
        # Give time for message to be sent before closing
        time.sleep(0.5)
        socket.close()
        context.term()
        return 0
    except Exception as e:
        logging.error(f"ZMQ publisher failed: {e}")
        return 1
