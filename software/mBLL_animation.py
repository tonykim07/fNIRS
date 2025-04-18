"""
mBLL_animation.py
==================
This script visualizes mBLL data in real-time using PyQtGraph.
It reads data from a CSV file and displays it in a GUI with multiple subplots.
"""

#!/usr/bin/env python
import sys
import os
import signal
import collections
import pandas as pd
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

# ------------------------------
# Determine data folder
# ------------------------------
DEMO = any(arg.lower() == 'demo' for arg in sys.argv[1:])
DATA_DIR = 'sample_data' if DEMO else '.'
CSV_PATH = os.path.join(DATA_DIR, 'processed_output.csv')

def signal_handler():
    """
    Graceful Exit Handler
    """
    print("Exiting gracefully...")
    app.quit()

# Register SIGINT handler (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)

# ------------------------------
# PyQtGraph Configuration
# ------------------------------
pg.setConfigOption('antialias', True)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# Data storage: 8 groups, 6 traces per group.
data = [[collections.deque(maxlen=5000) for _ in range(6)] for _ in range(8)]

# Load CSV data.
df = pd.read_csv(CSV_PATH)
n_rows = df.shape[0]

# ------------------------------
# Set Up PyQt Application & UI
# ------------------------------
app = QtWidgets.QApplication(sys.argv)

# Create main window.
main_window = QtWidgets.QWidget()
main_layout = QtWidgets.QVBoxLayout(main_window)

trace_colors = ["red", "lightcoral", "green", "lightgreen", "blue", "lightblue"]
trace_labels = ["D1_hbo", "D1_hbr", "D2_hbo", "D2_hbr", "D3_hbo", "D3_hbr"]

top_layout = QtWidgets.QHBoxLayout()
top_layout.addStretch()
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

# Create a GraphicsLayoutWidget for 8 subplots.
win = pg.GraphicsLayoutWidget(title="Real-Time mBLL Data")
win.resize(1200, 800)
plots = []
curves = []  # curves[group][trace]
for group in range(8):
    p = win.addPlot(title=f"Group {group+1}")
    p.showGrid(x=True, y=True, alpha=0.3)
    p.setLabel('bottom', 'Time (s)')
    group_curves = []
    for trace in range(6):
        pen = pg.mkPen(color=trace_colors[trace], width=2)
        curve = p.plot(pen=pen)
        group_curves.append(curve)
    plots.append(p)
    curves.append(group_curves)
    if group % 2 == 1:
        win.nextRow()
main_layout.addWidget(win)

# ------------------------------
# Streaming Simulation from CSV
# ------------------------------
CURRENT_INDEX = 0

def update():
    """
    Update the plots with new data from the CSV file.
    This function reads the next row from the CSV file and updates the plots.
    """
    global CURRENT_INDEX
    if CURRENT_INDEX < n_rows:
        row = df.iloc[CURRENT_INDEX]
        for group in range(8):
            start_idx = 1 + group * 6
            group_values = []
            for j in range(6):
                group_values.append(row.iloc[start_idx + j])
            # Append the values for each trace in this group.
            for trace in range(6):
                data[group][trace].append(group_values[trace])
        CURRENT_INDEX += 1

        # Update each subplot.
        for group in range(8):
            x = list(df["Time"].iloc[:len(data[group][0])])
            for trace in range(6):
                curves[group][trace].setData(x, list(data[group][trace]))
    else:
        # Once all rows are rendered, stop the timer and quit.
        timer.stop()
        app.quit()

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(100)  # Update every 100 ms; adjust as needed.

# ------------------------------
# Run the Application in Full Screen
# ------------------------------
main_window.showFullScreen()
sys.exit(app.exec_())
