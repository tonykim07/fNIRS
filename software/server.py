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
        time.sleep(0.5)  # Simulate data generation at 2 Hz
        
def send_data():
    while True:
        with lock:
            if latest_data:
                # Send only the latest frame of data
                latest_frame = latest_data[-1]
                socketio.emit('data_stream', {'data': latest_frame})
        time.sleep(1.0)  # Stream data to the client every 1s

# Run data generation and streaming threads
threading.Thread(target=generate_data, daemon=True).start()
threading.Thread(target=send_data, daemon=True).start()

if __name__ == '__main__':
    socketio.run(server, debug=True, port=5000)