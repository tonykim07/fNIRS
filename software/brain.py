from dash import Dash, html, dcc, Input, Output
import plotly.graph_objects as go
import numpy as np
import nibabel as nib
from scipy.spatial import cKDTree
import logging
import requests

# Set up logging
logging.basicConfig(level=logging.DEBUG)


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


coords, x, y, z, i, j, k, aal_data, affine = preload_static_data()


def filter_coordinates_to_surface(coords, surface_coords, threshold=2.0):
    """ 
    Filter coordinates by proximity to the brain surface.
    """
    tree = cKDTree(surface_coords)
    distances, _ = tree.query(coords)
    return coords[distances <= threshold]


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
    
    # Add sensor nodes trace with an explicit legend entry
    fig.add_trace(go.Scatter3d(
        x=[], y=[], z=[],  # Initially empty
        mode='markers',
        marker=dict(size=6, color=[], colorscale='RdBu_r', cmin=0, cmax=5000),
        name='Sensor Nodes',  # Legend entry
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
            colorscale='RdBu_r',
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
    Dynamically update the highlighted regions and sensor node activations.
    """
    # Generate custom sensor points and activation data
    custom_points_indices = np.random.choice(coords.shape[0], 15, replace=False)
    custom_points = coords[custom_points_indices]
    initial_activations = activation_data[custom_points_indices % activation_data.shape[0], frame]

    # Update the sensor node color dynamically (trace 1: sensor nodes)
    fig.data[1].update(
        x=custom_points[:, 0],
        y=custom_points[:, 1],
        z=custom_points[:, 2],
        marker=dict(
            size=6,
            color=initial_activations,
            colorscale='RdBu_r',  # Ensure the same color scale
            cmin=0,
            cmax=5000  # Ensure the color range remains static
        )
    )

    # Map nodes to regions and find regions to highlight
    regions = map_points_to_regions(custom_points, affine, aal_data)
    highlighted_regions = np.unique(regions[initial_activations > threshold])

    # Filter and update highlighted coordinates
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

    # Remove old highlighted regions and add updated ones
    fig.data = [trace for trace in fig.data if trace.name != 'Highlighted Regions']
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
            name='Highlighted Regions'  # Legend entry
        ))
    return fig


# Build Dash app
app = Dash(__name__)
static_fig = create_static_brain_mesh()

app.layout = html.Div([
    dcc.Graph(id='brain-mesh-graph', style={'display': 'inline-block'}, figure=static_fig),
    dcc.Graph(id='stacked-activation-graph', style={'display': 'inline-block'}),
    dcc.Store(id='streamed-data', data=None),
    dcc.Interval(id='fetch-interval', interval=1000, n_intervals=0)
])


@app.callback(
    Output('streamed-data', 'data'),
    Input('fetch-interval', 'n_intervals')
)
def fetch_real_time_data(n_intervals):
    """ 
    Fetch buffered data from the server.
    """
    try:
        response = requests.get('http://localhost:5000/data')
        if response.status_code == 200:
            return {'data': response.json()['data']}
    except Exception as e:
        logging.error(f"Error fetching data from server: {e}")
    return None


@app.callback(
    [Output('brain-mesh-graph', 'figure'),
     Output('stacked-activation-graph', 'figure')],
    Input('streamed-data', 'data')
)
def update_graphs(data):
    """ 
    Update brain region highlights and activation plot.
    """
    if not data or 'data' not in data:
        return static_fig, go.Figure()

    activation_data = np.array(data['data'])
    if activation_data.ndim == 1:
        activation_data = activation_data.reshape(-1, 1)

    frame = activation_data.shape[1] - 1
    updated_brain_mesh_fig = update_highlighted_regions(static_fig, activation_data, frame)

    # Update activation plot
    stacked_fig = go.Figure()
    offset = 5000
    for node, node_data in enumerate(activation_data):
        stacked_fig.add_trace(go.Scatter(
            x=np.arange(node_data.size),
            y=node_data + node * offset,
            mode='lines+markers',
            name=f"Node {node}"
        ))
    stacked_fig.update_layout(
        title="Node Activation Over Time",
        xaxis_title="Time (Frames)",  # X-axis label
        yaxis_title="Activation Level",  # Y-axis label
        height=800,
        width=600,
        showlegend=True
    )
    return updated_brain_mesh_fig, stacked_fig


if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False, port=8050)
