import serial
import struct
import numpy as np
import time
from tabulate import tabulate
import nirsimple.preprocessing as nsp
import nirsimple.processing as nproc

# Set up serial connection (adjust the port and baud rate as necessary)
ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 115200, timeout=1)  # Replace with your actual port

class DataProcessor:
    def __init__(self, age=22, sd_distance=5.0, molar_ext_coeff_table='wray', n_times_buffer=50):
        self.AGE = age
        self.SD_DISTANCE = sd_distance
        self.MOLAR_EXT_COEFF_TABLE = molar_ext_coeff_table
        self.n_channels_total = 48
        self.n_times_buffer = n_times_buffer
        self.raw_buffer = np.zeros((self.n_channels_total, self.n_times_buffer))
        self.buffer_initialized = False
        self.last_660_packet = None
        self.last_940_packet = None

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

    def process_data_packet(self, packet):
        """
        Processes a new 8x5 data packet.

        The packet is an 8x5 NumPy array of integers in the form:
            [group_id, short, long1, long2, mode]
        where mode is expected to be uniform across the packet:
            mode = 1 for 660 nm,
            mode = 2 for 940 nm.

        The packet is stored until both modes are available. Then, it combines
        the packets into a 48-element sample, updates the rolling buffer, and
        processes the data using the OD conversion, MBLL, and CBSI correction.

        Returns a tuple:
          (concentration_values_list, table_data)
        where table_data is a list of [Channel, Type, Concentration] rows.
        If both mode packets are not yet available, it returns None.
        """
        # Determine the mode of the incoming packet
        mode = packet[0, 4]
        if mode == 1:
            self.last_660_packet = packet
        elif mode == 2:
            self.last_940_packet = packet

        if self.last_660_packet is not None and self.last_940_packet is not None:
            sample = self.combine_packets(self.last_660_packet, self.last_940_packet)
            # Prefill the buffer if it hasn't been initialized yet
            if not self.buffer_initialized:
                self.raw_buffer = np.tile(sample.reshape(-1, 1), (1, self.n_times_buffer))
                self.buffer_initialized = True
            else:
                # Update the rolling buffer: shift left and insert the new sample
                self.raw_buffer = np.roll(self.raw_buffer, -1, axis=1)
                self.raw_buffer[:, -1] = sample

            # Apply OD Conversion, MBLL, and CBSI correction
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
            # Table for showing channel mapping and type
            table_data = []
            for i, name in enumerate(corr_ch_names):
                table_data.append([name, corr_ch_types[i], f"{concentration_values[i]:.4e} M"])
            return concentration_values.tolist(), table_data
        else:
            return None

# --------------------------------------------------------------------------------
# 1) parse_packet: Convert 64 bytes into an 8x5 numpy array
# --------------------------------------------------------------------------------
def parse_packet(data):
    """Parses 64 raw bytes into an 8x5 array of sensor data:
       [Group ID, Short, Long1, Long2, Emitter Status]."""
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

# --------------------------------------------------------------------------------
# 2) Optional debug printing function
# --------------------------------------------------------------------------------
def print_sensor_data(parsed_data):
    """Displays the 8x5 sensor array nicely."""
    print("\n--------------------------------------------------")
    print("Formatted Sensor Data (8x5 Array):")
    print(parsed_data)
    print("\nEach row represents: [Group ID, Short, Long1, Long2, Mode]")

# --------------------------------------------------------------------------------
# 3) MAIN LOOP: Accumulate readings for the current emitter
#               Once the emitter changes, compute/print the average, then reset.
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    # A) Accumulation buffers
    sensor_sums = np.zeros((8, 3), dtype=int)  # Summation for Short, Long1, Long2
    sensor_counts = np.zeros(8, dtype=int)     # Count how many packets we've accumulated
    current_emitter = None                     # Track which emitter we are currently accumulating
    
    processor = DataProcessor()
    print("Starting emitter-based accumulation...\n")
    while True:
        data = ser.read(64)  # Expecting 64 bytes (8 sensor groups * 8 bytes)
        if len(data) == 64:
            # Parse the packet into an 8x5 array
            parsed_data = parse_packet(data)
            # (Optional) print_sensor_data(parsed_data)

            # The emitter status for this packet (we assume all rows have the same)
            emitter = parsed_data[0, 4]

            # If we haven't set an emitter yet, this is our first cycle
            if current_emitter is None:
                current_emitter = emitter

            # If the emitter is the same, keep accumulating
            if emitter == current_emitter:
                for i in range(8):
                    sensor_sums[i] += parsed_data[i, 1:4]  # Accumulate [Short, Long1, Long2]
                    sensor_counts[i] += 1
            else:
                # Emitter changed!
                print(f"\nEmitter changed from {current_emitter} to {emitter}.")
                print("Computing average for old emitter...")

                # B) Compute average for the old emitter
                averaged_data = np.zeros((8, 5), dtype=int)
                for i in range(8):
                    # Use the final group_id from the last packet 
                    # or just i if group_id doesn't matter
                    group_id = i  # or store from the old parse if needed
                    count = max(sensor_counts[i], 1)
                    avg1  = sensor_sums[i, 0] // count
                    avg2  = sensor_sums[i, 1] // count
                    avg3  = sensor_sums[i, 2] // count
                    averaged_data[i] = [group_id, avg1, avg2, avg3, current_emitter]

                # C) Print or send the averaged data
                print("\nAveraged Sensor Data (8x5 Array):")
                print(averaged_data)
                print("\nEach row represents: [Group ID, Avg Short, Avg Long1, Avg Long2, Emitter]")
                print("--------------------------------------------------")

                # C-Proc) Data Processing
                result = processor.process_data_packet(averaged_data)
                if result is not None:
                    concentrations, table_data = result
                    print("Latest Concentration Values (48 channels):")
                    print(tabulate(table_data, headers=["Channel", "Type", "Concentration"]))
                    print("-" * 500)
                    print("Data Sent to GUI Graphing Function: ", concentrations)
                    print("-" * 500)
                    
                # D) Reset sums and counts
                sensor_sums.fill(0)
                sensor_counts.fill(0)

                # E) Start accumulating for the new emitter
                current_emitter = emitter
                for i in range(8):
                    sensor_sums[i] += parsed_data[i, 1:4]
                    sensor_counts[i] += 1
        else:
            print("No valid data received from the serial port.")
            time.sleep(0.1)  # Slight delay to avoid spamming

