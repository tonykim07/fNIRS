"""
visualizer.py
==================
This script visualizes fNIRS data in real-time using Flask and Plotly.
It connects to an upstream server for data and allows for interaction
through a web interface.
It also provides a demo mode for testing without actual data.
The script includes functions for creating a 3D brain mesh, processing
activation data, and updating the visualization.
"""

import sys
import signal
import time
import os
import logging
import subprocess
import threading
from queue import Queue

import serial
from flask import Flask, jsonify, send_from_directory, request
from flask_socketio import SocketIO
import plotly.graph_objs as go
from plotly.offline import plot
import numpy as np
import nibabel as nib
from scipy.spatial import cKDTree
import socketio as sio_client_lib
import pandas as pd

import eventlet
eventlet.monkey_patch()
import config

# Check command-line arguments for a demo flag.
demo_mode = any(arg.lower() == 'demo' for arg in sys.argv[1:])
if demo_mode:
    logging.info("Demo mode is active.")
else:
    logging.info("Demo mode is not active.")
    ser = serial.Serial(
        config.SERIAL_PORT,
        baudrate=config.BAUD_RATE,
        timeout=config.TIMEOUT
    )

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# -----------------------------------------------------
# Flask and Socket.IO Setup
# -----------------------------------------------------
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# -----------------------------------------------------
# Global Variables and Data Queue (for processed packets)
# -----------------------------------------------------
data_queue = Queue(maxsize=20)
data_lock = threading.Lock()  # Create a lock for synchronization
reader_thread = None

# -----------------------------------------------------
# Upstream Socket.IO Client Setup (receives processed_data)
# -----------------------------------------------------
sio_client = sio_client_lib.Client()

@sio_client.event
def connect():
    """
    Called when the client connects to the upstream server.
    """
    logging.info("Connected to upstream server for data.")

@sio_client.event
def disconnect():
    """
    Called when the client disconnects from the upstream server.
    """
    logging.info("Disconnected from upstream server.")

@sio_client.event
def processed_data(data):
    """Called when a new processed data packet is received."""
    activation_data = np.array(data['concentrations'])
    logging.info(f"Received new data: {activation_data}")
    if activation_data.ndim == 1:
        activation_data = activation_data.reshape(-1, 1)
    with data_lock:
        if data_queue.full():
            data_queue.get()  # remove oldest if full
        data_queue.put(activation_data)

    # Immediately update the graph if in mBLL mode.
    if current_mode == 'mBLL':
        update_graphs(activation_data)

def get_most_recent_packet():
    """
    Get the most recent packet from the data queue.
    """
    with data_lock:
        if not data_queue.empty():
            return list(data_queue.queue)[-1]
    return None

def signal_handler():
    """
    Graceful Exit Handler
    """
    print("Exiting gracefully...")
    if sio_client.connected:
        sio_client.disconnect()
    app.quit()

# Register the signal handler for SIGINT.
signal.signal(signal.SIGINT, signal_handler)

# -----------------------------------------------------
# fNIRS Data Processing and Brain Mesh Functions
# -----------------------------------------------------
def compute_vertex_normals(vertices, triangles):
    """Compute an approximate normal for each vertex in the mesh."""
    normals = np.zeros(vertices.shape, dtype=float)
    for tri in triangles:
        v0, v1, v2 = vertices[tri[0]], vertices[tri[1]], vertices[tri[2]]
        n = np.cross(v1 - v0, v2 - v0)
        norm = np.linalg.norm(n)
        if norm:
            n = n / norm
        normals[tri[0]] += n
        normals[tri[1]] += n
        normals[tri[2]] += n
    norms = np.linalg.norm(normals, axis=1)[:, None]
    normals = normals / (norms + 1e-8)
    return normals

