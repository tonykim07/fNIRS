"""
plot_mbll.py
==================
This script plots the hemoglobin concentration changes of a selected sensor group (3 sensors)
using existing post processed data.
"""

import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV file
filename = "testing-scripts/processed_output.csv"
df = pd.read_csv(filename)
time = df["Time"]

# Group columns by detector (D1, D2, D3) for S3 (change for other sensor groups)
s3_d1_columns = [col for col in df.columns if col.startswith("S3_D1")]
s3_d2_columns = [col for col in df.columns if col.startswith("S3_D2")]
s3_d3_columns = [col for col in df.columns if col.startswith("S3_D3")]
fig, axs = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

# Plot S3_D1
for col in s3_d1_columns:
    axs[0].plot(time, df[col], label=col)
axs[0].set_title("S3_D1 HbO and HbR over Time")
axs[0].set_ylabel("Concentration Change")
axs[0].legend(loc="upper right", fontsize="x-small", ncol=2)
axs[0].grid(True)

# Plot S3_D2
for col in s3_d2_columns:
    axs[1].plot(time, df[col], label=col)
axs[1].set_title("S3_D2 HbO and HbR over Time")
axs[1].set_ylabel("Concentration Change")
axs[1].legend(loc="upper right", fontsize="x-small", ncol=2)
axs[1].grid(True)

# Plot S3_D3
for col in s3_d3_columns:
    axs[2].plot(time, df[col], label=col)
axs[2].set_title("S3_D3 HbO and HbR over Time")
axs[2].set_xlabel("Time (s)")
axs[2].set_ylabel("Concentration Change")
axs[2].legend(loc="upper right", fontsize="x-small", ncol=2)
axs[2].grid(True)

plt.tight_layout()
plt.show()
