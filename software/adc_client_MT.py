import sys
import collections
import signal
import socketio
import numpy as np

from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

class SocketWorker(QtCore.QObject):
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

        @self._sio.on('batched_data')
        def on_batched_data(message):
            
            arrays = message.get('arrays', [])
            if arrays:
                self.batchedDataReceived.emit(arrays)

    @QtCore.pyqtSlot()
    def run(self):
        try:
            self._sio.connect(self._server_url)
            while not self._stop_flag:
                self._sio.sleep(0.01)
        except Exception as e:
            print(f"[SocketWorker] Could not connect: {e}")

        if self._sio.connected:
            self._sio.disconnect()

    def stop(self):
        self._stop_flag = True

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        pg.setConfigOption('antialias', False)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.setWindowTitle("Socket.IO Client: 8×5 Arrays from Server")
        layout = QtWidgets.QVBoxLayout(self)

        self.max_points = 1000
        # We'll store 8 groups × 3 channels => inv_short, inv_long1, inv_long2
        self.data = [[collections.deque(maxlen=self.max_points) for _ in range(3)] for _ in range(8)]

        self.plot_widget = pg.GraphicsLayoutWidget()
        layout.addWidget(self.plot_widget)

        self.plots = []
        self.curves = []

        self.trace_colors = [pg.mkPen('r', width=2),
                             pg.mkPen('g', width=2),
                             pg.mkPen('b', width=2)]

        for g in range(8):
            p = self.plot_widget.addPlot(title=f"Group {g}")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.setYRange(0, 4095, padding=0)
            p.disableAutoRange()
            group_curves = []
            for ch_idx in range(3):
                curve = p.plot(pen=self.trace_colors[ch_idx])
                group_curves.append(curve)
            self.curves.append(group_curves)
            self.plots.append(p)
            if g % 2 == 1:
                self.plot_widget.nextRow()

        self.setLayout(layout)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(10)

        self.skip = 6

    @QtCore.pyqtSlot(list)
    def on_batched_data_received(self, frames):
        """
        frames => list of 8×5 arrays, each row = [group_id, inv_short, inv_long1, inv_long2, emitter].
        We'll store just inv_short, inv_long1, inv_long2 for each group.
        """
        for arr_8x5 in frames:
            # arr_8x5 is effectively shape (8,5)
            # row i => [group_id, inv_short, inv_long1, inv_long2, emitter]
            # We'll store columns 1..3 in self.data[g][0..2].
            for g in range(8):
                inv_short = arr_8x5[g][1]
                inv_long1 = arr_8x5[g][2]
                inv_long2 = arr_8x5[g][3]
                self.data[g][0].append(inv_short)
                self.data[g][1].append(inv_long1)
                self.data[g][2].append(inv_long2)

    def update_plots(self):
        for g in range(8):
            for ch_idx in range(3):
                d = list(self.data[g][ch_idx])
                if d:
                    d_thinned = d[::self.skip]
                    x_thinned = range(len(d_thinned))
                    self.curves[g][ch_idx].setData(x_thinned, d_thinned)



def main():
    import signal
    def signal_handler(*args):
        print("Caught Ctrl+C, exiting.")
        QtWidgets.QApplication.quit()

    signal.signal(signal.SIGINT, signal_handler)

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()

    thread = QtCore.QThread()
    worker = SocketWorker('http://127.0.0.1:5000')
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
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
