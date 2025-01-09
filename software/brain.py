from dash import Dash, html, dcc, Input, Output
import plotly.graph_objects as go
import numpy as np
import nibabel as nib
from scipy.spatial import cKDTree
import logging
import requests

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load the AAL mapping
def load_aal_mapping(aal_file):
    aal_img = nib.load(aal_file)
    aal_data = aal_img.get_fdata()
    return aal_data, aal_img.affine

# Filter coordinates by proximity to the brain surface
def filter_coordinates_to_surface(coords, surface_coords, threshold=2.0):
    tree = cKDTree(surface_coords)
    distances, _ = tree.query(coords)
    return coords[distances <= threshold]

# Map points to regions based on their voxel positions
def map_points_to_regions(points, affine, aal_data):
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

# Combine everything into a brain mesh plot function
def create_brain_mesh_with_dynamic_highlight(aal_file, activation_data, frame, activation_threshold=3000):
    try:
        # Load and prepare dataset for brain mesh
        coords = np.loadtxt(np.lib.npyio.DataSource().open('BrainMesh_Ch2_smoothed.nv'), skiprows=1, max_rows=53469)
        x, y, z = coords.T

        triangles = np.loadtxt(np.lib.npyio.DataSource().open('BrainMesh_Ch2_smoothed.nv'), skiprows=53471, dtype=int)
        triangles_zero_offset = triangles - 1
        i, j, k = triangles_zero_offset.T

        # Load AAL mapping and affine transformation
        aal_data, affine = load_aal_mapping(aal_file)

        # Generate random sensor nodes and activation data
        num_nodes = 15
        custom_points_indices = np.random.choice(coords.shape[0], num_nodes, replace=False)
        custom_points = coords[custom_points_indices]
        initial_activations = activation_data[custom_points_indices % activation_data.shape[0], frame]  # Ensure correct indexing

        # Map nodes to regions
        regions = map_points_to_regions(custom_points, affine, aal_data)

        # Find regions to highlight
        highlighted_regions = np.unique(regions[initial_activations > activation_threshold])

        # Filter region coordinates for highlighting
        surface_coords = np.column_stack((x, y, z))
        highlighted_coords = []
        for region in highlighted_regions:
            if region <= 0:  # Skip invalid regions
                continue
            region_mask = aal_data == region
            region_voxels = np.argwhere(region_mask)
            region_world_coords = nib.affines.apply_affine(affine, region_voxels)
            filtered_coords = filter_coordinates_to_surface(region_world_coords, surface_coords, threshold=2.0)
            highlighted_coords.append(filtered_coords)
        highlighted_coords = np.vstack(highlighted_coords) if highlighted_coords else np.empty((0, 3))

        # Create a 3D brain mesh plot
        fig = go.Figure()

        # Add 3D mesh trace
        fig.add_trace(go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            color='lightpink', opacity=0.5, name='Brain Mesh', showscale=False
        ))

        # Add scatter trace for sensor nodes
        fig.add_trace(go.Scatter3d(
            x=custom_points[:, 0], 
            y=custom_points[:, 1], 
            z=custom_points[:, 2],
            mode='markers',
            marker=dict(
                size=6,
                color=initial_activations,
                colorscale='RdBu_r',  # Reversed color scale (Blue -> Red)
                colorbar=dict(
                    title="Activation Level",
                    x=0.0,  # Position colorbar on the left
                    xanchor='left',
                    tickvals=[0, 1000, 2000, 3000, 4000, 5000],
                    ticktext=['0', '1000', '2000', '3000', '4000', '5000']
                )
            ),
            name='Sensor Nodes'
        ))

        # Add scatter trace for highlighted regions
        if highlighted_coords.size > 0:
            fig.add_trace(go.Scatter3d(
                x=highlighted_coords[:, 0], 
                y=highlighted_coords[:, 1], 
                z=highlighted_coords[:, 2],
                mode='markers',
                marker=dict(
                    size=2,
                    color='red',
                    opacity=0.8
                ),
                name='Highlighted Regions'
            ))

        fig.update_layout(
            title=f"3D Brain Mesh with Dynamic Region Highlighting (Threshold: {activation_threshold})",
            scene=dict(xaxis_visible=False, yaxis_visible=False, zaxis_visible=False),
            width=800,
            height=800
        )
        return fig
    except Exception as e:
        logging.error(f"Error creating brain mesh: {e}")
        return go.Figure()


