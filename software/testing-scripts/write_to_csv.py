import serial
import struct
import numpy as np
import time
import csv

# Set up serial connection
ser = serial.Serial('/dev/tty.usbmodem205D388A47311', 115200, timeout=1)

NOISE_LEVEL = 2050

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
        sensor_channel_inv1 = 2 * NOISE_LEVEL - sensor_channel_1
        sensor_channel_2 = struct.unpack('>H', data[offset+3:offset+5])[0]
        sensor_channel_inv2 = 2 * NOISE_LEVEL - sensor_channel_2
        sensor_channel_3 = struct.unpack('>H', data[offset+5:offset+7])[0]
        sensor_channel_inv3 = 2 * NOISE_LEVEL - sensor_channel_3
        emitter_status    = data[offset+7]

        parsed_data[i] = [
            packet_identifier,
            sensor_channel_inv1,
            sensor_channel_inv2,
            sensor_channel_inv3,
            emitter_status
        ]
    return parsed_data

# === Create CSV and Overwrite Previous File ===
csv_filename = "all_groups.csv"
with open(csv_filename, mode='w', newline='') as csvfile:
    writer = csv.writer(csvfile)

    header = ["Time (s)"]
    for i in range(8):
        header += [f"G{i}_Short", f"G{i}_Long1", f"G{i}_Long2", f"G{i}_Emitter"]
    writer.writerow(header)

    print("Starting raw ADC logging (seconds elapsed)...\n")

    start_time = time.time()

    while True:
        data = ser.read(64)
        if len(data) == 64:
            parsed_data = parse_packet(data)

            elapsed_time = round(time.time() - start_time, 3)
            flat_row = [elapsed_time]
            for i in range(8):
                flat_row += parsed_data[i][1:5].tolist()

            # Write to CSV
            writer.writerow(flat_row)
            csvfile.flush()
            print(f"{elapsed_time}s - Logged frame to CSV.")
        else:
            print("No valid data received from the serial port.")
            time.sleep(0.1)


# import serial
# import struct
# import numpy as np
# import time
# import csv

# # Set up serial connection
# ser = serial.Serial('/dev/tty.usbmodem205D388A47311', 115200, timeout=1)

# NOISE_LEVEL = 2050

# def parse_packet(data):
#     """Parses 64 raw bytes into sensor data and its inverse."""
#     parsed_data = np.zeros((8, 5), dtype=int)
#     inv_data = np.zeros((8, 5), dtype=int)
#     for i in range(8):
#         offset = i * 8
#         packet_identifier = data[offset]
#         sensor_channel_1 = struct.unpack('>H', data[offset+1:offset+3])[0]
#         sensor_channel_inv1 = 2 * NOISE_LEVEL - sensor_channel_1
#         sensor_channel_2 = struct.unpack('>H', data[offset+3:offset+5])[0]
#         sensor_channel_inv2 = 2 * NOISE_LEVEL - sensor_channel_2
#         sensor_channel_3 = struct.unpack('>H', data[offset+5:offset+7])[0]
#         sensor_channel_inv3 = 2 * NOISE_LEVEL - sensor_channel_3
#         emitter_status = data[offset+7]

#         parsed_data[i] = [
#             packet_identifier,
#             sensor_channel_1,
#             sensor_channel_2,
#             sensor_channel_3,
#             emitter_status
#         ]

#         inv_data[i] = [
#             packet_identifier,
#             sensor_channel_inv1,
#             sensor_channel_inv2,
#             sensor_channel_inv3,
#             emitter_status
#         ]
#     return parsed_data, inv_data    

# # === Create CSV and Overwrite Previous File ===
# csv_filename = "parsed_plus_inv_data.csv"
# with open(csv_filename, mode='w', newline='') as csvfile:
#     writer = csv.writer(csvfile)

#     # Create header for parsed and inv data
#     header = ["Time (s)"]
#     for i in range(8):
#         header += [f"G{i}_Short", f"G{i}_Long1", f"G{i}_Long2", f"G{i}_Emitter"]
#     for i in range(8):
#         header += [f"Inv_G{i}_Short", f"Inv_G{i}_Long1", f"Inv_G{i}_Long2", f"Inv_G{i}_Emitter"]
#     writer.writerow(header)

#     print("Starting raw ADC logging (seconds elapsed)...\n")

#     start_time = time.time()
#     while True:
#         data = ser.read(64)
#         if len(data) == 64:
#             parsed_data, inv_data = parse_packet(data)

#             elapsed_time = round(time.time() - start_time, 3)
#             flat_row = [elapsed_time]

#             # Flatten parsed_data
#             for i in range(8):
#                 flat_row += parsed_data[i][1:5].tolist()  # exclude packet_identifier

#             # Flatten inv_data
#             for i in range(8):
#                 flat_row += inv_data[i][1:5].tolist()  # exclude packet_identifier

#             # Write to CSV
#             writer.writerow(flat_row)
#             csvfile.flush()
#             print(f"{elapsed_time}s - Logged frame to CSV.")
#         else:
#             print("No valid data received from the serial port.")
#             time.sleep(0.1)