def create_flat_cylinder_mesh(center, normal, radius, height=1.0, resolution=20, angle=0.0):
    """
    Create vertices and faces for a flat cylinder (like a bottle cap) centered at origin,
    oriented along the z-axis, then rotated to align with the given normal and translated to center.
    
    `angle` rotates the circle by that offset (in radians) before aligning with normal.
    """
    theta = np.linspace(0, 2*np.pi, resolution, endpoint=False) + angle
    circle_bottom = np.column_stack((radius * np.cos(theta),
                                     radius * np.sin(theta),
                                     np.zeros(resolution)))
    circle_top = np.column_stack((radius * np.cos(theta),
                                  radius * np.sin(theta),
                                  np.full(resolution, height)))
    vertices = np.vstack((circle_bottom, circle_top))

    faces = []
    for i in range(resolution):
        next_i = (i + 1) % resolution
        faces.append([i, next_i, i + resolution])
        faces.append([next_i, next_i + resolution, i + resolution])

    bottom_center_index = len(vertices)
    vertices = np.vstack((vertices, np.array([0, 0, 0])))
    for i in range(resolution):
        next_i = (i+1) % resolution
        faces.append([bottom_center_index, next_i, i])

    top_center_index = len(vertices)
    vertices = np.vstack((vertices, np.array([0, 0, height])))
    for i in range(resolution):
        next_i = (i+1) % resolution
        faces.append([top_center_index, i+resolution, next_i+resolution])

    def rotation_matrix_from_vectors(a, b):
        a = a / np.linalg.norm(a)
        b = b / np.linalg.norm(b)
        v = np.cross(a, b)
        c = np.dot(a, b)
        if np.linalg.norm(v) < 1e-8:
            return np.eye(3)
        s = np.linalg.norm(v)
        kmat = np.array([[0, -v[2], v[1]],
                         [v[2], 0, -v[0]],
                         [-v[1], v[0], 0]])
        R = np.eye(3) + kmat + np.dot(kmat, kmat) * ((1 - c) / (s**2))
        return R

    R = rotation_matrix_from_vectors(np.array([0, 0, 1]), normal)
    vertices_rotated = np.dot(vertices, R.T)
    vertices_translated = vertices_rotated + center
    return vertices_translated, faces


def preload_static_data():
    """
    Load brain mesh data from file.
    """
    coords = np.loadtxt('BrainMesh_Ch2_smoothed.nv', skiprows=1, max_rows=53469)
    x, y, z = coords.T
    triangles = np.loadtxt('BrainMesh_Ch2_smoothed.nv', skiprows=53471, dtype=int)
    triangles_zero_offset = triangles - 1
    i, j, k = triangles_zero_offset.T
    aal_img = nib.load('aal.nii')
    aal_data = aal_img.get_fdata()
    affine = aal_img.affine
    return coords, x, y, z, i, j, k, aal_data, affine

def initialize_sensor_positions(coords):
    """
    Define custom sensor positions, assign each a node type and rotation angle.
    Returns separate arrays for emitters and detectors.
    """
    # Emitter positions (8 nodes)
    emitter_positions = np.array([
        [-55.0, 21.0, 25.0],
        [-38.0, -47.0, 60.0],
        [16.0, -15.0, 78.0],
        [19.0, -100.0, -4.0],
        [-11.0, -75.0, 57.0],
        [-6.0, 59.0, 36.0],
        [52.0, -51.0, 51.0],
        [55.0, 21.0, 25.0],
    ])
    emitter_angles = np.array([0, 0, 0, 0, 0, 0, 0, 0])

    # Detector positions (16 nodes)
    detector_positions = np.array([
        [-38.0, 54.0, 18.0],    # Group 1
        [-65.0, -29.0, 33.0],

        [-43.0, -5.0, 58.0],    # Group 2
        [-51.0, -69.0, 29.0],

        [15.0, 28.0, 60.0],     # Group 3
        [-15.0, 28.0, 60.0],

        [20.0, -95.0, 30.0],    # Group 4
        [-20.0, -95.0, 30.0],

        [14.0, -43.0, 80.0],    # Group 5
        [-15.0, -41.0, 78.0],

        [15.0, 70.0, -3.0],     # Group 6
        [-15.0, 70.0, -3.0],

        [50.0, -74.0, 21.0],    # Group 7
        [66.0, -22.0, 38.0],

        [41.0, -13.0, 66.0],    # Group 8
        [43.0, 50.0, 22.0],
    ])
    detector_angles = np.zeros(len(detector_positions))

    return emitter_positions, emitter_angles, detector_positions, detector_angles

