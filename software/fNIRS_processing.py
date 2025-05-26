"""
fNIRS_processing.py
==================
This script captures raw ADC data from a serial port, processes it, and
outputs the results to a CSV file. It includes functions for parsing packets,
capturing data, interleaving mode blocks, and applying the Modified 
Beer-Lambert Law on the dataset to compute hemoglobin concentration changes.
"""

import csv
import time
import signal
import struct
import numpy as np
from tabulate import tabulate
import nirsimple.preprocessing as nsp
import nirsimple.processing as nproc
import pandas as pd
import serial
from config import SERIAL_PORT, BAUD_RATE, TIMEOUT
from scipy.signal import butter, sosfiltfilt, resample_poly, filtfilt

ser = serial.Serial(SERIAL_PORT, baudrate=BAUD_RATE, timeout=TIMEOUT)

STOP_FLAG = False  # Global flag for stopping the capture loop

def handle_stop_signal():
    """
    Signal handler for SIGUSR1 to set the STOP_FLAG.
    This allows the capture loop to stop gracefully.
    """
    global STOP_FLAG
    print("Received stop signal, setting stop_flag to True.")
    STOP_FLAG = True

# Register the handler for SIGUSR1
signal.signal(signal.SIGUSR1, handle_stop_signal)

def revert_inversion(df_in, zero_level=2050, out_csv="all_groups_no_inv.csv"):
    """
    Re-maps the Short/Long columns back to raw ADC counts and
    saves the result to `out_csv`.
    """
    df = df_in.copy()
    reading_cols = [c for c in df.columns if ("Short" in c or "Long" in c)]
    df[reading_cols] = 2 * zero_level - df[reading_cols]
    df.to_csv(out_csv, index=False)
    print(f"✓ Wrote non-inverted data → {out_csv}")
    return df

def threshold_filter(df, lower_threshold=200, upper_threshold=4000, zero_level=2050, exclude_columns=None):
    """Suppress outliers of a data frame."""
    if exclude_columns is None:
        exclude_columns = []

    suppressed_df = df.copy()

    for col in df.columns:
        if col not in exclude_columns:
            suppressed_df[col] = np.where(
                (df[col] < lower_threshold) | (df[col] > upper_threshold),
                zero_level,
                df[col]
            )

    return suppressed_df

def butter_lowpass_filter(df, cutoff_hz, fs, order=4, exclude_columns=None):
    """Apply a low-pass Butterworth filter to selected columns of a data frame."""
    if exclude_columns is None:
        exclude_columns = []

    filtered_df = df.copy()
    nyquist = 0.5 * fs
    normal_cutoff = cutoff_hz / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)

    for col in df.columns:
        if col not in exclude_columns:
            filtered_df[col] = filtfilt(b, a, df[col])

    return filtered_df

def sliding_window_rms(df, emitter_col="G0_Emitter", group_prefix="G", num_groups=8,
                         remove_dc=False, split_segments_in_half=False):
    """
    Apply RMS calculation to segments defined by the 
    emitter transitions 
    """
    df_rms = df.copy()

    emitter_reference = df[emitter_col].values
    change_points = np.where(np.diff(emitter_reference) != 0)[0] + 1
    segments = np.split(np.arange(len(df)), change_points)

    if split_segments_in_half:
        split_segments = []
        for segment in segments:
            n = len(segment)
            if n == 0:
                continue
            mid = n // 2
            split_segments.append(segment[:mid])
            split_segments.append(segment[mid:])
        segments = split_segments

    groups = [f"{group_prefix}{i}" for i in range(num_groups)]

    for g in groups:
        short_col = f"{g}_Short"
        long1_col = f"{g}_Long1"
        long2_col = f"{g}_Long2"

        for segment in segments:
            if len(segment) == 0:
                continue
            segment_idx = segment.tolist()

            for col in [short_col, long1_col, long2_col]:
                segment_data = df.loc[segment_idx, col]
                if remove_dc:
                    segment_data = segment_data - segment_data.mean()
                rms_val = np.sqrt(np.mean(np.square(segment_data)))
                df_rms.loc[segment_idx, col] = rms_val

    return df_rms


def butter_bandpass_sos(lowcut, highcut, fs, order=4):
    """Return an SOS band-pass filter."""
    nyq = 0.5 * fs
    sos = butter(order, [lowcut / nyq, highcut / nyq],
                 btype="band", output="sos")
    return sos

