# fNIRS Software Design

This software provides a graphical interface (GUI) for real-time collection, processing, and visualization of fNIRS (functional Near-Infrared Spectroscopy) data. It supports two main modes of operation:

1. **Live Readings Mode**  
   In this mode, only ADC (Analog-to-Digital Converter) data is captured and displayed on live plots. This mode is used for continuous monitoring and is ideal for observing raw signal behavior in real-time.

2. **Record & Visualize Mode**  
   In this mode, the system records data for a user-defined duration. The captured data is then taken through a series of post-processing steps (ex. interleaving sensor blocks, converting intensities to optical density, applying MBLL, and CBSI). Both ADC and mBLL (data processed by applying the Modified Beer-Lambert Law) readings are supported in this mode, and the final results are displayed on interactive graphs when processing is complete.

## Features

- **Two Operating Modes**
  - **Live Readings Mode (ADC Only):**  
    - Captures raw ADC data in real time from the serial port.
    - Displays interactive, real-time plots using PyQtGraph.
  - **Record & Visualize Mode (ADC and mBLL):**  
    - Records data for a specified duration.
    - Applies multiple post-processing steps (ex. interleaving, MBLL, CBSI).
    - Supports visualization of both raw ADC data and processed mBLL data using Plotly.

- **Data Capture and Processing**
  - Communicates with hardware over a serial port.
  - Logs raw ADC data as `all_groups.csv` in the `data/` folder.
  - Saves processed results as `processed_output.csv`.

- **Visualization Options**
  - **Interactive Static Plots (Plotly):**  
    - Supports both ADC and mBLL data.
    - Eight separate plots (one per sensor group) for displaying data recorded in `.csv` files.
    - Each plot includes its own legend and interactive mode bar (zoom, pan, full screen).
  - **Live Animations (PyQtGraph)**  
    - Supports ADC mode only.
    - Eight separate plots (one per sensor group) for displaying live readings as them come in.
  - **3D Brain Mesh**  
    - Interactive model showing brain structure, sensor positions, and group mappings.

- **Download Functionality:**
  - Export raw or processed CSV data using a simple popup prompt.

- **User-Friendly Interface:**
  - A web interface built with Bootstrap, jQuery, Plotly, and Socket.IO.
  - Control panels for sensor group selection, MUX/emitter control, and mode selection.

- **Demo Mode:**
  - A mock ADC server simulates data for testing or demonstrations.
  - Skips real data processing to simplify setup.


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

3. **Set COM Port (Serial Device):**

   - On Windows:
   Open PowerShell and run:
   ```bash
   Get-WMIObject Win32_SerialPort
   ```
      Look for something like COM3, COM4, etc.

   - On macOS/Linux:
   ```bash
   ls /dev/tty.*
   ```
      Look for something like /dev/tty.usbmodemXXXX or /dev/ttyUSB0.

   **Update the COM port path in config.py:**
   ```bash
   # Update this line with your actual port
   SERIAL_PORT = "COM3"       # Windows example
   # or
   SERIAL_PORT = "/dev/tty.usbmodem1234"   # macOS/Linux example
   ```
     
4. **Running the System:**

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

### Step 1: Choose Operating Mode
- **Live Readings:** for real-time, unprocessed data (ADC Only).
- **Record & Visualize:** to capture and process data for analysis (ADC and/or mBLL).

### Step 2: Start Data Capture / Recording
- Click the **Start** button to begin data acquisition.
  - In live mode, data is visualized in real time.
  - In record mode, data is recorded for a fixed duration, and logged to .csv files.

### Step 3: Stop and Visualize (mBLL Mode)
- Click **Stop and Plot** to end data capture.
- When data capsture is stopped, download options and visualization buttons for rendering static plots and animations will be displayed.

### Step 4: Analyze & Export
- **Static Plots:**  
  Click to view interactive Plotly figures with zoom, pan, and full-screen capabilities.
- **Animations:**  
  Launch real-time animation windows for dynamic analysis.
- **3D Brain Mesh:**  
  Explore the interactive 3D brain mesh with sensor nodes and sensor group highlights.
- **Download CSV Files:**  
  Click **Download CSV** to prompt for a file name and download the raw or processed data.

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
  Processes raw ADC data by interleaving sensor blocks, converting intensities to optical density, applying MBLL and CBSI, and writes processed output to CSV files in `data/`.

- **visualizer.py:**  
  The main Flask/SocketIO server that integrates data capture, processing, interactive visualization (including static plots and animations), and control endpoints. It also supports demo mode behavior.

- **index.html**  
  The main web interface built with Bootstrap, Plotly, and jQuery. It provides a 3D brain mesh view, sensor group controls, and a mode selection panel for choosing between live ADC readings or record & visualize (ADC and/or mBLL) modes.

#### Data

- **/data Directory:**
  - **all_groups.csv**  
    CSV file that logs the raw ADC sensor data captured by the system.
  - **processed_output.csv**  
    CSV file that contains the processed fNIRS data (after applying MBLL, CBSI, etc.) used for visualization in record & visualize mode.
