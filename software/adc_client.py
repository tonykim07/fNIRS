"""
adc_client.py
===================
This script creates a real-time data visualization application using PyQt5 and pyqtgraph.
It connects to a SocketIO server to receive sensor data and displays it in a GUI.
The data is organized into groups and traces, and the application allows for real-time 
updates of the plots.
"""

import sys
import signal
import collections
import socketio
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

# Signal handler to exit gracefully.
def signal_handler():
    """
    Graceful Exit Handler
    """
    print("Exiting gracefully...")
    if sio_thread.isRunning():
        sio_thread.requestInterruption()
        sio_thread.quit()
    app.quit()

signal.signal(signal.SIGINT, signal_handler)

# Modern UI configuration.
pg.setConfigOption('antialias', True)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# Data storage: For 8 groups and 3 traces per group, storing the last 5000 data points.
data = [[collections.deque(maxlen=5000) for _ in range(3)] for _ in range(8)]

# Define a QThread to run the SocketIO client.
class SocketClientThread(QtCore.QThread):
    """
    SocketClientThread is a QThread that connects to a SocketIO server
    and listens for incoming data. It emits a signal with the received
    sensor array when new data is available.
    """
    newData = QtCore.pyqtSignal(list)  # will emit the sensor array

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sio = socketio.Client()

        @self.sio.event
        def connect():
            print("SocketIO client connected.")

        @self.sio.event
        def disconnect():
            print("SocketIO client disconnected.")

        @self.sio.on('processed_data')
        def on_processed_data(message):
            sensor_array = message.get('sensor_array', [])
            if len(sensor_array) == 24:
                self.newData.emit(sensor_array)
            else:
                print("Received data does not contain 24 elements.")

    def run(self):
        """
        Run the SocketIO client loop.
        This method connects to the SocketIO server and starts listening
        for incoming data.
        """
        try:
            self.sio.connect('http://localhost:5000')
            # Run the SocketIO client loop until the thread is interrupted.
            self.sio.wait()
        except Exception as e:
            print("SocketIO connection error:", e)

    def stop(self):
        """
        Stop the SocketIO client and quit the thread.
        """
        self.sio.disconnect()
        self.quit()

# Create the Qt Application.
app = QtWidgets.QApplication([])

# Create the main window and layout.
main_window = QtWidgets.QWidget()
main_layout = QtWidgets.QVBoxLayout(main_window)

# Create a top horizontal layout for the legend.
top_layout = QtWidgets.QHBoxLayout()
top_layout.addStretch()

# Define colors and labels for the traces.
trace_colors = ["red", "green", "blue"]
trace_labels = ["Channel 1", "Channel 2", "Channel 3"]

# Create the legend layout.
legend_layout = QtWidgets.QHBoxLayout()
for color, label in zip(trace_colors, trace_labels):
    square = QtWidgets.QLabel()
    square.setFixedSize(15, 15)
    square.setStyleSheet(f"background-color: {color}; border: 1px solid black;")
    text_label = QtWidgets.QLabel(label)
    item_layout = QtWidgets.QHBoxLayout()
    item_layout.addWidget(square)
    item_layout.addWidget(text_label)
    item_widget = QtWidgets.QWidget()
    item_widget.setLayout(item_layout)
    legend_layout.addWidget(item_widget)
legend_layout.addStretch()
top_layout.addLayout(legend_layout)
main_layout.addLayout(top_layout)

# Create a GraphicsLayoutWidget to hold the plots.
win = pg.GraphicsLayoutWidget(title="Real-Time Sensor Data")
win.resize(1200, 800)

plots = []
curves = []  # curves[group][trace]
for group in range(8):
    p = win.addPlot(title=f"Group {group+1}")
    p.setTitle(f"Group {group+1}", size="20pt")
    p.showGrid(x=True, y=True, alpha=0.3)
    p.setLabel('left', 'ADC Readings')
    p.setLabel('bottom', 'Timeframe')
    group_curves = []
    for trace in range(3):
        pen = pg.mkPen(color=trace_colors[trace], width=2)
        curve = p.plot(pen=pen)
        group_curves.append(curve)
    plots.append(p)
    curves.append(group_curves)
    if group % 2 == 1:
        win.nextRow()

main_layout.addWidget(win)

# Function to update the plots.
def update():
    """
    Update function to refresh the plots with new data.
    This function is called periodically to redraw the curves
    with the latest data from the deque.
    """
    for group in range(8):
        for trace in range(3):
            d = list(data[group][trace])
            x = list(range(len(d)))
            curves[group][trace].setData(x, d)

# Timer to update the plots.
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(1)  # Adjust refresh rate as needed.

# Slot to handle new sensor data from the SocketIO thread.
def handle_new_data(sensor_array):
    """
    Handle new data received from the SocketIO server.
    This function processes the incoming sensor array and updates the
    data storage for each group and trace.
    """
    for group in range(8):
        group_values = sensor_array[group * 3: group * 3 + 3]
        for trace in range(3):
            data[group][trace].append(group_values[trace])

# Start the SocketIO client thread.
sio_thread = SocketClientThread()
sio_thread.newData.connect(handle_new_data)
sio_thread.start()

if __name__ == '__main__':
    main_window.showFullScreen()
    sys.exit(app.exec_())
