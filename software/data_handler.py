import numpy as np
import logging
import socketio
import threading
from queue import Queue

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Initialize the Socket.IO client
sio = socketio.Client()

# Data queue to store incoming data
data_queue = Queue(maxsize=20)
data_lock = threading.Lock()  # Create a lock for synchronization

# Connection events
@sio.event
def connect():
    logging.info("Connected to the server.")

@sio.event
def disconnect():
    logging.info("Disconnected from the server.")

# Handle incoming data from the server
@sio.event
def processed_data(data):
    """Handle incoming data from the server."""
    # logging.info("Received new data: %s", data['concentrations'])
    activation_data = np.array(data['concentrations'])
    if activation_data.ndim == 1:
        activation_data = activation_data.reshape(-1, 1)
    
    with data_lock:
        if data_queue.full():
            data_queue.get()  # Remove the oldest data if the queue is full
        data_queue.put(activation_data)
    # logging.info("Updated data queue with new data")

def get_latest_data():
    latest = None
    with data_lock:
        if not data_queue.empty():
            latest = np.hstack(list(data_queue.queue))  # Get the entire history
    return latest

# if __name__ == "__main__":
#     sio.connect("http://localhost:5000")
#     sio.wait()
