import nirsimple.processing as nproc
import nirsimple.preprocessing as nsp
from tabulate import tabulate
from flask_socketio import SocketIO
from flask import Flask
import struct
import serial
import numpy as np
import time
import eventlet
eventlet.monkey_patch()


# -------------------- Flask-SocketIO Server Setup --------------------
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


@app.route('/')
def index():
    return "<h2>Data Processor Server Running</h2>"


# Set up serial connection (adjust the port and baud rate as necessary)
ser = serial.Serial('/dev/tty.usbmodem205D388A47311', 115200,
                    timeout=1)  # Replace with your actual port


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
        emitter_status = data[offset+7]

        parsed_data[i] = [
            packet_identifier,
            sensor_channel_1,
            sensor_channel_2,
            sensor_channel_3,
            emitter_status
        ]
    return parsed_data


def data_processing_task():
    sensor_sums = np.zeros((8, 3), dtype=int)
    sensor_counts = np.zeros(8, dtype=int)
    current_emitter = None
    processor = DataProcessor()

    while True:
        data = ser.read(64)
        if len(data) == 64:
            parsed_data = parse_packet(data)

            NOISE_ESTIMATE = 2050
            for i in range(8):
                for j in range(1, 4):
                    parsed_data[i, j] = 2 * NOISE_ESTIMATE - parsed_data[i, j]

            emitter = parsed_data[0, 4]
            if current_emitter is None:
                current_emitter = emitter

            if emitter == current_emitter:
                for i in range(8):
                    ch1, ch2, ch3 = parsed_data[i,
                                                1], parsed_data[i, 2], parsed_data[i, 3]
                    if 100 <= ch1 <= 3900 and 100 <= ch2 <= 3900 and 100 <= ch3 <= 3900:
                        sensor_sums[i] += [ch1, ch2, ch3]
                        sensor_counts[i] += 1
            else:
                # print(
                #     f"\nEmitter changed from {current_emitter} to {emitter}.")
                # print("Computing average for old emitter...")

                averaged_data = np.zeros((8, 5), dtype=int)
                for i in range(8):
                    group_id = i
                    count = max(sensor_counts[i], 1)
                    avg1 = sensor_sums[i, 0] // count
                    avg2 = sensor_sums[i, 1] // count
                    avg3 = sensor_sums[i, 2] // count
                    averaged_data[i] = [group_id, avg1,
                                        avg2, avg3, current_emitter]

                # print("\nAveraged Sensor Data (8×5 Array):")
                # print(averaged_data)
                # print(
                #     "\nEach row => [Group ID, Avg Short, Avg Long1, Avg Long2, Emitter]")
                # print("--------------------------------------------------")

                result = processor.process_data_packet(averaged_data)

                if result is not None:
                    concentrations, table_data = result
                    socketio.emit('processed_data', {
                        'concentrations': concentrations,
                        'table_data': table_data
                    })
                    # print("Latest Concentration Values (48 channels):")
                    # print(tabulate(table_data, headers=[
                    #       "Channel", "Type", "Concentration"]))
                    # print("-" * 500)
                    # print("Data Sent to GUI Graphing Function: ", concentrations)
                    # print("-" * 500)

                sensor_sums.fill(0)
                sensor_counts.fill(0)

                current_emitter = emitter
                for i in range(8):
                    ch1, ch2, ch3 = parsed_data[i,
                                                1], parsed_data[i, 2], parsed_data[i, 3]
                    sensor_sums[i] += [ch1, ch2, ch3]
                    sensor_counts[i] += 1
        else:
            print("No valid data received from the serial port.")
            time.sleep(0.1)


if __name__ == '__main__':
    # Start the data processing in a background thread
    socketio.start_background_task(data_processing_task)
    socketio.run(app, debug=True, use_reloader=False, port=5000)