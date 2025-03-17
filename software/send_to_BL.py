import serial
import struct
import numpy as np
import time
from tabulate import tabulate
import nirsimple.preprocessing as nsp
import nirsimple.processing as nproc

# Set up serial connection (adjust the port and baud rate as necessary)
ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 115200, timeout=1)  # Replace with your actual port

# Initialize storage for averaging
sensor_sums = np.zeros((8, 3), dtype=int)  # Sum for each sensor group (3 channels)
sensor_counts = np.zeros(8, dtype=int)  # Count of readings per group
previous_emitter_status = np.full(8, -1, dtype=int)  # Store previous emitter statuses
latest_emitter_status = -1  # Track the latest emitter status to detect changes

# --------------------------------------Beer Lambert Law processing-------------------------------------------- #

class DataProcessor:
    def __init__(self, age=22, sd_distance=5.0, molar_ext_coeff_table='wray', n_times_buffer=50):
        self.AGE = age
        self.SD_DISTANCE = sd_distance
        self.MOLAR_EXT_COEFF_TABLE = molar_ext_coeff_table
        self.n_channels_total = 48
        self.n_times_buffer = n_times_buffer
        self.raw_buffer = np.zeros((self.n_channels_total, self.n_times_buffer))
        self.buffer_initialized = False

        # Build channel names for NIRSimple
        physical_channels = []
        for set_idx in range(1, 9):
            for det in range(1, 4):
                physical_channels.append(f"S{set_idx}_D{det}")
        self.channel_names = []
        self.ch_wls = []
        for name in physical_channels:
            self.channel_names.append(name)
            self.ch_wls.append(660.0)
            self.channel_names.append(name)
            self.ch_wls.append(940.0)

        self.ch_dpfs = [nsp.get_dpf(wl, self.AGE) for wl in self.ch_wls]
        self.ch_distances = [self.SD_DISTANCE] * len(self.ch_wls)
        self.unit = 'cm'

    def combine_packets(self, packet_660, packet_940):
        """
        Combines two 8x5 packets (one for mode 1 and one for mode 2)
        into a single sample of 48 values.
        For each sensor group (group_id from 1 to 8), the six output values are:
            [short_660, short_940, long1_660, long1_940, long2_660, long2_940]
        """
        sample = np.zeros(48)
        # Loop through each sensor group in the 660 packet
        for i in range(packet_660.shape[0]):
            group_id = packet_660[i, 0]
            # Find the matching row in the 940 packet
            index = np.where(packet_940[:, 0] == group_id)[0][0]
            row660 = packet_660[i, :]
            row940 = packet_940[index, :]
            base = (group_id - 1) * 6
            for j in range(3):
                sample[base + j * 2]     = row660[1 + j]
                sample[base + j * 2 + 1] = row940[1 + j]
        return sample

    def process_data_packets(self, packet_660, packet_940):
        """
        Processes a new pair of 8x5 data packets.
        
        Each packet is an 8x5 NumPy array of integers with rows formatted as:
          [group_id, short, long1, long2, mode]
        where mode = 1 for 660 nm and mode = 2 for 940 nm.
        
        This function combines the two packets into a 48-element sample,
        updates the rolling buffer, and processes the data using the OD conversion,
        MBLL, and CBSI correction.
        
        Returns a tuple:
          (concentration_values_list, table_data)
        where table_data is a list of rows [Channel, Type, Concentration].
        """
        sample = self.combine_packets(packet_660, packet_940)
        if not self.buffer_initialized:
            self.raw_buffer = np.tile(sample.reshape(-1, 1), (1, self.n_times_buffer))
            self.buffer_initialized = True
        else:
            self.raw_buffer = np.roll(self.raw_buffer, -1, axis=1)
            self.raw_buffer[:, -1] = sample

        # Apply OD conversion, MBLL, and CBSI correction.
        delta_od = nsp.intensities_to_od_changes(self.raw_buffer)
        delta_c, new_ch_names, new_ch_types = nsp.mbll(
            delta_od,
            self.channel_names,
            self.ch_wls,
            self.ch_dpfs,
            self.ch_distances,
            self.unit,
            table=self.MOLAR_EXT_COEFF_TABLE
        )
        delta_c_corr, corr_ch_names, corr_ch_types = nproc.cbsi(delta_c, new_ch_names, new_ch_types)
        concentration_values = delta_c_corr[:, -1]
        table_data = []
        for i, name in enumerate(corr_ch_names):
            table_data.append([name, corr_ch_types[i], f"{concentration_values[i]:.4e} M"])
        return concentration_values.tolist(), table_data


