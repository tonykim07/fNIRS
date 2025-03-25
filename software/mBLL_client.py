import sys
import socketio
import collections
import signal

from pyqtgraph.Qt import QtWidgets, QtCore
import pyqtgraph as pg
import engineio.base_client
engineio.base_client.printExc = lambda *args, **kwargs: None

# Signal handler to exit gracefully.
def signal_handler(sig, frame):
    print("Exiting gracefully...")
    if sio.connected:
        sio.disconnect()
    app.quit()

signal.signal(signal.SIGINT, signal_handler)

# Modern UI configuration:
pg.setConfigOption('antialias', True)             # Smoother curves and text.
pg.setConfigOption('background', 'w')             # White background.
pg.setConfigOption('foreground', 'k')             # Black text and lines.

# Create a SocketIO client instance.
sio = socketio.Client()

data = [[collections.deque(maxlen=5000) for _ in range(6)] for _ in range(8)]

# Create a Qt Application.
app = QtWidgets.QApplication([])

# Create the main window and layout.
main_window = QtWidgets.QWidget()
main_layout = QtWidgets.QVBoxLayout(main_window)

# Create a top horizontal layout for the legend.
top_layout = QtWidgets.QHBoxLayout()
top_layout.addStretch()  # Push the legend to the right.

# Define colors and labels for the traces.
trace_colors = ["#FF0000", "#FF6666", "#008000", "#90EE90", "#0000FF", "#ADD8E6"]
trace_labels = ["S1, hbo", "S1, hbr", "S2, hbo", "S2, hbr", "S3, hbo", "S3, hbr"]

# Create the legend layout.
legend_layout = QtWidgets.QHBoxLayout()
for color, label in zip(trace_colors, trace_labels):
    # Create a small colored square.
    square = QtWidgets.QLabel()
    square.setFixedSize(15, 15)
    # Set the background color and add a border so the color is clear.
    square.setStyleSheet(f"background-color: {color}; border: 1px solid black;")
    # Create a label for the channel.
    text_label = QtWidgets.QLabel(label)
    # Arrange the square and label horizontally.
    item_layout = QtWidgets.QHBoxLayout()
    item_layout.addWidget(square)
    item_layout.addWidget(text_label)
    item_widget = QtWidgets.QWidget()
    item_widget.setLayout(item_layout)
    legend_layout.addWidget(item_widget)
legend_layout.addStretch()
top_layout.addLayout(legend_layout)

# Add the top layout (legend) to the main layout.
main_layout.addLayout(top_layout)

# Create a GraphicsLayoutWidget to hold the sensor plots.
win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Sensor Data")
win.resize(1200, 800)

# Create 8 plots arranged in 4 rows x 2 columns.
plots = []
curves = []  # curves[group][trace]
for group in range(8):
    p = win.addPlot(title=f"Group {group+1}")
    p.showGrid(x=True, y=True, alpha=0.3)
    p.setLabel('bottom', 'Timeframe')
    group_curves = []
    # Create 6 traces for this group.
    for trace in range(6):
        color = pg.intColor(trace, hues=6)
        curve = p.plot(pen=pg.mkPen(color=color, width=2))
        group_curves.append(curve)
    plots.append(p)
    curves.append(group_curves)
    if group % 2 == 1:
        win.nextRow()

# Add the plotting widget to the main layout.
main_layout.addWidget(win)

@sio.event
def connect():
    print("SocketIO client connected.")

@sio.event
def disconnect():
    print("SocketIO client disconnected.")

@sio.on('processed_data')
def on_processed_data(message):
    sensor_array = message.get('concentrations', [])
    print("Received sensor data:", sensor_array)
    if len(sensor_array) == 48:
        # For each of the 8 groups, extract 6 consecutive values.
        for group in range(8):
            group_values = sensor_array[group * 6 : group * 6 + 6]
            for trace in range(6):
                data[group][trace].append(group_values[trace])
    else:
        print("Received data does not contain 48 elements.")

# -----------------------------------------------------------------------------
# Plot update: update all sensor plots.
def update():
    for group in range(8):
        for trace in range(6):
            d = list(data[group][trace])
            x_data = list(range(len(d)))
            curves[group][trace].setData(x_data, d)

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(1)  # Adjust the refresh rate as needed.

# Connect the Socket.IO client.
sio.connect('http://localhost:5000')

if __name__ == '__main__':
    main_window.showFullScreen()
    sys.exit(app.exec_())
