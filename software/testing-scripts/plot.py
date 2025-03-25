# # import pandas as pd
# # import pyqtgraph as pg
# # from pyqtgraph.Qt import QtWidgets, QtGui, QtCore
# # from PyQt5.QtGui import QColor
# # import sys

# # # -------- Theme: Light Background --------
# # pg.setConfigOption('background', 'w')
# # pg.setConfigOption('foreground', 'k')

# # # -------- Load Data --------
# # adc_df = pd.read_csv("all_groups.csv")
# # processed_df = pd.read_csv("processed_output.csv")

# # # -------- PyQt Application --------
# # app = QtWidgets.QApplication(sys.argv)
# # win = pg.GraphicsLayoutWidget(show=True, title="ADC and Beer-Lambert Data Visualization")
# # win.resize(1200, 700)
# # win.setWindowTitle('ADC and Beer-Lambert Plots')

# # # -------- Styles --------
# # title_style = {'color': 'k', 'size': '20pt'}

# # # Axis label font
# # axis_label_font = QtGui.QFont()
# # axis_label_font.setPointSize(20)

# # # Bold dashed vertical line style
# # bold_line_pen = pg.mkPen(color='k', style=QtCore.Qt.DashLine, width=4)

# # # Big, bold legend font
# # legend_font = QtGui.QFont()
# # legend_font.setPointSize(40)  # ⬅️ Bump up the legend font
# # legend_font.setBold(True)

# # # ------------------- Plot 1: ADC Reading -------------------
# # adc_plot = win.addPlot(row=1, col=1)
# # adc_plot.setTitle("1) Digitalized Sensor Data", **title_style)

# # # Line color: 10936122 → #A6CEE3
# # adc_color = QtGui.QColor(109, 36, 122)
# # adc_curve = adc_plot.plot(adc_df['Time (s)'], adc_df['G0_Short'], width=, pen=adc_color, name='G0_Short')

# # # Vertical dashed lines
# # adc_plot.addItem(pg.InfiniteLine(pos=20, angle=90, pen=bold_line_pen))
# # adc_plot.addItem(pg.InfiniteLine(pos=40, angle=90, pen=bold_line_pen))

# # # Legend
# # adc_legend = pg.LegendItem(offset=(70, 20))
# # adc_legend.setParentItem(adc_plot.graphicsItem())
# # adc_legend.setFont(legend_font)
# # adc_legend.layout.setSpacing(10)
# # adc_legend.addItem(adc_curve, 'G0_Short')

# # # External axis labels
# # adc_y_label = pg.LabelItem("1) Digitalized Sensor Data", angle=-90, justify='center')
# # adc_y_label.setFont(axis_label_font)
# # win.addItem(adc_y_label, row=1, col=0)

# # adc_x_label = pg.LabelItem("Time (s)", justify='center')
# # adc_x_label.setFont(axis_label_font)
# # win.addItem(adc_x_label, row=2, col=1)

# # # ------------------- Plot 2: ΔHbO and ΔHbR -------------------
# # bl_plot = win.addPlot(row=4, col=1)
# # bl_plot.setTitle("2) ΔHbO and ΔHbR", **title_style)


# # adc_color = QtGui.QColor(109, 36, 122)
# # # ΔHbO color: 111199234 → #69B3E2
# # hbo_color = QtGui.QColor(0, 127, 163)

# # # ΔHbR color: 2207051 → #21A5FB
# # hbr_color = QtGui.QColor(220, 70, 51)

# # hbo_curve = bl_plot.plot(processed_df['Time'], processed_df['S1_D1_hbo'], width=5, pen=hbo_color, name='ΔHbO')
# # hbr_curve = bl_plot.plot(processed_df['Time'], processed_df['S1_D1_hbr'], width=5, pen=hbr_color, name='ΔHbR')

# # # Vertical dashed lines
# # bl_plot.addItem(pg.InfiniteLine(pos=20, angle=90, pen=bold_line_pen))
# # bl_plot.addItem(pg.InfiniteLine(pos=40, angle=90, pen=bold_line_pen))

# # # Legend
# # bl_legend = pg.LegendItem(offset=(70, 20))
# # bl_legend.setParentItem(bl_plot.graphicsItem())
# # bl_legend.setFont(legend_font)
# # bl_legend.layout.setSpacing(10)
# # bl_legend.addItem(hbo_curve, 'ΔHbO')
# # bl_legend.addItem(hbr_curve, 'ΔHbR')

# # # External axis labels
# # bl_y_label = pg.LabelItem("Concentration Change", angle=-90, justify='center')
# # bl_y_label.setFont(axis_label_font)
# # win.addItem(bl_y_label, row=4, col=0)

# # bl_x_label = pg.LabelItem("Time (s)", justify='center')
# # bl_x_label.setFont(axis_label_font)
# # win.addItem(bl_x_label, row=5, col=1)

