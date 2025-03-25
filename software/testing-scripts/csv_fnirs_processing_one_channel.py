import numpy as np
import csv
from tabulate import tabulate

# If your nirsimple package is installed, keep these imports:
import nirsimple.preprocessing as nsp
import nirsimple.processing as nproc

def build_single_channel_info(age, sd_distance):
    """
    Builds channel names, wavelengths, DPFs, and source-detector distances
    for a single channel measured at two wavelengths (660 nm and 940 nm).
    """
    channel_names = ["S1_D1", "S1_D1"]   # Single physical channel, repeated for each wavelength
    ch_wls = [660.0, 940.0]             # Two wavelengths
    ch_dpfs = [nsp.get_dpf(wl, age) for wl in ch_wls]
    ch_distances = [sd_distance, sd_distance]
    return channel_names, ch_wls, ch_dpfs, ch_distances

def combine_two_rows(row_mode1, row_mode2):
    """
    Combines two rows: one for mode=1 (660 nm), the next for mode=2 (940 nm).

    row_mode1 -> [Time, G0_Short, G0_Emitter=1]
    row_mode2 -> [Time, G0_Short, G0_Emitter=2]

    Returns a 2-element vector of intensities: [short_660, short_940].
    """
    short_660 = float(row_mode1[1])  # G0_Short from the mode=1 row
    short_940 = float(row_mode2[1])  # G0_Short from the mode=2 row
    return np.array([short_660, short_940], dtype=float)

def process_csv_dataset_single_channel(input_csv, output_csv, age=22, sd_distance=3.0, molar_ext_coeff_table='wray'):
    """
    Processes a simplified fNIRS CSV dataset with only three columns:
      Time, G0_Short, G0_Emitter
    Rows alternate between emitter=1 (660 nm) and emitter=2 (940 nm).

    The output CSV will have columns:
      Time, S1_D1_hbo, S1_D1_hbr
    """
    # --- 1) Load CSV data (skip header) ---
    with open(input_csv, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)  # skip the header row
        data_lines = list(reader)

    # Convert rows to float arrays (only if they have at least 3 columns)
    data_matrix = []
    for line in data_lines:
        if len(line) >= 3:
            # e.g. line = [Time, G0_Short, G0_Emitter]
            try:
                data_matrix.append([float(line[0]), float(line[1]), float(line[2])])
            except ValueError:
                # skip any line that doesn't parse
                continue
    data_matrix = np.array(data_matrix)
    num_rows = data_matrix.shape[0]
    if num_rows < 2:
        print("Insufficient data rows for processing.")
        return

    # --- 2) Pair rows: assume row0 is emitter=1, row1 is emitter=2, etc. ---
    samples = []
    times = []
    i = 0
    while i < num_rows - 1:
        row_mode1 = data_matrix[i, :]     # [Time, G0_Short, G0_Emitter=1]
        row_mode2 = data_matrix[i + 1, :] # [Time, G0_Short, G0_Emitter=2]

        # If row_mode1[2] != 1 or row_mode2[2] != 2, you may want to skip or handle differently
        # For simplicity, assume perfect alternation: 1 then 2
        t_val = row_mode1[0]  # time from mode=1 row
        sample = combine_two_rows(row_mode1, row_mode2)
        samples.append(sample)
        times.append(t_val)
        i += 2  # move to the next pair

    # shape => 2 x N, where N is number of paired samples
    samples = np.array(samples).T

    # --- 3) Build single-channel info ---
    channel_names, ch_wls, ch_dpfs, ch_distances = build_single_channel_info(age, sd_distance)

    # --- 4) Convert intensities → ΔOD, apply MBLL, then CBSI ---
    delta_od = nsp.intensities_to_od_changes(samples)
    # MBLL => get concentration changes in [HbO, HbR] for each channel
    delta_c, new_ch_names, new_ch_types = nsp.mbll(
        delta_od,
        channel_names,
        ch_wls,
        ch_dpfs,
        ch_distances,
        unit='cm',
        table=molar_ext_coeff_table
    )
    # CBSI => further post-processing
    delta_c_corr, corr_ch_names, corr_ch_types = nproc.cbsi(delta_c, new_ch_names, new_ch_types)

    # --- 5) Create header labels and write output CSV ---
    processed_headers = [f"{name}_{ctype}" for name, ctype in zip(corr_ch_names, corr_ch_types)]
    header_out = ["Time"] + processed_headers

    with open(output_csv, "w", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header_out)
        for col_idx in range(delta_c_corr.shape[1]):
            time_val = times[col_idx]
            row_values = [time_val] + list(delta_c_corr[:, col_idx])
            writer.writerow(row_values)

    print(f"Post-processing complete. Output saved to '{output_csv}'.")

    # Optional: Print a table of final sample for quick check
    last_sample = delta_c_corr[:, -1]
    table_data = []
    for i, ch in enumerate(corr_ch_names):
        table_data.append([ch, corr_ch_types[i], f"{last_sample[i]:.4e}"])
    print("\nExample: Processed concentrations at the final time sample:")
    print(tabulate(table_data, headers=["Channel", "Type", "Concentration"]))

# ------------------ Main ------------------
if __name__ == '__main__':
    input_csv = "interleaved_output.csv"    # e.g. the 3-column file with Time, G0_Short, G0_Emitter
    output_csv = "processed_output.csv"
    process_csv_dataset_single_channel(input_csv, output_csv)
