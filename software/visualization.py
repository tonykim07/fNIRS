import eventlet
import serial
import json
eventlet.monkey_patch()

import logging
from flask import Flask, jsonify, send_from_directory, request
from flask_socketio import SocketIO
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import numpy as np
import nibabel as nib
from scipy.spatial import cKDTree
from data_handler import get_latest_data, sio

# Set up logging
logging.basicConfig(level=logging.DEBUG)
ser = serial.Serial('/dev/tty.usbmodem205D388A47311', baudrate=9600, timeout=1) 

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# -------------------- Helper Functions for Custom Mesh --------------------

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

# -------------------- Brain Mesh Functions --------------------

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

# Preload data.
coords, x, y, z, i, j, k, aal_data, affine = preload_static_data()
emitter_positions, emitter_angles, detector_positions, detector_angles = initialize_sensor_positions(coords)
combined_positions = np.vstack((emitter_positions, detector_positions))
regions = map_points_to_regions(combined_positions, affine, aal_data)

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

# -------------------- Brain Mesh Visualization Functions --------------------

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
        title="3D Brain Mesh with Sensor Nodes",
        scene=dict(xaxis_visible=False, yaxis_visible=False, zaxis_visible=False),
        width=800,
        height=800,
        showlegend=True
    )
    return fig

