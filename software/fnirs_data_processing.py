import time
import numpy as np
from tabulate import tabulate
import nirsimple.preprocessing as nsp
import nirsimple.processing as nproc

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

'''
# --------------------------------------Example with dummy data generator--------------------------------------------

def dummy_packet_generator():
    """
    Dummy generator for 8x5 packets.

    Each packet is an 8x5 NumPy array of integers.
    Each row corresponds to a sensor group with the following format:
        [group_id, short, long1, long2, mode]
    Group IDs are 1-indexed. Two types of packets are generated:
        mode 1 (660 nm) and mode 2 (940 nm), alternating.

    This is the same data format expected from the upstream serial
    read function Ingrid is making.
    """
    NUM_GROUPS = 8
    base_short = 2400
    base_long1 = 2500
    base_long2 = 2600
    while True:
        # Mode 1 packet (660 nm)
        packet1 = np.zeros((NUM_GROUPS, 5), dtype=int)
        for i in range(NUM_GROUPS):
            sensor_group = i + 1
            short_val = base_short + int(np.random.randn() * 5)
            long1_val = base_long1 + int(np.random.randn() * 5)
            long2_val = base_long2 + int(np.random.randn() * 5)
            packet1[i] = [sensor_group, short_val, long1_val, long2_val, 1]
        yield packet1
        time.sleep(1)
        # Mode 2 packet (940 nm)
        packet2 = np.zeros((NUM_GROUPS, 5), dtype=int)
        for i in range(NUM_GROUPS):
            sensor_group = i + 1
            short_val = base_short + int(np.random.randn() * 5)
            long1_val = base_long1 + int(np.random.randn() * 5)
            long2_val = base_long2 + int(np.random.randn() * 5)
            packet2[i] = [sensor_group, short_val, long1_val, long2_val, 2]
        yield packet2
        time.sleep(1)

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
'''
