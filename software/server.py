import eventlet
eventlet.monkey_patch()
from flask import Flask
from flask_socketio import SocketIO
import numpy as np
import time
from collections import deque

server = Flask(__name__)
socketio = SocketIO(server, cors_allowed_origins="*", async_mode="eventlet")

# Shared data container
latest_data = deque(maxlen=10)  # Buffer last 10 frames
num_nodes = 20  # Fixed number of nodes

def generate_data():
    while True:
        activation_data = np.random.randint(0, 5000, size=(num_nodes,)).tolist()
        latest_data.append(activation_data)
        # Use eventlet.sleep to yield control to other green threads
        eventlet.sleep(0.5)  # Generate data at 2 Hz

def send_data():
    while True:
        if latest_data:
            # Send only the latest frame of data
            latest_frame = latest_data[-1]
            socketio.emit('data_stream', {'data': latest_frame})
        eventlet.sleep(1.0)  # Stream data to the client every 1s

if __name__ == '__main__':
    # Start background tasks with the SocketIO helper
    socketio.start_background_task(generate_data)
    socketio.start_background_task(send_data)
    socketio.run(server, debug=True, use_reloader=False, port=5000)