def map_points_to_regions(points, affine, aal_data):
    """
    Map sensor positions to brain regions.
    """
    voxel_coords = np.round(np.linalg.inv(affine) @
                            np.column_stack((points, np.ones(points.shape[0]))).T).T[:, :3]
    voxel_coords = voxel_coords.astype(int)
    regions = []
    for voxel in voxel_coords:
        if (0 <= voxel[0] < aal_data.shape[0] and
            0 <= voxel[1] < aal_data.shape[1] and
            0 <= voxel[2] < aal_data.shape[2]):
            regions.append(aal_data[tuple(voxel)])
        else:
            regions.append(-1)
    return np.array(regions)

def filter_coordinates_to_surface(coords, surface_coords, threshold=2.0):
    """
    Filter coordinates that are close to the brain surface.
    """
    tree = cKDTree(surface_coords)
    distances, _ = tree.query(coords)
    return coords[distances <= threshold]

def create_static_brain_mesh():
    """
    Create a static 3D brain mesh with sensor nodes.
    Emitters are rendered as flat cylindrical caps (default white) and detectors as markers (black).
    """
    fig = go.Figure()

    # Add the brain mesh.
    fig.add_trace(go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        color='lightpink',
        opacity=0.5,
        name='Brain Mesh',
        showscale=False
    ))

    # Build KD-tree and compute vertex normals.
    vertices = np.column_stack((x, y, z))
    triangles = np.column_stack((i, j, k))
    vertex_normals = compute_vertex_normals(vertices, triangles)
    tree = cKDTree(vertices)

    # Plot Emitters.
    _, emitter_indices = tree.query(emitter_positions)
    emitter_normals = vertex_normals[emitter_indices]
    for pos, angle, norm in zip(emitter_positions, emitter_angles, emitter_normals):
        vertices_cap, faces_cap = create_flat_cylinder_mesh(pos,
                                                            norm,
                                                            radius=10,
                                                            height=2,
                                                            resolution=20,
                                                            angle=angle)
        faces_cap = np.array(faces_cap)
        i_cap, j_cap, k_cap = faces_cap[:, 0], faces_cap[:, 1], faces_cap[:, 2]
        fig.add_trace(go.Mesh3d(
            x=vertices_cap[:, 0],
            y=vertices_cap[:, 1],
            z=vertices_cap[:, 2],
            i=i_cap, j=j_cap, k=k_cap,
            color='white',  # Default color for emitters.
            opacity=1,
            name='Emitter'
        ))

    # Plot Detectors.
    _, detector_indices = tree.query(detector_positions)
    detector_normals = vertex_normals[detector_indices]
    for pos, angle, norm in zip(detector_positions, detector_angles, detector_normals):
        vertices_cap, faces_cap = create_flat_cylinder_mesh(pos,
                                                            norm,
                                                            radius=10,
                                                            height=2,
                                                            resolution=20,
                                                            angle=angle)
        faces_cap = np.array(faces_cap)
        i_cap, j_cap, k_cap = faces_cap[:, 0], faces_cap[:, 1], faces_cap[:, 2]
        fig.add_trace(go.Mesh3d(
            x=vertices_cap[:, 0],
            y=vertices_cap[:, 1],
            z=vertices_cap[:, 2],
            i=i_cap, j=j_cap, k=k_cap,
            color='black',
            opacity=1,
            name='Detector'
        ))

    fig.update_layout(
        # title="3D Brain Mesh with Sensor Nodes",
        scene=dict(xaxis_visible=False, yaxis_visible=False, zaxis_visible=False),
        width=800,
        height=800,
        showlegend=True
    )
    return fig


# -----------------------------------------------------
# Global Variables
# -----------------------------------------------------

# Preload data.
coords, x, y, z, i, j, k, aal_data, affine = preload_static_data()
emitter_positions, emitter_angles, detector_positions,detector_angles = initialize_sensor_positions(coords)
combined_positions = np.vstack((emitter_positions, detector_positions))
regions = map_points_to_regions(combined_positions, affine, aal_data)
brain_mesh_fig = create_static_brain_mesh()
emitter_states = [True] * len(emitter_positions)

# Global variable to store accumulated activation data
activation_history = None
processing_proc = None
running_processes = []
current_mode = None
current_sources = []

# Define control data (emitter and mux control states)
control_data = {
    'emitter_control_override_enable': 0,
    'emitter_control_state': 0,
    'emitter_pwm_control_h': 0,
    'emitter_pwm_control_l': 0,
    'mux_control_override_enable': 0,
    'mux_control_state': 0
}

