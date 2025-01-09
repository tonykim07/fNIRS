from flask import Flask, jsonify
from flask_socketio import SocketIO
import numpy as np
import threading
import time

server = Flask(__name__)
socketio = SocketIO(server, cors_allowed_origins="*")

# Shared data container
latest_data = {'data': []}
num_nodes = 25  # Fixed number of nodes

def generate_data():
    global latest_data
    while True:
        # Generate random activation data
        activation_data = np.random.randint(0, 5000, size=(num_nodes,)).tolist()
        latest_data['data'] = activation_data
        socketio.emit('data_stream', {'data': activation_data})
        time.sleep(1)

@server.route('/data', methods=['GET'])
def get_data():
    return jsonify(latest_data)

# Run data generator thread
thread = threading.Thread(target=generate_data)
thread.daemon = True
thread.start()

if __name__ == '__main__':
    socketio.run(server, debug=True, port=5000)