# # # ------------------- Run App -------------------
# # if __name__ == '__main__':
# #     QtWidgets.QApplication.instance().exec_()






# import pandas as pd
# import pyqtgraph as pg
# from pyqtgraph.Qt import QtWidgets, QtGui, QtCore
# from PyQt5.QtGui import QColor
# import sys

# # -------- Theme: Light Background --------
# pg.setConfigOption('background', 'w')
# pg.setConfigOption('foreground', 'k')

# # -------- Load Data --------
# adc_df = pd.read_csv("all_groups.csv")
# processed_df = pd.read_csv("processed_output.csv")

# adc_color = QtGui.QColor(109, 36, 122)
# # ΔHbO color: 111199234 → #69B3E2
# hbo_color = QtGui.QColor(0, 127, 163)

# # ΔHbR color: 2207051 → #21A5FB
# hbr_color = QtGui.QColor(220, 70, 51)

# # -------- PyQt Application --------
# app = QtWidgets.QApplication(sys.argv)
# win = pg.GraphicsLayoutWidget(show=True, title="ADC and Beer-Lambert Data Visualization")
# win.resize(1200, 700)
# win.setWindowTitle('ADC and Beer-Lambert Plots')

# # -------- Styles --------
# title_style = {'color': 'k', 'size': '25pt'}


# # Axis label font
# axis_label_font = QtGui.QFont()
# axis_label_font.setPointSize(50)


# # Bold dashed vertical line style
# bold_line_pen = pg.mkPen(color='k', style=QtCore.Qt.DashLine, width=4)

# # Big, bold legend font
# legend_font = QtGui.QFont()
# legend_font.setPointSize(22)
# legend_font.setBold(True)

# # ------------------- Plot 1: ADC Reading -------------------
# adc_plot = win.addPlot(row=1, col=1)
# adc_plot.setTitle("1) Digitalized Sensor Data", **title_style)

# # Line color: 10936122 → #A6CEE3
# adc_curve = adc_plot.plot(adc_df['Time (s)'], adc_df['G0_Short'], pen=pg.mkPen(adc_color, width=3), name='G0_Short')

# # Vertical dashed lines
# adc_plot.addItem(pg.InfiniteLine(pos=20, angle=90, pen=bold_line_pen))
# adc_plot.addItem(pg.InfiniteLine(pos=40, angle=90, pen=bold_line_pen))

# # Legend
# adc_legend = pg.LegendItem(offset=(70, 20))
# adc_legend.setParentItem(adc_plot.graphicsItem())
# adc_legend.setFont(legend_font)
# adc_legend.layout.setSpacing(20)
# adc_legend.setMaximumSize(300, 150)
# adc_legend.addItem(adc_curve, 'G0_Short')

# # External axis labels

# adc_y_label = pg.LabelItem("ADC Value", angle=-90, justify='center')
# adc_y_label.setFont(axis_label_font)
# win.addItem(adc_y_label, row=1, col=0)

# adc_x_label = pg.LabelItem("Time (s)", justify='center')
# adc_x_label.setFont(axis_label_font)
# win.addItem(adc_x_label, row=2, col=1)

# # ------------------- Plot 2: ΔHbO and ΔHbR -------------------
# bl_plot = win.addPlot(row=4, col=1)
# # bl_plot.setTitle("2) ΔHbO and ΔHbR", **title_style)


# hbo_curve = bl_plot.plot(processed_df['Time'], processed_df['S1_D1_hbo'], pen=pg.mkPen(hbo_color, width=3), name='ΔHbO')
# hbr_curve = bl_plot.plot(processed_df['Time'], processed_df['S1_D1_hbr'], pen=pg.mkPen(hbr_color, width=3), name='ΔHbR')

# # Vertical dashed lines
# bl_plot.addItem(pg.InfiniteLine(pos=20, angle=90, pen=bold_line_pen))
# bl_plot.addItem(pg.InfiniteLine(pos=40, angle=90, pen=bold_line_pen))

# # Legend
# bl_legend = pg.LegendItem(offset=(70, 20))
# bl_legend.setParentItem(bl_plot.graphicsItem())
# bl_legend.setFont(legend_font)
# bl_legend.layout.setSpacing(20)
# bl_legend.setMaximumSize(300, 150)
# bl_legend.addItem(hbo_curve, 'ΔHbO')
# bl_legend.addItem(hbr_curve, 'ΔHbR')

# # External axis labels
# bl_y_label = pg.LabelItem("Concentration Change (Molar)", angle=-90, justify='center')
# bl_y_label.setFont(axis_label_font)
# win.addItem(bl_y_label, row=4, col=0)

# bl_x_label = pg.LabelItem("Time (s)", justify='center')
# bl_x_label.setFont(axis_label_font)
# win.addItem(bl_x_label, row=5, col=1)

# # ------------------- Run App -------------------
# if __name__ == '__main__':
#     QtWidgets.QApplication.instance().exec_()