# Define sensor groupings
sensor_groups = [
    {"group_id": 1, "emitter_index": 0, "detector_indices": [0, 1]},
    {"group_id": 2, "emitter_index": 1, "detector_indices": [2, 3]},
    {"group_id": 3, "emitter_index": 2, "detector_indices": [4, 5]},
    {"group_id": 4, "emitter_index": 3, "detector_indices": [6, 7]},
    {"group_id": 5, "emitter_index": 4, "detector_indices": [8, 9]},
    {"group_id": 6, "emitter_index": 5, "detector_indices": [10, 11]},
    {"group_id": 7, "emitter_index": 6, "detector_indices": [12, 13]},
    {"group_id": 8, "emitter_index": 7, "detector_indices": [14, 15]},
]

# Define a mapping: for each hbo sensor (0-23)
sensor_mapping = [
    0, 8, 9,    # Group 1: emitter0, detector0, detector1
    1, 10, 11,  # Group 2: emitter1, detector2, detector3
    2, 12, 13,  # Group 3: emitter2, detector4, detector5
    3, 14, 15,  # Group 4: emitter3, detector6, detector7
    4, 16, 17,  # Group 5: emitter4, detector8, detector9
    5, 18, 19,  # Group 6: emitter5, detector10, detector11
    6, 20, 21,  # Group 7: emitter6, detector12, detector13
    7, 22, 23   # Group 8: emitter7, detector14, detector15
]


# -----------------------------------------------------
# Precomputation for Region Mappings
# -----------------------------------------------------

# Precompute sensor-to-region mapping (length 24)
sensor_region = [regions[sensor_mapping[i]] for i in range(len(sensor_mapping))]

# Precompute region-to-sensor indices for regions of interest.
region_to_sensor_indices = {}
for i, reg in enumerate(sensor_region):
    if reg > 0:
        region_to_sensor_indices.setdefault(reg, []).append(i)

# Precompute filtered coordinates for each region (using a constant threshold, e.g., 2.0)
surface_coords = np.column_stack((x, y, z))
region_filtered = {}
# Get the unique region IDs from the sensors (only those > 0)
unique_sensor_regions = np.unique([r for r in sensor_region if r > 0])
for reg in unique_sensor_regions:
    region_mask = aal_data == reg
    region_voxels = np.argwhere(region_mask)
    region_world_coords = nib.affines.apply_affine(affine, region_voxels)
    filtered_coords = filter_coordinates_to_surface(region_world_coords,
                                                    surface_coords,
                                                    threshold=2.0)
    region_filtered[reg] = filtered_coords


# -----------------------------------------------------
# Helper Functions for Updating the Brain Mesh
# -----------------------------------------------------
def update_highlighted_regions(fig, hbo_values):
    """
    Update the brain mesh with highlighted regions based on activation data.
    Uses precomputed sensor-to-region mapping, region-to-sensor indices, and
    precomputed filtered coordinates.
    """
    # Collect region IDs from sensors that are activated (hbo value < 0)
    highlighted_region_ids = []
    for i, value in enumerate(hbo_values):
        if value < 0 and sensor_region[i] > 0:
            highlighted_region_ids.append(sensor_region[i])
    highlighted_region_ids = np.unique(highlighted_region_ids)

    highlighted_coords = []
    highlighted_values = []
    for reg in highlighted_region_ids:
        filtered_coords = region_filtered.get(reg)
        if filtered_coords is not None and filtered_coords.size > 0:
            # Compute average sensor value from the sensors mapping to this region.
            indices = region_to_sensor_indices.get(reg, [])
            if indices:
                avg_val = np.mean([hbo_values[i] for i in indices])
            else:
                avg_val = 0
            highlighted_coords.append(filtered_coords)
            highlighted_values.extend([avg_val] * len(filtered_coords))

    if highlighted_coords:
        highlighted_coords = np.vstack(highlighted_coords)
        highlighted_values = np.array(highlighted_values)
        # Remove old highlight traces and add new trace.
        fig.data = [trace for trace in fig.data if trace.name != 'Highlighted Regions']
        fig.add_trace(go.Scatter3d(
            x=highlighted_coords[:, 0],
            y=highlighted_coords[:, 1],
            z=highlighted_coords[:, 2],
            mode='markers',
            marker=dict(
                size=2,
                color='red',
                opacity=0.1
            ),
            name='Highlighted Regions'
        ))
    return fig