def update_highlighted_regions(fig, activation_data, frame, threshold=3000):
    """
    Update the brain mesh with highlighted regions based on activation data.
    """
    if activation_data.shape[0] < 20:
        activation_data = np.pad(activation_data, ((0, 20 - activation_data.shape[0]), (0, 0)), mode='constant')
    activation_levels = activation_data[:20, frame]
    highlighted_regions = np.unique(regions[activation_levels > threshold])
    surface_coords = np.column_stack((x, y, z))
    highlighted_coords = []
    highlighted_values = []
    for idx, region in enumerate(highlighted_regions):
        if region <= 0:
            continue
        region_mask = aal_data == region
        region_voxels = np.argwhere(region_mask)
        region_world_coords = nib.affines.apply_affine(affine, region_voxels)
        filtered_coords = filter_coordinates_to_surface(region_world_coords, surface_coords, threshold=2.0)
        if filtered_coords.size > 0:
            highlighted_coords.append(filtered_coords)
            highlighted_values.extend([activation_levels[idx]] * len(filtered_coords))
    if highlighted_coords:
        highlighted_coords = np.vstack(highlighted_coords)
        highlighted_values = np.array(highlighted_values)
        min_activation = np.min(highlighted_values)
        max_activation = np.max(highlighted_values)
        normalized_values = (highlighted_values - min_activation) / (max_activation - min_activation + 1e-5)
        fig.data = [trace for trace in fig.data if trace.name != 'Highlighted Regions']
        fig.add_trace(go.Scatter3d(
            x=highlighted_coords[:, 0],
            y=highlighted_coords[:, 1],
            z=highlighted_coords[:, 2],
            mode='markers',
            marker=dict(
                size=2,
                color=normalized_values,
                colorscale='Reds',
                cmin=0,
                cmax=1,
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

# -------------------- Activation Plot Functions (unchanged) --------------------

def create_grouped_activation_plot(activation_data):
    """
    Create a grouped (stacked) plot with 8 subplots (each for a sensor group).
    Each group (6 channels) is plotted with custom colors.
    """
    num_frames = activation_data.shape[1]
    time = np.arange(num_frames)
    num_groups = 8  # 48 channels / 6 per group

    channel_colors = ["darkblue", "lightblue", "darkgreen", "lightgreen", "darkred", "lightcoral"]

    fig = make_subplots(
        rows=num_groups, cols=1, shared_xaxes=True, vertical_spacing=0.02,
        subplot_titles=[f"Sensor Group {i+1}" for i in range(num_groups)]
    )

    for group in range(num_groups):
        group_data = activation_data[group*6:(group+1)*6, :]
        for channel in range(6):
            color = channel_colors[channel]
            detector = f"D{channel//2 + 1}"
            modality = "hbo" if channel % 2 == 0 else "hbr"
            trace_name = f"{detector}, {modality}"
            fig.add_trace(
                go.Scatter(
                    x=time,
                    y=group_data[channel, :],
                    mode='lines+markers',
                    name=trace_name,
                    line=dict(color=color),
                    marker=dict(color=color),
                    showlegend=True
                ),
                row=group+1, col=1
            )
        fig.update_yaxes(title_text="Concentration (M)", row=group+1, col=1)

    fig.update_xaxes(title_text="Timeframe", row=num_groups, col=1)
    fig.update_layout(
        title="Grouped Activation Data (8 groups, 6 channels each)",
        height=300 * num_groups,
        showlegend=True
    )
    return fig

def create_single_group_plot(activation_data, group_index):
    """
    Create a Plotly figure for a single sensor group.
    """
    num_frames = activation_data.shape[1]
    time = np.arange(num_frames)
    
    channel_colors = ["darkblue", "lightblue", "darkgreen", "lightgreen", "darkred", "lightcoral"]
    
    group_data = activation_data[group_index*6:(group_index+1)*6, :]
    
    fig = go.Figure()
    for channel in range(6):
        color = channel_colors[channel]
        detector = f"D{channel//2 + 1}"
        modality = "hbo" if channel % 2 == 0 else "hbr"
        trace_name = f"{detector}, {modality}"
        fig.add_trace(go.Scatter(
            x=time,
            y=group_data[channel, :],
            mode='lines+markers',
            name=trace_name,
            line=dict(color=color),
            marker=dict(color=color)
        ))
    fig.update_layout(
        xaxis_title="Timeframe",
        yaxis_title="Concentration (M)",
        showlegend=True,
        margin=dict(l=5, r=5, t=5, b=5)
    )
    return fig

def create_stacked_activation_plot(activation_data, num_nodes, num_frames):
    """
    Create a stacked activation plot for all detectors.
    """
    fig = go.Figure()
    offset = 5000

    for node in range(num_nodes - 1, -1, -1):
        fig.add_trace(go.Scatter(
            x=np.arange(num_frames),
            y=activation_data[node, :] + node * offset,
            mode='lines+markers',
            name=f"Detector {node}",
            line=dict(width=2),
            marker=dict(size=6)
        ))

    fig.update_yaxes(
        title_text="Activation Level (Stacked)",
        tickmode="array",
        tickvals=[node * offset + offset / 2 for node in range(num_nodes)],
        ticktext=[f"Detector {node}" for node in range(num_nodes)]
    )
    fig.update_xaxes(title_text="Time (frames)")
    fig.update_layout(
        title="Detector Activation Levels Over Time",
        height=800,
        width=600,
        showlegend=True
    )
    return fig

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

@app.route('/data')
def data():
    latest_data = get_latest_data()
    if latest_data is None:
        return jsonify({'data': []})
    return jsonify({'data': latest_data.tolist()})

@app.route('/update_graphs')
def update_graphs_route():
    latest_data = get_latest_data()
    if latest_data is None:
        return jsonify({'brain_mesh': None, 'stacked_activation': None})
    
    activation_data = np.array(latest_data)
    if activation_data.ndim == 1:
        activation_data = activation_data.reshape(-1, 1)
    
    num_nodes, num_frames = activation_data.shape

    brain_mesh_fig = create_static_brain_mesh([True]*len(emitter_positions))
    # brain_mesh_fig = update_highlighted_regions(brain_mesh_fig, activation_data, num_frames - 1)
    stacked_fig = create_stacked_activation_plot(activation_data, num_nodes, num_frames)
    
    grouped_activation = {}
    for group_index in range(8):
        grouped_activation[f"group{group_index+1}"] = create_single_group_plot(activation_data, group_index).to_json()
    
    return jsonify({
        'brain_mesh': brain_mesh_fig.to_json(),
        'stacked_activation': stacked_fig.to_json(),
        'grouped_activation': grouped_activation
    })

@app.route('/select_group/<int:group_id>')
def select_group(group_id):
    brain_mesh_fig = create_static_brain_mesh([True]*len(emitter_positions))
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
    ser.write(data_bytes)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    sio.connect('http://127.0.0.1:5000', transports=['websocket'])
    socketio.run(app, debug=True, use_reloader=False, port=8050)
