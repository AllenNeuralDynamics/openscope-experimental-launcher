import logging
import zmq
import time
import json

def run_pre_acquisition(param_file):
    """
    Pre-acquisition ZMQ waiter module for OpenScope.

    Waits for a 'pre_acquisition_ready' message over ZMQ before proceeding.
    Timeout is configurable via param file (zmq_ready_waiter_timeout, in seconds).

    Args:
        param_file (str): Path to the parameter JSON file.
    Returns:
        int: 0 if message received successfully, 1 for failure.
    """
    timeout = 10
    try:
        with open(param_file, 'r') as f:
            params = json.load(f)
        timeout = params.get('zmq_ready_waiter_timeout', timeout)
    except Exception as e:
        logging.warning(f"Could not read param file for timeout: {e}")
    try:
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect("tcp://localhost:5555")
        socket.setsockopt_string(zmq.SUBSCRIBE, "pre_acquisition_ready")
        logging.info(f"ZMQ: Waiting for 'pre_acquisition_ready' on tcp://localhost:5555 (timeout={timeout}s)")
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        socks = dict(poller.poll(timeout * 1000))
        if socket in socks and socks[socket] == zmq.POLLIN:
            msg = socket.recv_string()
            if msg == "pre_acquisition_ready":
                logging.info("ZMQ: Received 'pre_acquisition_ready', proceeding.")
                socket.close()
                context.term()
                return 0
            else:
                logging.warning(f"ZMQ: Received unexpected message: {msg}")
        else:
            logging.error(f"ZMQ: Timeout waiting for 'pre_acquisition_ready' after {timeout} seconds.")
        socket.close()
        context.term()
        return 1
    except Exception as e:
        logging.error(f"ZMQ waiter failed: {e}")
        return 1
