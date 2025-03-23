import serial
import struct
import numpy as np
import time
import csv
import os
from datetime import datetime

# Set up serial connection (adjust the port and baud rate as necessary)
ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 115200, timeout=1)

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
        emitter_status    = data[offset+7]
        
        parsed_data[i] = [
            packet_identifier,
            sensor_channel_1,
            sensor_channel_2,
            sensor_channel_3,
            emitter_status
        ]
    return parsed_data

# Set up the unified CSV file
csv_filename = "all_groups.csv"
header_written = os.path.isfile(csv_filename)  # Check if file already exists

with open(csv_filename, mode='a', newline='') as csvfile:
    writer = csv.writer(csvfile)

    # Write header only if file is new
    if not header_written:
        header = ["Timestamp"]
        for i in range(8):
            header += [f"G{i}_Short", f"G{i}_Long1", f"G{i}_Long2", f"G{i}_Emitter"]
        writer.writerow(header)

    print("Starting raw ADC logging (single CSV)...\n")

    while True:
        data = ser.read(64)
        if len(data) == 64:
            parsed_data = parse_packet(data)

            # Get current timestamp
            timestamp = datetime.now().isoformat(timespec='milliseconds')

            # Flatten the 8x5 sensor array into one row (only keeping 4 columns per group)
            flat_row = [timestamp]
            for i in range(8):
                flat_row += parsed_data[i][1:5].tolist()  # [Short, Long1, Long2, Emitter]

            # Write the full row
            writer.writerow(flat_row)
            csvfile.flush()

            # Optional: print for debugging
            print(f"{timestamp} - Logged frame to CSV.")

        else:
            print("No valid data received from the serial port.")
            time.sleep(0.1)