def highlight_sensor_group(fig, group_id):
    """
    Highlight a sensor group by drawing extra traces on the figure.
    Removes any previous group highlight, then highlights the selected group.
    """
    # Remove previous group highlights.
    fig.data = [trace for trace in fig.data if trace.name != "Group Highlight"]

    group = next((g for g in sensor_groups if g["group_id"] == group_id), None)
    if group is None:
        return fig

    emitter_idx = group["emitter_index"]
    detector_indices = group["detector_indices"]

    emitter_coord = emitter_positions[emitter_idx]
    detector_coords = detector_positions[detector_indices]

    # Highlight emitter.
    fig.add_trace(go.Scatter3d(
        x=[emitter_coord[0]],
        y=[emitter_coord[1]],
        z=[emitter_coord[2]],
        mode='markers',
        marker=dict(size=14, color='yellow', symbol='circle'),
        showlegend=False,
        name="Group Highlight"
    ))

    # Highlight detectors.
    fig.add_trace(go.Scatter3d(
        x=detector_coords[:, 0],
        y=detector_coords[:, 1],
        z=detector_coords[:, 2],
        mode='markers',
        marker=dict(size=12, color='yellow', symbol='circle'),
        showlegend=False,
        name="Group Highlight"
    ))

    # Draw lines connecting emitter to detectors.
    for det in detector_coords:
        fig.add_trace(go.Scatter3d(
            x=[emitter_coord[0], det[0]],
            y=[emitter_coord[1], det[1]],
            z=[emitter_coord[2], det[2]],
            mode='lines',
            line=dict(color='yellow', width=4),
            showlegend=False,
            name="Group Highlight"
        ))
    return fig


def update_graphs(latest_packet):
    """
    Update the brain mesh with new data from the latest packet.
    This function is called when new data is received from the upstream server.
    """
    global brain_mesh_fig
    if latest_packet is None:
        return

    # Process incoming data
    activation_data = np.array(latest_packet)
    if activation_data.ndim == 1:
        activation_data = activation_data.reshape(-1, 1)
    hbo_values = activation_data[::2]  # Now an array of 24 values

    brain_mesh_fig = update_highlighted_regions(brain_mesh_fig, hbo_values)
    socketio.emit('brain_mesh_update', {
        'brain_mesh': brain_mesh_fig.to_json()
    })


def stop_serial_reader():
    """
    Stop the serial reader thread gracefully.
    """
    global ser
    try:
        ser.close()
        logging.info("Serial connection closed for record mode.")
    except Exception as e:
        logging.error(f"Error closing serial port: {e}")

def reinit_serial_connection():
    """
    Reinitialize the serial connection.
    """
    global ser
    try:
        ser = serial.Serial(
            config.SERIAL_PORT,
            baudrate=config.BAUD_RATE,
            timeout=config.TIMEOUT
        )
        logging.info("Serial connection reinitialized.")
    except Exception as e:
        logging.error(f"Error reinitializing serial port: {e}")


# -------------------- Flask Routes --------------------

@app.route('/')
def index():
    """
    Serve the main HTML page.
    This page contains the Plotly graph and other UI elements.
    """
    return send_from_directory('.', 'index.html')

@app.route('/update_graphs')
def update_graphs_route():
    """
    Update the brain mesh with new data from the latest packet.
    This function is called when new data is received from the upstream server.
    """
    return jsonify({
        'brain_mesh': brain_mesh_fig.to_json(),
    })

@app.route('/select_group/<int:group_id>')
def select_group(group_id):
    """
    Highlight a specific sensor group on the brain mesh.
    """
    global brain_mesh_fig
    brain_mesh_fig = highlight_sensor_group(brain_mesh_fig, group_id)
    return jsonify({'brain_mesh': brain_mesh_fig.to_json()})

@app.route('/update_emitter_states', methods=['POST'])
def update_emitter_states():
    """
    Update emitter states based on the received JSON data.
    """
    global emitter_states
    data = request.json
    emitter_states = data['emitter_states']
    return jsonify({'status': 'success'})