def smart_bandpass(data, fs,
                   lowcut=0.05, highcut=0.1, order=4,
                   target_fs=20.0):
    """
    Zero-phase band-pass along *time* axis.
    `data` shape: (n_channels, n_timepoints)
    """
    # Down-sample
    if fs > target_fs + 1: # leave a little margin
        decim = int(round(fs / target_fs))
        fs_ds = fs / decim
        data_ds = resample_poly(data, up=1, down=decim, axis=1)
    else:
        decim, fs_ds, data_ds = 1, fs, data
    # Design stable filter
    sos = butter_bandpass_sos(lowcut, highcut, fs_ds, order)
    # Zero-phase filtering
    data_bp = sosfiltfilt(sos, data_ds, axis=1, padtype="odd",
                          padlen=3 * (order + 1))
    # Up-sample back if we had decimated
    if decim > 1:
        data_bp = resample_poly(data_bp, up=decim, down=1, axis=1)
    return data_bp

def parse_packet(data):
    """ 
    Parses 64 raw bytes into an 8×5 array of sensor data:
       [Group ID, Short, Long1, Long2, Emitter Status].
    """
    ZERO_LEVEL = 2050
    parsed_data = np.zeros((8, 5), dtype=int)
    for i in range(8):
        offset = i * 8
        packet_identifier = data[offset]
        sensor_channel_1 = struct.unpack('>H', data[offset+1:offset+3])[0]
        sensor_channel_inv1 = 2 * ZERO_LEVEL - sensor_channel_1
        sensor_channel_2 = struct.unpack('>H', data[offset+3:offset+5])[0]
        sensor_channel_inv2 = 2 * ZERO_LEVEL - sensor_channel_2
        sensor_channel_3 = struct.unpack('>H', data[offset+5:offset+7])[0]
        sensor_channel_inv3 = 2 * ZERO_LEVEL - sensor_channel_3
        emitter_status    = data[offset+7]

        parsed_data[i] = [
            packet_identifier,
            sensor_channel_inv1,
            sensor_channel_inv2,
            sensor_channel_inv3,
            emitter_status
        ]
    return parsed_data

