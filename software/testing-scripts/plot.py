
import pandas as pd
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtGui, QtCore
from PyQt5.QtGui import QColor
import sys

# -------- Theme: Light Background --------
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# -------- Load Data --------
adc_df = pd.read_csv("all_groups.csv")
processed_df = pd.read_csv("processed_output.csv")

adc_color = QtGui.QColor(109, 36, 122)
# ΔHbO color: 111199234 → #69B3E2
hbo_color = QtGui.QColor(0, 127, 163)

# ΔHbR color: 2207051 → #21A5FB
hbr_color = QtGui.QColor(220, 70, 51)

# -------- PyQt Application --------
app = QtWidgets.QApplication(sys.argv)
win = pg.GraphicsLayoutWidget(show=True, title="ADC and Beer-Lambert Data Visualization")
win.resize(1200, 700)
win.setWindowTitle('ADC and Beer-Lambert Plots')

# -------- Styles --------
title_style = {'color': 'k', 'size': '25pt'}

# Axis label font
axis_label_font = QtGui.QFont()
axis_label_font.setPointSize(50)

# Bold dashed vertical line style
bold_line_pen = pg.mkPen(color='k', style=QtCore.Qt.DashLine, width=4)

# Big, bold legend font
legend_font = QtGui.QFont()
legend_font.setPointSize(22)
legend_font.setBold(True)

# ------------------- Plot 1: ADC Reading -------------------
adc_plot = win.addPlot(row=1, col=1)
adc_plot.setTitle("1) Digitalized Sensor Data", **title_style)

# Line color: 10936122 → #A6CEE3
adc_curve = adc_plot.plot(adc_df['Time (s)'], adc_df['G7_Long1'], pen=pg.mkPen(adc_color, width=3), name='G7_Long1')

# Vertical dashed lines
adc_plot.addItem(pg.InfiniteLine(pos=20, angle=90, pen=bold_line_pen))
adc_plot.addItem(pg.InfiniteLine(pos=40, angle=90, pen=bold_line_pen))

# Legend
adc_legend = pg.LegendItem(offset=(70, 20))
adc_legend.setParentItem(adc_plot.graphicsItem())
adc_legend.setFont(legend_font)
adc_legend.layout.setSpacing(20)
adc_legend.setMaximumSize(300, 150)
adc_legend.addItem(adc_curve, 'G7_Long1')

# External axis labels

adc_y_label = pg.LabelItem("ADC Value", angle=-90, justify='center')
adc_y_label.setFont(axis_label_font)
win.addItem(adc_y_label, row=1, col=0)

adc_x_label = pg.LabelItem("Time (s)", justify='center')
adc_x_label.setFont(axis_label_font)
win.addItem(adc_x_label, row=2, col=1)

# ------------------- Plot 2: ΔHbO and ΔHbR -------------------
bl_plot = win.addPlot(row=4, col=1)
# bl_plot.setTitle("2) ΔHbO and ΔHbR", **title_style)


hbo_curve = bl_plot.plot(processed_df['Time'], processed_df['S8_D2_hbo'], pen=pg.mkPen(hbo_color, width=3), name='ΔHbO')
hbr_curve = bl_plot.plot(processed_df['Time'], processed_df['S8_D2_hbr'], pen=pg.mkPen(hbr_color, width=3), name='ΔHbR')

# Vertical dashed lines
bl_plot.addItem(pg.InfiniteLine(pos=20, angle=90, pen=bold_line_pen))
bl_plot.addItem(pg.InfiniteLine(pos=40, angle=90, pen=bold_line_pen))

# Legend
bl_legend = pg.LegendItem(offset=(70, 20))
bl_legend.setParentItem(bl_plot.graphicsItem())
bl_legend.setFont(legend_font)
bl_legend.layout.setSpacing(20)
bl_legend.setMaximumSize(300, 150)
bl_legend.addItem(hbo_curve, 'ΔHbO')
bl_legend.addItem(hbr_curve, 'ΔHbR')

# External axis labels
bl_y_label = pg.LabelItem("Concentration Change (Molar)", angle=-90, justify='center')
bl_y_label.setFont(axis_label_font)
win.addItem(bl_y_label, row=4, col=0)

bl_x_label = pg.LabelItem("Time (s)", justify='center')
bl_x_label.setFont(axis_label_font)
win.addItem(bl_x_label, row=5, col=1)

# ------------------- Run App -------------------
if __name__ == '__main__':
    QtWidgets.QApplication.instance().exec_()