# fNIRS Software Design

This system is designed for real-time acquisition, processing, and visualization of fNIRS (functional Near-Infrared Spectroscopy) data. It features two operating modes:

1. **Live Readings Mode**  
   In this mode, only ADC (Analog-to-Digital Converter) data is captured in real time and visualized immediately. This mode is used for continuous monitoring and real-time plotting of raw sensor readings.

2. **Record & Visualize Mode**  
   In this mode, the system records data for a user-defined duration. The captured data is then processed through a series of post-processing steps (such as interleaving sensor blocks, converting intensities to optical density, applying MBLL, and CBSI). Both ADC and mBLL (processed) data are supported in this mode, and the final results are visualized interactively after processing is complete.


## Features

- **Two Operating Modes:**
  - **Live Readings Mode (ADC Only):**  
    - Captures raw ADC data in real time from the serial port.
    - Displays interactive, real-time plots for continuous monitoring.
  - **Record & Visualize Mode (ADC and mBLL):**  
    - Records data for a specified duration.
    - Processes recorded data using techniques such as interleaving mode blocks, OD conversion, MBLL, and CBSI.
    - Supports visualization of both raw ADC data and processed mBLL data.

- **Data Capture and Processing:**
  - Serial port communication for capturing sensor data.
  - CSV logging of raw ADC data (`all_groups.csv`) in a dedicated `data/` directory.
  - Post-processing pipeline that produces processed output (`processed_output.csv`).

- **Interactive Visualizations:**
  - **Static Plots with Plotly:**  
    - Eight separate interactive plots (one per sensor group) for ADC and mBLL modes.
    - Each plot includes its own legend and interactive mode bar (zoom, pan, full screen).
  - **Real-Time Animations:**  
    - Full-screen real-time animation windows (using PyQtGraph) for dynamic visualization.
  - **3D Brain Mesh Visualization:**  
    - A 3D interactive brain mesh with sensor node mapping and sensor group highlighting.

- **Download Functionality:**
  - Users can download CSV files with a custom file name via a popup prompt.

- **Demo Mode:**
  - When the system is started with a demo flag, it uses a mock ADC server and skips certain processing steps for demonstration purposes.

- **User-Friendly Interface:**
  - A web interface built with Bootstrap, jQuery, Plotly, and Socket.IO.
  - Control panels for sensor group selection, MUX/emitter control, and mode selection.
  - Ability to view individual plots in a modal (or new window) for detailed analysis.

## Setup Instructions

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/tonykim07/fNIRS.git
   cd software
   ```

2. **Set Up a Virtual Environment and Install Dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate      # On Windows: venv\Scripts\activate
   pip install -r requirements.txt 
   ```

3. **Running the System:**

    ___Normal Mode (requires connection to serial port)___ 

    ```bash
    python visualizer.py
    ```

    ___Demo Mode___
    ```bash
    python visualizer.py demo
    ```
    Then open your browser at http://localhost:8050 to access the interface.

## Usage Overview

### Select Operating Mode
- **Live Readings (ADC Only):**  
  Choose this option for real-time data visualization.
- **Record & Visualize:**  
  Choose this option to record data (supporting ADC and/or mBLL), then process and visualize the data.

### Start Data Capture / Recording
- Click the **Start** button to begin data acquisition.
  - In live mode, data is visualized in real time.
  - In record mode, data is recorded for a fixed duration.

### Stop and Visualize
- Click **Stop and Plot** to end data capture.
- After stopping, download options and visualization buttons (static plots and animations) will be displayed.

### Interactive Analysis
- **Static Plots:**  
  Click to view interactive Plotly figures with zoom, pan, and full-screen capabilities.
- **Animations:**  
  Launch real-time animation windows for dynamic analysis.
- **3D Brain Mesh:**  
  Explore the interactive 3D brain mesh with sensor nodes and sensor group highlights.

### Download CSV Files
- Click **Download CSV** to prompt for a file name and download the raw or processed data.

## File Descriptions

#### 3D Brain Model 

- **aal.nii:**  
  A NIfTI file containing anatomical brain data used to map sensor positions to brain regions.

- **BrainMesh_Ch2_smoothed.nv:**  
  Contains smoothed brain mesh data for rendering a 3D brain surface.

#### ADC Mode

- **adc_animation.py:**  
  A PyQtGraph-based script that reads ADC data from `data/all_groups.csv` and displays a full-screen real-time animation.

- **adc_client.py:**  
  A client application that uses SocketIO and PyQtGraph to receive and display live ADC data interactively.

- **adc_mock_server.py:**  
  A mock ADC server that generates fake sensor data (using, for example, a triangle wave) for demo mode.

- **adc_server.py:**  
  Reads sensor data from the serial port, parses the data, and emits it via SocketIO for live ADC visualization.

#### mBLL Mode

- **mBLL_animation.py:**  
  A PyQtGraph script that reads processed data from `data/processed_output.csv` and displays a full-screen real-time animation of processed mBLL data.

- **mBLL_client.py:**  
  A real-time client that uses Socket.IO and PyQtGraph to display live processed (mBLL) data interactively.

- **mBLL_mock_server.py:**  
  Simulates mBLL data processing by generating dummy packets, processing them, and sending processed concentration data via Socket.IO in demo mode.

- **mBLL_server.py**  
  Reads sensor data from the serial port, processes it using MBLL and CBSI (via NIRSimple), and emits the processed concentration values via Socket.IO.

#### Others

- **fNIRS_processing.py:**  
  (If included) Processes raw ADC data by interleaving sensor blocks, converting intensities to optical density, applying MBLL and CBSI, and writes processed output to CSV files in `data/`.

- **visualizer.py:**  
  The main Flask/SocketIO server that integrates data capture, processing, interactive visualization (including static plots and animations), and control endpoints. It also supports demo mode behavior.

- **fNIRS_processing.py:**  
  (If applicable) Processes raw CSV data (interleaving, OD conversion, MBLL, CBSI) and produces processed output for visualization in record & visualize mode.

- **index.html**  
  The main web interface built with Bootstrap, Plotly, and jQuery. It provides a 3D brain mesh view, sensor group controls, and a mode selection panel for choosing between live ADC readings or record & visualize (ADC and/or mBLL) modes.

#### Data

- **/data Directory:**
  - **all_groups.csv**  
    CSV file that logs the raw ADC sensor data captured by the system.
  - **processed_output.csv**  
    CSV file that contains the processed fNIRS data (after applying MBLL, CBSI, etc.) used for visualization in record & visualize mode.