# Description: This script generates fake sensor data and sends it to the client via SocketIO.

import eventlet
eventlet.monkey_patch()

import numpy as np
import time
from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

@app.route('/')
def index():
    return "<h2>Sensor Data Server Running</h2>"

# Function to generate fake sensor data (simulating the ADC reading)
def generate_fake_data():
    """
    Generate a 1D array of 24 sensor values (values between 0 and 4095).
    This simulates the ADC output for testing purposes.
    """
    return np.random.randint(0, 4096, 24, dtype=int)

def sensor_data_task():
    """Continuously generate and emit fake sensor data via SocketIO."""
    while True:
        # Generate a fake 1D array of 24 values simulating sensor data
        sensor_array = generate_fake_data()
        
        # Send the array as a SocketIO event
        socketio.emit('processed_data', {'sensor_array': sensor_array.tolist()})
        
        # Sleep for 0.0005 seconds to maintain the requested interval
        time.sleep(0.0005)

if __name__ == '__main__':
    socketio.start_background_task(sensor_data_task)
    socketio.run(app, debug=True, port=5000)
