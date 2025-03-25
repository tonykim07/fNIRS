# import sys
# import threading
# import time
# import struct
# import numpy as np
# import serial

# from PyQt5 import QtWidgets, QtCore
# import pyqtgraph as pg

# SERIAL_PORT = '/dev/tty.usbmodem205D388A47311'  # Adjust if needed
# BAUD_RATE   = 115200
# PACKET_SIZE = 64
# NOISE_LEVEL = 2050

# ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01)

# def parse_packet(data):
#     """
#     Parses 64 raw bytes into an 8×5 array of sensor data:
#     [group_id, inv_short, inv_long1, inv_long2, emitter].
#     Each group is 8 bytes:
#       [0]: group_id
#       [1..2]: short
#       [3..4]: long1
#       [5..6]: long2
#       [7]: emitter
#     We invert each channel: inv_val = 2*NOISE_LEVEL - raw_val.
#     """
#     parsed_data = np.zeros((8, 5), dtype=int)
#     for i in range(8):
#         offset = i * 8
#         group_id = data[offset]
#         raw_short = struct.unpack('>H', data[offset+1:offset+3])[0]
#         raw_long1 = struct.unpack('>H', data[offset+3:offset+5])[0]
#         raw_long2 = struct.unpack('>H', data[offset+5:offset+7])[0]
#         emitter   = data[offset+7]
#         inv_short = 2 * NOISE_LEVEL - raw_short
#         inv_long1 = 2 * NOISE_LEVEL - raw_long1
#         inv_long2 = 2 * NOISE_LEVEL - raw_long2
#         parsed_data[i] = [group_id, inv_short, inv_long1, inv_long2, emitter]
#     return parsed_data

# class SerialReaderThread(QtCore.QThread):
#     newData = QtCore.pyqtSignal(np.ndarray)
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.running = True
#     def run(self):
#         read_buffer = b""
#         while self.running:
#             chunk = ser.read(256)
#             if chunk:
#                 read_buffer += chunk
#                 while len(read_buffer) >= PACKET_SIZE:
#                     packet = read_buffer[:PACKET_SIZE]
#                     read_buffer = read_buffer[PACKET_SIZE:]
#                     arr_8x5 = parse_packet(packet)
#                     self.newData.emit(arr_8x5)
#             time.sleep(0.0005)
#     def stop(self):
#         self.running = False

# class MainWindow(QtWidgets.QWidget):
#     def __init__(self):
#         super().__init__()

#         # Keep standard CPU-based rendering (no OpenGL)
#         # pg.setConfigOption('useOpenGL', True)  # Omitted
#         pg.setConfigOption('antialias', False)
#         pg.setConfigOption('background', 'w')
#         pg.setConfigOption('foreground', 'k')

#         self.setWindowTitle("8 Groups × 3 Channels (No OpenGL, Low Latency)")

#         layout = QtWidgets.QVBoxLayout(self)
#         self.setLayout(layout)

#         # We'll hold 8 groups, each with 3 channels
#         self.max_points = 1000
#         self.data = [[[ ] for _ in range(3)] for _ in range(8)]

#         self.plot_widget = pg.GraphicsLayoutWidget()
#         layout.addWidget(self.plot_widget)

#         self.plots = []
#         self.curves = []

#         self.trace_colors = [pg.mkPen('r', width=2),
#                              pg.mkPen('g', width=2),
#                              pg.mkPen('b', width=2)]

#         # Create 8 subplots
#         for g in range(8):
#             p = self.plot_widget.addPlot(title=f"Group {g}")
#             p.showGrid(x=True, y=True)
#             p.setYRange(0, 4095, padding=0)
#             p.disableAutoRange()
#             group_curves = []
#             for ch_idx in range(3):
#                 c = p.plot(pen=self.trace_colors[ch_idx])
#                 group_curves.append(c)
#             self.curves.append(group_curves)
#             self.plots.append(p)
#             if g % 2 == 1:
#                 self.plot_widget.nextRow()

#         # 20 FPS timer
#         self.timer = QtCore.QTimer()
#         self.timer.timeout.connect(self.update_plots)
#         self.timer.start(50)

#         # We'll skip every 2 points to reduce overhead
#         self.skip = 2

#     @QtCore.pyqtSlot(np.ndarray)
#     def on_new_data(self, arr_8x5):
#         # arr_8x5.shape => (8, 5)
#         # row = [group_id, inv_short, inv_long1, inv_long2, emitter]
#         for g in range(8):
#             short_val = arr_8x5[g][1]
#             long1_val = arr_8x5[g][2]
#             long2_val = arr_8x5[g][3]
#             self.data[g][0].append(short_val)
#             self.data[g][1].append(long1_val)
#             self.data[g][2].append(long2_val)
#             for ch_idx in range(3):
#                 if len(self.data[g][ch_idx]) > self.max_points:
#                     self.data[g][ch_idx].pop(0)

#     def update_plots(self):
#         for g in range(8):
#             for ch_idx in range(3):
#                 d = self.data[g][ch_idx]
#                 if d:
#                     d_thinned = d[::self.skip]
#                     x_thinned = range(len(d_thinned))
#                     self.curves[g][ch_idx].setData(x_thinned, d_thinned)

