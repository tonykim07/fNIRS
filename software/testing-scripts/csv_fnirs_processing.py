import numpy as np
import csv
from tabulate import tabulate
import nirsimple.preprocessing as nsp
import nirsimple.processing as nproc
import serial
import struct
import numpy as np
import time
import csv
import pandas as pd
import msvcrt

# Set up serial connection
ser = serial.Serial('COM7', 115200, timeout=1)

NOISE_LEVEL = 2050

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
        sensor_channel_inv1 = 2 * NOISE_LEVEL - sensor_channel_1
        sensor_channel_2 = struct.unpack('>H', data[offset+3:offset+5])[0]
        sensor_channel_inv2 = 2 * NOISE_LEVEL - sensor_channel_2
        sensor_channel_3 = struct.unpack('>H', data[offset+5:offset+7])[0]
        sensor_channel_inv3 = 2 * NOISE_LEVEL - sensor_channel_3
        emitter_status    = data[offset+7]

        parsed_data[i] = [
            packet_identifier,
            sensor_channel_inv1,
            sensor_channel_inv2,
            sensor_channel_inv3,
            emitter_status
        ]
    return parsed_data

def capture_data(csv_filename, stop_on_enter=True, external_stop_flag=None):
    """
    Captures ADC data and writes it to a CSV file.
    
    Parameters:
      csv_filename (str): Name of the CSV file to write the data.
      stop_on_enter (bool): If True, the loop will check for the Enter key to stop logging.
      external_stop_flag: An object (e.g., threading.Event) with an is_set() method.
                          If provided and external_stop_flag.is_set() returns True,
                          the capture loop will stop.
    """
    with open(csv_filename, mode='w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        header = ["Time (s)"]
        for i in range(8):
            header += [f"G{i}_Short", f"G{i}_Long1", f"G{i}_Long2", f"G{i}_Emitter"]
        writer.writerow(header)

        print("Starting raw ADC logging (seconds elapsed)...")
        if stop_on_enter:
            print("Press Enter to stop logging and proceed to CSV processing.")
        if external_stop_flag is not None:
            print("External stop flag is active; it can also stop logging when set.")

        start_time = time.time()

        try:
            while True:
                # Check if the external stop flag is set
                if external_stop_flag is not None and external_stop_flag.is_set():
                    print("External stop signal received, stopping logging...")
                    break

                # Check for Enter key press if enabled
                if stop_on_enter and msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key == b'\r':  # Enter key is pressed (carriage return)
                        print("Enter key pressed, stopping logging...")
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

def build_channel_info(age, sd_distance):
    """
    Builds channel names, wavelengths, DPFs, and source-detector distances.
    There are 24 physical channels (8 sensor groups × 3 detectors), and each is
    measured at two wavelengths (660 nm and 940 nm), yielding 48 channels.
    """
    physical_channels = []
    for set_idx in range(1, 9):
        for det in range(1, 4):
            physical_channels.append(f"S{set_idx}_D{det}")
    channel_names = []
    ch_wls = []
    for name in physical_channels:
        channel_names.append(name)   # For 660 nm measurement
        ch_wls.append(660.0)
        channel_names.append(name)   # For 940 nm measurement
        ch_wls.append(940.0)
    ch_dpfs = [nsp.get_dpf(wl, age) for wl in ch_wls]
    ch_distances = [sd_distance] * len(ch_wls)
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

def process_csv_dataset(input_csv, output_csv, age=22, sd_distance=5.0, molar_ext_coeff_table='wray'):
    """
    Processes an fNIRS CSV dataset for post-processing.

    The CSV is expected to have a header and then rows with columns:
      Time, G0_Short, G0_Long1, G0_Long2, G0_Emitter, G1_Short, G1_Long1, G1_Long2, G1_Emitter, ..., G7_Short, G7_Long1, G7_Long2, G7_Emitter.

    Rows alternate between mode 1 (660 nm) and mode 2 (940 nm). The function
    pairs each mode 1 row with the following mode 2 row, applies the OD conversion,
    MBLL, and CBSI processing to compute hemoglobin concentration changes.

    The output CSV will have columns:
      Time, [for each processed channel: "{ChannelName}_{Type}"],
    where Type is either "hbo" or "hbr".
    """
    # Load CSV data (skip header)
    with open(input_csv, 'r') as f:
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
    channel_names, ch_wls, ch_dpfs, ch_distances = build_channel_info(age, sd_distance)

    # Apply OD conversion to the entire dataset
    delta_od = nsp.intensities_to_od_changes(samples)
    # Apply MBLL to compute concentration changes
    delta_c, new_ch_names, new_ch_types = nsp.mbll(
        delta_od,
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
        for col_idx in range(delta_c_corr.shape[1]):
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
    stop_flag=None
    capture_data("all_groups.csv", stop_on_enter=True, external_stop_flag=stop_flag)
    # Read CSV file
    df = pd.read_csv("all_groups.csv")

    # Data formmating and Processing
    # 1) Completely ignore the original timestamp by dropping it if it exists.
    if "Time (s)" in df.columns:
        df.drop(columns=["Time (s)"], inplace=True)

    # 2) Filter out rows with any Short/Long reading <200 or >3800.
    reading_cols = [c for c in df.columns if "Short" in c or "Long" in c]
    mask = (df[reading_cols] >= 0).all(axis=1) & (df[reading_cols] <= 4000).all(axis=1)
    df = df[mask].copy()

    # 3) Interleave the blocks based on the mode column.
    final_df = interleave_mode_blocks(df, mode_col="G0_Emitter")

    # 4) Assign new timestamps at a fixed increment (0.001 s in this example)
    increment = 0.001
    final_df.insert(0, "Time (s)", [i * increment for i in range(len(final_df))])

    # 5) Round the new timestamps to avoid floating-point artifacts.
    final_df["Time (s)"] = final_df["Time (s)"].round(3)

    # 6) Write the final DataFrame to CSV
    final_df.to_csv("interleaved_output.csv", index=False)

    # 7) Output the resulting DataFrame.
    print(final_df.head(20))

    # 8) Process collected data
    input_csv = "interleaved_output.csv"  # Path to input CSV file
    output_csv = "processed_output.csv" # Desired output CSV file name
    process_csv_dataset(input_csv, output_csv)