import sys
import threading
import time
import struct
import numpy as np
import serial

from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

##############################
# 1) CONFIG & SERIAL SETUP
##############################

# Adjust these as needed:
SERIAL_PORT = '/dev/tty.usbmodem205D388A47311'
BAUD_RATE   = 115200
PACKET_SIZE = 64

# Each packet:
#   [0] Group ID
#   [1..2] ShortVal (big-endian)
#   [3..4] Long1Val (big-endian)
#   [5..6] Long2Val (big-endian)
#   [7] Emitter status

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01)

# NOISE_LEVEL used for your inversion logic
NOISE_LEVEL = 2050

##############################
# 2) PARSING LOGIC (with inversion)
##############################
def parse_64_byte_packet(packet):
    """
    Convert 64 bytes -> 8 groups -> each group has [GroupID, Short, Long1, Long2, Emitter].
    We then apply: inverted_val = 2*NOISE_LEVEL - raw_val for each Short/Long1/Long2.
    
    Final array: 24 elements [g0_short_inv, g0_long1_inv, g0_long2_inv, g1_short_inv, ..., g7_long2_inv].
    """
    sensor_values = np.zeros(24, dtype=int)
    for i in range(8):
        offset = i * 8
        # group_id       = packet[offset]
        # emitter_status = packet[offset + 7]  # not used in final array

        short_val = struct.unpack('>H', packet[offset+1:offset+3])[0]
        long1_val = struct.unpack('>H', packet[offset+3:offset+5])[0]
        long2_val = struct.unpack('>H', packet[offset+5:offset+7])[0]

        # Apply the inversion
        short_inv = 2 * NOISE_LEVEL - short_val
        long1_inv = 2 * NOISE_LEVEL - long1_val
        long2_inv = 2 * NOISE_LEVEL - long2_val

        sensor_values[i*3 : i*3+3] = [short_inv, long1_inv, long2_inv]

    return sensor_values

##############################
# 3) READING THREAD
##############################
class SerialReaderThread(QtCore.QThread):
    """
    A QThread that continually reads serial data in chunks,
    ensuring each 64-byte packet is parsed, then emits the 
    24 inverted integers for plotting.
    """
    newData = QtCore.pyqtSignal(np.ndarray)  # 24-element NumPy array, inverted

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True

    def run(self):
        read_buffer = b""
        while self.running:
            # Read up to 256 bytes from serial
            chunk = ser.read(256)
            if chunk:
                read_buffer += chunk

                # Parse each full 64-byte frame
                while len(read_buffer) >= PACKET_SIZE:
                    packet = read_buffer[:PACKET_SIZE]
                    read_buffer = read_buffer[PACKET_SIZE:]
                    
                    parsed_vals = parse_64_byte_packet(packet)
                    self.newData.emit(parsed_vals)

            # Avoid maxing out CPU
            time.sleep(0.001)

    def stop(self):
        self.running = False


##############################
# 4) MAIN GUI APPLICATION
##############################
class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # ---------- Setup PyQtGraph Config ----------
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.setWindowTitle("Real-Time Inverted ADC Plot")

        layout = QtWidgets.QVBoxLayout(self)

        # We'll store the "G0 Short Inverted" data for demonstration
        self.g0_short_data = []
        self.max_points = 2000  # keep last 2000 points

        # Create the plotting widget
        self.plot_widget = pg.GraphicsLayoutWidget()
        layout.addWidget(self.plot_widget)

        self.adc_plot = self.plot_widget.addPlot(title="Group0 Short (Inverted)")
        self.adc_plot.showGrid(x=True, y=True)
        self.adc_plot.setLabel('bottom', 'Sample Index')
        self.adc_plot.setLabel('left', 'Inverted ADC Value')
        self.adc_curve = self.adc_plot.plot(pen=pg.mkPen(color='b', width=2))

        # Timer to refresh the plot
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)  # ~20 FPS

    @QtCore.pyqtSlot(np.ndarray)
    def on_new_data(self, parsed_array):
        """
        parsed_array is a 24-element array of inverted values:
          [g0_short_inv, g0_long1_inv, g0_long2_inv, g1_short_inv, ...].
        We'll only plot G0 short (index 0).
        """
        g0_short_inv = parsed_array[0]
        self.g0_short_data.append(g0_short_inv)
        # Keep the list from growing indefinitely
        if len(self.g0_short_data) > self.max_points:
            self.g0_short_data.pop(0)

    def update_plot(self):
        x_vals = range(len(self.g0_short_data))
        self.adc_curve.setData(x_vals, self.g0_short_data)


##############################
# 5) ENTRY POINT
##############################
def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # Start the serial reading thread
    reader_thread = SerialReaderThread()
    reader_thread.newData.connect(window.on_new_data)
    reader_thread.start()

    # Cleanup on close
    def cleanup():
        reader_thread.stop()
        reader_thread.wait()

    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
