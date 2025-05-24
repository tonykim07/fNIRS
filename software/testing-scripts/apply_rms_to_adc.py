import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
input_file = "testing-scripts/ADC_test1_filtered.csv"
output_file = "rms_output.csv"
column_to_plot = "G2_Short"  # Change this as needed
remove_dc = True  # Set to False to include DC component in RMS

# --- Load Data ---
df = pd.read_csv(input_file)
df_original = df.copy()

emitter_reference = df["G0_Emitter"].values
change_points = np.where(np.diff(emitter_reference) != 0)[0] + 1
segments = np.split(np.arange(len(df)), change_points)
groups = [f"G{i}" for i in range(8)]

# --- RMS Processing ---
for g in groups:
    short_col = f"{g}_Short"
    long1_col = f"{g}_Long1"
    long2_col = f"{g}_Long2"
    
    for segment in segments:
        if len(segment) == 0:
            continue
        segment_idx = segment.tolist()
        
        # --- Calculate RMS with or without DC component ---
        for col in [short_col, long1_col, long2_col]:
            segment_data = df.loc[segment_idx, col]
            if remove_dc:
                segment_data = segment_data - segment_data.mean()
            rms_val = np.sqrt(np.mean(np.square(segment_data)))
            df.loc[segment_idx, col] = rms_val

# --- Save Processed Data ---
df.to_csv(output_file, index=False)

# --- Plot Result ---
plt.figure(figsize=(12, 6))
plt.plot(df_original["Time (s)"], df_original[column_to_plot], label="Original", alpha=0.5)
plt.plot(df["Time (s)"], df[column_to_plot], label="RMS Processed", linewidth=2)
plt.xlabel("Time (s)")
plt.ylabel(column_to_plot)
plt.title(f"RMS Processing of {column_to_plot} (remove_dc={remove_dc})")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
