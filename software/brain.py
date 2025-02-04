from dash import Dash, html, dcc, Input, Output, State
import plotly.graph_objects as go
import numpy as np
import nibabel as nib
from scipy.spatial import cKDTree
import logging
import socketio

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Initialize the Socket.IO client
sio = socketio.Client()

# Connection events
@sio.event
def connect():
    logging.info("Connected to the server.")

@sio.event
def disconnect():
    logging.info("Disconnected from the server.")

# Store activation data
activation_data = None

@sio.event
def data_stream(data):
    """Handle incoming data from the server."""
    # print("Received new data:", data)

    global activation_data
    activation_data = np.array(data['data'])
    if activation_data.ndim == 1:
        activation_data = activation_data.reshape(-1, 1)


# Set up static data and initialization functions
def preload_static_data():
    """ 
    Preload static data.
    """
    # Load static brain mesh data
    coords = np.loadtxt(np.lib.npyio.DataSource().open('BrainMesh_Ch2_smoothed.nv'), skiprows=1, max_rows=53469)
    x, y, z = coords.T

    triangles = np.loadtxt(np.lib.npyio.DataSource().open('BrainMesh_Ch2_smoothed.nv'), skiprows=53471, dtype=int)
    triangles_zero_offset = triangles - 1
    i, j, k = triangles_zero_offset.T

    # Load AAL mapping
    aal_img = nib.load('aal.nii')
    aal_data = aal_img.get_fdata()
    affine = aal_img.affine

    return coords, x, y, z, i, j, k, aal_data, affine


def initialize_sensor_positions(coords):
    """
    Initialize 20 random sensor positions. 
    """
    # Randomly select 20 positions from the available coordinates
    sensor_indices = np.random.choice(coords.shape[0], 20, replace=False)
    return coords[sensor_indices]


def map_points_to_regions(points, affine, aal_data):
    """
    Map points to regions based on their voxel positions.
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
            regions.append(-1)  # Mark as invalid
    return np.array(regions)


coords, x, y, z, i, j, k, aal_data, affine = preload_static_data()
initial_sensor_positions = initialize_sensor_positions(coords)
regions = map_points_to_regions(initial_sensor_positions, affine, aal_data) # Map nodes to regions and find regions to highlight


def filter_coordinates_to_surface(coords, surface_coords, threshold=2.0):
    """ 
    Filter coordinates by proximity to the brain surface.
    """
    tree = cKDTree(surface_coords)
    distances, _ = tree.query(coords)
    return coords[distances <= threshold]


def create_static_brain_mesh():
    """
    Create the static brain mesh plot with a hidden trace for the colorbar.
    """
    fig = go.Figure()

    # Add 3D mesh trace (static)
    fig.add_trace(go.Mesh3d(
        x=x, y=y, z=z,
        i=i, j=j, k=k,
        color='lightpink',
        opacity=0.5,
        name='Brain Mesh',  # Legend entry
        showscale=False  # No colorbar for the mesh
    ))
    
    # Split sensor nodes into Emitters and Detectors
    emitter_positions = initial_sensor_positions[:8]  # First 8 as Emitters
    detector_positions = initial_sensor_positions[8:]  # Remaining 12 as Detectors
    
    # Add Emitters trace (Yellow)
    fig.add_trace(go.Scatter3d(
        x=emitter_positions[:, 0],
        y=emitter_positions[:, 1],
        z=emitter_positions[:, 2],
        mode='markers',
        marker=dict(size=6, color='yellow'),
        name='Emitters',  # Legend entry
        showlegend=True
    ))

    # Add Detectors trace (Blue)
    fig.add_trace(go.Scatter3d(
        x=detector_positions[:, 0],
        y=detector_positions[:, 1],
        z=detector_positions[:, 2],
        mode='markers',
        marker=dict(size=6, color='blue'),
        name='Detectors',  # Legend entry
        showlegend=True
    ))

    # Add a hidden trace to render the colorbar
    fig.add_trace(go.Scatter3d(
        x=[None],  # Hidden data
        y=[None],
        z=[None],
        mode='markers',
        marker=dict(
            size=0,  # Invisible markers
            color=[0],  # Dummy value
            colorscale='Reds',
            cmin=0,
            cmax=5000,
            colorbar=dict(
                title="Activation Level",
                x=0.0,  # Position colorbar on the left
                xanchor='left',
                tickvals=[0, 1000, 2000, 3000, 4000, 5000],
                ticktext=['0', '1000', '2000', '3000', '4000', '5000']
            )
        ),
        hoverinfo='none',  # No hover interaction
        showlegend=False  # Hide from legend
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
    Dynamically update the highlighted regions and sensor node activations with a gradient.
    """

    # print(f"activation data: {activation_data}")
    if activation_data.shape[0] < 20:
        activation_data = np.pad(activation_data, ((0, 20 - activation_data.shape[0]), (0, 0)), mode='constant')

    # Get activation levels for the regions
    activation_levels = activation_data[:20, frame]
    highlighted_regions = np.unique(regions[activation_levels > threshold])

    # Collect highlighted region coordinates
    surface_coords = np.column_stack((x, y, z))
    highlighted_coords = []
    highlighted_values = []  # Store corresponding activation values

    for idx, region in enumerate(highlighted_regions):
        if region <= 0:
            continue

        region_mask = aal_data == region
        region_voxels = np.argwhere(region_mask)
        region_world_coords = nib.affines.apply_affine(affine, region_voxels)

        filtered_coords = filter_coordinates_to_surface(region_world_coords, surface_coords, threshold=2.0)
        if filtered_coords.size > 0:
            highlighted_coords.append(filtered_coords)
            highlighted_values.extend([activation_levels[idx]] * len(filtered_coords))  # Assign colors

    if highlighted_coords:
        highlighted_coords = np.vstack(highlighted_coords)
        highlighted_values = np.array(highlighted_values)

        # Normalize activation values to [0, 1] for color mapping
        min_activation = np.min(highlighted_values)
        max_activation = np.max(highlighted_values)
        normalized_values = (highlighted_values - min_activation) / (max_activation - min_activation + 1e-5)

        # Remove old highlighted regions and add new ones with gradient
        fig.data = [trace for trace in fig.data if trace.name != 'Highlighted Regions']
        fig.add_trace(go.Scatter3d(
            x=highlighted_coords[:, 0],
            y=highlighted_coords[:, 1],
            z=highlighted_coords[:, 2],
            mode='markers',
            marker=dict(
                size=2,
                color=normalized_values,  # Use the normalized activation values
                colorscale='Reds',  # Change to desired gradient
                cmin=0,
                cmax=1,
                opacity=0.1
            ),
            name='Highlighted Regions'
        ))

    return fig


