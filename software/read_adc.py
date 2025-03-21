import serial
import struct
import numpy as np
import time

# Set up serial connection (adjust port as needed)
ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 115200, timeout=1)

def parse_packet(data):
    """
    Parses 64 raw bytes into an 8×5 array of sensor data:
       [Group ID, Short, Long1, Long2, Emitter Status]
    """
    parsed_data = np.zeros((8, 5), dtype=int)
    for i in range(8):
        offset = i * 8
        group_id         = data[offset]
        sensor_channel_1 = struct.unpack('>H', data[offset+1:offset+3])[0]
        sensor_channel_2 = struct.unpack('>H', data[offset+3:offset+5])[0]
        sensor_channel_3 = struct.unpack('>H', data[offset+5:offset+7])[0]
        emitter_status   = data[offset+7]

        parsed_data[i] = [
            group_id,
            sensor_channel_1,
            sensor_channel_2,
            sensor_channel_3,
            emitter_status
        ]
    return parsed_data

# ##
# ## [ group 1 ] [ group 2 ] [ group 3 ] [ group 4 ] [ group 5 ] [ group 6 ] [ group 7 ] [ group 8 ]
# ## each group as 3 sensor values 

# ## final output should be a 1d array of 24 values 

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

if __name__ == "__main__":
    print("Reading raw packets and outputting 1D array of 24 sensor values...\n")
    while True:
        data = ser.read(64)
        if len(data) == 64:
            sensor_array = parse_packet_to_flat_array(data)
            print("\nSensor Values (1D Array of 24):")
            print(sensor_array)
        else:
            print("No valid data received. Waiting...")
            time.sleep(0.1)