def capture_data(csv_filename, stop_on_enter=True):
    """
    Captures ADC data and writes it to a CSV file.
    
    Parameters:
      csv_filename (str): Name of the CSV file to write the data.
      stop_on_enter (bool): If True, the loop will check for the Enter key to stop logging.
      external_stop_flag: An object (e.g., threading.Event) with an is_set() method.
                          If provided and external_stop_flag.is_set() returns True,
                          the capture loop will stop.
    """
    global STOP_FLAG
    STOP_FLAG = False  # Reset the flag at the start

    with open(csv_filename, mode='w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        header = ["Time (s)"]
        for i in range(8):
            header += [f"G{i}_Short", f"G{i}_Long1", f"G{i}_Long2", f"G{i}_Emitter"]
        writer.writerow(header)

        print("Starting raw ADC logging (seconds elapsed)...")
        if stop_on_enter:
            print("Press Enter to stop logging and proceed to CSV processing.")

        start_time = time.time()

        try:
            while True:
                if STOP_FLAG:
                    print("Stop flag detected. Stopping capture...")
                    break
                data = ser.read(64)
                if len(data) == 64:
                    parsed_data = parse_packet(data)
                    elapsed_time = round(time.time() - start_time, 3)
                    flat_row = [elapsed_time]
                    for i in range(8):
                        flat_row += parsed_data[i][1:5].tolist()
                    writer.writerow(flat_row)
                    csvfile.flush()
                    print(f"{elapsed_time}s - Logged frame to CSV.")
                else:
                    print("No valid data received from the serial port.")
                    time.sleep(0.1)
        except Exception as e:
            print("An error occurred during logging:", str(e))


def interleave_mode_blocks(df, mode_col="G0_Emitter"):
    """
    Interleaves blocks of data based on the mode column.
    The function assumes that the DataFrame has a column named mode_col
    that indicates the mode (1 or 2) for each row.
    It creates a new DataFrame where each block of mode 1 rows is interleaved
    with the following block of mode 2 rows.
    """
    # Create groups based on changes in the mode column
    df["group"] = (df[mode_col] != df[mode_col].shift()).cumsum()

    # Collect each group into a list of DataFrames
    blocks = []
    for _, block_df in df.groupby("group"):
        block_df = block_df.drop(columns="group")
        blocks.append(block_df)

    all_rows = []
    i = 0
    # Process blocks in pairs; discard any leftover block if it exists.
    while i < len(blocks) - 1:
        block1 = blocks[i].reset_index(drop=True)
        block2 = blocks[i + 1].reset_index(drop=True)

        n1, n2 = len(block1), len(block2)
        max_len = max(n1, n2)

        for j in range(max_len):
            # Get row from block1; if out of range, repeat the last row
            row1 = block1.loc[j] if j < n1 else block1.loc[n1 - 1]
            # Get row from block2; if out of range, repeat the last row
            row2 = block2.loc[j] if j < n2 else block2.loc[n2 - 1]

            all_rows.append(row1.copy())
            all_rows.append(row2.copy())

        i += 2

    final_df = pd.DataFrame(all_rows)
    if "group" in final_df.columns:
        final_df.drop(columns="group", inplace=True)
    return final_df

def build_channel_info(age, sd_short, sd_long):
    """
    Builds channel names, wavelengths, DPFs, and source-detector distances.
    There are 24 physical channels (8 sensor groups × 3 detectors), and each is
    measured at two wavelengths (660 nm and 940 nm), yielding 48 channels.
    """
    physical_channels = [f"S{s}_D{d}"
                         for s in range(1, 9)      # sets 1–8
                         for d in (1, 2, 3)]       # detectors 1-3
    channel_names, ch_wls, ch_dpfs, ch_distances = [], [], [], []
    for name in physical_channels:
        det_num = int(name.split("_D")[1])
        dist    = sd_short if det_num == 1 else sd_long
        # 660nm
        channel_names.append(name)
        ch_wls.append(660.0)
        ch_dpfs.append(nsp.get_dpf(660.0, age))
        ch_distances.append(dist)
        # 940nm
        channel_names.append(name)
        ch_wls.append(940.0)
        ch_dpfs.append(nsp.get_dpf(940.0, age))
        ch_distances.append(dist)
    return channel_names, ch_wls, ch_dpfs, ch_distances

def combine_two_rows(row_mode1, row_mode2):
    """
    Combines two rows (one for mode=1 and the next for mode=2) from the CSV
    into a 48-element sample.

    Each row is assumed to have the following structure:
      [Time, G0_Short, G0_Long1, G0_Long2, G0_Emitter,
             G1_Short, G1_Long1, G1_Long2, G1_Emitter, ...,
             G7_Short, G7_Long1, G7_Long2, G7_Emitter]

    For each sensor group (0 through 7), we extract the three measurements from
    the mode=1 row (assumed to be 660 nm) and the three from the mode=2 row (assumed to be 940 nm),
    then interleave them to form a 48-element vector:
      [short_660, short_940, long1_660, long1_940, long2_660, long2_940] for each group.
    """
    sample = np.zeros(48, dtype=float)
    # There are 8 groups; each group occupies 4 columns (excluding the time)
    for g in range(8):
        # For mode 1 row (660 nm):
        short_660 = float(row_mode1[1 + 4*g])
        long1_660 = float(row_mode1[2 + 4*g])
        long2_660 = float(row_mode1[3 + 4*g])
        # For mode 2 row (940 nm):
        short_940 = float(row_mode2[1 + 4*g])
        long1_940 = float(row_mode2[2 + 4*g])
        long2_940 = float(row_mode2[3 + 4*g])
        base = g * 6
        sample[base + 0] = short_660
        sample[base + 1] = short_940
        sample[base + 2] = long1_660
        sample[base + 3] = long1_940
        sample[base + 4] = long2_660
        sample[base + 5] = long2_940
    return sample

def process_csv_dataset(
    input_csv,
    output_csv,
    age=22,
    sd_short=0.6,
    sd_long=3.5,
    molar_ext_coeff_table='wray',
    bp_low=0.05,
    bp_high=0.1,
    bp_order=4
):
    """
    Processes an fNIRS CSV dataset for post-processing.

    The CSV is expected to have a header and then rows with columns:
      Time, G0_Short, G0_Long1, G0_Long2, G0_Emitter, 
      G1_Short, G1_Long1, G1_Long2, G1_Emitter, ..., 
      G7_Short, G7_Long1, G7_Long2, G7_Emitter.

    Rows alternate between mode 1 (660 nm) and mode 2 (940 nm). The function
    pairs each mode 1 row with the following mode 2 row, applies the OD conversion,
    MBLL, and CBSI processing to compute hemoglobin concentration changes.

    The output CSV will have columns:
      Time, [for each processed channel: "{ChannelName}_{Type}"],
    where Type is either "hbo" or "hbr".
    """
    # Load CSV data (skip header)
    with open(input_csv, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        data_lines = list(reader)

    # Convert rows to float arrays
    data_matrix = np.array([[float(x) for x in line] for line in data_lines if len(line) >= 33])
    num_rows = data_matrix.shape[0]
    if num_rows < 2:
        print("Insufficient data rows for processing.")
        return

    # Pair rows: assume row0 is mode1, row1 is mode2, row2 is mode1, etc.
    samples = []
    times = []
    i = 0
    while i < num_rows - 1:
        row_mode1 = data_matrix[i, :]
        row_mode2 = data_matrix[i+1, :]
        t_val = row_mode1[0]  # use the timestamp from the mode1 row
        sample = combine_two_rows(row_mode1, row_mode2)
        samples.append(sample)
        times.append(t_val)
        i += 2

    samples = np.array(samples).T  # shape: (48, N)

    # Build channel information from established models
    channel_names, ch_wls, ch_dpfs, ch_distances = build_channel_info(age, sd_short, sd_long)

    # Apply OD conversion to the entire dataset
    delta_od = nsp.intensities_to_od_changes(samples)

    # Band-pass filtering the OD changes
    # High-pass ≥ 0.1 Hz to drop drifts; low-pass ≤ 0.05 Hz to drop pulse & noise.
    dt  = np.mean(np.diff(times))
    fs  = 1.0 / dt
    delta_od_filt = smart_bandpass(delta_od, fs, lowcut=bp_low, highcut=bp_high, order=bp_order)

    # Apply MBLL to compute concentration changes
    delta_c, new_ch_names, new_ch_types = nsp.mbll(
        delta_od_filt,
        channel_names,
        ch_wls,
        ch_dpfs,
        ch_distances,
        unit='cm',
        table=molar_ext_coeff_table
    )
    # Apply CBSI for signal improvement
    delta_c_corr, corr_ch_names, corr_ch_types = nproc.cbsi(delta_c, new_ch_names, new_ch_types)
    # delta_c_corr is of shape (48, N)

    # Create header labels for output CSV using processed channel names and types
    processed_headers = [f"{name}_{ctype}" for name, ctype in zip(corr_ch_names, corr_ch_types)]
    header_out = ["Time"] + processed_headers

    # Write output CSV with one row per time sample
    with open(output_csv, "w", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header_out)
        n_cols = min(len(times), delta_c_corr.shape[1])
        for col_idx in range(n_cols):
            time_val = times[col_idx]
            row_values = [time_val] + list(delta_c_corr[:, col_idx])
            writer.writerow(row_values)

    print(f"Post-processing complete. Output saved to '{output_csv}'.")

    # Print a table for the last time sample for verification
    last_sample = delta_c_corr[:, -1]
    table_data = []
    for i, ch in enumerate(corr_ch_names):
        table_data.append([ch, corr_ch_types[i], f"{last_sample[i]:.4e}"])
    print("\nExample: Processed concentrations at the final time sample:")
    print(tabulate(table_data, headers=["Channel", "Type", "Concentration"]))


# ------------------ Main ------------------
if __name__ == '__main__':

    # Capture Data
    STOP_FLAG=None # set to 1 from GUI to stop processing
    capture_data("all_groups.csv", stop_on_enter=True)

    # Read CSV file
    df = pd.read_csv("all_groups.csv")

    # Revert inversion (if needed)
    #df = revert_inversion(df)

    # Extract sampling rate from data
    time = df['Time (s)']
    dt = time.diff().mean()
    fs = 1.0 / dt

    # Data formating and Processing
    # 1) Completely ignore the original timestamp by dropping it if it exists.
    if "Time (s)" in df.columns:
        df.drop(columns=["Time (s)"], inplace=True)

    # 2) Filter out raw analog data
    exclude_cols = [c for c in df.columns if 'Emitter' in c]
    df = threshold_filter(df, exclude_columns=exclude_cols)
    df = butter_lowpass_filter(df=df, cutoff_hz=1.0, fs=fs, order=4, exclude_columns=exclude_cols)

    # 3) Convert raw analog data to intensities
    df = sliding_window_rms(df=df)

    # 4) Interleave the blocks based on the mode column.
    final_df = interleave_mode_blocks(df, mode_col="G0_Emitter")

    # 5) Assign new timestamps at a fixed increment (0.001 s in this example)
    INCREMENT = 0.001
    final_df.insert(0, "Time (s)", [i * INCREMENT for i in range(len(final_df))])

    # 6) Round the new timestamps to avoid floating-point artifacts.
    final_df["Time (s)"] = final_df["Time (s)"].round(3)

    # 7) Write the final DataFrame to CSV
    final_df.to_csv("interleaved_output.csv", index=False)

    # 8) Output the resulting DataFrame.
    print(final_df.head(20))

    # 9) Process collected data
    INPUT_CSV = "interleaved_output.csv"  
    OUTPUT_CSV = "processed_output.csv"
    process_csv_dataset(INPUT_CSV, OUTPUT_CSV)
