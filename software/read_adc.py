import eventlet
eventlet.monkey_patch()

import serial
import struct
import numpy as np
import time
from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

@app.route('/')
def index():
    return "<h2>Sensor Data Server Running</h2>"

# Set up the serial connection (adjust the port as needed)
ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 9600, timeout=1)

def parse_packet_to_flat_array(data):
    """
    Parses 64 raw bytes into a flat 1D array of 24 sensor values:
    [Short1, Long1_1, Long2_1, Short2, Long1_2, Long2_2, ..., Short8, Long1_8, Long2_8]
    """
    sensor_values = np.zeros(24, dtype=int)
    for i in range(8):
        offset = i * 8
        short  = struct.unpack('>H', data[offset+1:offset+3])[0]
        long1  = struct.unpack('>H', data[offset+3:offset+5])[0]
        long2  = struct.unpack('>H', data[offset+5:offset+7])[0]
        sensor_values[i * 3 : i * 3 + 3] = [short, long1, long2]
    return sensor_values

def sensor_data_task():
    """Continuously read sensor data from the serial port and emit it via SocketIO."""
    while True:
        data = ser.read(64)
        if len(data) == 64:
            sensor_array = parse_packet_to_flat_array(data)
            socketio.emit('processed_data', {'sensor_array': sensor_array.tolist()})
            print("\nSensor Values (1D Array of 24):")
            print(sensor_array)
            time.sleep(0.01)
        else:
            print("No valid data received. Waiting...")
            time.sleep(0.1)

if __name__ == '__main__':
    socketio.start_background_task(sensor_data_task)
    socketio.run(app, debug=True, port=5000)
