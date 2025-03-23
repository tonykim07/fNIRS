import serial
import struct
import numpy as np
import time
import csv
import os

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

def write_group_to_csv(group_id, row):
    """Appends a single row of raw sensor data to group_<id>.csv"""
    filename = f"group_{group_id}.csv"
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Group ID", "Short", "Long1", "Long2", "Emitter"])
        writer.writerow(row)

if __name__ == "__main__":
    print("Starting raw ADC logging...\n")
    while True:
        data = ser.read(64)
        if len(data) == 64:
            parsed_data = parse_packet(data)

            # Log each group to its own CSV
            for i in range(8):
                group_row = parsed_data[i]
                write_group_to_csv(group_id=i, row=group_row)

            # Optional: print to terminal
            print("\nRaw Sensor Data:")
            print(parsed_data)
        else:
            print("No valid data received from the serial port.")
            time.sleep(0.1)
