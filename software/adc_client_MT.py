import sys
import collections
import signal
import socketio

from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

class SocketWorker(QtCore.QObject):
    """
    Worker object running in a separate thread, connecting to Socket.IO.
    We'll now listen for 'batched_data' events.
    """
    # We emit a list of *samples*, each sample being a list of 24 ints.
    batchedDataReceived = QtCore.pyqtSignal(list)  

    def __init__(self, server_url='http://127.0.0.1:5000'):
        super().__init__()
        self._sio = socketio.Client()
        self._server_url = server_url
        self._stop_flag = False

        @self._sio.event
        def connect():
            print("[SocketWorker] Connected to server.")

        @self._sio.event
        def disconnect():
            print("[SocketWorker] Disconnected from server.")

        # Our new batched event:
        @self._sio.on('batched_data')
        def on_batched_data(message):
            """
            message = {
                'arrays': [
                    [sample0_0, sample0_1, ..., sample0_23],
                    [sample1_0, sample1_1, ..., sample1_23],
                    ...
                ]
            }
            """
            arrays = message.get('arrays', [])
            if arrays:
                self.batchedDataReceived.emit(arrays)

    @QtCore.pyqtSlot()
    def run(self):
        """
        Connect to the Socket.IO server and let it run in a loop.
        We'll do a cooperative event loop using sio.sleep(...) so it
        doesn't block the entire thread.
        """
        try:
            self._sio.connect(self._server_url)
            while not self._stop_flag:
                self._sio.sleep(0.01)
        except Exception as e:
            print(f"[SocketWorker] Could not connect: {e}")

        # Cleanup
        if self._sio.connected:
            self._sio.disconnect()

    def stop(self):
        self._stop_flag = True

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        
        pg.setConfigOption('useOpenGL', True)
        pg.setConfigOption('antialias', False)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.setWindowTitle("Batched ADC Client")
        self.layout = QtWidgets.QVBoxLayout(self)

        # Data: 8 groups, 3 channels each
        self.data = [[collections.deque(maxlen=1500) for _ in range(3)] for _ in range(8)]

        # Plot legend
        top_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(top_layout)

        trace_colors = ["red", "green", "blue"]
        trace_labels = ["Channel 1", "Channel 2", "Channel 3"]
        legend_layout = QtWidgets.QHBoxLayout()
        for color, label in zip(trace_colors, trace_labels):
            lab = QtWidgets.QLabel()
            lab.setFixedSize(15, 15)
            lab.setStyleSheet(f"background-color: {color}; border: 1px solid black;")
            txt = QtWidgets.QLabel(label)
            row_layout = QtWidgets.QHBoxLayout()
            row_layout.addWidget(lab)
            row_layout.addWidget(txt)
            container = QtWidgets.QWidget()
            container.setLayout(row_layout)
            legend_layout.addWidget(container)
        legend_layout.addStretch()
        top_layout.addLayout(legend_layout)

        # Create a GraphicsLayoutWidget to hold the plots.
        self.win = pg.GraphicsLayoutWidget(title="Real-Time Sensor Data")
        self.layout.addWidget(self.win)

        self.plots = []
        self.curves = []
        for g in range(8):
            p = self.win.addPlot(title=f"Group {g+1}")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.enableAutoRange()
            p.setLabel('bottom', 'Sample Index')
            group_curves = []
            for c, color in enumerate(trace_colors):
                pen = pg.mkPen(color=color, width=2)
                curve = p.plot(pen=pen)
                group_curves.append(curve)
            self.plots.append(p)
            self.curves.append(group_curves)
            if g % 2 == 1:
                self.win.nextRow()

        # Timer for updating plots
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(50)  # ~20 fps

    @QtCore.pyqtSlot(list)  
    def on_batched_data_received(self, arrays):
        """
        We receive multiple samples at once.
        'arrays' is a list of 24-element arrays.

        We'll just append them all to self.data.
        """
        for sample in arrays:
            if len(sample) == 24:
                # Add one sample to data
                for group_idx in range(8):
                    group_values = sample[group_idx*3 : group_idx*3+3]
                    for trace_idx in range(3):
                        self.data[group_idx][trace_idx].append(group_values[trace_idx])

    def update_plots(self):
        """
        Periodically update the plots from self.data.
        """
        skip = 2  # Keep every 2nd point for speed
        for g in range(8):
            for t in range(3):
                d = list(self.data[g][t])
                if len(d) > 0:
                    d_thinned = d[::skip]
                    x_thinned = list(range(len(d_thinned)))
                    self.curves[g][t].setData(x_thinned, d_thinned)

def main():
    def signal_handler(*args):
        print("Caught Ctrl+C, exiting.")
        QtWidgets.QApplication.quit()

    signal.signal(signal.SIGINT, signal_handler)

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # Worker thread
    thread = QtCore.QThread()
    worker = SocketWorker()
    worker.moveToThread(thread)

    # Start the worker when the thread starts
    thread.started.connect(worker.run)
    # Connect batched data signal to the main window's slot
    worker.batchedDataReceived.connect(window.on_batched_data_received)

    def on_quit():
        print("[Main] Quitting: stopping worker...")
        worker.stop()
        thread.quit()
        thread.wait()

    app.aboutToQuit.connect(on_quit)

    thread.start()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
