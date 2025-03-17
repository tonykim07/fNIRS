import serial
import struct
import numpy as np
import time
from tabulate import tabulate
import nirsimple.preprocessing as nsp
import nirsimple.processing as nproc

# Set up serial connection (adjust the port and baud rate as necessary)
ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 115200, timeout=1)  # Replace with your actual port

# Function to parse the packet data into an 8x5 array
def parse_packet(data):
    print(f"Received Data: {data.hex()}")  # Print raw hex data for debugging
    parsed_data = np.zeros((8, 5), dtype=int)  # Initialize an 8x5 array
    
    for i in range(8):  # Loop through the 8 sensor groups
        offset = i * 8  # Each group occupies 8 bytes
        packet_identifier = data[offset]
        sensor_channel_1 = struct.unpack('>H', data[offset+1:offset+3])[0]
        sensor_channel_2 = struct.unpack('>H', data[offset+3:offset+5])[0]
        sensor_channel_3 = struct.unpack('>H', data[offset+5:offset+7])[0]
        emitter_status = data[offset+7]
        
        parsed_data[i] = [packet_identifier, sensor_channel_1, sensor_channel_2, sensor_channel_3, emitter_status]
    
    return parsed_data

# Function to print data for each sensor channel
def print_sensor_data(parsed_data):
    print("\n--------------------------------------------------")
    print("Formatted Sensor Data (8x5 Array):")
    print(parsed_data)
    print("\nEach row represents: [Group ID, Short, Long1, Long2, Mode]")

# Read data from serial port and structure it for processing
def read_data_from_serial():
    while True:
        data = ser.read(64)  # Expecting 64 bytes (8 sensor groups * 8 bytes per group)
        if len(data) == 64:
            parsed_data = parse_packet(data)
            print_sensor_data(parsed_data)
        else:
            print("No valid data received from the serial port.")

# Start reading and printing the structured data
read_data_from_serial()
