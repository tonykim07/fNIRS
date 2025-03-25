import sys
import threading
import time
import struct
import numpy as np
import serial
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

SERIAL_PORT = '/dev/tty.usbmodem205D388A47311'
BAUD_RATE   = 115200
PACKET_SIZE = 64
NOISE_LEVEL = 2050

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01)

def parse_packet(data):
    """
    Parses 64 raw bytes into an 8×5 array of sensor data:
      [group_id, inv_short, inv_long1, inv_long2, emitter].
    Each group is 8 bytes:
      Byte0 => group_id
      Bytes1..2 => short
      Bytes3..4 => long1
      Bytes5..6 => long2
      Byte7 => emitter
    We do inv_val = 2*NOISE_LEVEL - raw_val for each channel.
    """
    parsed_data = np.zeros((8, 5), dtype=int)
    for i in range(8):
        offset = i * 8
        group_id = data[offset]
        raw_short = struct.unpack('>H', data[offset+1:offset+3])[0]
        raw_long1 = struct.unpack('>H', data[offset+3:offset+5])[0]
        raw_long2 = struct.unpack('>H', data[offset+5:offset+7])[0]
        emitter = data[offset+7]
        inv_short = 2*NOISE_LEVEL - raw_short
        inv_long1 = 2*NOISE_LEVEL - raw_long1
        inv_long2 = 2*NOISE_LEVEL - raw_long2
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
            time.sleep(0.001)
    def stop(self):
        self.running = False

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.setWindowTitle("Single Plot: Group 0 (Short, Long1, Long2)")

        layout = QtWidgets.QVBoxLayout(self)

        # We'll only store group 0's three channels:
        # data[0] => short, data[1] => long1, data[2] => long2
        self.max_points = 1000
        self.data = [[], [], []]

        self.plot_widget = pg.GraphicsLayoutWidget()
        layout.addWidget(self.plot_widget)

        # Single plot for group 0 (3 lines)
        self.plot = self.plot_widget.addPlot(title="Group 0 Channels")
        self.plot.showGrid(x=True, y=True)
        self.plot.setLabel('left', 'ADC Inverted')
        self.plot.setYRange(0, 4095, padding=0)
        self.plot.disableAutoRange()

        # Three curves on one plot
        pens = [pg.mkPen('r', width=2),
                pg.mkPen('g', width=2),
                pg.mkPen('b', width=2)]
        self.curves = []
        for pen in pens:
            c = self.plot.plot(pen=pen)
            self.curves.append(c)

        self.setLayout(layout)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)

    @QtCore.pyqtSlot(np.ndarray)
    def on_new_data(self, arr_8x5):
        """
        arr_8x5 => shape (8, 5).
        arr_8x5[0] => group 0: [group_id, short_inv, long1_inv, long2_inv, emitter].
        We'll take columns 1..3 => short_inv, long1_inv, long2_inv.
        """
        g1 = arr_8x5[1]
        short_val = g1[1]
        long1_val = g1[2]
        long2_val = g1[3]

        self.data[0].append(short_val)
        self.data[1].append(long1_val)
        self.data[2].append(long2_val)

        for i in range(3):
            if len(self.data[i]) > self.max_points:
                self.data[i].pop(0)

    def update_plot(self):
        for ch_idx in range(3):
            ydata = self.data[ch_idx]
            xdata = range(len(ydata))
            self.curves[ch_idx].setData(xdata, ydata)

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
