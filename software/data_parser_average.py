# import serial
# import struct
# import numpy as np
# import time
# from tabulate import tabulate
# import nirsimple.preprocessing as nsp
# import nirsimple.processing as nproc

# # Set up serial connection (adjust the port and baud rate as necessary)
# ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 115200, timeout=1)  # Replace with your actual port

# # --------------------------------------------------------------------------------
# # 1) parse_packet: Convert 64 bytes into an 8x5 numpy array
# # --------------------------------------------------------------------------------
# def parse_packet(data):
#     """Parses 64 raw bytes into an 8x5 array of sensor data:
#        [Group ID, Short, Long1, Long2, Emitter Status]."""
#     parsed_data = np.zeros((8, 5), dtype=int)
#     for i in range(8):
#         offset = i * 8
#         packet_identifier = data[offset]
#         sensor_channel_1 = struct.unpack('>H', data[offset+1:offset+3])[0]
#         sensor_channel_2 = struct.unpack('>H', data[offset+3:offset+5])[0]
#         sensor_channel_3 = struct.unpack('>H', data[offset+5:offset+7])[0]
#         emitter_status    = data[offset+7]
        
#         parsed_data[i] = [
#             packet_identifier,
#             sensor_channel_1,
#             sensor_channel_2,
#             sensor_channel_3,
#             emitter_status
#         ]
#     return parsed_data

# # --------------------------------------------------------------------------------
# # 2) Optional debug printing function
# # --------------------------------------------------------------------------------
# def print_sensor_data(parsed_data):
#     """Displays the 8x5 sensor array nicely."""
#     print("\n--------------------------------------------------")
#     print("Formatted Sensor Data (8x5 Array):")
#     print(parsed_data)
#     print("\nEach row represents: [Group ID, Short, Long1, Long2, Mode]")

# # --------------------------------------------------------------------------------
# # 3) MAIN LOOP: Accumulate readings for the current emitter
# #               Once the emitter changes, compute/print the average, then reset.
# #               We skip any row that has channel values < 100 or > 3900.
# # --------------------------------------------------------------------------------
# if __name__ == "__main__":
#     # A) Accumulation buffers
#     sensor_sums = np.zeros((8, 3), dtype=int)  # Summation for [Short, Long1, Long2]
#     sensor_counts = np.zeros(8, dtype=int)     # Count how many valid rows we've accumulated
#     current_emitter = None                     # Track which emitter we are currently accumulating

#     print("Starting emitter-based accumulation...\n")
#     while True:
#         data = ser.read(64)  # Expecting 64 bytes (8 sensor groups * 8 bytes)
#         if len(data) == 64:
#             # Parse the packet into an 8x5 array
#             parsed_data = parse_packet(data)
#             # (Optional) print_sensor_data(parsed_data)

#             # The emitter status for this packet (assuming all rows have the same)
#             emitter = parsed_data[0, 4]

#             # If we haven't set an emitter yet, this is our first cycle
#             if current_emitter is None:
#                 current_emitter = emitter

#             # If the emitter is the same, keep accumulating
#             if emitter == current_emitter:
#                 for i in range(8):
#                     # Extract the 3 channel values
#                     ch1, ch2, ch3 = parsed_data[i, 1], parsed_data[i, 2], parsed_data[i, 3]
#                     # Check each channel within [100..3900]
#                     if 100 <= ch1 <= 3900 and 100 <= ch2 <= 3900 and 100 <= ch3 <= 3900:
#                         sensor_sums[i] += [ch1, ch2, ch3]
#                         sensor_counts[i] += 1
#             else:
#                 # Emitter changed!
#                 print(f"\nEmitter changed from {current_emitter} to {emitter}.")
#                 print("Computing average for old emitter...")

#                 # B) Compute average for the old emitter
#                 averaged_data = np.zeros((8, 5), dtype=int)
#                 for i in range(8):
#                     # We'll just use i as group_id or you can store an actual ID
#                     group_id = i
#                     count = max(sensor_counts[i], 1)
#                     avg1  = sensor_sums[i, 0] // count
#                     avg2  = sensor_sums[i, 1] // count
#                     avg3  = sensor_sums[i, 2] // count
#                     averaged_data[i] = [group_id, avg1, avg2, avg3, current_emitter]

#                 # C) Print or send the averaged data
#                 print("\nAveraged Sensor Data (8x5 Array):")
#                 print(averaged_data)
#                 print("\nEach row represents: [Group ID, Avg Short, Avg Long1, Avg Long2, Emitter]")
#                 print("--------------------------------------------------")