@app.route('/update_control_data', methods=['POST'])
def update_control_data():
    """
    Update control data for the emitter and mux.
    This function receives a JSON object with control data and updates the
    global control_data dictionary. It also sends the updated data to the serial
    port if not in demo mode.
    """
    global control_data
    data = request.json
    control_data.update(data)
    print(f"Control data updated: {control_data}")
    values_list = list(control_data.values())
    data_bytes = bytes(values_list)
    if not demo_mode:
        ser.write(data_bytes)
    return jsonify({'status': 'success'})

@app.route('/start_processing', methods=['POST'])
def start_processing():
    """
    Start the processing based on the selected mode.
    """
    global processing_proc, current_mode, current_sources
    data = request.get_json()
    mode = data.get('mode')      # "live" or "record"
    current_sources = data.get('sources', [])

    # Live readings mode is available for ADC only.
    if mode == 'live':
        current_mode = 'adc_live'
        # In demo mode, use the mock server.
        if demo_mode:
            proc1 = subprocess.Popen(['python', 'adc_mock_server.py'])
            time.sleep(1)  # allow server to initialize
            proc2 = subprocess.Popen(['python', 'adc_client.py'])
            running_processes.extend([proc1, proc2])
        else:
            stop_serial_reader()
            proc = subprocess.Popen(['python', 'adc_live.py'])
            running_processes.append(proc)
        return jsonify({'status': 'ADC mode started'})

    # Record & visualize mode is available for both ADC and mBLL.
    if mode == 'record':
        current_mode = 'record'
        # In demo mode, skip starting fNIRS_processing.py.
        if demo_mode:
            return jsonify({'status': 'demo mode active, processing skipped'})
        try:
            # Stop the visualizer's serial reading
            stop_serial_reader()
            # Now launch fnirs_processing.py which creates its own serial connection.
            proc = subprocess.Popen(['python', 'fNIRS_processing.py'])
            running_processes.extend([proc])
            return jsonify({'status': 'processing started'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Invalid mode selected.'}), 400


@app.route('/stop_processing', methods=['POST'])
def stop_processing():
    """
    Stop the processing and reinitialize the serial connection.
    This function sends a SIGUSR1 signal to the subprocesses to stop them gracefully.
    """
    global running_processes
    # Send SIGUSR1 to each subprocess so that they stop gracefully.
    for proc in running_processes:
        os.kill(proc.pid, signal.SIGUSR1)
    running_processes = []
    # Wait a short time to ensure fnirs_processing.py has closed its connection.
    time.sleep(1)
    # Reinitialize the serial connection and restart the reader.
    try:
        if not ser.is_open:
            reinit_serial_connection()
        else:
            logging.info("Serial connection is already open; no need to reinitialize.")
    except Exception as e:
        logging.error(f"Error checking serial connection: {e}")
    return jsonify({'status': 'processing stop signal sent and serial reinitialized'})


@app.route('/download/<source>')
def download_file(source):
    """
    Download a CSV file based on the source parameter.
    The source can be 'ADC' or 'mBLL'.
    """
    # Map each source to its CSV file name (adjust as needed)
    csv_map = {
        'ADC': 'all_groups.csv',
        'mBLL': 'processed_output.csv'
    }
    filename = csv_map.get(source)
    if not filename:
        return jsonify({'status': 'error', 'message': 'Invalid source.'}), 400
    # Retrieve the file name provided by the user, or default to the filename.
    download_name = request.args.get('filename', filename)
    data_dir = os.path.dirname(os.path.abspath(__file__))

    return send_from_directory(data_dir, filename, as_attachment=True, download_name=download_name)


@app.route('/view_static/ADC')
def view_static_adc_plotly():
    """
    Generate static HTML for ADC data visualization.
    This function creates a Plotly figure for each group and returns the HTML.
    """
    # Load CSV data.
    data_dir = 'sample_data' if demo_mode else '.'
    csv_path = os.path.join(data_dir, 'all_groups.csv')
    df = pd.read_csv(csv_path)

    # Build separate figures for each group.
    figures_html = ""
    for i in range(8):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x = df["Time (s)"],
            y = df[f"G{i}_Short"],
            mode = 'lines',
            name = 'Short'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time (s)"],
            y = df[f"G{i}_Long1"],
            mode = 'lines',
            name = 'Long1'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time (s)"],
            y = df[f"G{i}_Long2"],
            mode = 'lines',
            name = 'Long2'
        ))

        fig.update_layout(
            title = f"Group {i+1}",
            xaxis_title = "Time (s)",
            yaxis_title = "Value",
            autosize=True,
            margin=dict(l=50, r=50, t=50, b=50)
        )

        # Generate an HTML div for this figure without including Plotly.js again.
        div = plot(fig,
                   output_type='div',
                   include_plotlyjs=False,
                   config={'displayModeBar': True,
                           'responsive': True})
        figures_html += f"<div style='margin-bottom:50px;'>{div}</div>"

    # Include Plotly.js only once in the head.
    html = f"""
    <html>
      <head>
         <title>ADC Static Plots</title>
         <meta charset="UTF-8">
         <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
         <style>
           body {{
             margin: 0;
             padding: 20px;
             background-color: #eef2f7;
             font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
           }}
         </style>
      </head>
      <body>
         {figures_html}
      </body>
    </html>
    """
    return html

