import threading
import time
import struct
import numpy as np
import serial

from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Serial config
SERIAL_PORT = '/dev/tty.usbmodem205E386D47311'
BAUD_RATE = 115200
PACKET_SIZE = 64
NOISE_LEVEL = 2050

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

def parse_packet(data):
    parsed_data = np.zeros((8, 5), dtype=int)
    for i in range(8):
        offset = i * 8
        group_id = data[offset]
        raw_short = struct.unpack('>H', data[offset+1:offset+3])[0]
        raw_long1 = struct.unpack('>H', data[offset+3:offset+5])[0]
        raw_long2 = struct.unpack('>H', data[offset+5:offset+7])[0]
        emitter = data[offset+7]
        inv_short = 2 * NOISE_LEVEL - raw_short
        inv_long1 = 2 * NOISE_LEVEL - raw_long1
        inv_long2 = 2 * NOISE_LEVEL - raw_long2
        parsed_data[i] = [group_id, inv_short, inv_long1, inv_long2, emitter]
    return parsed_data

def is_valid_packet(packet):
    group_ids = [packet[i * 8] for i in range(8)]
    return group_ids == list(range(240, 248))

def sensor_data_task():
    ser.reset_input_buffer()
    BATCH_INTERVAL = 0.05  # 50 ms
    buffer = bytearray()
    batch_buffer = []
    last_emit_time = time.time()

    while True:
        buffer += ser.read(64)

        while len(buffer) >= PACKET_SIZE:
            candidate = buffer[:PACKET_SIZE]
            group_ids = [candidate[i * 8] for i in range(8)]

            if is_valid_packet(candidate):
                arr_8x5 = parse_packet(candidate)

                # Print parsed data
                print("[Parsed arr_8x5]")
                for row in arr_8x5:
                    print(f"Group {row[0]}: short={row[1]}, long1={row[2]}, long2={row[3]}, emitter={row[4]}")

                batch_buffer.append(arr_8x5)
                buffer = buffer[PACKET_SIZE:]
            else:
                buffer = buffer[1:]  # resync

        now = time.time()
        if now - last_emit_time >= BATCH_INTERVAL and batch_buffer:
            socketio.emit('batched_data', {'arrays': [arr.tolist() for arr in batch_buffer]})
            print(f"[Sensor Thread] Emitted {len(batch_buffer)} synced frames.")
            batch_buffer.clear()
            last_emit_time = now

        time.sleep(0.005)

@app.route('/')
def index():
    return "<h3>Server running and streaming parsed 8×5 sensor packets.</h3>"

if __name__ == '__main__':
    ser.reset_input_buffer()
    sensor_thread = threading.Thread(target=sensor_data_task, daemon=True)
    sensor_thread.start()
    ser.reset_input_buffer()
    socketio.run(app, debug=True, port=5000)
