"""
plot_mbll.py
==================
This script reads the processed_output (computed mbll) and creates three static plot 
for select channels
"""

import pandas as pd
import matplotlib.pyplot as plt

# Set global font
plt.rcParams['font.family'] = 'Times New Roman'

filename = "sample_data/processed_output.csv"
df = pd.read_csv(filename)
time = df["Time"]

# Select detector columns to plot
detector1_column = [col for col in df.columns if col.startswith("S3_D1")]
detector2_column = [col for col in df.columns if col.startswith("S3_D2")]
detector3_column = [col for col in df.columns if col.startswith("S3_D3")]

# Flag to combine channels into a single plot
combine_plots = False

# Add shaded spans and centered interval labels
# Note: this is specifically for the sample data
def add_interval_shading_and_labels(ax):
    ymin, ymax = ax.get_ylim()
    label_y = ymin + 0.85 * (ymax - ymin)

    ax.axvspan(0, 20, color='blue', alpha=0.1)
    ax.axvspan(20, 140, color='green', alpha=0.1)
    ax.axvspan(140, time.max(), color='blue', alpha=0.1)

    ax.text(10, label_y, 'Rest', ha='center', color='indigo', fontsize=16, weight='bold')
    ax.text(80, label_y, 'Task', ha='center', color='green', fontsize=16, weight='bold')
    ax.text((140 + time.max()) / 2, label_y, 'Rest', ha='center', color='indigo', fontsize=16, weight='bold')

# Add vertical lines and bolded labels near the bottom
# Note: this is specifically for the sample data
def add_event_lines(ax):
    ymin, ymax = ax.get_ylim()
    label_y = ymin + 0.05 * (ymax - ymin)

    for t, label in zip([20, 140], ["Time = 20s", "Time = 140s"]):
        ax.axvline(x=t, color='red', linestyle='--')
        ax.text(t + 1, label_y, label, color='red', fontsize=14, weight='bold')

# Plotting
if combine_plots:
    plt.figure(figsize=(14, 6))
    for col in detector1_column + detector2_column + detector3_column:
        label = "HbO" if "hbo" in col else "HbR"
        det = col.split('_')[1]
        plt.plot(time, df[col], label=f"{label} ({det})")

    ax = plt.gca()
    add_interval_shading_and_labels(ax)
    add_event_lines(ax)

    plt.title("Combined fNIRS Readings (S3)", fontsize=24)
    plt.xlabel("Time (s)", fontsize=20)
    plt.ylabel("Concentration Changes", fontsize=20)
    ax.tick_params(axis='both', labelsize=12)
    plt.legend(loc="upper right", fontsize=12)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

else:
    fig, axs = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    # Subplot 1
    for col in detector1_column:
        label = "HbO" if "hbo" in col else "HbR"
        axs[0].plot(time, df[col], label=label)
    axs[0].set_title("Short Channel Reading (Channel 1)", fontsize=24)
    axs[0].set_ylabel("Concentration Changes", fontsize=20)
    axs[0].legend(loc="upper right", fontsize=16)
    axs[0].grid(True)
    axs[0].tick_params(axis='both', labelsize=12)  
    add_interval_shading_and_labels(axs[0])
    add_event_lines(axs[0])

    # Subplot 2
    for col in detector2_column:
        label = "HbO" if "hbo" in col else "HbR"
        axs[1].plot(time, df[col], label=label)
    axs[1].set_title("Long Channel Reading (Channel 2)", fontsize=24)
    axs[1].set_ylabel("Concentration Changes", fontsize=20)
    axs[1].legend(loc="upper right", fontsize=16)
    axs[1].grid(True)
    axs[1].tick_params(axis='both', labelsize=12) 
    add_interval_shading_and_labels(axs[1])
    add_event_lines(axs[1])

    # Subplot 3
    for col in detector3_column:
        label = "HbO" if "hbo" in col else "HbR"
        axs[2].plot(time, df[col], label=label)
    axs[2].set_title("Long Channel Reading (Channel 3)", fontsize=24)
    axs[2].set_xlabel("Time (s)", fontsize=20)
    axs[2].set_ylabel("Concentration Changes", fontsize=20)
    axs[2].legend(loc="upper right", fontsize=16)
    axs[2].grid(True)
    axs[2].tick_params(axis='both', labelsize=12) 
    add_interval_shading_and_labels(axs[2])
    add_event_lines(axs[2])

    plt.tight_layout()
    plt.show()