# Define the stacked activation plot function
def create_stacked_activation_plot(activation_data, num_nodes, num_frames):
    fig = go.Figure()
    offset = 5000

    # Reverse the loop order so node 19 is added first
    for node in range(num_nodes - 1, -1, -1):
        fig.add_trace(go.Scatter(
            x=np.arange(num_frames),  # Full time range
            y=activation_data[node, :] + node * offset,  # Maintain offset
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


# Build Dash app
app = Dash(__name__)
static_fig = create_static_brain_mesh()

app.layout = html.Div([
    dcc.Graph(id='brain-mesh-graph', style={'display': 'inline-block'}, figure=static_fig),
    dcc.Graph(id='stacked-activation-graph', style={'display': 'inline-block'}),
    dcc.Store(id='streamed-data', data=None),
    dcc.Interval(id='interval-component', interval=1*1000, n_intervals=0)  # Update every second
])


@app.callback(
    Output('streamed-data', 'data'),
    Input('interval-component', 'n_intervals'),
    State('streamed-data', 'data')
)
def update_store(n_intervals, current_data):
    global activation_data  # Ensure we use the latest activation data

    if activation_data is None:
        return current_data  # Keep old data if nothing new

    # Convert stored data to NumPy array (initialize if empty)
    if current_data is None or 'data' not in current_data:
        stored_array = np.empty((activation_data.shape[0], 0))  # Empty array with correct rows
    else:
        stored_array = np.array(current_data['data'])

    # Ensure stored_array is 2D and matches node count
    if stored_array.shape[0] != activation_data.shape[0]:
        stored_array = np.empty((activation_data.shape[0], 0))  # Reset if mismatch

    # Append the latest activation frame (column-wise)
    new_frame = activation_data[:, -1].reshape(-1, 1)  # Ensure 2D shape
    updated_data = np.hstack([stored_array, new_frame])  # Stack along time axis

    return {'data': updated_data.tolist()}  # Convert back to list for JSON storage


@app.callback(
    [Output('brain-mesh-graph', 'figure'),
     Output('stacked-activation-graph', 'figure')],
    Input('streamed-data', 'data')
)
def update_graphs(data):
    if data is None or 'data' not in data or len(data['data']) == 0:
        return static_fig, go.Figure()

    # Convert stored data back into a NumPy array
    activation_data = np.array(data['data'])
    if activation_data.ndim == 1:
        activation_data = activation_data.reshape(-1, 1)

    num_nodes, num_frames = activation_data.shape

    # Update the brain mesh with the latest frame
    updated_brain_mesh_fig = update_highlighted_regions(static_fig, activation_data, num_frames - 1)

    # Create stacked activation plot with full history
    stacked_fig = create_stacked_activation_plot(activation_data, num_nodes, num_frames)

    return updated_brain_mesh_fig, stacked_fig


if __name__ == '__main__':
    sio.connect('http://localhost:5000', transports=['websocket'])  # Connect to the WebSocket server
    app.run_server(debug=True, use_reloader=False, port=8050)
