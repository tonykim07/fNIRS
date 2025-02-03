import eventlet
eventlet.monkey_patch()
from flask import Flask
from flask_socketio import SocketIO
import numpy as np
import threading
import time
from collections import deque

server = Flask(__name__)
socketio = SocketIO(server, cors_allowed_origins="*", async_mode="eventlet")
lock = threading.Lock()

# Shared data container
latest_data = deque(maxlen=10)  # Buffer last 10 frames
num_nodes = 20  # Fixed number of nodes

def generate_data():
    while True:
        with lock:
            activation_data = np.random.randint(0, 5000, size=(num_nodes,)).tolist()
            latest_data.append(activation_data)
        time.sleep(0.1)  # Simulate data generation at 10 Hz

def send_data():
    while True:
        with lock:
            if latest_data:
                # print("Sending data:", latest_data)  # Debugging print
                socketio.emit('data_stream', {'data': list(latest_data)})
        time.sleep(0.5)  # Stream data to the client every 500 ms


# Run data generation and streaming threads
threading.Thread(target=generate_data, daemon=True).start()
threading.Thread(target=send_data, daemon=True).start()

if __name__ == '__main__':
    socketio.run(server, debug=True, port=5000)
