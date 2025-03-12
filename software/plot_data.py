import serial
import struct
import matplotlib.pyplot as plt

# Set up serial connection (adjust the port and baud rate as necessary)
ser = serial.Serial('/dev/tty.usbmodem205D388A47311', 115200, timeout=1)  # Replace with your port

# Function to parse the packet data based on the specified structure
def parse_packet(data):
    print(f"Received Data: {data.hex()}")  # Print raw hex data for debugging
    parsed_data = []
    for i in range(0, len(data), 8):  # Assuming each sensor module is 8 bytes
        packet = data[i:i+8]
        
        # Extract packet identifier
        packet_identifier = packet[0]
        
        # Extract sensor channel values (all three channels for each module)
        sensor_channel_1 = struct.unpack('>H', packet[1:3])[0]  # Big-endian unsigned short
        sensor_channel_2 = struct.unpack('>H', packet[3:5])[0]
        sensor_channel_3 = struct.unpack('>H', packet[5:7])[0]
        
        # Extract emitter status
        emitter_status = packet[7]
        
        # Store parsed values in a dictionary for each sensor module
        sensor_module_data = {
            'packet_identifier': packet_identifier,
            'sensor_channel_1': sensor_channel_1,
            'sensor_channel_2': sensor_channel_2,
            'sensor_channel_3': sensor_channel_3,
            'emitter_status': emitter_status
        }
        parsed_data.append(sensor_module_data)
    return parsed_data

# Function to plot data for each sensor channel in real-time
def plot_sensor_data_real_time(sensor_data):
    # Create a figure for real-time plotting
    plt.ion()  # Turn on interactive mode
    fig, ax = plt.subplots(figsize=(10, 6))
    
    while True:
        for i, module_data in enumerate(sensor_data):  # Loop through the parsed data for each sensor module
            # Clear previous plot data
            ax.clear()
            
            # Plot Sensor Channel 1
            ax.plot([module_data['sensor_channel_1'] for module_data in sensor_data], label="Sensor Channel 1")
            ax.set_title(f'Sensor Module {i+1} - Sensor Channel 1')
            ax.set_xlabel('Time')
            ax.set_ylabel('Sensor Value')
            ax.grid(True)

            # Plot Sensor Channel 2
            ax.plot([module_data['sensor_channel_2'] for module_data in sensor_data], label="Sensor Channel 2")
            ax.set_title(f'Sensor Module {i+1} - Sensor Channel 2')
            ax.set_xlabel('Time')
            ax.set_ylabel('Sensor Value')
            ax.grid(True)

            # Plot Sensor Channel 3
            ax.plot([module_data['sensor_channel_3'] for module_data in sensor_data], label="Sensor Channel 3")
            ax.set_title(f'Sensor Module {i+1} - Sensor Channel 3')
            ax.set_xlabel('Time')
            ax.set_ylabel('Sensor Value')
            ax.grid(True)

            # Refresh the plot
            plt.legend()
            plt.draw()
            plt.pause(0.1)  # Pause for a short time to update the plot

        plt.ioff()  # Turn off interactive mode

# Read data from serial port
def read_data_from_serial():
    while True:
        data = ser.read(64)  # Adjust the packet size if necessary (64 bytes for 8 modules)
        if len(data) > 0:
            parsed_data = parse_packet(data)
            plot_sensor_data_real_time(parsed_data)
        else:
            print("No data received from the serial port.")

# Start reading and plotting the data in real-time
read_data_from_serial()