@app.route('/view_static/mBLL')
def view_static_mbll_plotly():
    """
    Load and visualize mBLL data from CSV file.
    This function generates a static HTML page with Plotly figures.
    """
    # Load CSV data
    data_dir = 'sample_data' if demo_mode else '.'
    csv_path = os.path.join(data_dir, 'processed_output.csv')
    df = pd.read_csv(csv_path)

    # Build separate figures for each group.
    figures_html = ""
    for i in range(1, 9):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D1_hbo"],
            mode = 'lines',
            name = 'D1_hbo'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D1_hbr"],
            mode = 'lines',
            name = 'D1_hbr'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D2_hbo"],
            mode = 'lines',
            name = 'D2_hbo'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D2_hbr"],
            mode = 'lines',
            name = 'D2_hbr'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D3_hbo"],
            mode = 'lines',
            name = 'D3_hbo'
        ))
        fig.add_trace(go.Scatter(
            x = df["Time"],
            y = df[f"S{i}_D3_hbr"],
            mode = 'lines',
            name = 'D3_hbr'
        ))

        fig.update_layout(
            title = f"Group {i}",
            xaxis_title = "Time (s)",
            # yaxis_title = "Value",
            autosize=True,
            margin=dict(l=50, r=50, t=50, b=50)
        )

        # Generate an HTML div for this figure without including Plotly.js again.
        div = plot(fig,
                   output_type='div',
                   include_plotlyjs=False,
                   config={'displayModeBar': True, 'responsive': True})
        figures_html += f"<div style='margin-bottom:50px;'>{div}</div>"

    # Include Plotly.js only once in the head.
    html = f"""
    <html>
      <head>
         <title>ADC Static Plots</title>
         <meta charset="UTF-8">
         <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
         <style>
           body {{
             margin: 0;
             padding: 20px;
             background-color: #eef2f7;
             font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
           }}
         </style>
      </head>
      <body>
         {figures_html}
      </body>
    </html>
    """
    return html


@app.route('/view_animation/ADC')
def view_animation_adc():
    """
    Launch the ADC animation script in a separate process.
    """
    args = [sys.executable, 'adc_animation.py']
    if demo_mode:
        args.append('demo')
    subprocess.Popen(args)
    return ('', 204)

@app.route('/view_animation/mBLL')
def view_animation_mbll():
    """
    Launch the mBLL animation script in a separate process.
    """
    subprocess.Popen([sys.executable, 'mBLL_animation.py'])
    args = [sys.executable, 'mBLL_animation.py']
    if demo_mode:
        args.append('demo')
    subprocess.Popen(args)
    return ('', 204)

# -----------------------------------------------------
# Start the Upstream Client in a Background Thread
# -----------------------------------------------------
def run_socketio_client():
    """
    Run the Socket.IO client in a separate thread.
    """
    connected = False
    while not connected:
        try:
            logging.info("Attempting to connect to server at http://127.0.0.1:5000")
            sio_client.connect('http://127.0.0.1:5000', transports=['websocket'])
            connected = True
            sio_client.wait()  # This will keep the client running
        except Exception as e:
            logging.error(f"Connection failed: {e}. Retrying in 1 second...")
            time.sleep(1)

# -----------------------------------------------------
# Main: Start the Flask/Socket.IO server and client thread
# -----------------------------------------------------
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # Run the Flask-SocketIO server on port 8050.
    socketio.run(app, debug=True, use_reloader=False, port=8050)
