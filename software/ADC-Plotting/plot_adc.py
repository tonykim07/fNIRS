# import sys
# import collections
# import serial
# import struct
# from pyqtgraph.Qt import QtWidgets, QtCore
# import pyqtgraph as pg

# # Configure PyQtGraph
# pg.setConfigOption('antialias', True)
# pg.setConfigOption('background', 'w')
# pg.setConfigOption('foreground', 'k')

# # Create 8 groups x 3 traces
# data = [[collections.deque(maxlen=5000) for _ in range(3)] for _ in range(8)]

# # Create Qt app and plot window
# app = QtWidgets.QApplication([])
# win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Sensor Data")
# win.resize(1200, 800)

# plots = []
# curves = []
# for group in range(8):
#     p = win.addPlot(title=f"Group {group+1}")
#     p.showGrid(x=True, y=True, alpha=0.3)
#     p.setLabel('bottom', 'Timeframe')
#     group_curves = []
#     for trace in range(3):
#         color = pg.intColor(trace, hues=3)
#         curve = p.plot(pen=pg.mkPen(color=color, width=2))
#         group_curves.append(curve)
#     plots.append(p)
#     curves.append(group_curves)
#     if group % 2 == 1:
#         win.nextRow()

# # Serial setup (adjust port as needed)
# ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 115200, timeout=1)

# def parse_packet_to_flat_array(data):
#     values = [0] * 24
#     for i in range(8):
#         offset = i * 8
#         short = struct.unpack('>H', data[offset+1:offset+3])[0]
#         long1 = struct.unpack('>H', data[offset+3:offset+5])[0]
#         long2 = struct.unpack('>H', data[offset+5:offset+7])[0]
#         values[i * 3 : i * 3 + 3] = [short, long1, long2]
#     return values

# def update():
#     if ser.in_waiting >= 64:
#         raw = ser.read(64)
#         if len(raw) == 64:
#             sensor_array = parse_packet_to_flat_array(raw)
#             for group in range(8):
#                 group_values = sensor_array[group * 3 : group * 3 + 3]
#                 for trace in range(3):
#                     data[group][trace].append(group_values[trace])
    
#     for group in range(8):
#         for trace in range(3):
#             d = list(data[group][trace])
#             x = list(range(len(d)))
#             curves[group][trace].setData(x, d)

# # QTimer for periodic plot updates
# timer = QtCore.QTimer()
# timer.timeout.connect(update)
# timer.start(10)  # ~100 FPS or adjust based on system performance

# if __name__ == '__main__':
#     sys.exit(app.exec_())

import sys
import numpy as np
import serial
import struct
from pyqtgraph.Qt import QtWidgets, QtCore
import pyqtgraph as pg

# Configure PyQtGraph appearance
pg.setConfigOption('antialias', True)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# Constants
NUM_GROUPS = 8
NUM_TRACES = 3
BUFFER_SIZE = 5000  # Number of samples to display

# Initialize data buffers (NumPy)
data = np.zeros((NUM_GROUPS, NUM_TRACES, BUFFER_SIZE), dtype=np.float32)
index = 0  # Circular buffer index
x = np.arange(BUFFER_SIZE)

# Serial setup (adjust port as needed)
ser = serial.Serial('/dev/tty.usbmodem205E386D47311', 115200, timeout=0.01)

# Create Qt App and plot window
app = QtWidgets.QApplication([])
win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Sensor Data")
win.resize(1200, 800)

# Plotting setup
curves = []
for group in range(NUM_GROUPS):
    p = win.addPlot(title=f"Group {group+1}")
    p.showGrid(x=True, y=True, alpha=0.3)
    p.setLabel('bottom', 'Timeframe')
    group_curves = []
    for trace in range(NUM_TRACES):
        color = pg.intColor(trace, hues=3)
        curve = p.plot(pen=pg.mkPen(color=color, width=2))
        group_curves.append(curve)
    curves.append(group_curves)
    if group % 2 == 1:
        win.nextRow()

def parse_packet_to_flat_array(packet):
    """Parses 64-byte packet into 24 sensor values."""
    values = [0] * 24
    for i in range(8):
        offset = i * 8
        short = struct.unpack('>H', packet[offset+1:offset+3])[0]
        long1 = struct.unpack('>H', packet[offset+3:offset+5])[0]
        long2 = struct.unpack('>H', packet[offset+5:offset+7])[0]
        values[i * 3 : i * 3 + 3] = [short, long1, long2]
    return values

def update():
    global index
    # Read full packet if available
    if ser.in_waiting >= 64:
        packet = ser.read(64)
        if len(packet) == 64:
            values = parse_packet_to_flat_array(packet)
            for group in range(NUM_GROUPS):
                for trace in range(NUM_TRACES):
                    val = values[group * 3 + trace]
                    data[group][trace][index % BUFFER_SIZE] = val

            index += 1

    # Update all curves (full redraw from buffer slice)
    for group in range(NUM_GROUPS):
        for trace in range(NUM_TRACES):
            if index < BUFFER_SIZE:
                d = data[group][trace][:index]
                x_plot = x[:index]
            else:
                # Circular buffer logic: roll the array
                d = np.roll(data[group][trace], -index % BUFFER_SIZE)
                x_plot = x
            curves[group][trace].setData(x_plot, d)

# Start timer for GUI update
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(30)  # ~33 FPS

if __name__ == '__main__':
    sys.exit(app.exec_())