# Build Dash app
app = Dash(__name__)

app.layout = html.Div([
    dcc.Graph(id='brain-mesh-graph', style={'display': 'inline-block'}),
    dcc.Graph(id='stacked-activation-graph', style={'display': 'inline-block'}),
    dcc.Store(id='streamed-data', data=None),  # Store for streamed data
    dcc.Interval(id='fetch-interval', interval=1000, n_intervals=0)  # Trigger every second
])

# app.layout = html.Div([
# ], style={'display': 'flex', 'justify-content': 'center'})

@app.callback(
    Output('streamed-data', 'data'),
    [Input('fetch-interval', 'n_intervals')],
    [Input('streamed-data', 'data')]
)
def fetch_real_time_data(n_intervals, stored_data):
    try:
        response = requests.get('http://localhost:5000/data')
        if response.status_code == 200:
            new_data = response.json()['data']
            if stored_data:
                stored_array = np.array(stored_data['data'])
                new_array = np.array(new_data)
                
                # Ensure the shape matches the fixed node count
                if stored_array.shape[0] == len(new_data):
                    combined_data = np.column_stack([stored_array, new_array])
                else:
                    combined_data = np.array(new_data).reshape(-1, 1)  # Reset if inconsistent
            else:
                combined_data = np.array(new_data).reshape(-1, 1)
            return {'data': combined_data.tolist()}
    except Exception as e:
        logging.error(f"Error fetching data from server: {e}")
    return {'data': stored_data['data'] if stored_data else []}



def create_stacked_activation_plot(activation_data):
    try:
        fig = go.Figure()
        offset = 5000
        num_nodes, num_frames = activation_data.shape

        for node in range(num_nodes):
            fig.add_trace(go.Scatter(
                x=np.arange(num_frames),  # All frames
                y=activation_data[node, :] + node * offset,
                mode='lines+markers',
                name=f"Node {node}",
                marker=dict(size=6),
                line=dict(width=2)
            ))

        fig.update_yaxes(
            title_text="Activation Level (Stacked)",
            tickmode="array",
            tickvals=[node * offset + offset / 2 for node in range(num_nodes)],
            ticktext=[f"Node {node}" for node in range(num_nodes)]
        )
        fig.update_xaxes(title_text="Time (frames)")

        fig.update_layout(
            title="Node Activation Over Time",
            height=800,
            width=600,
            showlegend=True
        )

        return fig
    except Exception as e:
        logging.error(f"Error creating stacked activation plot: {e}")
        return go.Figure()


@app.callback(
    [Output('brain-mesh-graph', 'figure'),
     Output('stacked-activation-graph', 'figure')],
    [Input('streamed-data', 'data'),
     Input('fetch-interval', 'n_intervals')]
)
def update_graphs(data, n_intervals):
    if not data or 'data' not in data or not data['data']:
        return go.Figure(), go.Figure()

    try:
        activation_data = np.array(data['data'])
        if activation_data.ndim == 1:
            activation_data = activation_data.reshape(-1, 1)

        frame = n_intervals % activation_data.shape[1]  # Loop through frames
        brain_mesh_fig = create_brain_mesh_with_dynamic_highlight(
            aal_file='aal.nii',
            activation_data=activation_data,
            frame=frame,
            activation_threshold=3000
        )
        stacked_fig = create_stacked_activation_plot(activation_data)
        return brain_mesh_fig, stacked_fig
    except Exception as e:
        logging.error(f"Error updating graphs: {e}")
        return go.Figure(), go.Figure()


if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False, port=8050)
