"""
apply_rms_to_adc.py
==================
This script reads from the all_groups.csv, the collected raw ADC samples and applies 
rms calculations and outputs a new csv, all_groups_rms.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

input_file = "sample_data/all_groups.csv"
output_file = "all_groups_rms.csv"

# Change this as needed
column_to_plot = "G2_Short" 
# Flag to remove DC component before RMS
remove_dc = False  
# Flag to split emitter segments in half
split_emitter_window_in_half = False 

df = pd.read_csv(input_file)
df_original = df.copy()

# Use one emitter channel for segmentation
emitter_reference = df["G0_Emitter"].values
change_points = np.where(np.diff(emitter_reference) != 0)[0] + 1
segments = np.split(np.arange(len(df)), change_points)

# Split segments into halves if flag is enabled
if split_emitter_window_in_half:
    split_segments = []
    for segment in segments:
        n = len(segment)
        if n == 0:
            continue
        mid = n // 2
        split_segments.append(segment[:mid])
        split_segments.append(segment[mid:])
    segments = split_segments

# Group names
groups = [f"G{i}" for i in range(8)]

# RMS Processing
for g in groups:
    short_col = f"{g}_Short"
    long1_col = f"{g}_Long1"
    long2_col = f"{g}_Long2"
    
    for segment in segments:
        if len(segment) == 0:
            continue
        segment_idx = segment.tolist()
        
        # Calculate RMS with or without DC component
        for col in [short_col, long1_col, long2_col]:
            segment_data = df.loc[segment_idx, col]
            if remove_dc:
                segment_data = segment_data - segment_data.mean()
            rms_val = np.sqrt(np.mean(np.square(segment_data)))
            df.loc[segment_idx, col] = rms_val

df.to_csv(output_file, index=False)

# Plot Result, change column to plot above to select the channel
plt.figure(figsize=(12, 6))
plt.plot(df_original["Time (s)"], df_original[column_to_plot], label="Original", alpha=0.5)
plt.plot(df["Time (s)"], df[column_to_plot], label="RMS Processed", linewidth=2)
plt.xlabel("Time (s)")
plt.ylabel(column_to_plot)
plt.title(f"RMS Processing of {column_to_plot} (remove_dc={remove_dc}, half_window={split_emitter_window_in_half})")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
