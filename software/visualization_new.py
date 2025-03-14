import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, send_from_directory, request
from flask_socketio import SocketIO
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import numpy as np
import nibabel as nib
from scipy.spatial import cKDTree
import logging
from data_handler import get_latest_data, sio

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# -------------------- Brain Mesh Functions --------------------
def preload_static_data():
    """
    Preload static data.
    Loads brain mesh coordinates, triangles, AAL mapping, and affine.
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
    Randomly select 20 sensor positions from available coordinates.
    """
    sensor_indices = np.random.choice(coords.shape[0], 20, replace=False)
    return coords[sensor_indices]

def map_points_to_regions(points, affine, aal_data):
    """
    Map points to brain regions based on voxel positions.
    """
    voxel_coords = np.round(np.linalg.inv(affine) @ np.column_stack((points, np.ones(points.shape[0]))).T).T[:, :3]
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

# Preload brain mesh and mapping data
coords, x, y, z, i, j, k, aal_data, affine = preload_static_data()
initial_sensor_positions = initialize_sensor_positions(coords)
regions = map_points_to_regions(initial_sensor_positions, affine, aal_data)

def create_static_brain_mesh(emitter_states):
    """
    Create a static 3D brain mesh plot with sensor nodes.
    """
    fig = go.Figure()

    # Add brain mesh (static)
    fig.add_trace(go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        color='lightpink',
        opacity=0.5,
        name='Brain Mesh',
        showscale=False
    ))

    # Split sensor nodes: first 16 are emitters, remaining 4 are detectors.
    emitter_positions = initial_sensor_positions[:16]
    detector_positions = initial_sensor_positions[16:]

    emitter_colors = ['yellow' if state else 'gray' for state in emitter_states]
    fig.add_trace(go.Scatter3d(
        x=emitter_positions[:, 0],
        y=emitter_positions[:, 1],
        z=emitter_positions[:, 2],
        mode='markers',
        marker=dict(size=6, color=emitter_colors),
        name='Emitters',
        showlegend=True
    ))

    fig.add_trace(go.Scatter3d(
        x=detector_positions[:, 0],
        y=detector_positions[:, 1],
        z=detector_positions[:, 2],
        mode='markers',
        marker=dict(size=6, color='blue'),
        name='Detectors',
        showlegend=True
    ))

    # Hidden trace for the colorbar
    fig.add_trace(go.Scatter3d(
        x=[None],
        y=[None],
        z=[None],
        mode='markers',
        marker=dict(
            size=0,
            color=[0],
            colorscale='Reds',
            cmin=0,
            cmax=5000,
            colorbar=dict(
                title="Activation Level",
                x=0.0,
                xanchor='left',
                tickvals=[0, 1000, 2000, 3000, 4000, 5000],
                ticktext=['0', '1000', '2000', '3000', '4000', '5000']
            )
        ),
        hoverinfo='none',
        showlegend=False
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
    Update brain mesh with highlighted regions based on activation data.
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

# -------------------- Sensor Group Chart Functions --------------------
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
    Create a Plotly figure for a single sensor group without an embedded title.
    
    Parameters:
      activation_data: NumPy array with shape (48, num_timeframes)
      group_index: integer from 0 to 7 indicating which group (each group = 6 rows)
    
    Returns:
      A Plotly figure with:
        - x-axis labeled "Timeframe"
        - y-axis labeled "Concentration (M)"
        - 6 traces with custom colors and a separate legend.
    """
    num_frames = activation_data.shape[1]
    time = np.arange(num_frames)
    
    # Colors for the 6 channels in order.
    channel_colors = ["darkblue", "lightblue", "darkgreen", "lightgreen", "darkred", "lightcoral"]
    
    # Extract data for the specific sensor group.
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
    # Remove the embedded title; only include axis labels and legend.
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
emitter_states = [True] * 16
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
def update_graphs():
    latest_data = get_latest_data()
    if latest_data is None:
        return jsonify({'brain_mesh': None, 'stacked_activation': None})
    
    activation_data = np.array(latest_data)
    if activation_data.ndim == 1:
        activation_data = activation_data.reshape(-1, 1)
    
    num_nodes, num_frames = activation_data.shape

    # Update the brain mesh (static with highlighted regions based on the latest frame)
    updated_brain_mesh_fig = update_highlighted_regions(create_static_brain_mesh(emitter_states), activation_data, num_frames - 1)
    # Create a stacked activation plot (as a fallback or additional visualization)
    stacked_fig = create_stacked_activation_plot(activation_data, num_nodes, num_frames)
    # Create one figure per sensor group for separate charts (if needed on a different endpoint)
    grouped_activation = {}
    for group_index in range(8):
        grouped_activation[f"group{group_index+1}"] = create_single_group_plot(activation_data, group_index).to_json()
    
    return jsonify({
        'brain_mesh': updated_brain_mesh_fig.to_json(),
        'stacked_activation': stacked_fig.to_json(),
        'grouped_activation': grouped_activation
    })

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
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    sio.connect('http://localhost:5000', transports=['websocket'])
    socketio.run(app, debug=True, use_reloader=False, port=8050)
