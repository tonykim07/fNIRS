from fnirs_data_processing import DataProcessor as DataProcessor
import nirsimple.processing as nproc
import nirsimple.preprocessing as nsp
from tabulate import tabulate
from flask_socketio import SocketIO
from flask import Flask
import struct
import serial
import numpy as np
import time
import eventlet
eventlet.monkey_patch()


# -------------------- Flask-SocketIO Server Setup --------------------
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


@app.route('/')
def index():
    return "<h2>Data Processor Server Running</h2>"


# Set up serial connection (adjust the port and baud rate as necessary)
ser = serial.Serial('/dev/tty.usbmodem205D388A47311', 115200,
                    timeout=1)  # Replace with your actual port


def parse_packet(data):
    """
    Parses 64 raw bytes into an 8×5 array of sensor data:
       [Group ID, Short, Long1, Long2, Emitter Status].
    """
    parsed_data = np.zeros((8, 5), dtype=int)
    for i in range(8):
        offset = i * 8
        packet_identifier = data[offset]
        sensor_channel_1 = struct.unpack('>H', data[offset+1:offset+3])[0]
        sensor_channel_2 = struct.unpack('>H', data[offset+3:offset+5])[0]
        sensor_channel_3 = struct.unpack('>H', data[offset+5:offset+7])[0]
        emitter_status = data[offset+7]

        parsed_data[i] = [
            packet_identifier,
            sensor_channel_1,
            sensor_channel_2,
            sensor_channel_3,
            emitter_status
        ]
    return parsed_data


def print_sensor_data(parsed_data):
    """
    Displays the 8×5 sensor array nicely.
    Rows => [Group ID, Short, Long1, Long2, Emitter].
    """
    print("\n--------------------------------------------------")
    print("Formatted Sensor Data (8×5 Array):")
    print(parsed_data)
    print("\nEach row represents: [Group ID, Short, Long1, Long2, Emitter]")


def data_processing_task():
    sensor_sums = np.zeros((8, 3), dtype=int)
    sensor_counts = np.zeros(8, dtype=int)
    current_emitter = None
    processor = DataProcessor()

    while True:
        data = ser.read(64)
        if len(data) == 64:
            parsed_data = parse_packet(data)

            NOISE_ESTIMATE = 2050
            for i in range(8):
                for j in range(1, 4):
                    parsed_data[i, j] = 2 * NOISE_ESTIMATE - parsed_data[i, j]

            emitter = parsed_data[0, 4]
            if current_emitter is None:
                current_emitter = emitter

            if emitter == current_emitter:
                for i in range(8):
                    ch1, ch2, ch3 = parsed_data[i,
                                                1], parsed_data[i, 2], parsed_data[i, 3]
                    if 100 <= ch1 <= 3900 and 100 <= ch2 <= 3900 and 100 <= ch3 <= 3900:
                        sensor_sums[i] += [ch1, ch2, ch3]
                        sensor_counts[i] += 1
            else:
                # print(
                #     f"\nEmitter changed from {current_emitter} to {emitter}.")
                # print("Computing average for old emitter...")

                averaged_data = np.zeros((8, 5), dtype=int)
                for i in range(8):
                    group_id = i
                    count = max(sensor_counts[i], 1)
                    avg1 = sensor_sums[i, 0] // count
                    avg2 = sensor_sums[i, 1] // count
                    avg3 = sensor_sums[i, 2] // count
                    averaged_data[i] = [group_id, avg1,
                                        avg2, avg3, current_emitter]

                # print("\nAveraged Sensor Data (8×5 Array):")
                # print(averaged_data)
                # print(
                #     "\nEach row => [Group ID, Avg Short, Avg Long1, Avg Long2, Emitter]")
                # print("--------------------------------------------------")

                result = processor.process_data_packet(averaged_data)

                if result is not None:
                    concentrations, table_data = result
                    socketio.emit('processed_data', {
                        'concentrations': concentrations,
                        'table_data': table_data
                    })
                    # print("Latest Concentration Values (48 channels):")
                    # print(tabulate(table_data, headers=[
                    #       "Channel", "Type", "Concentration"]))
                    # print("-" * 500)
                    # print("Data Sent to GUI Graphing Function: ", concentrations)
                    # print("-" * 500)

                sensor_sums.fill(0)
                sensor_counts.fill(0)

                current_emitter = emitter
                for i in range(8):
                    ch1, ch2, ch3 = parsed_data[i,
                                                1], parsed_data[i, 2], parsed_data[i, 3]
                    sensor_sums[i] += [ch1, ch2, ch3]
                    sensor_counts[i] += 1
        else:
            print("No valid data received from the serial port.")
            time.sleep(0.1)


if __name__ == '__main__':
    # Start the data processing in a background thread
    socketio.start_background_task(data_processing_task)
    socketio.run(app, debug=True, use_reloader=False, port=5000)
