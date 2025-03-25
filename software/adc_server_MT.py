import threading
import time
import struct
import numpy as np
import serial

from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

SERIAL_PORT = '/dev/tty.usbmodem205D388A47311'
BAUD_RATE   = 115200
PACKET_SIZE = 64
NOISE_LEVEL = 2050

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

def parse_packet(data):
    parsed_data = np.zeros((8, 5), dtype=int)
    for i in range(8):
        offset = i * 8
        group_id = data[offset]
        raw_short = struct.unpack('>H', data[offset+1 : offset+3])[0]
        raw_long1 = struct.unpack('>H', data[offset+3 : offset+5])[0]
        raw_long2 = struct.unpack('>H', data[offset+5 : offset+7])[0]
        emitter   = data[offset+7]
        inv_short = 2*NOISE_LEVEL - raw_short
        inv_long1 = 2*NOISE_LEVEL - raw_long1
        inv_long2 = 2*NOISE_LEVEL - raw_long2
        parsed_data[i] = [group_id, inv_short, inv_long1, inv_long2, emitter]
    return parsed_data

def sensor_data_task():
    """
    Continuously read 64-byte packets, parse them into 8×5 arrays,
    and batch them up every 50ms to emit over Socket.IO as 'batched_data'.
    """
    BATCH_INTERVAL = 0.05
    batch_buffer = []
    last_emit_time = time.time()

    while True:
        packet = ser.read(PACKET_SIZE)
        if len(packet) == PACKET_SIZE:
            arr_8x5 = parse_packet(packet)
            batch_buffer.append(arr_8x5)
            now = time.time()
            if now - last_emit_time >= BATCH_INTERVAL:
                arrays_list = [arr.tolist() for arr in batch_buffer]
                socketio.emit('batched_data', {'arrays': arrays_list})
                print(f"[Sensor Thread] Emitted {len(batch_buffer)} frames in one batch.")
                batch_buffer = []
                last_emit_time = now
            time.sleep(0.005)
        else:
            print("[Sensor Thread] No valid 64-byte frame received.")
            time.sleep(0.1)

@app.route('/')
def index():
    return "<h2>Server Running with 8×5 Inverted Parsing</h2>"

if __name__ == '__main__':
    sensor_thread = threading.Thread(target=sensor_data_task, daemon=True)
    sensor_thread.start()
    socketio.run(app, debug=True, port=5000)
