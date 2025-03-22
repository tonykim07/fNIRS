import eventlet
eventlet.monkey_patch()

import time
import numpy as np
from flask import Flask
from flask_socketio import SocketIO
from tabulate import tabulate
import nirsimple.preprocessing as nsp
import nirsimple.processing as nproc

# -------------------- DataProcessor Code --------------------
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
            self.channel_names.append(name)   # for 660 nm measurement
            self.ch_wls.append(660.0)
            self.channel_names.append(name)   # for 940 nm measurement
            self.ch_wls.append(940.0)

        self.ch_dpfs = [nsp.get_dpf(wl, self.AGE) for wl in self.ch_wls]
        self.ch_distances = [self.SD_DISTANCE] * len(self.ch_wls)
        self.unit = 'cm'

    def combine_packets(self, packet_660, packet_940):
        sample = np.zeros(48)
        for i in range(packet_660.shape[0]):
            group_id = packet_660[i, 0]
            index = np.where(packet_940[:, 0] == group_id)[0][0]
            row660 = packet_660[i, :]
            row940 = packet_940[index, :]
            base = (group_id - 1) * 6
            for j in range(3):
                sample[base + j * 2]     = row660[1 + j]
                sample[base + j * 2 + 1] = row940[1 + j]
        return sample

    def process_data_packet(self, packet):
        mode = packet[0, 4]
        if mode == 1:
            self.last_660_packet = packet
        elif mode == 2:
            self.last_940_packet = packet

        if self.last_660_packet is not None and self.last_940_packet is not None:
            sample = self.combine_packets(self.last_660_packet, self.last_940_packet)
            if not self.buffer_initialized:
                self.raw_buffer = np.tile(sample.reshape(-1, 1), (1, self.n_times_buffer))
                self.buffer_initialized = True
            else:
                self.raw_buffer = np.roll(self.raw_buffer, -1, axis=1)
                self.raw_buffer[:, -1] = sample

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
        else:
            return None

# -------------------- Dummy Packet Generator --------------------
def dummy_packet_generator():
    NUM_GROUPS = 8
    base_short = 2400
    base_long1 = 2500
    base_long2 = 2600
    while True:
        packet1 = np.zeros((NUM_GROUPS, 5), dtype=int)
        for i in range(NUM_GROUPS):
            sensor_group = i + 1
            short_val = base_short + int(np.random.randn() * 5)
            long1_val = base_long1 + int(np.random.randn() * 5)
            long2_val = base_long2 + int(np.random.randn() * 5)
            packet1[i] = [sensor_group, short_val, long1_val, long2_val, 1]
        yield packet1
        time.sleep(1)
        packet2 = np.zeros((NUM_GROUPS, 5), dtype=int)
        for i in range(NUM_GROUPS):
            sensor_group = i + 1
            short_val = base_short + int(np.random.randn() * 5)
            long1_val = base_long1 + int(np.random.randn() * 5)
            long2_val = base_long2 + int(np.random.randn() * 5)
            packet2[i] = [sensor_group, short_val, long1_val, long2_val, 2]
        yield packet2
        time.sleep(1)

# -------------------- Flask-SocketIO Server Setup --------------------
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

@app.route('/')
def index():
    return "<h2>Data Processor Server Running</h2>"

def data_processing_task():
    processor = DataProcessor()
    dummy_gen = dummy_packet_generator()
    while True:
        packet = next(dummy_gen)
        result = processor.process_data_packet(packet)
        if result is not None:
            concentrations, table_data = result
            # Emit the processed data to connected clients
            socketio.emit('processed_data', {
                'concentrations': concentrations,
                'table_data': table_data
            })
            # (Optional) Also log or print the table in the server console
            print("Latest Concentration Values (48 channels):")
            print(tabulate(table_data, headers=["Channel", "Type", "Concentration"]))
            print("-" * 80)
        eventlet.sleep(0.1)

if __name__ == '__main__':
    # Start the data processing in a background thread
    socketio.start_background_task(data_processing_task)
    socketio.run(app, debug=True, use_reloader=False, port=5000)
