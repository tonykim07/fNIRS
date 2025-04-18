"""
adc_mock_server.py
===================
This script creates a Flask web server that simulates an ADC (Analog-to-Digital Converter)
and emits fake sensor data via SocketIO. The data is structured as a 1D array of 24 values
that ramp from 0 to 5000 and then back down to 0, simulating a triangle wave.
"""

import time
from flask import Flask
from flask_socketio import SocketIO
import eventlet
eventlet.monkey_patch()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Global variables for the triangle wave
CURRENT_VALUE = 0
DIRECTION = 1       # 1 for increasing, -1 for decreasing
STEP = 10           # Adjust step size to control ramp speed

@app.route('/')
def index():
    """
    Serve the main page of the web application.
    """
    return "<h2>Sensor Data Server Running</h2>"

def generate_fake_data():
    """
    Generate a 1D array of 24 sensor values that ramp from 0 to 5000,
    then ramp down to 0, and repeat.
    """
    global CURRENT_VALUE, DIRECTION, STEP
    CURRENT_VALUE += STEP * DIRECTION

    if CURRENT_VALUE >= 5000:
        CURRENT_VALUE = 5000
        DIRECTION = -1
    elif CURRENT_VALUE <= 0:
        CURRENT_VALUE = 0
        DIRECTION = 1

    # Create an array of 24 identical values
    return [CURRENT_VALUE] * 24

def sensor_data_task():
    """
    Continuously generate and emit fake sensor data via SocketIO.
    """
    while True:
        # Generate a fake 1D array of 24 values simulating sensor data
        sensor_array = generate_fake_data()

        # Send the array as a SocketIO event
        socketio.emit('processed_data', {'sensor_array': sensor_array})

        # Sleep for 0.0005 seconds to maintain the requested interval
        time.sleep(0.0005)

if __name__ == '__main__':
    socketio.start_background_task(sensor_data_task)
    socketio.run(app, debug=True, port=5000)