#                 # D) Reset sums and counts
#                 sensor_sums.fill(0)
#                 sensor_counts.fill(0)

#                 # E) Start accumulating for the new emitter
#                 current_emitter = emitter
#                 for i in range(8):
#                     ch1, ch2, ch3 = parsed_data[i, 1], parsed_data[i, 2], parsed_data[i, 3]
#                     if 100 <= ch1 <= 3900 and 100 <= ch2 <= 3900 and 100 <= ch3 <= 3900:
#                         sensor_sums[i] += [ch1, ch2, ch3]
#                         sensor_counts[i] += 1
#         else:
#             print("No valid data received from the serial port.")
#             time.sleep(0.1)  # Slight delay to avoid spamming

import serial
import struct
import numpy as np
import time
from tabulate import tabulate
import nirsimple.preprocessing as nsp
import nirsimple.processing as nproc

# Set up serial connection (adjust the port and baud rate as necessary)
ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 115200, timeout=1)  # Replace with your actual port

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

def print_sensor_data(parsed_data):
    """
    Displays the 8×5 sensor array nicely.
    Rows => [Group ID, Short, Long1, Long2, Emitter].
    """
    print("\n--------------------------------------------------")
    print("Formatted Sensor Data (8×5 Array):")
    print(parsed_data)
    print("\nEach row represents: [Group ID, Short, Long1, Long2, Emitter]")

if __name__ == "__main__":
    # 1) Accumulation buffers
    # sensor_sums[i] => sum of [Short, Long1, Long2] for group i
    # sensor_counts[i] => how many valid samples we've added for group i
    sensor_sums = np.zeros((8, 3), dtype=int)
    sensor_counts = np.zeros(8, dtype=int)

    current_emitter = None  # track which emitter we are currently reading

    print("Starting emitter-based accumulation...\n")
    while True:
        data = ser.read(64)  # read 64 bytes (8 groups × 8 bytes)
        if len(data) == 64:
            # 2) Parse the packet (8×5 array)
            parsed_data = parse_packet(data)

            # 3) We assume all rows have the same emitter
            emitter = parsed_data[0, 4]

            # First time? set current_emitter
            if current_emitter is None:
                current_emitter = emitter

            # 4) If emitter is unchanged, accumulate
            if emitter == current_emitter:
                for i in range(8):
                    # Extract the 3 channels
                    ch1, ch2, ch3 = parsed_data[i, 1], parsed_data[i, 2], parsed_data[i, 3]
                    # Accept only if in [100..3900]
                    if 100 <= ch1 <= 3900 and 100 <= ch2 <= 3900 and 100 <= ch3 <= 3900:
                        sensor_sums[i] += [ch1, ch2, ch3]
                        sensor_counts[i] += 1

            else:
                # 5) Emitter changed => compute averages for the OLD emitter
                print(f"\nEmitter changed from {current_emitter} to {emitter}.")
                print("Computing average for old emitter...")

                averaged_data = np.zeros((8, 5), dtype=int)
                for i in range(8):
                    # group_id can be i, or you can store from previous parse
                    group_id = i
                    count = max(sensor_counts[i], 1)  # avoid div by zero
                    avg1  = sensor_sums[i, 0] // count
                    avg2  = sensor_sums[i, 1] // count
                    avg3  = sensor_sums[i, 2] // count
                    # store in final 8×5
                    averaged_data[i] = [group_id, avg1, avg2, avg3, current_emitter]

                # 6) Print or send the averaged data
                print("\nAveraged Sensor Data (8×5 Array):")
                print(averaged_data)
                print("\nEach row => [Group ID, Avg Short, Avg Long1, Avg Long2, Emitter]")
                print("--------------------------------------------------")

                # 7) Reset sums & counts
                sensor_sums.fill(0)
                sensor_counts.fill(0)

                # 8) Start new cycle for the new emitter
                current_emitter = emitter
                for i in range(8):
                    ch1, ch2, ch3 = parsed_data[i, 1], parsed_data[i, 2], parsed_data[i, 3]
                    if 100 <= ch1 <= 3900 and 100 <= ch2 <= 3900 and 100 <= ch3 <= 3900:
                        sensor_sums[i] += [ch1, ch2, ch3]
                        sensor_counts[i] += 1
        else:
            print("No valid data received from the serial port.")
            time.sleep(0.1)  # slight delay to avoid spamming
