import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time

# Serial port setup — adjust for your Mac's port
ser = serial.Serial('/dev/tty.usbmodem205D388A47311', 9600, timeout=1) 

# Data storage
data = []
timestamps = []
start_time = time.time()

# Function to read and update plot
def update(frame):
    current_time = time.time() - start_time

    # Read all available 16-bit values
    while ser.in_waiting >= 2:
        raw = ser.read(2)
        value = int.from_bytes(raw, byteorder='little', signed=True)
        data.append(value)
        timestamps.append(current_time)

    # Keep only the last 10 seconds of data
    while timestamps and (current_time - timestamps[0]) > 1:
        timestamps.pop(0)
        data.pop(0)

    ax.clear()
    ax.plot(timestamps, data, color='blue')
    ax.set_title('Real-time Serial Data (Last 10 seconds)')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Value')
    ax.grid(True)
    ax.set_xlim(max(0, current_time - 1), current_time)

# Set up the plot
fig, ax = plt.subplots()
ani = animation.FuncAnimation(fig, update, interval=10)
plt.show()

# Close serial on exit
ser.close()
