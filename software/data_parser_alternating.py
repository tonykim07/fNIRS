import serial
import struct
import time

# Set up serial connection
ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 115200, timeout=1)  # Adjust your port

NUM_SENSOR_GROUPS = 8  # 8 sensor groups
NUM_SAMPLES = 10  # Average over 10 samples per emitter status

# Data storage: Separate buffers for emitter 1 and emitter 2
samples = {
    1: {i: {j: [] for j in range(1, 4)} for i in range(1, NUM_SENSOR_GROUPS + 1)},  # Emitter 1
    2: {i: {j: [] for j in range(1, 4)} for i in range(1, NUM_SENSOR_GROUPS + 1)},  # Emitter 2
}

# Store packet identifiers separately for each emitter status
packet_identifiers = {1: {i: None for i in range(1, NUM_SENSOR_GROUPS + 1)},
                      2: {i: None for i in range(1, NUM_SENSOR_GROUPS + 1)}}

# Store last known emitter statuses
emitter_statuses = {i: None for i in range(1, NUM_SENSOR_GROUPS + 1)}

def parse_packet(data):
    """ Parses raw serial data into structured sensor readings. """
    parsed_data = []
    for i in range(0, len(data), 8):  # Each sensor module packet is 8 bytes
        if i + 8 <= len(data):
            packet = data[i:i+8]

            # Extract packet identifier
            packet_identifier = packet[0]

            # Extract sensor channel values (big-endian format)
            sensor_channel_1 = struct.unpack('>H', packet[1:3])[0]
            sensor_channel_2 = struct.unpack('>H', packet[3:5])[0]
            sensor_channel_3 = struct.unpack('>H', packet[5:7])[0]

            # Extract emitter status from the packet (last byte)
            emitter_status = packet[7]

            # Store parsed values
            sensor_module_data = {
                'packet_identifier': packet_identifier,
                'sensor_channel_1': sensor_channel_1,
                'sensor_channel_2': sensor_channel_2,
                'sensor_channel_3': sensor_channel_3,
                'emitter_status': emitter_status
            }
            parsed_data.append(sensor_module_data)
    return parsed_data

def store_sensor_data(sensor_group, module_data):
    """ Stores rolling buffer of last 10 samples per emitter status. """
    global samples, packet_identifiers, emitter_statuses

    # Get the emitter status from the received data
    emitter_status = module_data['emitter_status']

    if emitter_status not in [1, 2]:  # Ensure it's a valid emitter status
        return  

    # Extract channel values
    channel_values = [
        module_data['sensor_channel_1'],
        module_data['sensor_channel_2'],
        module_data['sensor_channel_3']
    ]

    for channel in range(1, 4):
        samples[emitter_status][sensor_group][channel].append(channel_values[channel - 1])  # Add new value

        # Keep only the last 10 samples for this emitter status
        if len(samples[emitter_status][sensor_group][channel]) > NUM_SAMPLES:
            samples[emitter_status][sensor_group][channel] = samples[emitter_status][sensor_group][channel][-NUM_SAMPLES:]

    # Store the most recent packet identifier and emitter status for this group
    packet_identifiers[emitter_status][sensor_group] = module_data['packet_identifier']
    emitter_statuses[sensor_group] = emitter_status  # Store last known emitter status

def calculate_averages(emitter_status):
    """ Computes the average of the last 10 samples for each channel per emitter status. """
    averages = {i: {'packet_id': None, 'ch1': 0, 'ch2': 0, 'ch3': 0, 'emitter_status': emitter_status} 
                for i in range(1, NUM_SENSOR_GROUPS + 1)}

    # Ensure each sensor group has 10 samples before averaging
    if all(len(samples[emitter_status][group][1]) == NUM_SAMPLES for group in range(1, NUM_SENSOR_GROUPS + 1)):
        for group in range(1, NUM_SENSOR_GROUPS + 1):
            averages[group]['packet_id'] = packet_identifiers[emitter_status][group]
            averages[group]['ch1'] = sum(samples[emitter_status][group][1]) // NUM_SAMPLES  # Integer division
            averages[group]['ch2'] = sum(samples[emitter_status][group][2]) // NUM_SAMPLES
            averages[group]['ch3'] = sum(samples[emitter_status][group][3]) // NUM_SAMPLES
        return averages
    else:
        return None  # Not enough samples yet

def display_averages(averages):
    """ Displays only the averaged values after 10 samples, with packet ID and emitter status. """
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n[{timestamp}] AVERAGED SENSOR DATA (LAST 10 SAMPLES for Emitter {averages[1]['emitter_status']})")
    print("=" * 100)

    for group in range(1, NUM_SENSOR_GROUPS + 1):
        print(f"\n--------------------------------------------------")
        print(f"Sensor Group {group} - Packet Identifier: {averages[group]['packet_id']}")
        print(f"  Channel 1: {averages[group]['ch1']}, Channel 2: {averages[group]['ch2']}, Channel 3: {averages[group]['ch3']}")
        print(f"  Emitter Status: {averages[group]['emitter_status']}")

def main():
    """ Continuously reads, averages, and prints sensor data after 10 samples per emitter status. """
    print("Starting sensor averaging...")
    try:
        while True:
            data = ser.read(64)  # Read up to 64 bytes
            if len(data) > 0:
                parsed_data = parse_packet(data)

                # Store data for each sensor group
                for i, module_data in enumerate(parsed_data):
                    if i >= NUM_SENSOR_GROUPS:  # Limit to 8 sensor groups
                        break

                    sensor_group = i + 1
                    store_sensor_data(sensor_group, module_data)

                # Get the last known emitter status
                last_known_emitter = next((v for v in emitter_statuses.values() if v in [1, 2]), None)

                # Compute and print averages only after 10 samples for the current emitter
                if last_known_emitter:
                    averages = calculate_averages(last_known_emitter)
                    if averages:
                        display_averages(averages)
                
                time.sleep(0.5)  # Small delay to prevent excessive looping

    except KeyboardInterrupt:
        print("Program terminated by user.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == "__main__":
    main()
