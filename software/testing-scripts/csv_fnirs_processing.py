import numpy as np
import csv
from tabulate import tabulate
import nirsimple.preprocessing as nsp
import nirsimple.processing as nproc

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
    input_csv = "interleaved_output.csv"  # Path to input CSV file
    output_csv = "processed_output.csv" # Desired output CSV file name
    process_csv_dataset(input_csv, output_csv)
