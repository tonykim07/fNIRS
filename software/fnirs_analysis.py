import matplotlib.pyplot as plt
import numpy as np
import mne

# Parameters
n_channels = 5  # Number of channels
sfreq = 100  # Sampling frequency in Hz
n_times = sfreq * 10  # 10 seconds of data

# Generate random data (5 channels, 10 seconds at 100 Hz)
data = np.random.randn(n_channels, n_times)
print(data)

# Define channel names and types
ch_names = ['1', '2', '3', '4', '5']
ch_types = ['fnirs_fd_ac_amplitude'] * n_channels  # Assuming all channels are EEG

# Create the info structure for MNE
info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)

# Create the RawArray with the data and info
raw = mne.io.RawArray(data, info)

plt.plot(data[0])  # Plot data from the first channel
plt.title("First Channel Test Plot")
plt.show()


# to do :
# Need to:
# 1. convert raw 12-bit data (0 through 4096) to NIRx format
#     - use MATLAB 
# 2. pro-process data using MNE toolbox 