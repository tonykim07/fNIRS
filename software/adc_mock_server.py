# Description: This script generates fake sensor data and sends it to the client via SocketIO.

import eventlet
eventlet.monkey_patch()

import numpy as np
import time
from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Global variables for the triangle wave
current_value = 0
direction = 1  # 1 for increasing, -1 for decreasing
step = 10      # Adjust step size to control ramp speed

@app.route('/')
def index():
    return "<h2>Sensor Data Server Running</h2>"

# Function to generate fake sensor data (simulating the ADC reading)
def generate_fake_data():
    # """
    # Generate a 1D array of 24 sensor values (values between 0 and 4095).
    # This simulates the ADC output for testing purposes.
    # """
    # return np.random.randint(0, 4096, 24, dtype=int)
    """
    Generate a 1D array of 24 sensor values that ramp from 0 to 5000,
    then ramp down to 0, and repeat.
    """
    global current_value, direction, step
    current_value += step * direction

    if current_value >= 5000:
        current_value = 5000
        direction = -1
    elif current_value <= 0:
        current_value = 0
        direction = 1

    # Create an array of 24 identical values
    return [current_value] * 24

def sensor_data_task():
    """Continuously generate and emit fake sensor data via SocketIO."""
    while True:
        # Generate a fake 1D array of 24 values simulating sensor data
        sensor_array = generate_fake_data()
        
        # Send the array as a SocketIO event
        # socketio.emit('processed_data', {'sensor_array': sensor_array.tolist()})
        socketio.emit('processed_data', {'sensor_array': sensor_array})

        # Sleep for 0.0005 seconds to maintain the requested interval
        time.sleep(0.0005)

if __name__ == '__main__':
    socketio.start_background_task(sensor_data_task)
    socketio.run(app, debug=True, port=5000)
