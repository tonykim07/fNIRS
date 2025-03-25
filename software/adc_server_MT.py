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
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

def parse_packet_to_flat_array(data):
    """
    Given 64 bytes, interpret them as 8 groups of 8 bytes each:
        Byte layout in each group of 8:
          [0]   group_id
          [1..2] short_val (big-endian)
          [3..4] long1_val (big-endian)
          [5..6] long2_val (big-endian)
          [7]   emitter_status
    We ONLY store short, long1, long2 for plotting (ignore group_id & emitter).
    So the final output is a 24-element array: [s0, l10, l20, s1, l11, l21, ..., s7, l17, l27].
    """
    sensor_values = np.zeros(24, dtype=int)
    for i in range(8):
        offset = i * 8

        # Not used in final array but read them to stay aligned
        group_id       = data[offset]
        emitter_status = data[offset + 7]

        short_val = struct.unpack('>H', data[offset+1:offset+3])[0]
        long1_val = struct.unpack('>H', data[offset+3:offset+5])[0]
        long2_val = struct.unpack('>H', data[offset+5:offset+7])[0]

        # Store short, long1, long2 in the final 24-element array
        sensor_values[i*3 : i*3+3] = [short_val, long1_val, long2_val]

    return sensor_values

def sensor_data_task():
    """
    Read 64-byte packets, parse them, and emit the 24-element array to clients.
    We'll do simple 'batched_data' logic: gather a batch every 50ms, then emit.
    """
    BATCH_INTERVAL = 0.05
    batch_buffer   = []
    last_emit_time = time.time()

    while True:
        packet = ser.read(64)
        if len(packet) == 64:
            parsed_24 = parse_packet_to_flat_array(packet)
            batch_buffer.append(parsed_24)

            now = time.time()
            if now - last_emit_time >= BATCH_INTERVAL:
                # Convert each parsed array to Python list for JSON
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
    return "<h2>Non-CSV Server Running (GroupID + Emitter ignored for plots)</h2>"

if __name__ == '__main__':
    sensor_thread = threading.Thread(target=sensor_data_task, daemon=True)
    sensor_thread.start()
    socketio.run(app, debug=True, port=5000)



# import threading
# import time
# import struct
# import numpy as np
# import serial

# from flask import Flask
# from flask_socketio import SocketIO

# app = Flask(__name__)
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# # Adjust these as needed.
# SERIAL_PORT = '/dev/tty.usbmodem205D388A47311'
# BAUD_RATE   = 9600
# PACKET_SIZE = 64  # each packet is exactly 64 bytes

# ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01)

# def parse_packet_to_flat_array(packet):
#     """
#     Convert 64 bytes -> 24 sensor values. 
#     Make sure your offsets and endianness match the actual microcontroller format!
#     """
#     sensor_values = np.zeros(24, dtype=int)
#     for i in range(8):
#         offset = i * 8
#         # Example big-endian parsing
#         short_val = struct.unpack('>H', packet[offset+1:offset+3])[0]
#         long1_val = struct.unpack('>H', packet[offset+3:offset+5])[0]
#         long2_val = struct.unpack('>H', packet[offset+5:offset+7])[0]
#         sensor_values[i * 3 : i * 3 + 3] = [short_val, long1_val, long2_val]
#     return sensor_values

# def sensor_data_task():
#     """
#     Continuously read from serial in a 'ring buffer' fashion. 
#     We only parse valid 64-byte frames once we have them.
#     """
#     BATCH_INTERVAL = 0.02  # 50 ms, for example
#     batch_buffer   = []
#     last_emit_time = time.time()

#     read_buffer    = b""   # Accumulate raw bytes here

#     while True:
#         # Read up to some chunk (e.g., up to 256 bytes) each iteration.
#         chunk = ser.read(256)
#         if chunk:
#             read_buffer += chunk  # Append the new bytes

#             # While we have at least one complete 64-byte packet, parse it
#             while len(read_buffer) >= PACKET_SIZE:
#                 packet  = read_buffer[:PACKET_SIZE]
#                 read_buffer = read_buffer[PACKET_SIZE:]  # remove those bytes from the buffer

#                 # Now parse the 64-byte packet as usual
#                 sensor_array = parse_packet_to_flat_array(packet)
#                 batch_buffer.append(sensor_array)

#         # If we have collected enough data and time has passed, emit it
#         now = time.time()
#         if (now - last_emit_time) >= BATCH_INTERVAL and batch_buffer:
#             # Emit all buffered samples at once
#             batched_samples = [arr.tolist() for arr in batch_buffer]
#             socketio.emit('batched_data', {'arrays': batched_samples})

#             print(f"[Sensor Thread] Emitted {len(batched_samples)} samples in one batch.")
#             batch_buffer = []
#             last_emit_time = now

