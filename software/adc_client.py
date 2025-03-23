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

# Register the signal handler for SIGINT.
signal.signal(signal.SIGINT, signal_handler)

# Modern UI configuration.
pg.setConfigOption('antialias', True)  # Smoother curves and text.
pg.setConfigOption('background', 'w')  # White background.
pg.setConfigOption('foreground', 'k')  # Black text and lines.

# Create a SocketIO client instance.
sio = socketio.Client()

# For each group (8 total) and for each trace (3 per group), store the last 5000 datapoints.
data = [[collections.deque(maxlen=5000) for _ in range(3)] for _ in range(8)]

# Create a Qt Application.
app = QtWidgets.QApplication([])

# Create a main window widget with a vertical layout.
main_window = QtWidgets.QWidget()
layout = QtWidgets.QVBoxLayout(main_window)

# Create a Pause/Play button. Initially it says "Pause".
pause_button = QtWidgets.QPushButton("Pause")
layout.addWidget(pause_button)

# Create a GraphicsLayoutWidget to hold the plots.
win = pg.GraphicsLayoutWidget(title="Real-Time Sensor Data")
win.resize(1200, 800)

# Create 8 plots arranged in 4 rows x 2 columns.
plots = []
curves = []  # curves[group][trace]
for group in range(8):
    p = win.addPlot(title=f"Group {group+1}")
    p.showGrid(x=True, y=True, alpha=0.3)  # Softer grid lines.
    p.setLabel('bottom', 'Timeframe')
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

# Add the plotting widget to the main layout.
layout.addWidget(win)

# Global flag to track pause/play state.
paused = False

def toggle_pause():
    """Toggle pause/play state: disconnect/reconnect SocketIO, stop/restart update timer, and clear queued data."""
    global paused
    if not paused:
        # Pause: disconnect socket, stop timer, clear any queued data.
        paused = True
        pause_button.setText("Play")
        if sio.connected:
            sio.disconnect()
        timer.stop()
        for group_data in data:
            for deque_obj in group_data:
                deque_obj.clear()
        print("Paused plotting and data reception.")
    else:
        # Resume: reconnect socket and restart the timer.
        paused = False
        pause_button.setText("Pause")
        sio.connect('http://localhost:5000')
        timer.start(1)
        print("Resumed plotting and data reception.")

pause_button.clicked.connect(toggle_pause)

@sio.event
def connect():
    print("SocketIO client connected.")

@sio.event
def disconnect():
    print("SocketIO client disconnected.")

@sio.on('processed_data')
def on_processed_data(message):
    # If paused, ignore any incoming data.
    if paused:
        return
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
    if paused:
        return
    for group in range(8):
        for trace in range(3):
            d = list(data[group][trace])
            x = list(range(len(d)))
            curves[group][trace].setData(x, d)

# Create a QTimer to update the plots.
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(1)  # Refresh rate in ms (subject to system performance).

# Connect the SocketIO client.
sio.connect('http://localhost:5000')

# Show the main window.
main_window.show()
sys.exit(app.exec_())
