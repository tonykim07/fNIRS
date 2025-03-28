# adc_live.py
import sys
import struct
import numpy as np
import serial
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
# from visualizer import ser  # shared serial connection

SERIAL_PORT = '/dev/tty.usbmodem205D388A47311'
BAUD_RATE = 9600
PACKET_SIZE = 64
NOISE_LEVEL = 2050
# ser is imported from visualizer.py

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01)

# Define colors and labels for the traces.
trace_colors = ["red", "green", "blue"]
trace_labels = ["Channel 1", "Channel 2", "Channel 3"]

def parse_packet(data):
    parsed_data = np.zeros((8, 5), dtype=int)
    for i in range(8):
        offset = i * 8
        group_id = data[offset]
        raw_short = struct.unpack('>H', data[offset+1:offset+3])[0]
        raw_long1 = struct.unpack('>H', data[offset+3:offset+5])[0]
        raw_long2 = struct.unpack('>H', data[offset+5:offset+7])[0]
        emitter   = data[offset+7]
        parsed_data[i] = [group_id, raw_short, raw_long1, raw_long2, emitter]
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
            QtCore.QThread.msleep(1)  # avoid busy waiting
    def stop(self):
        self.running = False

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        # Set up the global PyQtGraph appearance
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.setWindowTitle("ADC Live Mode")

        self.max_len = 0
        
        # Main vertical layout
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # Top horizontal layout for legend and Reset button
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addStretch()
        # Add legend items for each channel.
        for color, label in zip(trace_colors, trace_labels):
            legend_item = QtWidgets.QWidget()
            legend_layout = QtWidgets.QHBoxLayout(legend_item)
            legend_layout.setContentsMargins(0, 0, 0, 0)
            square = QtWidgets.QLabel()
            square.setFixedSize(15, 15)
            square.setStyleSheet(f"background-color: {color}; border: 1px solid black;")
            text_label = QtWidgets.QLabel(label)
            legend_layout.addWidget(square)
            legend_layout.addWidget(text_label)
            top_layout.addWidget(legend_item)
        
        # Add a Reset All button to the same top layout.
        btn_reset = QtWidgets.QPushButton("Reset All")
        btn_reset.clicked.connect(self.reset_plots)
        top_layout.addWidget(btn_reset)
        top_layout.addStretch()
        
        # Add the top layout (legend and button) to the main layout.
        main_layout.addLayout(top_layout)
        
        # Data storage: for 8 groups and 3 channels
        self.max_points = 3000
        self.data = [[[ ] for _ in range(3)] for _ in range(8)]
        
        # Create the plot widget.
        self.plot_widget = pg.GraphicsLayoutWidget(title="Live ADC Readings")
        self.plot_widget.resize(1200, 800)
        main_layout.addWidget(self.plot_widget)
        
        # Create plots and curves.
        self.plots = []
        self.curves = []
        self.pg_trace_colors = [pg.mkPen('r', width=2),
                                 pg.mkPen('g', width=2),
                                 pg.mkPen('b', width=2)]
        for g in range(8):
            p = self.plot_widget.addPlot()
            p.setTitle(f"Sensor Group {g+1}", size="16pt")  
            p.showGrid(x=True, y=True)
            p.setLabel('bottom', 'Time (ms)')
            p.setLabel('left', 'ADC Value')
            p.setYRange(0, 4095, padding=0)
            p.disableAutoRange()
            group_curves = []
            for ch_idx in range(3):
                c = p.plot(pen=self.pg_trace_colors[ch_idx])
                group_curves.append(c)
            self.plots.append(p)
            self.curves.append(group_curves)
            if g % 2 == 1:
                self.plot_widget.nextRow()
        
        # Timer to update plots.
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(50)

    @QtCore.pyqtSlot(np.ndarray)
    def on_new_data(self, arr_8x5):
        for g in range(8):
            self.data[g][0].append(arr_8x5[g][1])
            self.data[g][1].append(arr_8x5[g][2])
            self.data[g][2].append(arr_8x5[g][3])
            for ch_idx in range(3):
                if len(self.data[g][ch_idx]) > self.max_points:
                    self.data[g][ch_idx].pop(0)
        
    def update_plots(self):
        for g in range(8):
            for ch_idx in range(3):
                d = self.data[g][ch_idx]
                if d:
                    self.curves[g][ch_idx].setData(range(len(d)), d)
            self.plots[g].setYRange(0, 4095, padding=0)

    def reset_plots(self):
        self.data = [[[ ] for _ in range(3)] for _ in range(8)]
        for g in range(8):
            for ch_idx in range(3):
                self.curves[g][ch_idx].setData([])

def main():
    # Clear any previous data from the serial port.
    ser.reset_input_buffer()
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.showFullScreen()  # Launch GUI in full screen.
    reader_thread = SerialReaderThread()
    reader_thread.newData.connect(window.on_new_data)
    reader_thread.start()
    app.aboutToQuit.connect(lambda: (reader_thread.stop(), reader_thread.wait()))
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