# def main():
#     app = QtWidgets.QApplication(sys.argv)
#     window = MainWindow()
#     window.show()

#     reader_thread = SerialReaderThread()
#     reader_thread.newData.connect(window.on_new_data)
#     reader_thread.start()

#     def on_quit():
#         reader_thread.stop()
#         reader_thread.wait()

#     app.aboutToQuit.connect(on_quit)
#     sys.exit(app.exec_())

# if __name__ == '__main__':
#     main()

import sys
import struct
import numpy as np
import serial

from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

SERIAL_PORT = '/dev/tty.usbmodem205D388A47311'
BAUD_RATE = 115200
PACKET_SIZE = 64
NOISE_LEVEL = 2050
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01)

def parse_packet(data):
    parsed_data = np.zeros((8, 5), dtype=int)
    for i in range(8):
        offset = i * 8
        group_id = data[offset]
        raw_short = struct.unpack('>H', data[offset+1:offset+3])[0]
        raw_long1 = struct.unpack('>H', data[offset+3:offset+5])[0]
        raw_long2 = struct.unpack('>H', data[offset+5:offset+7])[0]
        emitter   = data[offset+7]
        inv_short = 2 * NOISE_LEVEL - raw_short
        inv_long1 = 2 * NOISE_LEVEL - raw_long1
        inv_long2 = 2 * NOISE_LEVEL - raw_long2
        parsed_data[i] = [group_id, inv_short, inv_long1, inv_long2, emitter]
    return parsed_data

class SerialReaderThread(QtCore.QThread):
    newData = QtCore.pyqtSignal(np.ndarray)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
    def run(self):
        read_buffer = b""
        while self.running:
            chunk = ser.read(256)
            if chunk:
                read_buffer += chunk
                while len(read_buffer) >= PACKET_SIZE:
                    packet = read_buffer[:PACKET_SIZE]
                    read_buffer = read_buffer[PACKET_SIZE:]
                    arr_8x5 = parse_packet(packet)
                    self.newData.emit(arr_8x5)
            # small sleep to avoid busy loop
            QtCore.QThread.msleep(1)
    def stop(self):
        self.running = False

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.setWindowTitle("PushButton: Reset All Plots")

        main_layout = QtWidgets.QVBoxLayout(self)

        # Top buttons layout
        button_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(button_layout)

        # "Reset All" pushbutton
        self.btn_reset = QtWidgets.QPushButton("Reset All")
        self.btn_reset.clicked.connect(self.reset_plots)
        button_layout.addWidget(self.btn_reset)

        # We'll store data for 8 groups × 3 channels
        self.max_points = 1000
        self.data = [[[ ] for _ in range(3)] for _ in range(8)]

        self.plot_widget = pg.GraphicsLayoutWidget()
        main_layout.addWidget(self.plot_widget)

        self.plots = []
        self.curves = []
        self.trace_colors = [pg.mkPen('r', width=2),
                             pg.mkPen('g', width=2),
                             pg.mkPen('b', width=2)]

        # Create 8 subplots
        for g in range(8):
            p = self.plot_widget.addPlot(title=f"Group {g}")
            p.showGrid(x=True, y=True)
            p.setYRange(0, 4095, padding=0)
            p.disableAutoRange()
            group_curves = []
            for ch_idx in range(3):
                c = p.plot(pen=self.trace_colors[ch_idx])
                group_curves.append(c)
            self.curves.append(group_curves)
            self.plots.append(p)
            if g % 2 == 1:
                self.plot_widget.nextRow()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(50)

    @QtCore.pyqtSlot(np.ndarray)
    def on_new_data(self, arr_8x5):
        
        for g in range(8):
            short_val = arr_8x5[g][1]
            long1_val = arr_8x5[g][2]
            long2_val = arr_8x5[g][3]
            self.data[g][0].append(short_val)
            self.data[g][1].append(long1_val)
            self.data[g][2].append(long2_val)
            for ch_idx in range(3):
                if len(self.data[g][ch_idx]) > self.max_points:
                    self.data[g][ch_idx].pop(0)
        
    def update_plots(self):
        skip = 2
        for g in range(8):
            for ch_idx in range(1):
                d = self.data[g][ch_idx]
                if d:
                    y_thinned = d[::skip]
                    x_thinned = range(len(y_thinned))
                    self.curves[g][ch_idx].setData(x_thinned, y_thinned)

    def reset_plots(self):
        # Clear data arrays
        self.data = [[[ ] for _ in range(3)] for _ in range(8)]
        # Immediately refresh to show empty
        for g in range(8):
            for ch_idx in range(3):
                self.curves[g][ch_idx].setData([])

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()

    reader_thread = SerialReaderThread()
    reader_thread.newData.connect(window.on_new_data)
    reader_thread.start()

    def on_quit():
        reader_thread.stop()
        reader_thread.wait()

    app.aboutToQuit.connect(on_quit)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