#         # Optional short sleep to avoid busy-wait
#         time.sleep(0.005)

# @app.route('/')
# def index():
#     return "<h2>Verifying Aligned 64-byte Packets</h2>"

# if __name__ == '__main__':
#     sensor_thread = threading.Thread(target=sensor_data_task, daemon=True)
#     sensor_thread.start()
#     socketio.run(app, debug=True, port=5000)







# ################ testing w/ csv ###################
# import threading
# import time
# import struct
# import numpy as np
# import serial
# import csv

# from flask import Flask
# from flask_socketio import SocketIO

# app = Flask(__name__)
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# # Adjust as needed
# SERIAL_PORT = '/dev/tty.usbmodem205D388A47311'
# BAUD_RATE   = 115200
# NOISE_LEVEL = 2050

# # Open serial connection
# ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

# def parse_packet(data):
#     """
#     Parses 64 raw bytes into an 8×5 array of sensor data:
#     [Group ID, ShortInv, Long1Inv, Long2Inv, EmitterStatus].

#     Each group = 8 bytes:
#       - Byte 0:  packet_identifier (Group ID?)
#       - Bytes 1-2: sensor_channel_1 (2 bytes, big-endian)
#       - Bytes 3-4: sensor_channel_2 (2 bytes, big-endian)
#       - Bytes 5-6: sensor_channel_3 (2 bytes, big-endian)
#       - Byte  7:  emitter_status

#     We also apply the "inverted" channel calculation:
#        sensor_channel_inv = 2 * NOISE_LEVEL - sensor_channel
#     """
#     parsed_data = np.zeros((8, 5), dtype=int)
#     for i in range(8):
#         offset = i * 8

#         packet_identifier = data[offset]  # e.g., group ID
#         sensor_channel_1  = struct.unpack('>H', data[offset+1:offset+3])[0]
#         sensor_channel_2  = struct.unpack('>H', data[offset+3:offset+5])[0]
#         sensor_channel_3  = struct.unpack('>H', data[offset+5:offset+7])[0]
#         emitter_status    = data[offset+7]

#         # Invert the channels using NOISE_LEVEL as you specified
#         sensor_channel_inv1 = 2 * NOISE_LEVEL - sensor_channel_1
#         sensor_channel_inv2 = 2 * NOISE_LEVEL - sensor_channel_2
#         sensor_channel_inv3 = 2 * NOISE_LEVEL - sensor_channel_3

#         parsed_data[i] = [
#             packet_identifier,
#             sensor_channel_inv1,
#             sensor_channel_inv2,
#             sensor_channel_inv3,
#             emitter_status
#         ]
#     return parsed_data

# def sensor_thread_task():
#     """
#     Continuously reads 64-byte packets from the serial port, parses them,
#     and appends each frame to all_groups.csv. Also prints some debug info.
#     """
#     csv_filename = "all_groups.csv"

#     # Overwrite any previous file
#     with open(csv_filename, mode='w', newline='') as csvfile:
#         writer = csv.writer(csvfile)

#         # Build a header row: Time + (8 groups × 4 sensor fields)
#         header = ["Time (s)"]
#         for i in range(8):
#             header += [f"G{i}_Short", f"G{i}_Long1", f"G{i}_Long2", f"G{i}_Emitter"]
#         writer.writerow(header)

#         print("Starting raw ADC logging to", csv_filename)
#         start_time = time.time()

#         while True:
#             data = ser.read(64)
#             if len(data) == 64:
#                 parsed_data = parse_packet(data)
#                 elapsed_time = round(time.time() - start_time, 3)

#                 # Flatten out the 8 rows of data, ignoring the group ID column (index 0)
#                 # parsed_data[i] is [GroupID, ShortInv, Long1Inv, Long2Inv, Emitter]
#                 # We'll only store [ShortInv, Long1Inv, Long2Inv, Emitter].
#                 row = [elapsed_time]
#                 for i in range(8):
#                     # Grab columns 1..4 from parsed_data[i]
#                     row.extend(parsed_data[i][1:5].tolist())

#                 writer.writerow(row)
#                 csvfile.flush()

#                 print(f"{elapsed_time}s - Logged frame to CSV. [First group ID={parsed_data[0][0]}]")
#             else:
#                 print("No valid 64-byte frame received. Retrying...")
#                 time.sleep(0.1)

# @app.route('/')
# def index():
#     return "<h2>Server with CSV Logging is Running</h2>"

# if __name__ == '__main__':
#     # Spawn the sensor reading + CSV logging thread
#     sensor_thread = threading.Thread(target=sensor_thread_task, daemon=True)
#     sensor_thread.start()

#     # Run Flask-SocketIO server on port 5000 (optional)
#     socketio.run(app, debug=True, port=5000)
