import serial
import struct
import numpy as np
import csv
import time

# Set up serial connection (adjust the port and baud rate as necessary)
ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 115200, timeout=1)  # Replace with your actual port

# Set up CSV file
csv_filename = "sensor_data.csv"
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Time (s)", "Sensor 1 - Short Channel"])

def parse_packet(data):
    if len(data) < 64:
        print("Warning: Incomplete packet received.")
        return None  # Return None if data size is incorrect
    
    parsed_data = np.zeros((8, 2), dtype=int)  # Adjusted to (8,2) for correct storage
    
    try:
        for i in range(8):  # Loop through the 8 sensor groups
            offset = i * 8  # Each group occupies 8 bytes
            packet_identifier = data[offset]
            sensor_channel_1 = struct.unpack('>H', data[offset+1:offset+3])[0]
            parsed_data[i] = [packet_identifier, sensor_channel_1]
    except struct.error as e:
        print(f"Error parsing packet: {e}")
        return None
    
    return parsed_data

def read_data_from_serial():
    start_time = time.time()
    while True:
        data = ser.read(64)  # Expecting 64 bytes (8 sensor groups * 8 bytes per group)
        if len(data) == 64:
            parsed_data = parse_packet(data)
            if parsed_data is not None:
                sensor_1_short_channel = parsed_data[0, 1]  # Sensor 1, Short Channel
                
                # Shrink time scale to show more horizontally
                elapsed_time = (time.time() - start_time) / 2  # Scale down time axis
                
                # Print data to terminal
                print(f"Time: {elapsed_time:.2f}s, Sensor 1 - Short Channel: {sensor_1_short_channel}")
                
                # Save data to CSV
                with open(csv_filename, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([elapsed_time, sensor_1_short_channel])
        else:
            print("No valid data received from the serial port.")

# Start reading and saving to CSV
read_data_from_serial()