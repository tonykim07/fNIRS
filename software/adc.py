import sys
import socketio
import collections
from pyqtgraph.Qt import QtWidgets, QtCore
import pyqtgraph as pg
import engineio.base_client
engineio.base_client.printExc = lambda *args, **kwargs: None

# Create a SocketIO client instance.
sio = socketio.Client()

# For each group (8 total) and for each trace (3 per group), store the last 500 datapoints.
data = [[collections.deque(maxlen=5000) for _ in range(3)] for _ in range(8)]

# Create a Qt Application.
app = QtWidgets.QApplication([])

# Create a GraphicsLayoutWidget to hold the plots.
win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Sensor Data")
win.resize(1200, 800)

# Create 8 plots arranged in 4 rows x 2 columns.
plots = []
curves = []  # curves[group][trace]
for group in range(8):
    p = win.addPlot(title=f"Group {group+1}")
    p.showGrid(x=True, y=True)
    group_curves = []
    # Create 3 traces for this group.
    for trace in range(3):
        color = pg.intColor(trace, hues=3)
        curve = p.plot(pen=pg.mkPen(color=color, width=2))
        group_curves.append(curve)
    plots.append(p)
    curves.append(group_curves)
    # Arrange plots in two columns.
    if group % 2 == 1:
        win.nextRow()

@sio.event
def connect():
    print("SocketIO client connected.")

@sio.event
def disconnect():
    print("SocketIO client disconnected.")

@sio.on('processed_data')
def on_processed_data(message):
    sensor_array = message.get('sensor_array', [])
    print("Received sensor data:", sensor_array)
    if len(sensor_array) == 24:
        for group in range(8):
            group_values = sensor_array[group * 3: group * 3 + 3]
            for trace in range(3):
                data[group][trace].append(group_values[trace])
    else:
        print("Received data does not contain 24 elements.")

def update():
    """Update all plots with the latest data."""
    for group in range(8):
        for trace in range(3):
            d = list(data[group][trace])
            x = list(range(len(d)))
            curves[group][trace].setData(x, d)

# Create a QTimer to update the plots.
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(1)  # Try a 1 ms interval; actual refresh may depend on your system.

# Connect the SocketIO client.
sio.connect('http://localhost:5000')

if __name__ == '__main__':
    sys.exit(app.exec_())