# --------------------------------------Beer Lambert Law processing-------------------------------------------- #


# Function to parse the packet data into an 8x5 NumPy array
def parse_packet(data):
    global sensor_sums, sensor_counts, previous_emitter_status, latest_emitter_status
    
    parsed_data = np.zeros((8, 5), dtype=int)  # Initialize an 8x5 array
    
    for i in range(8):  # Loop through the 8 sensor groups
        offset = i * 8  # Each group occupies 8 bytes
        packet_identifier = data[offset]
        sensor_channel_1 = struct.unpack('>H', data[offset+1:offset+3])[0]
        sensor_channel_2 = struct.unpack('>H', data[offset+3:offset+5])[0]
        sensor_channel_3 = struct.unpack('>H', data[offset+5:offset+7])[0]
        emitter_status = data[offset+7]
        
        # Store the latest emitter status (assuming all rows have the same status)
        if i == 0:
            latest_emitter_status = emitter_status
        
        # Accumulate sums and counts
        sensor_sums[i] += np.array([sensor_channel_1, sensor_channel_2, sensor_channel_3])
        sensor_counts[i] += 1
        
        # Store parsed values in the NumPy array
        parsed_data[i] = [packet_identifier, sensor_channel_1, sensor_channel_2, sensor_channel_3, emitter_status]
    
    return parsed_data  # Return 8x5 structured data

# Function to compute averages and reset on emitter status change
def compute_and_reset_averages():
    global sensor_sums, sensor_counts, previous_emitter_status
    
    averaged_data = np.zeros((8, 5), dtype=int)
    for i in range(8):
        avg_sensor_values = sensor_sums[i] // max(sensor_counts[i], 1)  # Avoid division by zero
        averaged_data[i] = [i, avg_sensor_values[0], avg_sensor_values[1], avg_sensor_values[2], previous_emitter_status[i]]
    
    # Reset sums and counts after sending
    sensor_sums.fill(0)
    sensor_counts.fill(0)
    
    return averaged_data

# Function to read data from the serial port and return the parsed array
def read_data_from_serial():
    """ Reads 64 bytes from serial and returns the parsed 8x5 array. """
    data = ser.read(64)  # Expecting 64 bytes (8 sensor groups * 8 bytes per group)
    if len(data) == 64:
        return parse_packet(data)  # Return parsed data
    else:
        print("⚠️ No valid data received from the serial port.")
        return None  # Return None if data is invalid
    

if __name__ == '__main__':
    processor = DataProcessor()
    dummy_gen = dummy_packet_generator()
    print("Starting processing.\n")
    try:
        while True:
            packet = next(dummy_gen)
            result = processor.process_data_packet(packet)
            if result is not None:
                concentrations, table_data = result
                print("Latest Concentration Values (48 channels):")
                print(tabulate(table_data, headers=["Channel", "Type", "Concentration"]))
                print("-" * 500)
                print("Data Sent to GUI Graphing Function: ", concentrations)
                print("-" * 500)
    except KeyboardInterrupt:
        print("Stopping processing.")

# Main loop to continuously read and display sensor data
if __name__ == "__main__":
    processor = DataProcessor()
    while True:
        packet = read_data_from_serial()
        result = processor.process_data_packet(packet)
        if packet is not None:
            # Check if emitter status changed
            if latest_emitter_status != previous_emitter_status[0]:
                # Compute and send averaged data
                averaged_data = compute_and_reset_averages()

                # print("\nAveraged Sensor Data (8x5 Array):")
                # print(averaged_data)
                # print("\nEach row represents: [Group ID, Avg Short, Avg Long1, Avg Long2, Mode]")

                result = processor.process_data_packet(averaged_data)

                concentrations, table_data = result
                print("Latest Concentration Values (48 channels):")
                print(tabulate(table_data, headers=["Channel", "Type", "Concentration"]))
                print("-" * 500)
                print("Data Sent to GUI Graphing Function: ", concentrations)
                print("-" * 500)
                
                # Update previous emitter status
                previous_emitter_status.fill(latest_emitter_status)