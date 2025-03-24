import eventlet
import serial
import json
eventlet.monkey_patch()

import signal
import time
import logging
import subprocess
from flask import Flask, jsonify, send_from_directory, request
from flask_socketio import SocketIO
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import numpy as np
import nibabel as nib
import threading
from queue import Queue
from scipy.spatial import cKDTree
import socketio as sio_client_lib

# Set up logging
logging.basicConfig(level=logging.DEBUG)
# ser = serial.Serial('/dev/tty.usbmodem205D388A47311', baudrate=9600, timeout=1) 

# -----------------------------------------------------
# Flask and Socket.IO Setup
# -----------------------------------------------------
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# -----------------------------------------------------
# Global Variables and Data Queue (for processed packets)
# -----------------------------------------------------
current_mode = 'default'  # default mode when the app starts
# Data queue to store incoming data
data_queue = Queue(maxsize=20)
data_lock = threading.Lock()  # Create a lock for synchronization

# -----------------------------------------------------
# Upstream Socket.IO Client Setup (receives processed_data)
# -----------------------------------------------------
sio_client = sio_client_lib.Client()

@sio_client.event
def connect():
    logging.info("Connected to upstream server for data.")

@sio_client.event
def disconnect():
    logging.info("Disconnected from upstream server.")

@sio_client.event
def processed_data(data):
    """Called when a new processed data packet is received."""
    activation_data = np.array(data['concentrations'])
    # logging.info(f"Received new data: {activation_data}")
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
    with data_lock:
        if not data_queue.empty():
            return list(data_queue.queue)[-1]
    return None

# Signal handler to exit the application gracefully.
def signal_handler(sig, frame):
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
    
    The parameter `angle` rotates the circle by that offset (in radians) before aligning with the normal.
    """
    theta = np.linspace(0, 2*np.pi, resolution, endpoint=False) + angle
    circle_bottom = np.column_stack((radius * np.cos(theta), radius * np.sin(theta), np.zeros(resolution)))
    circle_top = np.column_stack((radius * np.cos(theta), radius * np.sin(theta), np.full(resolution, height)))
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
    voxel_coords = np.round(np.linalg.inv(affine) @ np.column_stack((points, np.ones(points.shape[0]))).T).T[:, :3]
    voxel_coords = voxel_coords.astype(int)
    regions = []
    for voxel in voxel_coords:
        if (0 <= voxel[0] < aal_data.shape[0] and 0 <= voxel[1] < aal_data.shape[1] and 0 <= voxel[2] < aal_data.shape[2]):
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

def create_static_brain_mesh(emitter_states):
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
        vertices_cap, faces_cap = create_flat_cylinder_mesh(pos, norm, radius=10, height=2, resolution=20, angle=angle)
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
        vertices_cap, faces_cap = create_flat_cylinder_mesh(pos, norm, radius=10, height=2, resolution=20, angle=angle)
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


# Preload data.
coords, x, y, z, i, j, k, aal_data, affine = preload_static_data()
emitter_positions, emitter_angles, detector_positions, detector_angles = initialize_sensor_positions(coords)
combined_positions = np.vstack((emitter_positions, detector_positions))
regions = map_points_to_regions(combined_positions, affine, aal_data)
brain_mesh_fig = create_static_brain_mesh([True]*8)


# Define sensor groupings.
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

# Define a mapping: for each hbo sensor (0-23) give its corresponding index in combined_positions (0-23)
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
    filtered_coords = filter_coordinates_to_surface(region_world_coords, surface_coords, threshold=2.0)
    region_filtered[reg] = filtered_coords



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

# -----------------------------------------------------
# Graph Update Function (called when new data arrives)
# -----------------------------------------------------
# INFO:root:update_highlighted_regions took 1.4346 seconds, which is 99.94% of update_graphs
def update_graphs(latest_packet):
    global brain_mesh_fig
    total_start = time.perf_counter()  # start of the function
    logging.info(f"Updating brain mesh with new data: {latest_packet}")
    
    if latest_packet is None:
        return

    # Process incoming data
    activation_data = np.array(latest_packet)
    if activation_data.ndim == 1:
        activation_data = activation_data.reshape(-1, 1)
    hbo_values = activation_data[::2]  # Now an array of 24 values

    # Measure the time taken by update_highlighted_regions
    update_start = time.perf_counter()
    brain_mesh_fig = update_highlighted_regions(brain_mesh_fig, hbo_values)
    update_end = time.perf_counter()

    total_end = time.perf_counter()
    
    overall_time = total_end - total_start
    update_time = update_end - update_start
    percentage = (update_time / overall_time) * 100 if overall_time else 0

    logging.info(f"update_highlighted_regions took {update_time:.4f} seconds, which is {percentage:.2f}% of update_graphs")
    
    socketio.emit('brain_mesh_update', {'brain_mesh': brain_mesh_fig.to_json()})

# -------------------- Global State --------------------

emitter_states = [True] * len(emitter_positions)
control_data = {
    'emitter_control_override_enable': 0,
    'emitter_control_state': 0,
    'emitter_pwm_control_h': 0,
    'emitter_pwm_control_l': 0,
    'mux_control_override_enable': 0,
    'mux_control_state': 0
}

# -------------------- Flask Routes --------------------

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# @app.route('/data')
# def data():
#     latest_data = get_latest_data()
#     if latest_data is None:
#         return jsonify({'data': []})
#     return jsonify({'data': latest_data.tolist()})

@app.route('/update_graphs')
def update_graphs_route():
    return jsonify({
        'brain_mesh': brain_mesh_fig.to_json(),
    })

@app.route('/select_group/<int:group_id>')
def select_group(group_id):
    brain_mesh_fig = highlight_sensor_group(brain_mesh_fig, group_id)
    return jsonify({'brain_mesh': brain_mesh_fig.to_json()})

@app.route('/update_emitter_states', methods=['POST'])
def update_emitter_states():
    global emitter_states
    data = request.json
    emitter_states = data['emitter_states']
    return jsonify({'status': 'success'})

@app.route('/update_control_data', methods=['POST'])
def update_control_data():
    global control_data
    data = request.json
    control_data.update(data)
    logging.info(f"Control data updated: {control_data}")
    values_list = list(control_data.values())
    data_bytes = bytes(values_list)
    # ser.write(data_bytes)
    return jsonify({'status': 'success'})

@app.route('/set_mode/<mode>')
def set_mode(mode):
    global current_mode
    if mode.lower() == 'adc':
        current_mode = 'adc'
        subprocess.Popen(['python', 'adc_server.py'])
        time.sleep(1)  # allow server to initialize
        subprocess.Popen(['python', 'adc_client.py'])
        return jsonify({'status': 'ADC mode started'})
    elif mode.lower() == 'mbll':
        current_mode = 'mBLL'
        # subprocess.Popen(['python', 'mBLL_client.py'])
        return jsonify({'status': 'mBLL mode selected, not implemented yet'})
    else:
        return jsonify({'status': 'Invalid mode selected'}), 400

# -----------------------------------------------------
# Start the Upstream Client in a Background Thread
# -----------------------------------------------------
def run_socketio_client():
    # Connect to your upstream server (e.g., the one in server.py)
    sio_client.connect('http://127.0.0.1:5000', transports=['websocket'])
    sio_client.wait()

# -----------------------------------------------------
# Main: Start the Flask/Socket.IO server and client thread
# -----------------------------------------------------
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # Start the Socket.IO client that receives processed data.
    threading.Thread(target=run_socketio_client, daemon=True).start()
    # Run the Flask-SocketIO server on port 8050.
    socketio.run(app, debug=True, use_reloader=False, port=8050)