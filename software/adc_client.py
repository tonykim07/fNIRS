import sys
import socketio
import collections
import signal

from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import engineio.base_client
engineio.base_client.printExc = lambda *args, **kwargs: None

# Signal handler to exit the application gracefully.
def signal_handler(sig, frame):
    print("Exiting gracefully...")
    if sio.connected:
        sio.disconnect()
    app.quit()

signal.signal(signal.SIGINT, signal_handler)

# Modern UI configuration.
pg.setConfigOption('antialias', True)    # Smoother curves and text.
pg.setConfigOption('background', 'w')      # White background.
pg.setConfigOption('foreground', 'k')      # Black text and lines.

# Create a SocketIO client instance.
sio = socketio.Client()

# For each group (8 total) and for each trace (3 per group), store the last 5000 datapoints.
data = [[collections.deque(maxlen=5000) for _ in range(3)] for _ in range(8)]

# Create a Qt Application.
app = QtWidgets.QApplication([])

# Create the main window and layout.
main_window = QtWidgets.QWidget()
main_layout = QtWidgets.QVBoxLayout(main_window)

# Create a top horizontal layout for the legend.
top_layout = QtWidgets.QHBoxLayout()
top_layout.addStretch()  # Push the legend to the right.

# Define colors and labels for the traces.
# Note: The request is for first trace red, second green, and third green.
trace_colors = ["red", "green", "blue"]
trace_labels = ["Channel 1", "Channel 2", "Channel 3"]

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

# Create a GraphicsLayoutWidget to hold the plots.
win = pg.GraphicsLayoutWidget(title="Real-Time Sensor Data")
win.resize(1200, 800)

plots = []
curves = []  # curves[group][trace]
for group in range(8):
    p = win.addPlot(title=f"Group {group+1}")
    p.showGrid(x=True, y=True, alpha=0.3)  # Softer grid lines.
    p.setLabel('bottom', 'Timeframe')       # Set x-axis label.
    group_curves = []
    for trace in range(3):
        pen = pg.mkPen(color=trace_colors[trace], width=2)
        curve = p.plot(pen=pen)
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
timer.start(1)  # The actual refresh rate may vary by system performance.

# Connect the SocketIO client.
sio.connect('http://localhost:5000')

if __name__ == '__main__':
    main_window.showFullScreen()
    sys.exit(app.exec_())
